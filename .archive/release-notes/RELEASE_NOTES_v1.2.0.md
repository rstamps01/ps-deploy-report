# Release v1.2.0 - Hardware Inventory Enhancements and Port Mapping Improvements

**Release Date:** November 11, 2025  
**Target VAST Version:** 5.3+  
**API Version:** v7

## 🎉 Major Features

### Hardware Inventory Table Enhancements

#### Node Column Implementation
- **Replaced ID column** with "Node" column showing programmatically generated CNode/DNode names
- **Node names**: Uses deployment index-based names (e.g., `cnode-3-10`, `cnode-3-11`, `dnode-3-112`, `dnode-3-113`)
- **Not hostnames**: Uses programmatically generated `name` field instead of customer-assigned hostnames for consistency

#### One Row Per Node
- **Detailed tracking**: Each CNode and DNode now appears on its own row
- **Multiple nodes per box**: If a CBox or DBox contains multiple nodes, each node gets a separate row with the same Name/Serial Number
- **Better visibility**: Easier to track individual nodes and their associations

#### Column Improvements
- **Renamed columns**:
  - "CNode/DNode" → "Node" (more concise)
  - "Position" → "Height" (clearer terminology)
- **Optimized column widths**:
  - Model: Increased from 30% to 40% (better readability for long model names)
  - Rack: Decreased from 10% to 8%
  - Node: Decreased from 18% to 12%
  - Height: Decreased from 10% to 8%
  - Status: Decreased from 10% to 8%

### Port Mapping Collection

#### Enhanced SSH-Based Collection
- **Automatic collection**: Use `--enable-port-mapping` flag to collect port mapping data
- **Switch support**: Supports Cumulus Linux and Onyx switch operating systems
- **IPL detection**: Automatically detects Inter-Peer Link (IPL) connections between switches
- **Network topology**: Network diagram includes port mapping connections when available

#### Credential Management
- **Switch credentials**: `--switch-user` and `--switch-password` for switch SSH access
- **Node credentials**: `--node-user` and `--node-password` for node SSH access
- **Default values**: cumulus/vastdata usernames with configurable passwords

## 🔧 Technical Improvements

### Data Collection
- **Enhanced name extraction**: Improved CNode and DNode name extraction from API
- **DBox association**: Fixed DNode to DBox association with `dbox_id` field
- **Data structure**: Added `name` and `hostname` fields to hardware inventory data
- **Multiple nodes**: Better handling of multiple nodes per physical box

### Code Quality
- **Fixed dataclass**: Resolved Python dataclass field ordering issues
- **Data extractor**: Enhanced `_process_hardware_node` to include all required fields
- **API handler**: Improved DBox ID extraction and storage

## 📝 Documentation Updates

- **README.md**: Updated with v1.2.0 features, usage examples, and recent updates section
- **CHANGELOG.md**: New changelog file documenting all version changes
- **Usage examples**: Added port mapping collection examples
- **Column descriptions**: Updated Hardware Inventory section descriptions

## 🚀 Usage Examples

### Basic Report Generation
```bash
python3 -m src.main --cluster 10.143.11.204 \
  --username support --password <PASSWORD> \
  --output output
```

### Report with Port Mapping
```bash
python3 -m src.main --cluster 10.143.11.204 \
  --username support --password <PASSWORD> \
  --node-user vastdata --node-password <NODE_PASSWORD> \
  --switch-user cumulus --switch-password <SWITCH_PASSWORD> \
  --enable-port-mapping \
  --output output
```

### Regenerate Report from JSON
```bash
python3 scripts/regenerate_report.py output/vast_data_CLUSTER_TIMESTAMP.json
```

## 📊 Report Improvements

### Hardware Inventory Table
- **Before**: One row per box with comma-separated node IDs
- **After**: One row per node with programmatically generated names
- **Example**: A CBox with 3 CNodes now shows 3 rows, each with the CBox Name/Serial Number and individual CNode names

### Network Topology
- **Before**: Static diagram without connections
- **After**: Dynamic diagram with port mapping connections and IPL links (when port mapping is enabled)

## 🔄 Migration Notes

### For Existing Users
- **No breaking changes**: Existing JSON files remain compatible
- **Regeneration recommended**: Regenerate reports from cluster to get new node names
- **Port mapping optional**: Port mapping requires `--enable-port-mapping` flag and SSH credentials

### For New Installations
- **Follow installation guide**: See `docs/deployment/INSTALLATION-GUIDE.md`
- **Port mapping setup**: Configure switch and node SSH credentials for port mapping collection

## 🐛 Bug Fixes

- Fixed missing `name` field in hardware inventory data extraction
- Fixed missing `dbox_id` field for DNode to DBox association
- Fixed Python dataclass field ordering in `VastHardwareInfo`
- Fixed column width calculations for Hardware Inventory table

## 📦 Files Changed

- `src/api_handler.py`: Added hostname field, improved dbox_id extraction
- `src/data_extractor.py`: Added name and dbox_id fields to node processing
- `src/report_builder.py`: One row per node implementation, column renaming
- `src/brand_compliance.py`: Column width ratio adjustments
- `src/main.py`: Version number update to 1.2.0
- `README.md`: Comprehensive documentation updates
- `CHANGELOG.md`: New changelog file

## 🔗 Related Documentation

- [Installation Guide](docs/deployment/INSTALLATION-GUIDE.md)
- [Port Mapping Analysis](docs/PORT_MAPPING_ISSUE_ANALYSIS.md)
- [Multi-Rack Support](docs/MULTI_RACK_IDENTIFICATION_ANALYSIS.md)

---

**Full Changelog**: See [CHANGELOG.md](CHANGELOG.md) for complete version history.

