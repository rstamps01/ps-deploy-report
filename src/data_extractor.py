"""
VAST As-Built Report Generator - Data Extractor Module

This module processes and organizes data collected from the VAST API for report generation.
It transforms raw API responses into structured, report-ready data with enhanced capabilities
for rack positioning and cluster support tracking integration.

Features:
- Data validation and sanitization
- Enhanced data processing (rack heights, PSNT)
- Report section organization
- Data completeness validation
- Error handling and graceful degradation
- Support for both enhanced and legacy cluster versions

Author: Manus AI
Date: September 26, 2025
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger


@dataclass
class ReportSection:
    """Data class for report section information."""
    name: str
    title: str
    data: Dict[str, Any]
    completeness: float  # Percentage of data available
    status: str  # 'complete', 'partial', 'missing', 'error'


@dataclass
class ClusterSummary:
    """Data class for cluster summary information."""
    name: str
    guid: str
    version: str
    state: str
    license: str
    psnt: Optional[str] = None
    enhanced_features: Dict[str, bool] = None
    collection_timestamp: Optional[datetime] = None


@dataclass
class HardwareInventory:
    """Data class for hardware inventory with enhanced positioning."""
    cnodes: List[Dict[str, Any]]
    dnodes: List[Dict[str, Any]]
    total_nodes: int
    rack_positions_available: bool
    physical_layout: Optional[Dict[str, Any]] = None


class DataExtractionError(Exception):
    """Custom exception for data extraction errors."""
    pass


class VastDataExtractor:
    """
    VAST Data Extractor for processing and organizing API data.

    This class transforms raw VAST API responses into structured, report-ready data
    with enhanced capabilities for rack positioning and cluster support tracking.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the data extractor.

        Args:
            config (Dict[str, Any], optional): Configuration dictionary
        """
        self.logger = get_logger(__name__)
        self.config = config or {}

        # Data collection configuration
        self.data_config = self.config.get('data_collection', {})
        self.validate_responses = self.data_config.get('validate_responses', True)
        self.graceful_degradation = self.data_config.get('graceful_degradation', True)

        # Report sections configuration
        self.sections_config = self.data_config.get('sections', {})

        self.logger.info("Data extractor initialized with enhanced processing capabilities")

    def extract_cluster_summary(self, raw_data: Dict[str, Any]) -> ClusterSummary:
        """
        Extract and process cluster summary information.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ClusterSummary: Processed cluster summary data
        """
        try:
            self.logger.info("Extracting cluster summary information")

            cluster_info = raw_data.get('cluster_info', {})
            enhanced_features = raw_data.get('enhanced_features', {})

            # Extract basic cluster information
            summary = ClusterSummary(
                name=cluster_info.get('name', 'Unknown'),
                guid=cluster_info.get('guid', 'Unknown'),
                version=cluster_info.get('version', 'Unknown'),
                state=cluster_info.get('state', 'Unknown'),
                license=cluster_info.get('license', 'Unknown'),
                psnt=cluster_info.get('psnt'),
                enhanced_features=enhanced_features,
                collection_timestamp=datetime.fromtimestamp(
                    raw_data.get('collection_timestamp', 0)
                ) if raw_data.get('collection_timestamp') else None
            )

            # Validate data completeness
            completeness = self._calculate_completeness([
                summary.name != 'Unknown',
                summary.guid != 'Unknown',
                summary.version != 'Unknown',
                summary.state != 'Unknown',
                summary.license != 'Unknown'
            ])

            if completeness < 0.8:
                self.logger.warning(f"Cluster summary completeness: {completeness:.1%}")

            self.logger.info(f"Cluster summary extracted: {summary.name} (v{summary.version})")
            return summary

        except Exception as e:
            self.logger.error(f"Error extracting cluster summary: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract cluster summary: {e}")
            return ClusterSummary(
                name='Error', guid='Error', version='Error',
                state='Error', license='Error'
            )

    def extract_hardware_inventory(self, raw_data: Dict[str, Any]) -> HardwareInventory:
        """
        Extract and process hardware inventory with enhanced positioning.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            HardwareInventory: Processed hardware inventory data
        """
        try:
            self.logger.info("Extracting hardware inventory with enhanced positioning")

            hardware_data = raw_data.get('hardware', {})
            enhanced_features = raw_data.get('enhanced_features', {})

            # Process CNodes
            cnodes = []
            for cnode in hardware_data.get('cnodes', []):
                processed_cnode = self._process_hardware_node(cnode, 'cnode')
                cnodes.append(processed_cnode)

            # Process DNodes
            dnodes = []
            for dnode in hardware_data.get('dnodes', []):
                processed_dnode = self._process_hardware_node(dnode, 'dnode')
                dnodes.append(processed_dnode)

            # Calculate total nodes
            total_nodes = len(cnodes) + len(dnodes)

            # Check if rack positions are available
            rack_positions_available = enhanced_features.get('rack_height_supported', False)

            # Generate physical layout if rack positions available
            physical_layout = None
            if rack_positions_available:
                physical_layout = self._generate_physical_layout(cnodes, dnodes)

            inventory = HardwareInventory(
                cnodes=cnodes,
                dnodes=dnodes,
                total_nodes=total_nodes,
                rack_positions_available=rack_positions_available,
                physical_layout=physical_layout
            )

            self.logger.info(f"Hardware inventory extracted: {total_nodes} total nodes")
            if rack_positions_available:
                self.logger.info("Rack positioning data included in inventory")

            return inventory

        except Exception as e:
            self.logger.error(f"Error extracting hardware inventory: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract hardware inventory: {e}")
            return HardwareInventory(
                cnodes=[], dnodes=[], total_nodes=0,
                rack_positions_available=False
            )

    def _process_hardware_node(self, node_data: Dict[str, Any], node_type: str) -> Dict[str, Any]:
        """
        Process individual hardware node data.

        Args:
            node_data (Dict[str, Any]): Raw node data
            node_type (str): Type of node ('cnode' or 'dnode')

        Returns:
            Dict[str, Any]: Processed node data
        """
        processed_node = {
            'id': node_data.get('id', 'Unknown'),
            'type': node_type,
            'model': node_data.get('model', 'Unknown'),
            'serial_number': node_data.get('serial_number', 'Unknown'),
            'status': node_data.get('status', 'unknown'),
            'rack_position': node_data.get('rack_position'),
            'rack_position_available': node_data.get('rack_position') is not None
        }

        # Add enhanced information if available
        if processed_node['rack_position'] is not None:
            processed_node['rack_u'] = f"U{processed_node['rack_position']}"
            processed_node['positioning_note'] = "Automated via API"
        else:
            processed_node['rack_u'] = "Manual Entry Required"
            processed_node['positioning_note'] = "Not available for this cluster version"

        return processed_node

    def _generate_physical_layout(self, cnodes: List[Dict], dnodes: List[Dict]) -> Dict[str, Any]:
        """
        Generate physical rack layout information.

        Args:
            cnodes (List[Dict]): Processed CNode data
            dnodes (List[Dict]): Processed DNode data

        Returns:
            Dict[str, Any]: Physical layout information
        """
        try:
            # Group nodes by rack position
            rack_layout = {}

            # Process CNodes
            for cnode in cnodes:
                if cnode.get('rack_position') is not None:
                    pos = cnode['rack_position']
                    if pos not in rack_layout:
                        rack_layout[pos] = {'cnodes': [], 'dnodes': []}
                    rack_layout[pos]['cnodes'].append(cnode)

            # Process DNodes
            for dnode in dnodes:
                if dnode.get('rack_position') is not None:
                    pos = dnode['rack_position']
                    if pos not in rack_layout:
                        rack_layout[pos] = {'cnodes': [], 'dnodes': []}
                    rack_layout[pos]['dnodes'].append(dnode)

            # Calculate layout statistics
            occupied_positions = len(rack_layout)
            min_position = min(rack_layout.keys()) if rack_layout else 0
            max_position = max(rack_layout.keys()) if rack_layout else 0

            layout_info = {
                'rack_layout': rack_layout,
                'statistics': {
                    'occupied_positions': occupied_positions,
                    'min_position': min_position,
                    'max_position': max_position,
                    'total_cnodes': len(cnodes),
                    'total_dnodes': len(dnodes)
                },
                'generated_timestamp': datetime.now().isoformat()
            }

            self.logger.debug(f"Physical layout generated: {occupied_positions} occupied positions")
            return layout_info

        except Exception as e:
            self.logger.error(f"Error generating physical layout: {e}")
            return None

    def extract_network_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process network configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed network configuration section
        """
        try:
            self.logger.info("Extracting network configuration")

            network_data = raw_data.get('network', {})

            # Process DNS configuration
            dns_config = self._process_dns_configuration(network_data.get('dns'))

            # Process NTP configuration
            ntp_config = self._process_ntp_configuration(network_data.get('ntp'))

            # Process VIP pools
            vippool_config = self._process_vippool_configuration(network_data.get('vippools'))

            # Combine all network data
            processed_data = {
                'dns': dns_config,
                'ntp': ntp_config,
                'vippools': vippool_config,
                'extraction_timestamp': datetime.now().isoformat()
            }

            # Calculate completeness
            completeness = self._calculate_completeness([
                dns_config is not None,
                ntp_config is not None,
                vippool_config is not None
            ])

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name='network_configuration',
                title='Network Configuration',
                data=processed_data,
                completeness=completeness,
                status=status
            )

            self.logger.info(f"Network configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting network configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract network configuration: {e}")
            return ReportSection(
                name='network_configuration',
                title='Network Configuration',
                data={},
                completeness=0.0,
                status='error'
            )

    def _process_dns_configuration(self, dns_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Process DNS configuration data."""
        if not dns_data:
            return None

        return {
            'servers': dns_data.get('servers', []),
            'search_domains': dns_data.get('search_domains', []),
            'enabled': dns_data.get('enabled', False),
            'source': 'API'
        }

    def _process_ntp_configuration(self, ntp_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Process NTP configuration data."""
        if not ntp_data:
            return None

        return {
            'servers': ntp_data.get('servers', []),
            'enabled': ntp_data.get('enabled', False),
            'source': 'API'
        }

    def _process_vippool_configuration(self, vippool_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Process VIP pool configuration data."""
        if not vippool_data:
            return None

        return {
            'pools': vippool_data.get('pools', []),
            'total_pools': len(vippool_data.get('pools', [])),
            'source': 'API'
        }

    def extract_logical_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process logical configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed logical configuration section
        """
        try:
            self.logger.info("Extracting logical configuration")

            logical_data = raw_data.get('logical', {})

            # Process tenants
            tenants = self._process_tenants(logical_data.get('tenants'))

            # Process views
            views = self._process_views(logical_data.get('views'))

            # Process view policies
            view_policies = self._process_view_policies(logical_data.get('viewpolicies'))

            # Combine all logical data
            processed_data = {
                'tenants': tenants,
                'views': views,
                'view_policies': view_policies,
                'extraction_timestamp': datetime.now().isoformat()
            }

            # Calculate completeness
            completeness = self._calculate_completeness([
                tenants is not None,
                views is not None,
                view_policies is not None
            ])

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name='logical_configuration',
                title='Logical Configuration',
                data=processed_data,
                completeness=completeness,
                status=status
            )

            self.logger.info(f"Logical configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting logical configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract logical configuration: {e}")
            return ReportSection(
                name='logical_configuration',
                title='Logical Configuration',
                data={},
                completeness=0.0,
                status='error'
            )

    def _process_tenants(self, tenants_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process tenants data."""
        if not tenants_data:
            return None

        processed_tenants = []
        for tenant in tenants_data:
            processed_tenant = {
                'name': tenant.get('name', 'Unknown'),
                'id': tenant.get('id', 'Unknown'),
                'state': tenant.get('state', 'Unknown'),
                'source': 'API'
            }
            processed_tenants.append(processed_tenant)

        return {
            'tenants': processed_tenants,
            'total_count': len(processed_tenants),
            'source': 'API'
        }

    def _process_views(self, views_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process views data."""
        if not views_data:
            return None

        processed_views = []
        for view in views_data:
            processed_view = {
                'name': view.get('name', 'Unknown'),
                'path': view.get('path', 'Unknown'),
                'state': view.get('state', 'Unknown'),
                'source': 'API'
            }
            processed_views.append(processed_view)

        return {
            'views': processed_views,
            'total_count': len(processed_views),
            'source': 'API'
        }

    def _process_view_policies(self, policies_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process view policies data."""
        if not policies_data:
            return None

        processed_policies = []
        for policy in policies_data:
            processed_policy = {
                'name': policy.get('name', 'Unknown'),
                'type': policy.get('type', 'Unknown'),
                'state': policy.get('state', 'Unknown'),
                'source': 'API'
            }
            processed_policies.append(processed_policy)

        return {
            'policies': processed_policies,
            'total_count': len(processed_policies),
            'source': 'API'
        }

    def extract_security_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process security configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed security configuration section
        """
        try:
            self.logger.info("Extracting security configuration")

            security_data = raw_data.get('security', {})

            # Process Active Directory
            ad_config = self._process_ad_configuration(security_data.get('activedirectory'))

            # Process LDAP
            ldap_config = self._process_ldap_configuration(security_data.get('ldap'))

            # Process NIS
            nis_config = self._process_nis_configuration(security_data.get('nis'))

            # Combine all security data
            processed_data = {
                'active_directory': ad_config,
                'ldap': ldap_config,
                'nis': nis_config,
                'extraction_timestamp': datetime.now().isoformat()
            }

            # Calculate completeness
            completeness = self._calculate_completeness([
                ad_config is not None,
                ldap_config is not None,
                nis_config is not None
            ])

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name='security_configuration',
                title='Security & Authentication',
                data=processed_data,
                completeness=completeness,
                status=status
            )

            self.logger.info(f"Security configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting security configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract security configuration: {e}")
            return ReportSection(
                name='security_configuration',
                title='Security & Authentication',
                data={},
                completeness=0.0,
                status='error'
            )

    def _process_ad_configuration(self, ad_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Process Active Directory configuration."""
        if not ad_data:
            return None

        return {
            'enabled': ad_data.get('enabled', False),
            'domain': ad_data.get('domain', 'Unknown'),
            'servers': ad_data.get('servers', []),
            'source': 'API'
        }

    def _process_ldap_configuration(self, ldap_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Process LDAP configuration."""
        if not ldap_data:
            return None

        return {
            'enabled': ldap_data.get('enabled', False),
            'servers': ldap_data.get('servers', []),
            'base_dn': ldap_data.get('base_dn', 'Unknown'),
            'source': 'API'
        }

    def _process_nis_configuration(self, nis_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Process NIS configuration."""
        if not nis_data:
            return None

        return {
            'enabled': nis_data.get('enabled', False),
            'servers': nis_data.get('servers', []),
            'domain': nis_data.get('domain', 'Unknown'),
            'source': 'API'
        }

    def extract_data_protection_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process data protection configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed data protection configuration section
        """
        try:
            self.logger.info("Extracting data protection configuration")

            protection_data = raw_data.get('data_protection', {})

            # Process snapshot programs
            snapshot_config = self._process_snapshot_configuration(protection_data.get('snapprograms'))

            # Process protection policies
            policy_config = self._process_protection_policy_configuration(protection_data.get('protectionpolicies'))

            # Combine all protection data
            processed_data = {
                'snapshot_programs': snapshot_config,
                'protection_policies': policy_config,
                'extraction_timestamp': datetime.now().isoformat()
            }

            # Calculate completeness
            completeness = self._calculate_completeness([
                snapshot_config is not None,
                policy_config is not None
            ])

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name='data_protection_configuration',
                title='Data Protection',
                data=processed_data,
                completeness=completeness,
                status=status
            )

            self.logger.info(f"Data protection configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting data protection configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract data protection configuration: {e}")
            return ReportSection(
                name='data_protection_configuration',
                title='Data Protection',
                data={},
                completeness=0.0,
                status='error'
            )

    def _process_snapshot_configuration(self, snapshot_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process snapshot programs configuration."""
        if not snapshot_data:
            return None

        processed_snapshots = []
        for snapshot in snapshot_data:
            processed_snapshot = {
                'name': snapshot.get('name', 'Unknown'),
                'schedule': snapshot.get('schedule', 'Unknown'),
                'enabled': snapshot.get('enabled', False),
                'source': 'API'
            }
            processed_snapshots.append(processed_snapshot)

        return {
            'programs': processed_snapshots,
            'total_count': len(processed_snapshots),
            'source': 'API'
        }

    def _process_protection_policy_configuration(self, policy_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process protection policies configuration."""
        if not policy_data:
            return None

        processed_policies = []
        for policy in policy_data:
            processed_policy = {
                'name': policy.get('name', 'Unknown'),
                'type': policy.get('type', 'Unknown'),
                'retention': policy.get('retention', 'Unknown'),
                'enabled': policy.get('enabled', False),
                'source': 'API'
            }
            processed_policies.append(processed_policy)

        return {
            'policies': processed_policies,
            'total_count': len(processed_policies),
            'source': 'API'
        }

    def extract_all_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and process all report data from raw API responses.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            Dict[str, Any]: Complete processed report data
        """
        try:
            self.logger.info("Starting comprehensive data extraction")

            # Extract all sections
            cluster_summary = self.extract_cluster_summary(raw_data)
            hardware_inventory = self.extract_hardware_inventory(raw_data)
            network_config = self.extract_network_configuration(raw_data)
            logical_config = self.extract_logical_configuration(raw_data)
            security_config = self.extract_security_configuration(raw_data)
            protection_config = self.extract_data_protection_configuration(raw_data)

            # Calculate overall completeness
            section_completeness = [
                network_config.completeness,
                logical_config.completeness,
                security_config.completeness,
                protection_config.completeness
            ]
            overall_completeness = sum(section_completeness) / len(section_completeness)

            # Compile final report data
            report_data = {
                'metadata': {
                    'extraction_timestamp': datetime.now().isoformat(),
                    'overall_completeness': overall_completeness,
                    'enhanced_features': raw_data.get('enhanced_features', {}),
                    'cluster_version': raw_data.get('cluster_version'),
                    'api_version': raw_data.get('api_version')
                },
                'cluster_summary': asdict(cluster_summary),
                'hardware_inventory': asdict(hardware_inventory),
                'sections': {
                    'network_configuration': asdict(network_config),
                    'logical_configuration': asdict(logical_config),
                    'security_configuration': asdict(security_config),
                    'data_protection_configuration': asdict(protection_config)
                }
            }

            self.logger.info(f"Data extraction completed (overall completeness: {overall_completeness:.1%})")
            return report_data

        except Exception as e:
            self.logger.error(f"Error during comprehensive data extraction: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract all data: {e}")
            return {'error': str(e), 'metadata': {'extraction_timestamp': datetime.now().isoformat()}}

    def _calculate_completeness(self, conditions: List[bool]) -> float:
        """Calculate data completeness percentage."""
        if not conditions:
            return 0.0
        return sum(conditions) / len(conditions)

    def _determine_section_status(self, completeness: float) -> str:
        """Determine section status based on completeness."""
        if completeness >= 0.9:
            return 'complete'
        elif completeness >= 0.5:
            return 'partial'
        elif completeness > 0.0:
            return 'missing'
        else:
            return 'error'

    def save_processed_data(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Save processed data to JSON file.

        Args:
            data (Dict[str, Any]): Processed report data
            output_path (str): Output file path

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Processed data saved to: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving processed data: {e}")
            return False


# Convenience function for easy usage
def create_data_extractor(config: Optional[Dict[str, Any]] = None) -> VastDataExtractor:
    """
    Create and return a configured VastDataExtractor instance.

    Args:
        config (Dict[str, Any], optional): Configuration dictionary

    Returns:
        VastDataExtractor: Configured data extractor instance
    """
    return VastDataExtractor(config)


if __name__ == "__main__":
    """
    Test the data extractor when run as a standalone module.
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
        'data_collection': {
            'validate_responses': True,
            'graceful_degradation': True,
            'sections': {
                'executive_summary': True,
                'hardware_inventory': True,
                'network_configuration': True,
                'logical_configuration': True,
                'security_authentication': True,
                'data_protection': True
            }
        }
    }

    logger.info("VAST Data Extractor Module Test")
    logger.info("This module processes and organizes API data for report generation")
    logger.info("Enhanced features: rack positioning and PSNT integration")
    logger.info("Ready for integration with report builder")
