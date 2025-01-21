#!/usr/bin/env bash
# NurOS APG Package Installer Build Script
# Created: 2025-01-21 13:40:38
# Author: AnmiTaliDev

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Application info
APP_NAME="nuros-apginstall"
APP_VERSION="1.0.0"
APP_ID="org.nuros.apginstall"

# Original user detection
ORIGINAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(getent passwd "$ORIGINAL_USER" | cut -d: -f6)

# Check root
[[ $EUID -ne 0 ]] && log_error "This script must be run as root"

# Check dependencies
check_deps() {
    log_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 is not installed"
    fi
    
    # Check Python version without bc
    PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info[0]}{sys.version_info[1]}")')
    if [ "$PYTHON_VER" -lt 310 ]; then
        log_error "Python 3.10 or higher is required"
    fi
    
    # Check required Python modules using user's Python environment
    if ! sudo -u "$ORIGINAL_USER" python3 -c "import PySide6" 2>/dev/null; then
        log_error "PySide6 module is not installed for user $ORIGINAL_USER"
    fi
    
    if ! sudo -u "$ORIGINAL_USER" python3 -c "import nuitka" 2>/dev/null; then
        log_error "Nuitka module is not installed for user $ORIGINAL_USER"
    fi
    
    # Check system tools
    if ! command -v clang &>/dev/null; then
        log_error "clang is not installed"
    fi
    
    if ! command -v make &>/dev/null; then
        log_error "make is not installed"
    fi
    
    log_success "All dependencies found"
}

# Build application
build_app() {
    log_info "Building application..."
    
    # Clean and create build directory
    rm -rf build/
    mkdir -p build/
    chown "$ORIGINAL_USER:$ORIGINAL_USER" build/
    
    # Copy source files
    cp src/*.py build/
    chown -R "$ORIGINAL_USER:$ORIGINAL_USER" build/
    
    # Create temporary build directory with correct permissions
    BUILD_TMP=$(mktemp -d)
    chown "$ORIGINAL_USER:$ORIGINAL_USER" "$BUILD_TMP"
    
    # Build with Nuitka using user's Python environment
    cd build
    sudo -u "$ORIGINAL_USER" \
        TMPDIR="$BUILD_TMP" \
        HOME="$USER_HOME" \
        python3 -m nuitka \
        --follow-imports \
        --plugin-enable=pyside6 \
        --include-package=PySide6 \
        --clang \
        --static-libpython=no \
        --onefile \
        --output-filename="$APP_NAME" \
        --company-name="NurOS" \
        --product-name="APG Package Installer" \
        --file-version="$APP_VERSION" \
        main.py
        
    cd ..
    
    # Cleanup temp directory
    rm -rf "$BUILD_TMP"
}

# Install application
install_app() {
    log_info "Installing application..."
    
    # Create directories
    mkdir -p /usr/bin
    mkdir -p /usr/share/applications
    mkdir -p /usr/share/mime/packages
    mkdir -p /var/lib/nuros/{backups,packages}
    mkdir -p /var/log/nuros
    
    # Install binary
    install -m 755 build/$APP_NAME /usr/bin/$APP_NAME
    
    # Install desktop file
    cat > /usr/share/applications/$APP_ID.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=NurOS APG Installer
GenericName=Package Installer
Comment=Install NurOS APG packages
Exec=nuros-apginstall %F
Icon=system-software-install
MimeType=application/x-apg;
Categories=System;PackageManager;GTK;
Terminal=false
StartupNotify=true
EOF
    
    # Install MIME type
    cat > /usr/share/mime/packages/$APP_ID.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
    <mime-type type="application/x-apg">
        <comment>NurOS Package</comment>
        <glob pattern="*.apg"/>
        <icon name="package-x-generic"/>
    </mime-type>
</mime-info>
EOF
    
    # Update MIME and desktop databases
    if command -v update-mime-database &>/dev/null; then
        update-mime-database /usr/share/mime
    fi
    
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database
    fi
    
    # Set permissions
    chown -R root:root /var/lib/nuros
    chmod -R 755 /var/lib/nuros
    chown -R root:root /var/log/nuros
    chmod -R 755 /var/log/nuros
}

# Main function
main() {
    log_info "Starting build process for $APP_NAME v$APP_VERSION"
    
    # Check dependencies
    check_deps
    
    # Build and install
    build_app
    install_app
    
    log_success "Installation completed successfully!"
    log_info "You can now install .apg packages by double-clicking them"
}

# Error handling
set -e
trap 'log_error "An error occurred. Exiting..."' ERR

# Run main
main "$@"