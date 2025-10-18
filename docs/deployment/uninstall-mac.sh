#!/bin/bash

################################################################################
# VAST As-Built Report Generator - macOS Uninstall Script
################################################################################
#
# Purpose: Clean uninstallation of the VAST As-Built Report Generator
# Platform: macOS (Intel and Apple Silicon)
# Requirements: bash, git (optional for repo removal)
#
# Usage:
#   chmod +x uninstall-mac.sh
#   ./uninstall-mac.sh
#
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default installation directory
DEFAULT_INSTALL_DIR="$HOME/vast-reporter"

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  VAST As-Built Report Generator - macOS Uninstaller${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${BLUE}▶ $1${NC}"
    echo "─────────────────────────────────────────────────────────────"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "  $1"
}

confirm_action() {
    local prompt="$1"
    local response

    while true; do
        read -p "$(echo -e ${YELLOW}${prompt}${NC}) [y/N]: " response
        case "$response" in
            [yY]|[yY][eE][sS])
                return 0
                ;;
            [nN]|[nN][oO]|"")
                return 1
                ;;
            *)
                print_warning "Please answer yes (y) or no (n)."
                ;;
        esac
    done
}

################################################################################
# Uninstallation Functions
################################################################################

find_installation() {
    print_section "Locating Installation"

    # Check default location
    if [ -d "$DEFAULT_INSTALL_DIR" ]; then
        INSTALL_DIR="$DEFAULT_INSTALL_DIR"
        print_success "Found installation at: $INSTALL_DIR"
        return 0
    fi

    # Check current directory
    if [ -f "./src/main.py" ] && [ -f "./requirements.txt" ]; then
        INSTALL_DIR="$(pwd)"
        print_success "Found installation at: $INSTALL_DIR"
        return 0
    fi

    # Ask user for custom location
    print_warning "Installation not found in default location"
    read -p "Enter installation directory path (or press Enter to skip): " custom_dir

    if [ -n "$custom_dir" ] && [ -d "$custom_dir" ]; then
        INSTALL_DIR="$custom_dir"
        print_success "Using custom location: $INSTALL_DIR"
        return 0
    fi

    print_error "Installation directory not found"
    return 1
}

check_running_processes() {
    print_section "Checking for Running Processes"

    if pgrep -f "src.main" > /dev/null 2>&1; then
        print_warning "VAST Report Generator processes are running"

        if confirm_action "Stop running processes?"; then
            pkill -f "src.main" || true
            sleep 2
            print_success "Processes stopped"
        else
            print_warning "Processes still running - uninstall may be incomplete"
        fi
    else
        print_success "No running processes found"
    fi
}

backup_data() {
    print_section "Backup Data"

    if [ ! -d "$INSTALL_DIR" ]; then
        print_warning "Installation directory not found, skipping backup"
        return 0
    fi

    local has_data=false

    # Check for reports
    if [ -d "$INSTALL_DIR/reports" ] && [ "$(ls -A $INSTALL_DIR/reports 2>/dev/null)" ]; then
        has_data=true
    fi

    # Check for output
    if [ -d "$INSTALL_DIR/output" ] && [ "$(ls -A $INSTALL_DIR/output 2>/dev/null)" ]; then
        has_data=true
    fi

    # Check for logs
    if [ -d "$INSTALL_DIR/logs" ] && [ "$(ls -A $INSTALL_DIR/logs 2>/dev/null)" ]; then
        has_data=true
    fi

    # Check for config
    if [ -f "$INSTALL_DIR/config/config.yaml" ]; then
        has_data=true
    fi

    if [ "$has_data" = true ]; then
        print_warning "Found user data (reports, logs, config)"

        if confirm_action "Create backup before uninstalling?"; then
            local backup_dir="$HOME/vast-reporter-backup-$(date +%Y%m%d_%H%M%S)"
            mkdir -p "$backup_dir"

            # Backup reports
            if [ -d "$INSTALL_DIR/reports" ]; then
                cp -r "$INSTALL_DIR/reports" "$backup_dir/" 2>/dev/null || true
                print_info "Backed up reports"
            fi

            # Backup output
            if [ -d "$INSTALL_DIR/output" ]; then
                cp -r "$INSTALL_DIR/output" "$backup_dir/" 2>/dev/null || true
                print_info "Backed up output"
            fi

            # Backup logs
            if [ -d "$INSTALL_DIR/logs" ]; then
                cp -r "$INSTALL_DIR/logs" "$backup_dir/" 2>/dev/null || true
                print_info "Backed up logs"
            fi

            # Backup config
            if [ -f "$INSTALL_DIR/config/config.yaml" ]; then
                mkdir -p "$backup_dir/config"
                cp "$INSTALL_DIR/config/config.yaml" "$backup_dir/config/" 2>/dev/null || true
                print_info "Backed up configuration"
            fi

            print_success "Backup created at: $backup_dir"
            BACKUP_CREATED="$backup_dir"
        fi
    else
        print_info "No user data found to backup"
    fi
}

remove_virtual_environment() {
    print_section "Removing Virtual Environment"

    if [ -d "$INSTALL_DIR/venv" ]; then
        # Deactivate if active
        if [[ "$VIRTUAL_ENV" == "$INSTALL_DIR/venv" ]]; then
            deactivate 2>/dev/null || true
        fi

        rm -rf "$INSTALL_DIR/venv"
        print_success "Virtual environment removed"
    else
        print_info "No virtual environment found"
    fi
}

remove_installation_directory() {
    print_section "Removing Installation"

    if [ ! -d "$INSTALL_DIR" ]; then
        print_warning "Installation directory not found"
        return 0
    fi

    print_warning "This will permanently delete: $INSTALL_DIR"

    if confirm_action "Remove installation directory?"; then
        # Remove the entire directory
        rm -rf "$INSTALL_DIR"
        print_success "Installation directory removed"
        return 0
    else
        print_info "Installation directory preserved"
        return 1
    fi
}

remove_shell_configurations() {
    print_section "Cleaning Shell Configurations"

    local modified=false

    # Check and clean .bashrc
    if [ -f "$HOME/.bashrc" ]; then
        if grep -q "vast-reporter" "$HOME/.bashrc" 2>/dev/null; then
            if confirm_action "Remove VAST reporter entries from .bashrc?"; then
                sed -i.bak '/vast-reporter/d' "$HOME/.bashrc"
                print_success "Cleaned .bashrc"
                modified=true
            fi
        fi
    fi

    # Check and clean .bash_profile
    if [ -f "$HOME/.bash_profile" ]; then
        if grep -q "vast-reporter" "$HOME/.bash_profile" 2>/dev/null; then
            if confirm_action "Remove VAST reporter entries from .bash_profile?"; then
                sed -i.bak '/vast-reporter/d' "$HOME/.bash_profile"
                print_success "Cleaned .bash_profile"
                modified=true
            fi
        fi
    fi

    # Check and clean .zshrc
    if [ -f "$HOME/.zshrc" ]; then
        if grep -q "vast-reporter" "$HOME/.zshrc" 2>/dev/null; then
            if confirm_action "Remove VAST reporter entries from .zshrc?"; then
                sed -i.bak '/vast-reporter/d' "$HOME/.zshrc"
                print_success "Cleaned .zshrc"
                modified=true
            fi
        fi
    fi

    if [ "$modified" = false ]; then
        print_info "No shell configuration entries found"
    fi
}

remove_symlinks() {
    print_section "Removing Symlinks"

    local removed=false

    # Check common bin directories
    local bin_dirs=(
        "$HOME/bin"
        "$HOME/.local/bin"
        "/usr/local/bin"
    )

    for bin_dir in "${bin_dirs[@]}"; do
        if [ -L "$bin_dir/vast-reporter" ]; then
            if confirm_action "Remove symlink from $bin_dir?"; then
                rm -f "$bin_dir/vast-reporter"
                print_success "Removed symlink from $bin_dir"
                removed=true
            fi
        fi
    done

    if [ "$removed" = false ]; then
        print_info "No symlinks found"
    fi
}

clean_system_logs() {
    print_section "Cleaning System Logs"

    # Check for system-wide logs
    if [ -d "/var/log/vast-reporter" ]; then
        if confirm_action "Remove system logs from /var/log/vast-reporter?"; then
            sudo rm -rf "/var/log/vast-reporter"
            print_success "System logs removed"
        fi
    else
        print_info "No system logs found"
    fi
}

display_summary() {
    print_section "Uninstallation Summary"

    echo ""
    print_success "Uninstallation completed successfully!"
    echo ""

    if [ -n "$BACKUP_CREATED" ]; then
        print_info "Backup Location: $BACKUP_CREATED"
        print_info "  - Reports, logs, and configuration have been preserved"
        echo ""
    fi

    print_info "The following items were removed:"
    print_info "  ✓ Installation directory"
    print_info "  ✓ Virtual environment"
    print_info "  ✓ Python dependencies"
    echo ""

    print_info "What remains (if any):"
    print_info "  • User backups (if created)"
    print_info "  • Shell configuration backups (.bak files)"
    echo ""

    print_warning "Note: You may need to restart your terminal or run:"
    print_info "  source ~/.bashrc  # or ~/.zshrc, ~/.bash_profile"
    echo ""
}

################################################################################
# Main Uninstallation Process
################################################################################

main() {
    print_header

    # Check if running as root (not recommended)
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root is not recommended"
        if ! confirm_action "Continue anyway?"; then
            print_error "Uninstallation cancelled"
            exit 1
        fi
    fi

    # Step 1: Find installation
    if ! find_installation; then
        print_error "Cannot proceed without installation directory"
        exit 1
    fi

    # Confirm uninstallation
    echo ""
    print_warning "This will uninstall the VAST As-Built Report Generator"
    print_warning "Installation: $INSTALL_DIR"
    echo ""

    if ! confirm_action "Proceed with uninstallation?"; then
        print_error "Uninstallation cancelled by user"
        exit 0
    fi

    # Step 2: Check for running processes
    check_running_processes

    # Step 3: Backup data
    backup_data

    # Step 4: Remove virtual environment
    remove_virtual_environment

    # Step 5: Clean shell configurations
    remove_shell_configurations

    # Step 6: Remove symlinks
    remove_symlinks

    # Step 7: Clean system logs
    clean_system_logs

    # Step 8: Remove installation directory
    remove_installation_directory

    # Display summary
    display_summary

    print_success "Uninstallation complete!"
    echo ""
}

################################################################################
# Error Handling
################################################################################

trap 'echo -e "\n${RED}Uninstallation interrupted${NC}"; exit 130' INT TERM

################################################################################
# Execute Main
################################################################################

main "$@"

exit 0
