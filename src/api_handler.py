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
    name: str
    serial_number: str
    model: str = "Unknown"
    status: str = "unknown"
    rack_position: Optional[int] = None  # Enhanced: Rack height/U position

    # Network information
    primary_ip: Optional[str] = None
    secondary_ip: Optional[str] = None
    tertiary_ip: Optional[str] = None
    mgmt_ip: Optional[str] = None
    ipmi_ip: Optional[str] = None

    # Hardware details
    cores: Optional[int] = None
    box_id: Optional[int] = None
    box_vendor: Optional[str] = None
    bios_version: Optional[str] = None
    cpld_version: Optional[str] = None

    # Role information
    is_mgmt: bool = False
    is_leader: bool = False
    is_pfc: bool = False

    # Software information
    os_version: Optional[str] = None
    build_version: Optional[str] = None
    bmc_state: Optional[str] = None
    bmc_fw_version: Optional[str] = None

    # Performance features
    turbo_boost: bool = False
    required_cores: Optional[int] = None

    # DTray information (for DNodes)
    dtray_name: Optional[str] = None
    dtray_position: Optional[str] = None
    hardware_type: Optional[str] = None
    mcu_state: Optional[str] = None
    mcu_version: Optional[str] = None
    pcie_switch_version: Optional[str] = None
    bmc_ip: Optional[str] = None


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

        # API version detection - will be determined during authentication
        self.api_version = None
        self.detected_api_version = None

        # Session management
        self.session = None
        self.base_url = None  # Will be set after API version detection
        self.authenticated = False
        self.api_token = None
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

    def _detect_api_version(self) -> str:
        """
        Detect the highest supported API version for this cluster.

        Returns:
            str: The highest supported API version (v7, v6, v5, v4, v3, v2, v1)
        """
        # API versions in order of preference (newest to oldest)
        api_versions = ['v7', 'v6', 'v5', 'v4', 'v3', 'v2', 'v1']

        self.logger.info("Detecting highest supported API version...")

        for version in api_versions:
            try:
                # Test the version by making a simple API call
                test_url = f"https://{self.cluster_ip}/api/{version}/vms/"
                self.logger.debug(f"Testing API version {version} with URL: {test_url}")

                response = self.session.get(
                    test_url,
                    auth=(self.username, self.password),
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )

                if response.status_code == 200:
                    self.logger.info(f"Successfully detected API version: {version}")
                    return version
                else:
                    self.logger.debug(f"API version {version} not supported: {response.status_code}")

            except Exception as e:
                self.logger.debug(f"API version {version} test failed: {e}")
                continue

        # Fallback to v1 if no version works
        self.logger.warning("No API version detected, falling back to v1")
        return 'v1'

    def _set_api_version(self, version: str) -> None:
        """
        Set the API version and update the base URL.

        Args:
            version (str): API version to use
        """
        self.api_version = version
        self.detected_api_version = version
        self.base_url = f"https://{self.cluster_ip}/api/{version}/"
        self.logger.info(f"Using API version: {version}")

    def authenticate(self) -> bool:
        """
        Authenticate with the VAST cluster using basic auth or API tokens.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            self.logger.info(f"Authenticating with VAST cluster at {self.cluster_ip}")

            if not self.session:
                self.session = self._setup_session()

            # First detect the highest supported API version
            detected_version = self._detect_api_version()
            self._set_api_version(detected_version)

            # Try basic authentication with the detected API version
            if self._try_basic_auth():
                self.authenticated = True
                self.logger.info(f"Successfully authenticated with VAST cluster using basic authentication (API {self.api_version})")
                self._detect_cluster_capabilities()
                return True

            # If basic auth fails, try to create an API token
            if self._create_api_token():
                self.authenticated = True
                self.logger.info(f"Successfully authenticated with VAST cluster using API token (API {self.api_version})")
                self._detect_cluster_capabilities()
                return True
            else:
                self.logger.error("Failed to authenticate with VAST cluster")
                return False

        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {e}")
            return False

    def _try_existing_tokens(self) -> bool:
        """Try to use existing API tokens for authentication."""
        try:
            self.logger.debug("Checking for existing API tokens")

            # Get list of existing tokens
            response = self.session.get(
                urljoin(self.base_url, 'apitokens/'),
                auth=(self.username, self.password),
                timeout=self.timeout,
                verify=self.verify_ssl
            )

            if response.status_code != 200:
                self.logger.debug(f"Failed to get existing tokens: {response.status_code}")
                return False

            tokens = response.json()
            if not tokens:
                self.logger.debug("No existing tokens found")
                return False

            # Try to use the most recent non-revoked token
            for token in sorted(tokens, key=lambda x: x.get('created', ''), reverse=True):
                if not token.get('revoked', False):
                    token_id = token.get('id')
                    if token_id:
                        # Test the token by making a simple API call
                        test_response = self.session.get(
                            urljoin(self.base_url, 'vms/'),
                            headers={'Authorization': f'Api-Token {token_id}'},
                            timeout=self.timeout,
                            verify=self.verify_ssl
                        )

                        if test_response.status_code == 200:
                            self.api_token = token_id
                            self.session.headers.update({
                                'Authorization': f'Api-Token {token_id}'
                            })
                            self.logger.debug(f"Successfully using existing token: {token_id}")
                            return True
                        else:
                            self.logger.debug(f"Token {token_id} failed test: {test_response.status_code}")

            self.logger.debug("No valid existing tokens found")
            return False

        except Exception as e:
            self.logger.debug(f"Error trying existing tokens: {e}")
            return False

    def _create_api_token(self) -> bool:
        """Create an API token for authentication."""
        try:
            # First, create an API token using basic auth
            token_data = {
                "name": f"VAST-As-Built-Report-{int(time.time())}",
                "expiry_date": "30D",
                "owner": self.username
            }

            self.logger.debug(f"Creating API token for user: {self.username}")

            # Use basic auth to create the token
            response = self.session.post(
                urljoin(self.base_url, 'apitokens/'),
                json=token_data,
                auth=(self.username, self.password),
                timeout=self.timeout,
                verify=self.verify_ssl
            )

            if response.status_code == 201:  # 201 Created is the correct status for token creation
                token_info = response.json()
                if 'token' in token_info:
                    self.api_token = token_info['token']
                    # Set the API token in the session headers for future requests
                    self.session.headers.update({
                        'Authorization': f'Api-Token {self.api_token}'
                    })
                    self.logger.debug("API token created and set in session headers")
                    return True
                else:
                    self.logger.error(f"API token creation response missing token: {token_info}")
                    return False
            elif response.status_code == 503:
                # Handle token limit reached
                try:
                    error_info = response.json()
                    if 'detail' in error_info and 'maximum number of API Tokens' in error_info['detail']:
                        self.logger.warning("User has reached maximum API token limit. Cannot create new token.")
                        return False
                except:
                    pass
                self.logger.error(f"API token creation failed: {response.status_code} - {response.text}")
                return False
            else:
                self.logger.error(f"API token creation failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Error creating API token: {e}")
            return False

    def _try_basic_auth(self) -> bool:
        """Try basic authentication."""
        try:
            # Test basic auth with a simple endpoint
            url = urljoin(self.base_url, 'vms/')
            self.logger.debug(f"Trying basic auth with URL: {url}")
            response = self.session.get(
                url,
                auth=(self.username, self.password),
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            self.logger.debug(f"Basic auth response: {response.status_code}")
            if response.status_code == 200:
                # Set up the session for basic auth
                self.session.auth = (self.username, self.password)
                self.logger.debug("Basic auth successful, session configured")
                return True
            else:
                self.logger.debug(f"Basic auth failed: {response.text}")
                return False
        except Exception as e:
            self.logger.debug(f"Basic auth exception: {e}")
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
            if response.status_code == 200:
                # Store session token if provided
                if 'sessionid' in response.cookies:
                    self.session.cookies.update(response.cookies)
                return True
            else:
                self.logger.debug(f"Session auth failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.debug(f"Session auth exception: {e}")
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
            # Try clusters/ endpoint first for more comprehensive data
            cluster_data = self._make_api_request('clusters/')
            if not cluster_data:
                # Fallback to vms/ endpoint
                cluster_data = self._make_api_request('vms/')

            if cluster_data:
                # Handle both single object and array responses
                if isinstance(cluster_data, list) and len(cluster_data) > 0:
                    cluster_data = cluster_data[0]

                # Extract version from clusters/ endpoint (sw_version) or vms/ endpoint (version)
                version = cluster_data.get('sw_version', cluster_data.get('version'))
                if version:
                    self.cluster_version = version
                    self.logger.info(f"Detected cluster version: {self.cluster_version}")
                else:
                    self.logger.warning("Could not extract cluster version from response")

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
        # Check both API version and cluster version
        api_supports_enhanced = self.api_version and self.api_version in ['v7', 'v6', 'v5']
        cluster_supports_enhanced = self.cluster_version and self.cluster_version >= "5.3"

        if api_supports_enhanced and cluster_supports_enhanced:
            self.rack_height_supported = True
            self.psnt_supported = True
            self.logger.info(f"Enhanced features enabled: rack heights and PSNT (API {self.api_version}, Cluster {self.cluster_version})")
        else:
            self.rack_height_supported = False
            self.psnt_supported = False
            reason = []
            if not api_supports_enhanced:
                reason.append(f"API version {self.api_version} does not support enhanced features")
            if not cluster_supports_enhanced:
                reason.append(f"Cluster version {self.cluster_version} does not support enhanced features")
            self.logger.info(f"Enhanced features disabled: {'; '.join(reason)}")

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

            # Try clusters/ endpoint first (more comprehensive data)
            cluster_data = self._make_api_request('clusters/')
            if not cluster_data:
                self.logger.warning("clusters/ endpoint not available, falling back to vms/")
                cluster_data = self._make_api_request('vms/')
                if not cluster_data:
                    self.logger.error("Failed to retrieve cluster information from both endpoints")
                    return None

            # Handle both single object and array responses
            if isinstance(cluster_data, list) and len(cluster_data) > 0:
                cluster_data = cluster_data[0]  # Use first cluster if array
            elif not isinstance(cluster_data, dict):
                self.logger.error(f"Unexpected cluster data format: {type(cluster_data)}")
                return None

            # Extract comprehensive cluster information
            cluster_info = VastClusterInfo(
                name=cluster_data.get('name', 'Unknown'),
                guid=cluster_data.get('guid', 'Unknown'),
                version=cluster_data.get('sw_version', cluster_data.get('version', 'Unknown')),
                state=cluster_data.get('state', 'Unknown'),
                license=cluster_data.get('license', 'Unknown')
            )

            # Enhanced: Add PSNT if available
            if 'psnt' in cluster_data:
                cluster_info.psnt = cluster_data['psnt']
                self.logger.info(f"Retrieved cluster PSNT: {cluster_info.psnt}")
            else:
                self.logger.info("PSNT not available in cluster data")

            # Log additional valuable information
            if 'build' in cluster_data:
                self.logger.info(f"Cluster build: {cluster_data['build']}")
            if 'uptime' in cluster_data:
                self.logger.info(f"Cluster uptime: {cluster_data['uptime']}")

            self.logger.info(f"Cluster: {cluster_info.name} (v{cluster_info.version})")
            return cluster_info

        except Exception as e:
            self.logger.error(f"Error collecting cluster information: {e}")
            return None

    def get_cnode_details(self) -> List[VastHardwareInfo]:
        """
        Get CNode details including enhanced rack positioning and comprehensive hardware information.

        Returns:
            List[VastHardwareInfo]: List of CNode information
        """
        try:
            self.logger.info("Collecting CNode details")

            cnodes_data = self._make_api_request('cnodes/')
            if not cnodes_data:
                self.logger.error("Failed to retrieve CNode information")
                return []

            # Get CBox information for rack positioning
            cboxes = self.get_cbox_details()

            cnodes = []
            for cnode in cnodes_data:
                # Get associated CBox information for rack positioning
                cbox_name = cnode.get('cbox')
                cbox_info = cboxes.get(cbox_name, {}) if cbox_name else {}

                # Extract comprehensive hardware information
                hardware_info = VastHardwareInfo(
                    node_id=str(cnode.get('id', 'Unknown')),
                    node_type='cnode',
                    name=cnode.get('name', 'Unknown'),
                    serial_number=cnode.get('sn', cnode.get('serial_number', 'Unknown')),
                    model=cnode.get('box_vendor', 'Unknown'),
                    status=cnode.get('state', 'unknown'),

                    # Network information
                    primary_ip=cnode.get('ip'),
                    secondary_ip=cnode.get('ip1'),
                    tertiary_ip=cnode.get('ip2'),
                    mgmt_ip=cnode.get('mgmt_ip'),
                    ipmi_ip=cnode.get('ipmi_ip'),

                    # Hardware details
                    cores=cnode.get('cores'),
                    box_id=cnode.get('box_id'),
                    box_vendor=cnode.get('box_vendor'),
                    bios_version=cnode.get('bios_version'),
                    cpld_version=cnode.get('cpld'),

                    # Role information
                    is_mgmt=cnode.get('is_mgmt', False),
                    is_leader=cnode.get('is_leader', False),
                    is_pfc=cnode.get('is_pfc', False),

                    # Software information
                    os_version=cnode.get('os_version'),
                    build_version=cnode.get('build'),
                    bmc_state=cnode.get('bmc_state'),
                    bmc_fw_version=cnode.get('bmc_fw_version'),

                    # Performance features
                    turbo_boost=cnode.get('turbo_boost', False),
                    required_cores=cnode.get('required_num_of_cores')
                )

                # Enhanced: Add rack position from CBox information
                if cbox_info.get('rack_unit'):
                    # Extract rack unit number from "U23" format
                    rack_unit = cbox_info.get('rack_unit', '')
                    if rack_unit.startswith('U'):
                        try:
                            hardware_info.rack_position = int(rack_unit[1:])
                            self.logger.debug(f"CNode {hardware_info.name} rack position: {hardware_info.rack_position} ({rack_unit})")
                        except ValueError:
                            self.logger.debug(f"CNode {hardware_info.name} invalid rack unit format: {rack_unit}")
                    else:
                        self.logger.debug(f"CNode {hardware_info.name} rack unit format not recognized: {rack_unit}")
                elif self.rack_height_supported and 'index_in_rack' in cnode:
                    hardware_info.rack_position = cnode['index_in_rack']
                    self.logger.debug(f"CNode {hardware_info.name} rack position: {hardware_info.rack_position}")
                else:
                    self.logger.debug(f"CNode {hardware_info.name} rack position not available")

                # Log key information
                self.logger.debug(f"CNode {hardware_info.name}: {hardware_info.box_vendor}, {hardware_info.cores} cores, {hardware_info.status}")
                if hardware_info.is_leader:
                    self.logger.debug(f"CNode {hardware_info.name} is cluster leader")
                if hardware_info.is_mgmt:
                    self.logger.debug(f"CNode {hardware_info.name} is management node")

                cnodes.append(hardware_info)

            self.logger.info(f"Retrieved {len(cnodes)} CNode details with comprehensive information")
            return cnodes

        except Exception as e:
            self.logger.error(f"Error collecting CNode details: {e}")
            return []

    def get_dnode_details(self) -> List[VastHardwareInfo]:
        """
        Get DNode details including enhanced rack positioning and comprehensive hardware information.

        Returns:
            List[VastHardwareInfo]: List of DNode information
        """
        try:
            self.logger.info("Collecting DNode details")

            dnodes_data = self._make_api_request('dnodes/')
            if not dnodes_data:
                self.logger.error("Failed to retrieve DNode information")
                return []

            # Get DTray and DBox information for enhanced hardware details
            dtrays = self.get_dtray_details()
            dboxes = self.get_dbox_details()

            dnodes = []
            for dnode in dnodes_data:
                # Get associated DTray and DBox information
                dtray_name = dnode.get('dtray')
                dtray_info = dtrays.get(dtray_name, {}) if dtray_name else {}

                dbox_name = dnode.get('dbox')
                dbox_info = dboxes.get(dbox_name, {}) if dbox_name else {}

                # Extract comprehensive hardware information
                hardware_info = VastHardwareInfo(
                    node_id=str(dnode.get('id', 'Unknown')),
                    node_type='dnode',
                    name=dnode.get('name', 'Unknown'),
                    serial_number=dnode.get('sn', dnode.get('serial_number', 'Unknown')),
                    model=dnode.get('box', 'Unknown'),
                    status=dnode.get('state', 'unknown'),

                    # Network information
                    primary_ip=dnode.get('ip'),
                    secondary_ip=dnode.get('ip1'),
                    tertiary_ip=dnode.get('ip2'),
                    mgmt_ip=dnode.get('mgmt_ip'),
                    ipmi_ip=dnode.get('ipmi_ip'),

                    # Hardware details
                    box_id=dnode.get('box_id'),
                    box_vendor=dnode.get('box', 'Unknown'),
                    bios_version=dnode.get('bios_version'),
                    cpld_version=dnode.get('cpld'),

                    # Role information (DNodes don't have mgmt/leader roles)
                    is_mgmt=False,
                    is_leader=False,
                    is_pfc=False,

                    # Software information
                    os_version=dnode.get('os_version'),
                    build_version=dnode.get('build'),
                    bmc_state=dnode.get('bmc_state'),
                    bmc_fw_version=dnode.get('bmc_fw_version'),

                    # Performance features (DNodes don't have turbo_boost/cores)
                    turbo_boost=False,
                    required_cores=None,

                    # DTray information
                    dtray_name=dtray_name,
                    dtray_position=dtray_info.get('position'),
                    hardware_type=dtray_info.get('hardware_type'),
                    mcu_state=dtray_info.get('mcu_state'),
                    mcu_version=dtray_info.get('mcu_version'),
                    pcie_switch_version=dtray_info.get('pcie_switch_firmware_version'),
                    bmc_ip=dtray_info.get('bmc_ip')
                )

                # Enhanced: Add rack position from DBox information
                if dbox_info.get('rack_unit'):
                    # Extract rack unit number from "U18" format
                    rack_unit = dbox_info.get('rack_unit', '')
                    if rack_unit.startswith('U'):
                        try:
                            hardware_info.rack_position = int(rack_unit[1:])
                            self.logger.debug(f"DNode {hardware_info.name} rack position: {hardware_info.rack_position} ({rack_unit})")
                        except ValueError:
                            self.logger.debug(f"DNode {hardware_info.name} invalid rack unit format: {rack_unit}")
                    else:
                        self.logger.debug(f"DNode {hardware_info.name} rack unit format not recognized: {rack_unit}")
                elif self.rack_height_supported and 'index_in_rack' in dnode:
                    hardware_info.rack_position = dnode['index_in_rack']
                    self.logger.debug(f"DNode {hardware_info.name} rack position: {hardware_info.rack_position}")
                else:
                    self.logger.debug(f"DNode {hardware_info.name} rack position not available")

                # Log key information
                self.logger.debug(f"DNode {hardware_info.name}: {hardware_info.box_vendor}, {hardware_info.status}")
                if 'position' in dnode:
                    self.logger.debug(f"DNode {hardware_info.name} position: {dnode['position']}")
                if hardware_info.hardware_type:
                    self.logger.debug(f"DNode {hardware_info.name} hardware type: {hardware_info.hardware_type}")
                if hardware_info.dtray_position:
                    self.logger.debug(f"DNode {hardware_info.name} DTray position: {hardware_info.dtray_position}")
                if dbox_info.get('rack_unit'):
                    self.logger.debug(f"DNode {hardware_info.name} DBox rack unit: {dbox_info.get('rack_unit')}")

                dnodes.append(hardware_info)

            self.logger.info(f"Retrieved {len(dnodes)} DNode details with comprehensive information")
            return dnodes

        except Exception as e:
            self.logger.error(f"Error collecting DNode details: {e}")
            return []

    def get_dtray_details(self) -> Dict[str, Any]:
        """
        Get DTray details for enhanced hardware information.

        Returns:
            Dict[str, Any]: DTray information keyed by dtray name
        """
        try:
            self.logger.info("Collecting DTray details")

            dtrays_data = self._make_api_request('dtrays/')
            if not dtrays_data:
                self.logger.warning("Failed to retrieve DTray information")
                return {}

            dtrays = {}
            for dtray in dtrays_data:
                dtray_name = dtray.get('name', 'Unknown')
                dtrays[dtray_name] = {
                    'id': dtray.get('id'),
                    'guid': dtray.get('guid'),
                    'name': dtray_name,
                    'dbox': dtray.get('dbox'),
                    'position': dtray.get('position'),
                    'state': dtray.get('state'),
                    'enabled': dtray.get('enabled'),
                    'hardware_type': dtray.get('hardware_type'),
                    'serial_number': dtray.get('serial_number'),
                    'dbox_id': dtray.get('dbox_id'),
                    'cpld_version': dtray.get('cpld_version'),
                    'mcu_state': dtray.get('mcu_state'),
                    'mcu_version': dtray.get('mcu_version'),
                    'bmc_state': dtray.get('bmc_state'),
                    'bmc_fw_version': dtray.get('bmc_fw_version'),
                    'bmc_ip': dtray.get('bmc_ip'),
                    'pcie_switch_mfg_version': dtray.get('pcie_switch_mfg_version'),
                    'pcie_switch_firmware_version': dtray.get('pcie_switch_firmware_version'),
                    'led_status': dtray.get('led_status'),
                    'dnodes': dtray.get('dnodes', [])
                }

                self.logger.debug(f"DTray {dtray_name}: {dtray.get('hardware_type')} at {dtray.get('position')} position")

            self.logger.info(f"Retrieved {len(dtrays)} DTray details")
            return dtrays

        except Exception as e:
            self.logger.error(f"Error collecting DTray details: {e}")
            return {}

    def get_cbox_details(self) -> Dict[str, Any]:
        """
        Get CBox details including rack positioning information.

        Returns:
            Dict[str, Any]: CBox information keyed by cbox name
        """
        try:
            self.logger.info("Collecting CBox details")

            cboxes_data = self._make_api_request('cboxes/')
            if not cboxes_data:
                self.logger.warning("Failed to retrieve CBox information")
                return {}

            cboxes = {}
            for cbox in cboxes_data:
                cbox_name = cbox.get('name', 'Unknown')
                cboxes[cbox_name] = {
                    'id': cbox.get('id'),
                    'guid': cbox.get('guid'),
                    'name': cbox_name,
                    'uid': cbox.get('uid'),
                    'state': cbox.get('state'),
                    'cluster': cbox.get('cluster'),
                    'cluster_id': cbox.get('cluster_id'),
                    'description': cbox.get('description'),
                    'subsystem': cbox.get('subsystem'),
                    'index_in_rack': cbox.get('index_in_rack'),
                    'rack_id': cbox.get('rack_id'),
                    'rack_unit': cbox.get('rack_unit'),
                    'rack_name': cbox.get('rack_name')
                }

                self.logger.debug(f"CBox {cbox_name}: {cbox.get('rack_unit')} in {cbox.get('rack_name')}")

            self.logger.info(f"Retrieved {len(cboxes)} CBox details")
            return cboxes

        except Exception as e:
            self.logger.error(f"Error collecting CBox details: {e}")
            return {}

    def get_dbox_details(self) -> Dict[str, Any]:
        """
        Get DBox details including rack positioning information.

        Returns:
            Dict[str, Any]: DBox information keyed by dbox name
        """
        try:
            self.logger.info("Collecting DBox details")

            dboxes_data = self._make_api_request('dboxes/')
            if not dboxes_data:
                self.logger.warning("Failed to retrieve DBox information")
                return {}

            dboxes = {}
            for dbox in dboxes_data:
                dbox_name = dbox.get('name', 'Unknown')
                dboxes[dbox_name] = {
                    'id': dbox.get('id'),
                    'guid': dbox.get('guid'),
                    'name': dbox_name,
                    'uid': dbox.get('uid'),
                    'state': dbox.get('state'),
                    'cluster': dbox.get('cluster'),
                    'cluster_id': dbox.get('cluster_id'),
                    'drive_type': dbox.get('drive_type'),
                    'description': dbox.get('description'),
                    'sync': dbox.get('sync'),
                    'sync_time': dbox.get('sync_time'),
                    'arch_type': dbox.get('arch_type'),
                    'is_conclude_possible': dbox.get('is_conclude_possible'),
                    'is_replace_possible': dbox.get('is_replace_possible'),
                    'subsystem': dbox.get('subsystem'),
                    'index_in_rack': dbox.get('index_in_rack'),
                    'rack_id': dbox.get('rack_id'),
                    'rack_unit': dbox.get('rack_unit'),
                    'box_vendor': dbox.get('box_vendor'),
                    'is_migrate_target': dbox.get('is_migrate_target'),
                    'is_migrate_source': dbox.get('is_migrate_source'),
                    'rack_name': dbox.get('rack_name'),
                    'hardware_type': dbox.get('hardware_type'),
                    'failure_domain': dbox.get('failure_domain')
                }

                self.logger.debug(f"DBox {dbox_name}: {dbox.get('rack_unit')} in {dbox.get('rack_name')}, {dbox.get('hardware_type')}")

            self.logger.info(f"Retrieved {len(dboxes)} DBox details")
            return dboxes

        except Exception as e:
            self.logger.error(f"Error collecting DBox details: {e}")
            return {}

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
