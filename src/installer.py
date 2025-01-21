#!/usr/bin/env python3
"""
NurOS APG Package Installer
Installation Logic

Author: AnmiTaliDev
Date: 2025-01-21 13:21:10
License: GNU GPL v3
"""

import os
import json
import shutil
import tarfile
import hashlib
import logging
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal, QThread

class PackageError(Exception):
    """Base exception for package-related errors"""
    pass

class DependencyError(PackageError):
    """Exception for dependency-related errors"""
    pass

class ValidationError(PackageError):
    """Exception for validation-related errors"""
    pass

class Package:
    """APG package representation"""
    def __init__(self, path: Path):
        self.path = path
        self.temp_dir = None
        self.metadata = {}
        self.md5sums = {}
        
    def extract(self) -> Path:
        """Extract package to temporary directory"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="apginstall-"))
        
        with tarfile.open(self.path, "r:xz") as tar:
            tar.extractall(self.temp_dir)
            
        # Load metadata
        metadata_path = self.temp_dir / "metadata.json"
        if not metadata_path.exists():
            raise ValidationError("metadata.json not found in package")
            
        with open(metadata_path) as f:
            self.metadata = json.load(f)
            
        # Load MD5 sums if present
        md5sums_path = self.temp_dir / "md5sums"
        if md5sums_path.exists():
            with open(md5sums_path) as f:
                for line in f:
                    hashsum, path = line.strip().split("  ", 1)
                    self.md5sums[path] = hashsum
                    
        return self.temp_dir
        
    def cleanup(self) -> None:
        """Clean up temporary files"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            
    def __str__(self) -> str:
        return f"{self.metadata.get('name', 'Unknown')} {self.metadata.get('version', 'Unknown')}"

class Installer(QObject):
    """Package installer"""
    progress_updated = Signal(int)
    log_message = Signal(str)
    installation_completed = Signal()
    installation_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.system_root = Path("/")
        self.backup_dir = Path("/var/lib/nuros/backups")
        self.log_dir = Path("/var/lib/nuros/logs")
        self.db_file = Path("/var/lib/nuros/packages.db")
        
        # Ensure directories exist
        for directory in [self.backup_dir, self.log_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def verify_checksums(self, package: Package) -> bool:
        """Verify package file checksums"""
        if not package.md5sums:
            return True
            
        self.log_message.emit("Verifying package checksums...")
        
        for file_path, expected_hash in package.md5sums.items():
            full_path = package.temp_dir / file_path
            if not full_path.exists():
                raise ValidationError(f"File not found: {file_path}")
                
            with open(full_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash != expected_hash:
                    raise ValidationError(f"Checksum mismatch for {file_path}")
                    
        return True

    def verify_dependencies(self, package: Package) -> bool:
        """Verify package dependencies"""
        if 'dependencies' not in package.metadata:
            return True
            
        self.log_message.emit("Checking dependencies...")
        
        for dep in package.metadata['dependencies']:
            name = dep['name']
            version = dep['version']
            condition = dep.get('condition', '>=')
            
            # TODO: Implement actual dependency checking
            # For now, just log the dependency
            self.log_message.emit(f"Required: {name} {condition} {version}")
            
        return True

    def create_backup(self, package: Package) -> None:
        """Create backup of files that will be overwritten"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{package.metadata['name']}_{timestamp}.tar.xz"
        
        self.log_message.emit("Creating backup...")
        
        with tarfile.open(backup_path, "w:xz") as tar:
            data_dir = package.temp_dir / "data"
            if data_dir.exists():
                for src in data_dir.rglob("*"):
                    if src.is_file():
                        dst = self.system_root / src.relative_to(data_dir)
                        if dst.exists():
                            tar.add(dst, src.relative_to(data_dir))

    def run_script(self, script_path: Path, env: Dict[str, str] = None) -> bool:
        """Run installation script"""
        if not script_path.exists():
            return True
            
        script_name = script_path.name
        self.log_message.emit(f"Running {script_name}...")
        
        try:
            env = env or {}
            env.update(os.environ)
            env["PACKAGE_ROOT"] = str(script_path.parent.parent)
            
            subprocess.run(
                [str(script_path)],
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            return True
            
        except subprocess.CalledProcessError as e:
            raise PackageError(f"{script_name} failed: {e.stderr}")

    def copy_files(self, source_dir: Path, target_dir: Path) -> None:
        """Copy package files to system"""
        if not source_dir.exists():
            return
            
        self.log_message.emit("Copying files...")
        
        for src in source_dir.rglob("*"):
            if src.is_file():
                dst = target_dir / src.relative_to(source_dir)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    def register_package(self, package: Package) -> None:
        """Register package in system database"""
        # TODO: Implement package registration
        pass

    def install_package(self, package_path: Path) -> bool:
        """Install single package"""
        package = Package(package_path)
        
        try:
            # Extract package
            self.log_message.emit(f"Extracting {package_path.name}...")
            package.extract()
            self.progress_updated.emit(10)

            # Verify checksums
            self.verify_checksums(package)
            self.progress_updated.emit(20)

            # Check dependencies
            self.verify_dependencies(package)
            self.progress_updated.emit(30)

            # Create backup
            self.create_backup(package)
            self.progress_updated.emit(40)

            # Run preinstall script
            self.run_script(package.temp_dir / "scripts" / "preinstall")
            self.progress_updated.emit(50)

            # Copy files
            self.copy_files(package.temp_dir / "data", self.system_root)
            self.progress_updated.emit(70)

            # Run postinstall script
            self.run_script(package.temp_dir / "scripts" / "postinstall")
            self.progress_updated.emit(80)

            # Register package
            self.register_package(package)
            self.progress_updated.emit(90)

            self.log_message.emit(f"Successfully installed {package}")
            return True
            
        except Exception as e:
            self.log_message.emit(f"Failed to install {package}: {str(e)}")
            raise
            
        finally:
            package.cleanup()

class InstallerThread(QThread):
    """Background installation thread"""
    def __init__(self, installer: Installer, packages: List[Path]):
        super().__init__()
        self.installer = installer
        self.packages = packages

    def run(self) -> None:
        """Run installation process"""
        total = len(self.packages)
        success = 0
        
        try:
            for i, package_path in enumerate(self.packages, 1):
                try:
                    if self.installer.install_package(package_path):
                        success += 1
                except Exception as e:
                    logging.error(f"Failed to install {package_path}: {e}")
                    
                progress = (i / total) * 100
                self.installer.progress_updated.emit(int(progress))
                
            if success == total:
                self.installer.installation_completed.emit()
            else:
                self.installer.installation_failed.emit(
                    f"Failed to install {total - success} package(s)"
                )
                
        except Exception as e:
            logging.error(f"Installation thread error: {e}")
            self.installer.installation_failed.emit(str(e))