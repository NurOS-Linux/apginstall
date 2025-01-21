#!/usr/bin/env python3
"""
NurOS APG Package Installer
GUI Components

Author: AnmiTaliDev
Date: 2025-01-21 13:19:12
License: GNU GPL v3
"""

import logging
from pathlib import Path
from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QProgressBar, QTextEdit, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QFont, QTextCursor
from installer import Installer, InstallerThread

class PackageInfoWidget(QFrame):
    """Widget displaying package information"""
    def __init__(self, package_path: Path):
        super().__init__()
        self.package_path = package_path
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            PackageInfoWidget {
                background-color: white;
                border: 1px solid #d1d1d1;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Package name
        name_label = QLabel(package_path.name)
        name_font = QFont()
        name_font.setBold(True)
        name_label.setFont(name_font)
        layout.addWidget(name_label)
        
        # Package size
        size_mb = package_path.stat().st_size / (1024 * 1024)
        size_label = QLabel(f"Size: {size_mb:.1f} MB")
        size_label.setStyleSheet("color: #666666;")
        layout.addWidget(size_label)

class LogWidget(QTextEdit):
    """Enhanced log widget with auto-scroll"""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            LogWidget {
                border: 1px solid #d1d1d1;
                border-radius: 4px;
                background-color: white;
                padding: 5px;
                font-family: monospace;
            }
        """)
        
    def append(self, text: str) -> None:
        """Append text and auto-scroll"""
        super().append(text)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self, packages: List[Path]):
        super().__init__()
        self.packages = packages
        self.setup_ui()
        self.setup_installer()
        
        # Start installation automatically after 1 second
        QTimer.singleShot(1000, self.start_install)
        
    def setup_ui(self) -> None:
        """Setup user interface"""
        # Window properties
        self.setWindowTitle("NurOS APG Installer")
        self.setMinimumSize(600, 500)
        
        # GTK-like style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6f7;
            }
            QProgressBar {
                border: 1px solid #d1d1d1;
                border-radius: 4px;
                background-color: white;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3584e4;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #3584e4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #3d8ff0;
            }
            QPushButton:pressed {
                background-color: #1c71d8;
            }
            QPushButton:disabled {
                background-color: #99c1f1;
            }
            QLabel {
                color: #1a1a1a;
            }
        """)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Installing Packages")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(14)
        header.setFont(header_font)
        layout.addWidget(header)

        # Package list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        packages_widget = QWidget()
        packages_layout = QVBoxLayout(packages_widget)
        packages_layout.setSpacing(8)
        
        for package in self.packages:
            packages_layout.addWidget(PackageInfoWidget(package))
            
        scroll.setWidget(packages_widget)
        layout.addWidget(scroll)

        # Progress section
        progress_label = QLabel("Progress:")
        layout.addWidget(progress_label)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # Log section
        log_label = QLabel("Installation Log:")
        layout.addWidget(log_label)
        
        self.log = LogWidget()
        layout.addWidget(self.log)

        # Buttons
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        
        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.start_install)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.close)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e01b24;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
            QPushButton:pressed {
                background-color: #c01c28;
            }
        """)
        
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.install_button)
        layout.addLayout(buttons)

    def setup_installer(self) -> None:
        """Setup package installer"""
        self.installer = Installer()
        self.installer.progress_updated.connect(self.progress.setValue)
        self.installer.log_message.connect(self.log.append)
        self.installer.installation_completed.connect(self.on_completed)
        self.installer.installation_failed.connect(self.on_failed)

    def start_install(self) -> None:
        """Start package installation"""
        try:
            self.install_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.log.append("Starting installation...")
            
            self.thread = InstallerThread(self.installer, self.packages)
            self.thread.start()
            
        except Exception as e:
            logging.error(f"Failed to start installation: {e}")
            self.on_failed(str(e))

    def on_completed(self) -> None:
        """Handle successful installation"""
        self.log.append("Installation completed successfully")
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Installation Complete")
        msg.setText("All packages were installed successfully.")
        msg.setStandardButtons(QMessageBox.Ok)
        
        self.install_button.setText("Close")
        self.install_button.setEnabled(True)
        self.install_button.clicked.disconnect()
        self.install_button.clicked.connect(self.close)
        
        self.cancel_button.setEnabled(False)
        
        msg.exec()

    def on_failed(self, error: str) -> None:
        """Handle installation failure"""
        self.log.append(f"Error: {error}")
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Installation Failed")
        msg.setText("Failed to install packages.")
        msg.setDetailedText(error)
        msg.setStandardButtons(QMessageBox.Close)
        
        self.install_button.setText("Close")
        self.install_button.setEnabled(True)
        self.install_button.clicked.disconnect()
        self.install_button.clicked.connect(self.close)
        
        self.cancel_button.setEnabled(False)
        
        msg.exec()

    def closeEvent(self, event) -> None:
        """Handle window close"""
        if hasattr(self, 'thread') and self.thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Installation is in progress. Are you sure you want to cancel?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.thread.terminate()
                self.thread.wait()
                event.accept()
            else:
                event.ignore()