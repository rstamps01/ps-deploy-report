"""
VAST As-Built Report Generator - API Handler Module

This module provides comprehensive VAST API integration for the As-Built Report Generator.
It implements session-based authentication, retry logic, and enhanced data collection
capabilities including rack heights and cluster PSNT integration.

Features:
- Session-based authentication with automatic refresh
- Retry logic with exponential backoff for transient failures
- Enhanced data collection (80% automation target)
- Rack height collection for CBoxes and DBoxes
- Cluster PSNT (Product Serial Number Tracking) integration
- Backward compatibility for older cluster versions
- Comprehensive error handling and graceful degradation

Author: Manus AI
Date: September 12, 2025
"""

import requests
import time
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger


class VastApiVersion(Enum):
    """Supported VAST API versions."""
    V5_1 = "5.1"
    V5_2 = "5.2"
    V5_3 = "5.3"
    V7 = "7"


@dataclass
class VastClusterInfo:
    """Data class for cluster information."""
    name: str
    guid: str
    version: str
    state: str
    license: str
    psnt: Optional[str] = None  # Enhanced: Product Serial Number Tracking


@dataclass
class VastHardwareInfo:
    """Data class for hardware information with enhanced rack positioning."""
    node_id: str
    node_type: str  # 'cnode' or 'dnode'
    model: str
    serial_number: str
    rack_position: Optional[int] = None  # Enhanced: Rack height/U position
    status: str = "unknown"


class VastApiError(Exception):
    """Custom exception for VAST API errors."""
    pass


class VastApiHandler:
    """
    VAST API Handler for comprehensive data collection.

    This class provides a robust interface to the VAST REST API with enhanced
    capabilities for automated data collection, including rack positioning
    and cluster support tracking integration.
    """

    def __init__(self, cluster_ip: str, username: str, password: str,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the VAST API handler.

        Args:
            cluster_ip (str): IP address of the VAST Management Service
            username (str): Username for authentication
            password (str): Password for authentication
            config (Dict[str, Any], optional): Configuration dictionary
        """
        self.logger = get_logger(__name__)
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password
        self.config = config or {}

        # API configuration
        self.api_config = self.config.get('api', {})
        self.timeout = self.api_config.get('timeout', 30)
        self.max_retries = self.api_config.get('max_retries', 3)
        self.retry_delay = self.api_config.get('retry_delay', 2)
        self.verify_ssl = self.api_config.get('verify_ssl', True)
        self.api_version = self.api_config.get('version', 'v7')

        # Session management
        self.session = None
        self.base_url = f"https://{cluster_ip}/api/{self.api_version}/"
        self.authenticated = False
        self.cluster_version = None
        self.supported_features = set()

        # Enhanced API capabilities
        self.rack_height_supported = False
        self.psnt_supported = False

        self.logger.info(f"Initialized VAST API handler for cluster {cluster_ip}")

    def _setup_session(self) -> requests.Session:
        """Set up requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'VAST-As-Built-Report-Generator/1.0'
        })

        return session

    def authenticate(self) -> bool:
        """
        Authenticate with the VAST cluster using multiple methods.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            self.logger.info(f"Authenticating with VAST cluster at {self.cluster_ip}")

            if not self.session:
                self.session = self._setup_session()

            # Try different authentication methods
            auth_methods = [
                self._try_basic_auth,
                self._try_session_auth,
                self._try_jwt_auth
            ]

            for auth_method in auth_methods:
                try:
                    if auth_method():
                        self.authenticated = True
                        self.logger.info("Successfully authenticated with VAST cluster")
                        self._detect_cluster_capabilities()
                        return True
                except Exception as e:
                    self.logger.debug(f"Authentication method failed: {e}")
                    continue

            self.logger.error("All authentication methods failed")
            return False

        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {e}")
            return False

    def _try_basic_auth(self) -> bool:
        """Try basic authentication."""
        try:
            # Test basic auth with a simple endpoint
            response = self.session.get(
                urljoin(self.base_url, 'vms/'),
                auth=(self.username, self.password),
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            return response.status_code == 200
        except Exception:
            return False

    def _try_session_auth(self) -> bool:
        """Try session-based authentication."""
        try:
            # Prepare authentication data
            auth_data = {
                'username': self.username,
                'password': self.password
            }

            # Attempt authentication
            response = self.session.post(
                urljoin(self.base_url, 'sessions/'),
                json=auth_data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            return response.status_code == 200
        except Exception:
            return False

    def _try_jwt_auth(self) -> bool:
        """Try JWT token authentication."""
        try:
            # First get a JWT token
            auth_data = {
                'username': self.username,
                'password': self.password
            }

            response = self.session.post(
                urljoin(self.base_url, 'jwt/'),
                json=auth_data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )

            if response.status_code == 200:
                token_data = response.json()
                if 'access' in token_data:
                    # Set the JWT token in the session headers
                    self.session.headers.update({
                        'Authorization': f"Bearer {token_data['access']}"
                    })
                    return True
            return False
        except Exception:
            return False

    def _detect_cluster_capabilities(self) -> None:
        """Detect cluster version and supported features."""
        try:
            # Get cluster info to detect version
            cluster_info = self._make_api_request('vms/')
            if cluster_info and 'version' in cluster_info:
                self.cluster_version = cluster_info['version']
                self.logger.info(f"Detected cluster version: {self.cluster_version}")

                # Determine supported features based on version
                self._determine_supported_features()
            else:
                self.logger.warning("Could not detect cluster version, using conservative feature set")
                self._determine_supported_features()

        except Exception as e:
            self.logger.warning(f"Could not detect cluster capabilities: {e}")
            self._determine_supported_features()

    def _determine_supported_features(self) -> None:
        """Determine which enhanced features are supported."""
        # Enhanced features available in API v7 with cluster 5.3+
        if self.cluster_version and self.cluster_version >= "5.3":
            self.rack_height_supported = True
            self.psnt_supported = True
            self.logger.info("Enhanced features enabled: rack heights and PSNT")
        else:
            self.rack_height_supported = False
            self.psnt_supported = False
            self.logger.info("Enhanced features disabled: older cluster version")

    def _make_api_request(self, endpoint: str, method: str = 'GET',
                         data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make an authenticated API request with retry logic.

        Args:
            endpoint (str): API endpoint (relative to base URL)
            method (str): HTTP method
            data (Dict, optional): Request data for POST/PUT
            params (Dict, optional): Query parameters

        Returns:
            Optional[Dict]: API response data or None if failed
        """
        if not self.authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return None

        try:
            url = urljoin(self.base_url, endpoint)

            # Make request with appropriate method
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout, verify=self.verify_ssl)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=self.timeout, verify=self.verify_ssl)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, timeout=self.timeout, verify=self.verify_ssl)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=self.timeout, verify=self.verify_ssl)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle response
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                self.logger.warning("Session expired, attempting re-authentication")
                if self.authenticate():
                    # Retry the request
                    return self._make_api_request(endpoint, method, data, params)
                else:
                    self.logger.error("Re-authentication failed")
                    return None
            elif response.status_code == 404:
                self.logger.warning(f"Endpoint not found: {endpoint}")
                return None
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during API request: {e}")
            return None

    def get_cluster_info(self) -> Optional[VastClusterInfo]:
        """
        Get comprehensive cluster information including enhanced PSNT.

        Returns:
            Optional[VastClusterInfo]: Cluster information or None if failed
        """
        try:
            self.logger.info("Collecting cluster information")

            cluster_data = self._make_api_request('vms/')
            if not cluster_data:
                self.logger.error("Failed to retrieve cluster information")
                return None

            # Extract basic cluster information
            cluster_info = VastClusterInfo(
                name=cluster_data.get('name', 'Unknown'),
                guid=cluster_data.get('guid', 'Unknown'),
                version=cluster_data.get('version', 'Unknown'),
                state=cluster_data.get('state', 'Unknown'),
                license=cluster_data.get('license', 'Unknown')
            )

            # Enhanced: Add PSNT if supported
            if self.psnt_supported and 'psnt' in cluster_data:
                cluster_info.psnt = cluster_data['psnt']
                self.logger.info(f"Retrieved cluster PSNT: {cluster_info.psnt}")
            else:
                self.logger.info("PSNT not available for this cluster version")

            self.logger.info(f"Cluster: {cluster_info.name} (v{cluster_info.version})")
            return cluster_info

        except Exception as e:
            self.logger.error(f"Error collecting cluster information: {e}")
            return None

    def get_cnode_details(self) -> List[VastHardwareInfo]:
        """
        Get CNode details including enhanced rack positioning.

        Returns:
            List[VastHardwareInfo]: List of CNode information
        """
        try:
            self.logger.info("Collecting CNode details")

            cnodes_data = self._make_api_request('cnodes/')
            if not cnodes_data:
                self.logger.error("Failed to retrieve CNode information")
                return []

            cnodes = []
            for cnode in cnodes_data:
                hardware_info = VastHardwareInfo(
                    node_id=cnode.get('id', 'Unknown'),
                    node_type='cnode',
                    model=cnode.get('model', 'Unknown'),
                    serial_number=cnode.get('serial_number', 'Unknown'),
                    status=cnode.get('state', 'unknown')
                )

                # Enhanced: Add rack position if supported
                if self.rack_height_supported and 'index_in_rack' in cnode:
                    hardware_info.rack_position = cnode['index_in_rack']
                    self.logger.debug(f"CNode {hardware_info.node_id} rack position: {hardware_info.rack_position}")
                else:
                    self.logger.debug(f"CNode {hardware_info.node_id} rack position not available")

                cnodes.append(hardware_info)

            self.logger.info(f"Retrieved {len(cnodes)} CNode details")
            return cnodes

        except Exception as e:
            self.logger.error(f"Error collecting CNode details: {e}")
            return []

    def get_dnode_details(self) -> List[VastHardwareInfo]:
        """
        Get DNode details including enhanced rack positioning.

        Returns:
            List[VastHardwareInfo]: List of DNode information
        """
        try:
            self.logger.info("Collecting DNode details")

            dnodes_data = self._make_api_request('dnodes/')
            if not dnodes_data:
                self.logger.error("Failed to retrieve DNode information")
                return []

            dnodes = []
            for dnode in dnodes_data:
                hardware_info = VastHardwareInfo(
                    node_id=dnode.get('id', 'Unknown'),
                    node_type='dnode',
                    model=dnode.get('model', 'Unknown'),
                    serial_number=dnode.get('serial_number', 'Unknown'),
                    status=dnode.get('state', 'unknown')
                )

                # Enhanced: Add rack position if supported
                if self.rack_height_supported and 'index_in_rack' in dnode:
                    hardware_info.rack_position = dnode['index_in_rack']
                    self.logger.debug(f"DNode {hardware_info.node_id} rack position: {hardware_info.rack_position}")
                else:
                    self.logger.debug(f"DNode {hardware_info.node_id} rack position not available")

                dnodes.append(hardware_info)

            self.logger.info(f"Retrieved {len(dnodes)} DNode details")
            return dnodes

        except Exception as e:
            self.logger.error(f"Error collecting DNode details: {e}")
            return []

    def get_network_configuration(self) -> Dict[str, Any]:
        """
        Get network configuration including DNS, NTP, and VIP pools.

        Returns:
            Dict[str, Any]: Network configuration data
        """
        try:
            self.logger.info("Collecting network configuration")

            network_config = {}

            # DNS configuration
            dns_data = self._make_api_request('dns/')
            if dns_data:
                network_config['dns'] = dns_data
                self.logger.debug("Retrieved DNS configuration")
            else:
                self.logger.warning("DNS configuration not available")
                network_config['dns'] = None

            # NTP configuration
            ntp_data = self._make_api_request('ntps/')
            if ntp_data:
                network_config['ntp'] = ntp_data
                self.logger.debug("Retrieved NTP configuration")
            else:
                self.logger.warning("NTP configuration not available")
                network_config['ntp'] = None

            # VIP pools
            vippool_data = self._make_api_request('vippools/')
            if vippool_data:
                network_config['vippools'] = vippool_data
                self.logger.debug("Retrieved VIP pool configuration")
            else:
                self.logger.warning("VIP pool configuration not available")
                network_config['vippools'] = None

            self.logger.info("Network configuration collection completed")
            return network_config

        except Exception as e:
            self.logger.error(f"Error collecting network configuration: {e}")
            return {}

    def get_logical_configuration(self) -> Dict[str, Any]:
        """
        Get logical configuration including tenants, views, and policies.

        Returns:
            Dict[str, Any]: Logical configuration data
        """
        try:
            self.logger.info("Collecting logical configuration")

            logical_config = {}

            # Tenants
            tenants_data = self._make_api_request('tenants/')
            if tenants_data:
                logical_config['tenants'] = tenants_data
                self.logger.debug("Retrieved tenants configuration")
            else:
                self.logger.warning("Tenants configuration not available")
                logical_config['tenants'] = None

            # Views
            views_data = self._make_api_request('views/')
            if views_data:
                logical_config['views'] = views_data
                self.logger.debug("Retrieved views configuration")
            else:
                self.logger.warning("Views configuration not available")
                logical_config['views'] = None

            # View policies
            viewpolicies_data = self._make_api_request('viewpolicies/')
            if viewpolicies_data:
                logical_config['viewpolicies'] = viewpolicies_data
                self.logger.debug("Retrieved view policies configuration")
            else:
                self.logger.warning("View policies configuration not available")
                logical_config['viewpolicies'] = None

            self.logger.info("Logical configuration collection completed")
            return logical_config

        except Exception as e:
            self.logger.error(f"Error collecting logical configuration: {e}")
            return {}

    def get_security_configuration(self) -> Dict[str, Any]:
        """
        Get security configuration including authentication providers.

        Returns:
            Dict[str, Any]: Security configuration data
        """
        try:
            self.logger.info("Collecting security configuration")

            security_config = {}

            # Active Directory
            ad_data = self._make_api_request('activedirectory/')
            if ad_data:
                security_config['activedirectory'] = ad_data
                self.logger.debug("Retrieved Active Directory configuration")
            else:
                self.logger.warning("Active Directory configuration not available")
                security_config['activedirectory'] = None

            # LDAP
            ldap_data = self._make_api_request('ldap/')
            if ldap_data:
                security_config['ldap'] = ldap_data
                self.logger.debug("Retrieved LDAP configuration")
            else:
                self.logger.warning("LDAP configuration not available")
                security_config['ldap'] = None

            # NIS
            nis_data = self._make_api_request('nis/')
            if nis_data:
                security_config['nis'] = nis_data
                self.logger.debug("Retrieved NIS configuration")
            else:
                self.logger.warning("NIS configuration not available")
                security_config['nis'] = None

            self.logger.info("Security configuration collection completed")
            return security_config

        except Exception as e:
            self.logger.error(f"Error collecting security configuration: {e}")
            return {}

    def get_data_protection_configuration(self) -> Dict[str, Any]:
        """
        Get data protection configuration including snapshot and replication policies.

        Returns:
            Dict[str, Any]: Data protection configuration data
        """
        try:
            self.logger.info("Collecting data protection configuration")

            protection_config = {}

            # Snapshot programs
            snapprograms_data = self._make_api_request('snapprograms/')
            if snapprograms_data:
                protection_config['snapprograms'] = snapprograms_data
                self.logger.debug("Retrieved snapshot programs configuration")
            else:
                self.logger.warning("Snapshot programs configuration not available")
                protection_config['snapprograms'] = None

            # Protection policies
            protectionpolicies_data = self._make_api_request('protectionpolicies/')
            if protectionpolicies_data:
                protection_config['protectionpolicies'] = protectionpolicies_data
                self.logger.debug("Retrieved protection policies configuration")
            else:
                self.logger.warning("Protection policies configuration not available")
                protection_config['protectionpolicies'] = None

            self.logger.info("Data protection configuration collection completed")
            return protection_config

        except Exception as e:
            self.logger.error(f"Error collecting data protection configuration: {e}")
            return {}

    def get_all_data(self) -> Dict[str, Any]:
        """
        Collect all available data from the VAST cluster.

        Returns:
            Dict[str, Any]: Complete cluster data for report generation
        """
        try:
            self.logger.info("Starting comprehensive data collection")

            if not self.authenticated:
                self.logger.error("Not authenticated. Call authenticate() first.")
                return {}

            all_data = {
                'collection_timestamp': time.time(),
                'cluster_ip': self.cluster_ip,
                'api_version': self.api_version,
                'cluster_version': self.cluster_version,
                'enhanced_features': {
                    'rack_height_supported': self.rack_height_supported,
                    'psnt_supported': self.psnt_supported
                }
            }

            # Collect all data sections
            cluster_info = self.get_cluster_info()
            if cluster_info:
                all_data['cluster_info'] = {
                    'name': cluster_info.name,
                    'guid': cluster_info.guid,
                    'version': cluster_info.version,
                    'state': cluster_info.state,
                    'license': cluster_info.license,
                    'psnt': cluster_info.psnt
                }

            # Hardware inventory
            cnodes = self.get_cnode_details()
            dnodes = self.get_dnode_details()
            all_data['hardware'] = {
                'cnodes': [
                    {
                        'id': cnode.node_id,
                        'type': cnode.node_type,
                        'model': cnode.model,
                        'serial_number': cnode.serial_number,
                        'rack_position': cnode.rack_position,
                        'status': cnode.status
                    } for cnode in cnodes
                ],
                'dnodes': [
                    {
                        'id': dnode.node_id,
                        'type': dnode.node_type,
                        'model': dnode.model,
                        'serial_number': dnode.serial_number,
                        'rack_position': dnode.rack_position,
                        'status': dnode.status
                    } for dnode in dnodes
                ]
            }

            # Configuration sections
            all_data['network'] = self.get_network_configuration()
            all_data['logical'] = self.get_logical_configuration()
            all_data['security'] = self.get_security_configuration()
            all_data['data_protection'] = self.get_data_protection_configuration()

            self.logger.info("Comprehensive data collection completed successfully")
            return all_data

        except Exception as e:
            self.logger.error(f"Error during comprehensive data collection: {e}")
            return {}

    def close(self) -> None:
        """Close the API session and clean up resources."""
        try:
            if self.session:
                self.session.close()
                self.authenticated = False
                self.logger.info("API session closed")
        except Exception as e:
            self.logger.error(f"Error closing API session: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function for easy usage
def create_vast_api_handler(cluster_ip: str, username: str, password: str,
                           config: Optional[Dict[str, Any]] = None) -> VastApiHandler:
    """
    Create and return a configured VastApiHandler instance.

    Args:
        cluster_ip (str): IP address of the VAST Management Service
        username (str): Username for authentication
        password (str): Password for authentication
        config (Dict[str, Any], optional): Configuration dictionary

    Returns:
        VastApiHandler: Configured API handler instance
    """
    return VastApiHandler(cluster_ip, username, password, config)


if __name__ == "__main__":
    """
    Test the API handler when run as a standalone module.
    """
    import sys
    from pathlib import Path

    # Add src directory to Python path
    sys.path.insert(0, str(Path(__file__).parent))

    from utils.logger import setup_logging

    # Set up logging
    setup_logging()
    logger = get_logger(__name__)

    # Test configuration
    test_config = {
        'api': {
            'timeout': 30,
            'max_retries': 3,
            'retry_delay': 2,
            'verify_ssl': True,
            'version': 'v7'
        }
    }

    logger.info("VAST API Handler Module Test")
    logger.info("This module provides comprehensive VAST API integration")
    logger.info("Enhanced features: rack heights and PSNT integration")
    logger.info("Ready for integration with data extractor and report builder")
