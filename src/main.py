#!/usr/bin/env python3
"""
NurOS APG Package Installer
Main entry point

Author: AnmiTaliDev
Date: 2025-01-21 13:17:31
License: GNU GPL v3
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui import MainWindow

# Constants
APP_NAME = "NurOS APG Installer"
APP_VERSION = "1.0.0" 
APP_ORGANIZATION = "NurOS"
APP_DOMAIN = "nuros.org"
APP_ID = "org.nuros.apginstall"

# Setup logging
def setup_logging() -> None:
    """Configure logging to file and console"""
    log_dir = Path("/var/log/nuros")
    log_file = log_dir / "apginstall.log"

    try:
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    except PermissionError:
        # Fallback to user's home directory if no permission
        user_log_dir = Path.home() / ".local/share/nuros/log"
        user_log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(user_log_dir / "apginstall.log"),
                logging.StreamHandler()
            ]
        )

def check_root() -> bool:
    """Check if running as root"""
    return os.geteuid() == 0

def validate_packages(paths: List[Path]) -> List[Path]:
    """Validate package paths and return valid ones"""
    valid_packages = []
    
    for path in paths:
        if not path.exists():
            logging.warning(f"Package not found: {path}")
            continue
            
        if not path.is_file():
            logging.warning(f"Not a file: {path}")
            continue
            
        if path.suffix != ".apg":
            logging.warning(f"Not an APG package: {path}")
            continue
            
        valid_packages.append(path)
        
    return valid_packages

def setup_application() -> Optional[QApplication]:
    """Initialize Qt application with proper settings"""
    try:
        app = QApplication(sys.argv)
        
        # Set application info
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName(APP_ORGANIZATION)
        app.setOrganizationDomain(APP_DOMAIN)
        app.setApplicationDisplayName(APP_NAME)
        app.setDesktopFileName(APP_ID)
        
        # Set application icon
        icon_paths = [
            "/usr/share/icons/hicolor/scalable/apps/org.nuros.apginstall.svg",
            "/usr/share/pixmaps/org.nuros.apginstall.png"
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
                break
                
        # Set Qt style to match system
        if os.environ.get("XDG_CURRENT_DESKTOP") in ["GNOME", "Unity"]:
            app.setStyle("adwaita")
        
        return app
        
    except Exception as e:
        logging.error(f"Failed to initialize application: {e}")
        return None

def main() -> int:
    """Main entry point"""
    try:
        # Setup logging
        setup_logging()
        logging.info(f"Starting {APP_NAME} v{APP_VERSION}")
        
        # Check if running as root
        if not check_root():
            logging.error("This application requires root privileges")
            return 1
            
        # Get and validate package paths
        packages = validate_packages([Path(p) for p in sys.argv[1:]])
        
        if not packages:
            logging.error("No valid packages specified")
            return 1
            
        logging.info(f"Found {len(packages)} valid package(s)")
        
        # Initialize application
        app = setup_application()
        if not app:
            return 1
            
        # Create and show main window    
        window = MainWindow(packages)
        window.show()
        
        # Start event loop
        return app.exec()
        
    except KeyboardInterrupt:
        logging.info("Installation cancelled by user")
        return 130
        
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        return 1
        
    finally:
        logging.info("Application exiting")

if __name__ == "__main__":
    sys.exit(main())