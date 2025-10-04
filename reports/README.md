# VAST As-Built Report Generator - Reports Directory

## Directory Structure

### `/reference/`
Contains the latest, production-ready reports for reference:

- **`latest_model_centering_fix.pdf/`** - Latest report with Model column centering fix
  - Generated: 2025-10-04 09:06
  - Features: Properly centered Model column text in CBox/DBox inventory tables
  - Status: ✅ Production Ready

### `/archive/`
Contains all previous test reports and revisions:

- **`test_consistent_table_sizing.pdf/`** - Initial table sizing improvements
- **`test_executive_summary_tables.pdf/`** - Executive summary table implementation
- **`test_executive_summary_tables_v2.pdf/`** - Executive summary table v2
- **`test_executive_summary_tables_v3.pdf/`** - Executive summary table v3
- **`test_final_pagination.pdf/`** - Pagination implementation
- **`test_fixed_table_titles.pdf/`** - Table title fixes
- **`test_hardware_summary_updates.pdf/`** - Hardware summary updates
- **`test_html_rendering_fix.pdf/`** - HTML rendering fixes
- **`test_model_column_centering.pdf/`** - Initial Model column centering attempt
- **`test_model_paragraph_centering.pdf/`** - Model column centering with Paragraph alignment
- **`test_network_config_report.pdf/`** - Network configuration report
- **`test_network_config_report_v2.pdf/`** - Network configuration report v2
- **`test_pagination.pdf/`** - Pagination testing
- **`test_reverted_formatting.pdf/` - Reverted formatting changes
- **`test_status_colors.pdf/`** - Status color implementation
- **`test_status_colors_fixed.pdf/`** - Status color fixes
- **`test_updated_sections.pdf/`** - Updated sections
- **`test_updated_sections_v2.pdf/`** - Updated sections v2

## Report Generation

To generate a new report, use:

```bash
python3 src/main.py --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output reports/<REPORT_NAME>
```

## Latest Features

The latest report (`latest_model_centering_fix.pdf/`) includes:

- ✅ **Model Column Centering**: Properly centered text in CBox and DBox inventory tables
- ✅ **HTML Support**: Line breaks and text wrapping in Model column
- ✅ **Professional Layout**: Consistent table styling and alignment
- ✅ **Multi-page Support**: Automatic pagination for large inventories
- ✅ **VAST Brand Compliance**: Full brand guidelines implementation

## Archive Policy

- **Reference reports**: Keep latest production-ready versions
- **Test reports**: Archive all test iterations for historical reference
- **Cleanup**: Remove test reports older than 30 days (manual process)
