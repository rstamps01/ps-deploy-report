# PENDING - Installation Procedure: VAST As-Built Report Generator

Create a local virtual environment:

```
mkdir -p ~/abreport
cd ~/abreport
python3 -m venv .venv
source .venv/bin/activate
```

NOTE: To ACTIVATE virtual environment

```
source .venv/bin/activate
```

NOTE: To DEACTIVATE virtual environment

```
deactivate
```

Create environment validation script

```
vi validation_check.py
a
```

Copy/Paste into script:

```python
#!/usr/bin/env python3
"""
VAST As-Built Report Generator - Environment Validation Script

This script validates that the development environment is properly set up
with all required dependencies and configurations.

Author: Manus AI
Version: 1.0.0-dev
"""

import sys
import os
import importlib
import yaml
from pathlib import Path


def check_python_version():
    """Check if Python version meets requirements."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False


def check_required_packages():
    """Check if all required packages are installed."""
    print("\n📦 Checking required packages...")
    
    required_packages = [
        'requests',
        'yaml',
        'reportlab',
        'weasyprint',
        'click',
        'pytest',
        'colorlog',
        'dateutil',
        'jsonschema',
        'dotenv'
    ]
    
    all_packages_ok = True
    
    for package in required_packages:
        try:
            if package == 'yaml':
                importlib.import_module('yaml')
            elif package == 'dateutil':
                importlib.import_module('dateutil')
            elif package == 'dotenv':
                importlib.import_module('dotenv')
            else:
                importlib.import_module(package)
            print(f"   ✅ {package} - OK")
        except ImportError:
            print(f"   ❌ {package} - NOT FOUND")
            all_packages_ok = False
    
    return all_packages_ok


def check_project_structure():
    """Check if project directory structure is correct."""
    print("\n📁 Checking project structure...")
    
    required_dirs = [
        'src',
        'tests',
        'config',
        'templates',
        'logs',
        'output'
    ]
    
    required_files = [
        'README.md',
        'requirements.txt',
        'config/config.yaml',
        'src/__init__.py',
        'tests/__init__.py'
    ]
    
    all_structure_ok = True
    
    # Check directories
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"   ✅ {dir_name}/ - OK")
        else:
            print(f"   ❌ {dir_name}/ - MISSING")
            all_structure_ok = False
    
    # Check files
    for file_name in required_files:
        if os.path.isfile(file_name):
            print(f"   ✅ {file_name} - OK")
        else:
            print(f"   ❌ {file_name} - MISSING")
            all_structure_ok = False
    
    return all_structure_ok


def check_configuration():
    """Check if configuration file is valid."""
    print("\n⚙️  Checking configuration...")
    
    config_file = 'config/config.yaml'
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for required configuration sections
        required_sections = ['api', 'logging', 'report', 'output', 'data_collection', 'security']
        
        all_config_ok = True
        for section in required_sections:
            if section in config:
                print(f"   ✅ {section} section - OK")
            else:
                print(f"   ❌ {section} section - MISSING")
                all_config_ok = False
        
        return all_config_ok
        
    except FileNotFoundError:
        print(f"   ❌ Configuration file {config_file} not found")
        return False
    except yaml.YAMLError as e:
        print(f"   ❌ Configuration file has invalid YAML syntax: {e}")
        return False


def check_virtual_environment():
    """Check if running in virtual environment."""
    print("\n🔒 Checking virtual environment...")
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("   ✅ Virtual environment - ACTIVE")
        
        # Check if venv directory exists
        if os.path.isdir('venv'):
            print("   ✅ venv/ directory - OK")
        else:
            print("   ⚠️  venv/ directory not found (may be using different venv location)")
        
        return True
    else:
        print("   ❌ Virtual environment - NOT ACTIVE")
        print("   💡 Run: source venv/bin/activate")
        return False


def check_git_status():
    """Check Git repository status."""
    print("\n📋 Checking Git status...")
    
    if os.path.isdir('.git'):
        print("   ✅ Git repository - OK")
        
        # Check if we're on develop branch
        try:
            with open('.git/HEAD', 'r') as f:
                head_content = f.read().strip()
            
            if 'refs/heads/develop' in head_content:
                print("   ✅ On develop branch - OK")
            else:
                print("   ⚠️  Not on develop branch")
                
        except FileNotFoundError:
            print("   ⚠️  Could not determine current branch")
        
        return True
    else:
        print("   ❌ Git repository - NOT FOUND")
        return False


def main():
    """Run all validation checks."""
    print("🔍 VAST As-Built Report Generator - Environment Validation")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_virtual_environment(),
        check_required_packages(),
        check_project_structure(),
        check_configuration(),
        check_git_status()
    ]
    
    print("\n" + "=" * 60)
    
    if all(checks):
        print("🎉 All checks passed! Development environment is ready.")
        print("\n💡 Next steps:")
        print("   1. Start implementing Task 1.1.3: Logging Infrastructure")
        print("   2. Create src/utils.py with logging configuration")
        print("   3. Update STATUS.md with progress")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\n💡 Common fixes:")
        print("   - Activate virtual environment: source venv/bin/activate")
        print("   - Install dependencies: pip install -r requirements.txt")
        print("   - Check project structure matches development guide")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

Press "Esc" key

Enter following to save/quit

```
:wq 
```

Create requirements.txt file

```
vi requirements.txt
a
```

Copy/Paste into script:

```
# VAST As-Built Report Generator Dependencies
# Core HTTP and API libraries
requests>=2.31.0
urllib3>=2.0.0

# Configuration management
PyYAML>=6.0.1

# PDF generation
reportlab>=4.0.0
weasyprint>=60.0

# CLI argument parsing (built-in argparse is sufficient, but click is an alternative)
click>=8.1.0

# Testing framework
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0

# Code quality and linting
flake8>=6.0.0
black>=23.0.0

# Logging enhancements
colorlog>=6.7.0

# Date/time handling
python-dateutil>=2.8.0

# JSON schema validation
jsonschema>=4.19.0

# Environment variable management
python-dotenv>=1.0.0
```

Press "Esc" key

Enter following to save/quit

```
:wq 
```

Install required packages

```
pip install --no-cache-dir -r requirements.txt
```

NOTE: I also upgraded pip at this point.  As follows:

```
/home/vastdata/abreport/.venv/bin/python3 -m pip install --upgrade pip
```
