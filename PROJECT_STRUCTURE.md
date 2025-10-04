# VAST As-Built Report Generator - Project Structure

This document outlines the organized project structure following Python best practices.

## 📁 Directory Structure

```
ps-deploy-report/
├── README.md                          # Main project documentation
├── requirements.txt                   # Python dependencies
├── PROJECT_STRUCTURE.md              # This file
├── ps-deploy-report.code-workspace   # VS Code workspace
│
├── src/                              # Main source code
│   ├── __init__.py
│   ├── main.py                       # CLI entry point
│   ├── api_handler.py                # VAST API integration
│   ├── data_extractor.py             # Data processing and extraction
│   ├── report_builder.py             # Basic PDF report generation
│   ├── enhanced_report_builder.py    # Enhanced report generation
│   ├── comprehensive_report_template.py # Report template definitions
│   ├── brand_compliance.py           # VAST brand compliance
│   └── utils/                        # Utility modules
│       ├── __init__.py
│       └── logger.py                 # Logging configuration
│
├── scripts/                          # Utility and standalone scripts
│   ├── utilities/                    # General utility scripts
│   │   ├── autonomous_excel_populator.py
│   │   ├── enhanced_autonomous_populator.py
│   │   ├── fixed_autonomous_populator.py
│   │   ├── final_comprehensive_solution.py
│   │   ├── generate_api_data.py
│   │   ├── generate_curl_commands.py
│   │   ├── curl_command_tester.py
│   │   └── validate_environment.py
│   ├── data_processing/              # Data processing scripts
│   │   ├── demo.py
│   │   └── demo_excel_population.py
│   └── testing/                      # Test scripts
│       ├── test_auth.py
│       ├── test_authentication.py
│       ├── test_logging.py
│       ├── test_token_auth.py
│       ├── test_token_auth_ssl_fix.py
│       └── test_vast_brand.py
│
├── tests/                            # Test suite
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── data/                         # Test data and fixtures
│       ├── test-cluster-full.txt
│       ├── test-installation.sh
│       └── curl_test_report_*.txt
│
├── docs/                             # Documentation
│   ├── design-guide/                 # Design documentation
│   ├── manus-export/                 # Manual export files
│   ├── report-generator/             # Report generator docs
│   ├── test/                         # Test documentation
│   ├── api/                          # API documentation
│   │   ├── API-REFERENCE.md
│   │   ├── API_CURL_COMMANDS.md
│   │   └── WORKING_CURL_COMMANDS.md
│   ├── deployment/                   # Deployment documentation
│   │   ├── INSTALLATION-GUIDE.md
│   │   ├── DEPLOYMENT.md
│   │   ├── install-mac.sh
│   │   └── install-windows.ps1
│   ├── guides/                       # User guides
│   │   ├── AUTONOMOUS_EXCEL_GUIDE.md
│   │   ├── EXCEL_POPULATION_GUIDE.md
│   │   ├── IMPLEMENTATION_GUIDE.md
│   │   ├── TOKEN_AUTHENTICATION_GUIDE.md
│   │   ├── STATUS.md
│   │   └── TROUBLESHOOTING.md
│   └── analysis/                     # Analysis documents
│       └── BANDWIDTH_ANALYSIS_CORRECTED.md
│
├── data/                             # Data files and outputs
│   ├── excel/                        # Excel data files
│   │   ├── cluster_basic_info*.csv
│   │   ├── cluster_capacity_info*.csv
│   │   ├── cluster_state_info*.csv
│   │   ├── cnodes_info*.csv
│   │   ├── dnodes_info*.csv
│   │   ├── network_*.csv
│   │   ├── vast_data_*.json
│   │   └── vast_data_*.xlsx
│   ├── logs/                         # Log files
│   │   ├── testing-*.txt
│   │   └── vast_report_generator.log
│   ├── reports/                      # Generated reports
│   │   └── test_section1_final_complete/
│   │       ├── vast_asbuilt_report_*.pdf
│   │       └── vast_data_*.json
│   └── archive/                      # Archived data
│       └── [draft reports and old data]
│
├── config/                           # Configuration files
│   ├── config.yaml                   # Main configuration
│   ├── test_config.yaml              # Test configuration
│   └── logrotate.conf                # Log rotation config
│
├── templates/                        # Template files
│   └── config.yaml.template          # Configuration template
│
└── archive/                          # Archived/obsolete files
    └── old_scripts/                  # Old script versions
        ├── fixed_curl_commands.py
        └── cluster-full-output.txt
```

## 🎯 Organization Principles

### **1. Separation of Concerns**
- **`src/`**: Core application logic
- **`scripts/`**: Standalone utility scripts
- **`tests/`**: Test code and data
- **`docs/`**: All documentation
- **`data/`**: All data files and outputs

### **2. Categorization by Purpose**
- **Utilities**: General-purpose scripts
- **Data Processing**: Scripts that process data
- **Testing**: Test-related scripts and data
- **API**: API-related documentation
- **Deployment**: Installation and deployment docs
- **Guides**: User guides and tutorials
- **Analysis**: Analysis and research documents

### **3. Clear Naming Conventions**
- **Directories**: lowercase with underscores
- **Python files**: snake_case
- **Documentation**: UPPERCASE_WITH_UNDERSCORES.md
- **Data files**: descriptive names with timestamps

### **4. Logical Grouping**
- Related files are grouped together
- Clear hierarchy for easy navigation
- Minimal nesting to avoid deep paths

## 🚀 Benefits of This Structure

1. **Maintainability**: Easy to find and modify files
2. **Scalability**: Clear structure for adding new components
3. **Collaboration**: Team members can easily understand the layout
4. **Testing**: Dedicated test structure with proper organization
5. **Documentation**: All docs in one place with clear categorization
6. **Data Management**: Centralized data storage with clear separation

## 📝 Usage Guidelines

### **Adding New Files**
- **Source code**: Place in `src/` or appropriate subdirectory
- **Scripts**: Place in `scripts/` with appropriate subdirectory
- **Tests**: Place in `tests/` with appropriate subdirectory
- **Documentation**: Place in `docs/` with appropriate subdirectory
- **Data**: Place in `data/` with appropriate subdirectory

### **File Naming**
- Use descriptive names
- Follow Python naming conventions
- Include timestamps for data files when appropriate
- Use consistent prefixes for related files

### **Directory Maintenance**
- Keep directories focused on their purpose
- Move obsolete files to `archive/`
- Regularly clean up temporary files
- Update this document when structure changes

## 🔄 Migration Notes

This structure was created by reorganizing the original project layout to follow Python best practices. Key changes include:

1. **Consolidated scattered files** into logical directories
2. **Separated concerns** between source code, scripts, tests, and data
3. **Organized documentation** by category and purpose
4. **Created clear hierarchy** for easy navigation
5. **Established naming conventions** for consistency

The reorganization maintains all functionality while significantly improving maintainability and clarity.
