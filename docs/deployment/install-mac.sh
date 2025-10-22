#!/bin/bash
# VAST As-Built Report Generator - macOS Installation Script
# For VAST Professional Services Engineers
# Version: 1.0.0-dev
# Date: September 27, 2025

# Enable strict error handling
set -euo pipefail

# Set up logging
LOG_FILE="install-mac.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output with timestamps
print_status() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[INFO]${NC} [${timestamp}] $1"
}

print_success() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[SUCCESS]${NC} [${timestamp}] $1"
}

print_warning() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARNING]${NC} [${timestamp}] $1"
}

print_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR]${NC} [${timestamp}] $1"
}

print_debug() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[DEBUG]${NC} [${timestamp}] $1"
}

# Function to handle errors gracefully
handle_error() {
    local exit_code=$?
    local line_number=$1
    local command=$2

    print_error "Installation failed at line $line_number"
    print_error "Command that failed: $command"
    print_error "Exit code: $exit_code"

    # Show helpful troubleshooting information
    echo
    print_error "TROUBLESHOOTING:"
    print_error "1. Check the log file: $LOG_FILE"
    print_error "2. Ensure you have internet connectivity"
    print_error "3. Verify you have administrator privileges"
    print_error "4. Check available disk space (requires ~1GB)"
    print_error "5. Try running: brew doctor (if Homebrew is installed)"

    # Cleanup on error
    cleanup_on_error

    exit $exit_code
}

# Function to cleanup on error
cleanup_on_error() {
    print_debug "Cleaning up after error..."

    # Remove partial installations
    if [ -d "venv" ] && [ ! -f "venv/pyvenv.cfg" ]; then
        print_debug "Removing incomplete virtual environment..."
        rm -rf venv 2>/dev/null || true
    fi

    # Remove partial downloads
    if [ -f "requirements.txt" ] && [ ! -s "requirements.txt" ]; then
        print_debug "Removing incomplete requirements file..."
        rm -f requirements.txt 2>/dev/null || true
    fi
}

# Set up error handling
trap 'handle_error $LINENO "$BASH_COMMAND"' ERR

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check macOS version
check_macos_version() {
    print_status "Checking macOS version..."

    if ! command_exists sw_vers; then
        print_error "Cannot determine macOS version. 'sw_vers' command not found."
        exit 1
    fi

    local macos_version
    if ! macos_version=$(sw_vers -productVersion 2>/dev/null); then
        print_error "Failed to get macOS version"
        exit 1
    fi

    print_debug "Detected macOS version: $macos_version"

    local major_version minor_version
    if ! major_version=$(echo "$macos_version" | cut -d. -f1) || ! minor_version=$(echo "$macos_version" | cut -d. -f2); then
        print_error "Failed to parse macOS version: $macos_version"
        exit 1
    fi

    if [ "$major_version" -lt 10 ] || ([ "$major_version" -eq 10 ] && [ "$minor_version" -lt 15 ]); then
        print_error "macOS 10.15 (Catalina) or later is required. Current version: $macos_version"
        print_error "Please upgrade your macOS version and try again."
        exit 1
    fi

    print_success "macOS version check passed: $macos_version"
}

# Function to install Homebrew
install_homebrew() {
    print_status "Checking Homebrew installation..."

    if command_exists brew; then
        local brew_version
        if brew_version=$(brew --version 2>/dev/null | head -n1); then
            print_success "Homebrew is already installed: $brew_version"
        else
            print_warning "Homebrew command exists but version check failed. Reinstalling..."
        fi
        return 0
    fi

    print_status "Installing Homebrew..."
    print_debug "Downloading Homebrew installation script..."

    # Check internet connectivity
    if ! curl -s --connect-timeout 10 https://raw.githubusercontent.com >/dev/null; then
        print_error "No internet connectivity. Please check your network connection."
        exit 1
    fi

    # Install Homebrew with error handling
    if ! /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; then
        print_error "Homebrew installation failed"
        print_error "Please check the log file for details: $LOG_FILE"
        exit 1
    fi

    # Add Homebrew to PATH for Apple Silicon Macs
    local arch=$(uname -m)
    print_debug "Detected architecture: $arch"

    if [[ "$arch" == "arm64" ]]; then
        print_status "Adding Homebrew to PATH for Apple Silicon Mac..."
        local shell_profile="$HOME/.zprofile"
        if [ -f "$shell_profile" ]; then
            if ! grep -q "homebrew/bin/brew shellenv" "$shell_profile"; then
                echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$shell_profile"
                print_debug "Added Homebrew to $shell_profile"
            fi
        else
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$shell_profile"
            print_debug "Created $shell_profile with Homebrew PATH"
        fi

        # Source the profile for current session
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    # Verify Homebrew installation
    if ! command_exists brew; then
        print_error "Homebrew installation completed but 'brew' command not found in PATH"
        print_error "Please restart your terminal and try again"
        exit 1
    fi

    print_success "Homebrew installed successfully"
}

# Function to install Python
install_python() {
    if command_exists python3; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        local major_version=$(echo $python_version | cut -d. -f1)
        local minor_version=$(echo $python_version | cut -d. -f2)

        if [ "$major_version" -eq 3 ] && [ "$minor_version" -ge 8 ]; then
            print_success "Python 3.$minor_version is already installed"
            return 0
        fi
    fi

    print_status "Installing Python 3.12..."
    brew install python@3.12

    # Create symlink for python3
    if [[ $(uname -m) == "arm64" ]]; then
        ln -sf /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3
    else
        ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3
    fi

    print_success "Python 3.12 installed successfully"
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies for PDF generation..."

    # Install WeasyPrint dependencies
    brew install pango harfbuzz libffi libxml2 libxslt

    # Install additional dependencies
    brew install cairo gobject-introspection

    print_success "System dependencies installed successfully"
}

# Function to create project directory
setup_project() {
    local project_dir="$HOME/vast-asbuilt-reporter"

    if [ -d "$project_dir" ]; then
        print_warning "Project directory already exists: $project_dir"
        read -p "Do you want to update the existing installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Installation cancelled"
            exit 0
        fi
        print_status "Updating existing installation..."
    else
        print_status "Creating project directory: $project_dir"
        mkdir -p "$project_dir"
    fi

    cd "$project_dir"

    # Clone or update repository based on installation mode
    if [ -d ".git" ]; then
        print_status "Updating repository..."
        git pull origin "$INSTALL_BRANCH"
    else
        print_status "Cloning repository from '$INSTALL_BRANCH' branch..."

        if [ "$INSTALL_MODE" = "minimal" ]; then
            # Minimal: Download source archive only (no git)
            print_status "Downloading source archive (no Git history)..."
            curl -L "https://github.com/rstamps01/ps-deploy-report/archive/refs/heads/$INSTALL_BRANCH.zip" -o repo.zip
            unzip -q repo.zip
            mv "ps-deploy-report-$INSTALL_BRANCH"/* .
            mv "ps-deploy-report-$INSTALL_BRANCH"/.* . 2>/dev/null || true
            rm -rf "ps-deploy-report-$INSTALL_BRANCH" repo.zip
            print_success "Source code downloaded"
        else
            # Full or Production: Clone with Git
            if [ "$INSTALL_MODE" = "production" ]; then
                print_status "Cloning repository with shallow history..."
                git clone --depth 1 -b "$INSTALL_BRANCH" https://github.com/rstamps01/ps-deploy-report.git .
            else
                print_status "Cloning repository with full history..."
                git clone -b "$INSTALL_BRANCH" https://github.com/rstamps01/ps-deploy-report.git .
            fi
        fi
    fi

    # Remove .git folder for production mode
    if [ "$INSTALL_MODE" = "production" ] && [ -d ".git" ]; then
        print_status "Removing Git repository (production mode)..."
        rm -rf .git
        print_success "Git repository removed (saved ~101 MB)"
    fi

    print_success "Project setup completed"
}

# Function to create virtual environment
create_virtual_environment() {
    # Skip virtual environment for minimal installation
    if [ "$INSTALL_MODE" = "minimal" ]; then
        print_warning "Skipping virtual environment creation (minimal mode)"
        print_warning "Using system Python packages"
        return 0
    fi

    print_status "Creating Python virtual environment..."

    # Remove existing virtual environment if it exists
    if [ -d "venv" ]; then
        print_status "Removing existing virtual environment..."
        rm -rf venv
    fi

    # Create new virtual environment
    python3 -m venv venv

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    print_success "Virtual environment created successfully"
}

# Function to install Python dependencies
install_python_dependencies() {
    print_status "Installing Python dependencies..."

    # Handle installation based on mode
    if [ "$INSTALL_MODE" = "minimal" ]; then
        # Minimal: Install to system Python
        print_warning "Installing to system Python (minimal mode)"
        pip3 install -r requirements.txt --user
    else
        # Full or Production: Install to virtual environment
        source venv/bin/activate
        pip install -r requirements.txt
    fi

    print_success "Python dependencies installed successfully"
}

# Function to create configuration
setup_configuration() {
    print_status "Setting up configuration..."

    # Copy configuration template
    if [ ! -f "config/config.yaml" ]; then
        cp config/config.yaml.template config/config.yaml
        print_success "Configuration file created: config/config.yaml"
    else
        print_success "Configuration file already exists: config/config.yaml"
    fi

    # Create output directory
    mkdir -p output
    mkdir -p logs

    print_success "Configuration setup completed"
}

# Function to create launch script
create_launch_script() {
    print_status "Creating launch script..."

    cat > run-vast-asbuilt-reporter.sh << 'EOF'
#!/bin/bash
# VAST As-Built Report Generator Launch Script for macOS

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

# Run the application with provided arguments
python3 src/main.py "$@"
EOF

    chmod +x run-vast-asbuilt-reporter.sh

    print_success "Launch script created: run-vast-asbuilt-reporter.sh"
}

# Function to create desktop shortcut
create_desktop_shortcut() {
    print_status "Creating desktop shortcut..."

    local project_dir="$HOME/vast-asbuilt-reporter"
    local desktop_file="$HOME/Desktop/VAST As-Built Reporter.command"

    cat > "$desktop_file" << EOF
#!/bin/bash
# VAST As-Built Report Generator Desktop Shortcut

cd "$project_dir"
./run-vast-asbuilt-reporter.sh
EOF

    chmod +x "$desktop_file"

    print_success "Desktop shortcut created: VAST As-Built Reporter.command"
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."

    # Activate virtual environment
    source venv/bin/activate

    # Test Python version
    local python_version=$(python3 --version)
    print_success "Python version: $python_version"

    # Test application version
    local app_version=$(python3 src/main.py --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "Unknown")
    print_success "Application version: $app_version"

    # Test help command
    if python3 src/main.py --help >/dev/null 2>&1; then
        print_success "Application help command working"
    else
        print_error "Application help command failed"
        return 1
    fi

    print_success "Installation test completed successfully"
}

# Function to display usage instructions
display_usage_instructions() {
    local project_dir="$HOME/vast-asbuilt-reporter"

    echo
    echo "=================================================================="
    echo "VAST AS-BUILT REPORT GENERATOR - INSTALLATION COMPLETE"
    echo "=================================================================="
    echo
    echo "Installation Location: $project_dir"
    echo
    echo "USAGE INSTRUCTIONS:"
    echo "==================="
    echo
    echo "1. Using the Desktop Shortcut:"
    echo "   - Double-click 'VAST As-Built Reporter.command' on your desktop"
    echo "   - Follow the prompts to enter cluster IP and credentials"
    echo
    echo "2. Using Terminal:"
    echo "   cd $project_dir"
    echo "   ./run-vast-asbuilt-reporter.sh --cluster <CLUSTER_IP> --output ./output"
    echo
    echo "3. Direct Python execution:"
    echo "   cd $project_dir"
    echo "   source venv/bin/activate"
    echo "   python3 src/main.py --cluster <CLUSTER_IP> --output ./output"
    echo
    echo "EXAMPLE COMMANDS:"
    echo "================="
    echo "   # Basic usage with interactive credentials"
    echo "   ./run-vast-asbuilt-reporter.sh --cluster 192.168.1.100 --output ./output"
    echo
    echo "   # Using environment variables"
    echo "   export VAST_USERNAME=admin"
    echo "   export VAST_PASSWORD=your_password"
    echo "   ./run-vast-asbuilt-reporter.sh --cluster 192.168.1.100 --output ./output"
    echo
    echo "   # Verbose output for debugging"
    echo "   ./run-vast-asbuilt-reporter.sh --cluster 192.168.1.100 --output ./output --verbose"
    echo
    echo "CONFIGURATION:"
    echo "=============="
    echo "   Edit: $project_dir/config/config.yaml"
    echo "   Logs: $project_dir/logs/vast_report_generator.log"
    echo "   Output: $project_dir/output/"
    echo
    echo "SUPPORT:"
    echo "========"
    echo "   - Check logs: tail -f $project_dir/logs/vast_report_generator.log"
    echo "   - View help: ./run-vast-asbuilt-reporter.sh --help"
    echo "   - GitHub: https://github.com/rstamps01/ps-deploy-report"
    echo
    echo "=================================================================="
}

# Function to display installation summary
display_installation_summary() {
    local project_dir="$HOME/vast-asbuilt-reporter"

    echo
    echo "=================================================================="
    echo "INSTALLATION SUMMARY"
    echo "=================================================================="
    echo
    print_success "Installation completed successfully!"
    echo

    # Display installation mode and approximate size
    case "$INSTALL_MODE" in
        "full")
            echo "📦 Installation Type: Full Installation (Development)"
            echo "💾 Approximate Size: ~215 MB"
            echo "   • Application code: ~7 MB"
            echo "   • Virtual environment: ~107 MB"
            echo "   • Git repository: ~101 MB"
            echo "🔄 Update Method: git pull origin main"
            ;;
        "production")
            echo "📦 Installation Type: Production Deployment"
            echo "💾 Approximate Size: ~114 MB (47% smaller)"
            echo "   • Application code: ~7 MB"
            echo "   • Virtual environment: ~107 MB"
            echo "   • Git repository: Removed"
            echo "🔄 Update Method: Manual download"
            ;;
        "minimal")
            echo "📦 Installation Type: Minimal Installation"
            echo "💾 Approximate Size: ~20 MB (91% smaller)"
            echo "   • Application code: ~7 MB"
            echo "   • System Python packages: ~13 MB"
            echo "   • Virtual environment: Not created"
            echo "🔄 Update Method: Manual download"
            ;;
    esac
    echo
    echo "📁 Installation Location: $project_dir"
    echo "📋 Log File: $LOG_FILE"
    echo "🐍 Python Version: $(python3 --version 2>/dev/null || echo 'Not found')"
    echo "🍺 Homebrew Version: $(brew --version 2>/dev/null | head -n1 || echo 'Not found')"

    if [ "$INSTALL_MODE" = "minimal" ]; then
        echo "📦 Virtual Environment: Not created (using system Python)"
    else
        echo "📦 Virtual Environment: $project_dir/venv"
    fi
    echo "⚙️  Configuration: $project_dir/config/config.yaml"
    echo "📊 Output Directory: $project_dir/output"
    echo "📝 Logs Directory: $project_dir/logs"
    echo
    echo "🚀 Quick Start:"
    echo "   cd $project_dir"
    echo "   ./run-vast-asbuilt-reporter.sh --cluster <CLUSTER_IP> --output ./output"
    echo
    echo "📖 Documentation:"
    echo "   - README.md: Complete usage guide"
    echo "   - INSTALLATION-GUIDE.md: Detailed installation instructions"
    echo "   - TROUBLESHOOTING.md: Common issues and solutions"
    echo
    echo "🆘 Support:"
    echo "   - GitHub: https://github.com/rstamps01/ps-deploy-report"
    echo "   - Logs: tail -f $LOG_FILE"
    echo "   - Help: ./run-vast-asbuilt-reporter.sh --help"
    echo
}

# Global variables for installation
INSTALL_MODE="full"
INSTALL_BRANCH="${VAST_INSTALL_BRANCH:-main}"  # Allow override via environment variable

# Function to display installation menu
show_installation_menu() {
    clear
    echo "=================================================================="
    echo "VAST AS-BUILT REPORT GENERATOR - macOS INSTALLATION"
    echo "=================================================================="
    echo
    echo -e "${BLUE}Select Installation Type:${NC}"
    echo
    echo "  1) Full Installation (Development)"
    echo "     • Complete with Git repository for easy updates"
    echo "     • Includes version control and update capabilities"
    echo "     • Installation size: ~215 MB"
    echo "     • Best for: Development, testing, frequent updates"
    echo
    echo "  2) Production Deployment (Recommended)"
    echo "     • Optimized for production without Git history"
    echo "     • Cleaner deployment, smaller footprint"
    echo "     • Installation size: ~114 MB (47% smaller)"
    echo "     • Best for: Production servers, one-time deployments"
    echo
    echo "  3) Minimal Installation (Advanced)"
    echo "     • Uses system Python packages"
    echo "     • Smallest footprint, no virtual environment"
    echo "     • Installation size: ~20 MB"
    echo "     • Best for: Containerized deployments"
    echo "     • Warning: May conflict with system packages"
    echo
    echo "  4) Exit Installation"
    echo
    echo "=================================================================="
    echo
}

# Function to get user selection
get_installation_choice() {
    while true; do
        show_installation_menu
        read -p "$(echo -e ${YELLOW}Enter your choice [1-4]:${NC} )" choice

        case $choice in
            1)
                INSTALL_MODE="full"
                print_status "Selected: Full Installation (~215 MB)"
                echo
                echo "This installation includes:"
                echo "  ✓ Application code and assets (~7 MB)"
                echo "  ✓ Python virtual environment (~107 MB)"
                echo "  ✓ Git repository with full history (~101 MB)"
                echo
                echo "You will be able to update using: git pull origin main"
                echo
                read -p "$(echo -e ${YELLOW}Continue with Full Installation? [y/N]:${NC} )" confirm
                [[ $confirm =~ ^[Yy]$ ]] && return 0
                ;;
            2)
                INSTALL_MODE="production"
                print_status "Selected: Production Deployment (~114 MB)"
                echo
                echo "This installation includes:"
                echo "  ✓ Application code and assets (~7 MB)"
                echo "  ✓ Python virtual environment (~107 MB)"
                echo "  ✗ Git repository removed (saves ~101 MB)"
                echo
                echo "Note: Updates require manual download of new version"
                echo
                read -p "$(echo -e ${YELLOW}Continue with Production Deployment? [y/N]:${NC} )" confirm
                [[ $confirm =~ ^[Yy]$ ]] && return 0
                ;;
            3)
                INSTALL_MODE="minimal"
                print_warning "Selected: Minimal Installation (~20 MB)"
                echo
                echo "This installation includes:"
                echo "  ✓ Application code and assets (~7 MB)"
                echo "  ✓ System Python packages (~13 MB)"
                echo "  ✗ Virtual environment not created"
                echo "  ✗ Git repository not included"
                echo
                print_warning "WARNING: This method may cause package conflicts!"
                print_warning "Not recommended for production use."
                echo
                read -p "$(echo -e ${YELLOW}Are you sure you want to continue? [y/N]:${NC} )" confirm
                [[ $confirm =~ ^[Yy]$ ]] && return 0
                ;;
            4)
                print_status "Installation cancelled by user."
                exit 0
                ;;
            *)
                print_error "Invalid choice. Please enter 1, 2, 3, or 4."
                sleep 2
                ;;
        esac
    done
}

# Main installation function
main() {
    # Show installation menu and get user choice
    get_installation_choice

    echo "=================================================================="
    echo "STARTING INSTALLATION - $INSTALL_MODE MODE"
    echo "=================================================================="
    echo
    echo "This script will install the VAST As-Built Report Generator on your Mac."
    echo "The installation includes Python, dependencies, and creates shortcuts."
    echo
    echo "📋 Installation will be logged to: $LOG_FILE"
    echo
    read -p "Do you want to continue? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! $REPLY == "" ]]; then
        print_status "Installation cancelled by user"
        exit 0
    fi

    # Check macOS version
    check_macos_version

    # Install Homebrew
    install_homebrew

    # Install Python
    install_python

    # Install system dependencies
    install_system_dependencies

    # Setup project
    setup_project

    # Create virtual environment
    create_virtual_environment

    # Install Python dependencies
    install_python_dependencies

    # Setup configuration
    setup_configuration

    # Create launch script
    create_launch_script

    # Create desktop shortcut
    create_desktop_shortcut

    # Test installation
    test_installation

    # Display installation summary
    display_installation_summary
}

# Run main function
main "$@"
