#!/usr/bin/env python3
"""
binsmith_gui_enhanced.py - Enhanced GUI frontend for binsmith utility with bin explorer functionality
"""

import sys
import os
import pathlib
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QFileDialog, QTextEdit, QGroupBox, QCheckBox,
                            QListWidget, QAbstractItemView, QSplitter,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QComboBox, QMessageBox, QDialog, QDialogButtonBox,
                            QTabWidget)
from PyQt5.QtCore import Qt

# Import the binsmith functionality
import avb
from binsmith import ViewModes, BinDisplays, get_binview_from_file, create_bin, resolve_path

# Import the bin explorer functionality
from bin_explorer import BinExplorer
from bin_explorer_tab import BinExplorerTab

# Dialog for batch adding bin names
class BatchAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Multiple Bins")
        self.setMinimumSize(500, 300)
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Instructions label
        instr_label = QLabel("Enter one bin name per line:")
        layout.addWidget(instr_label)
        
        # Text area for bin names
        self.text_area = QTextEdit()
        self.text_area.setAcceptRichText(False)
        self.text_area.setPlaceholderText("Bin1\nBin2\nBin3")
        layout.addWidget(self.text_area)
        
        # Output path
        path_layout = QHBoxLayout()
        path_label = QLabel("Output path (optional):")
        self.path_field = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_directory)
        
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_field)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        
        # Option to add .avb extension
        self.add_extension = QCheckBox("Automatically add .avb extension")
        self.add_extension.setChecked(True)
        layout.addWidget(self.add_extension)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory")
        
        if directory:
            self.path_field.setText(directory)
    
    def get_bin_names(self):
        text = self.text_area.toPlainText().strip()
        if not text:
            return []
        
        # Split text by newlines and filter empty lines
        bin_names = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Add extension if checked
        if self.add_extension.isChecked():
            bin_names = [name if name.lower().endswith('.avb') else f"{name}.avb" 
                         for name in bin_names]
        
        return bin_names
    
    def get_output_path(self):
        return self.path_field.text().strip()


class BinsmithGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Binsmith GUI")
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create bins tab
        self.bins_tab = QWidget()
        self.create_bins_tab()
        self.tab_widget.addTab(self.bins_tab, "Create Bins")
        
        # Create bin explorer tab
        self.explorer_tab = BinExplorerTab(log_callback=self.log)
        self.tab_widget.addTab(self.explorer_tab, "Bin Explorer")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Log area (shared across all tabs)
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        
        # Clear log button
        clear_log_button = QPushButton("Clear Log")
        clear_log_button.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_log_button)
        
        # Add log to main layout
        main_layout.addWidget(log_group)
        
        # Set initial size for the log area (about 1/4 of the window)
        main_layout.setStretch(0, 3)  # Tab widget gets 3/4
        main_layout.setStretch(1, 1)  # Log gets 1/4
        
        self.log("Ready to create and explore Avid bins.")
        self.log(f"Default output location: {os.getcwd()}")
    
    def create_bins_tab(self):
        """Create the contents of the bins tab"""
        
        bins_layout = QVBoxLayout(self.bins_tab)
        
        # Create a splitter for better UI organization
        splitter = QSplitter(Qt.Vertical)
        
        # Template section
        template_group = QGroupBox("Template (Optional)")
        template_layout = QVBoxLayout()
        template_group.setLayout(template_layout)
        
        template_file_layout = QHBoxLayout()
        self.template_path = QLineEdit()
        self.template_path.setPlaceholderText("Path to template bin (optional)")
        template_browse = QPushButton("Browse...")
        template_browse.clicked.connect(self.browse_template)
        template_file_layout.addWidget(self.template_path)
        template_file_layout.addWidget(template_browse)
        
        template_layout.addLayout(template_file_layout)
        
        # Template info section
        self.template_info = QTextEdit()
        self.template_info.setReadOnly(True)
        self.template_info.setPlaceholderText("Template bin information will appear here...")
        self.template_info.setMaximumHeight(100)
        template_layout.addWidget(self.template_info)
        
        # Current working directory display
        cwd_layout = QHBoxLayout()
        cwd_label = QLabel("Current Working Directory:")
        self.cwd_display = QLineEdit(os.getcwd())
        self.cwd_display.setReadOnly(True)
        cwd_layout.addWidget(cwd_label)
        cwd_layout.addWidget(self.cwd_display)
        
        # Output bins section
        bins_group = QGroupBox("Output Bins")
        bins_inner_layout = QVBoxLayout()
        bins_group.setLayout(bins_inner_layout)
        
        # Table for bin entries
        self.bins_table = QTableWidget(0, 2)
        self.bins_table.setHorizontalHeaderLabels(["Bin Name", "Output Path"])
        self.bins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Controls for adding bins
        add_bin_layout = QHBoxLayout()
        self.bin_name_entry = QLineEdit()
        self.bin_name_entry.setPlaceholderText("Bin name (e.g., MyBin)")
        
        self.bin_path_entry = QLineEdit()
        self.bin_path_entry.setPlaceholderText("Output path (optional)")
        
        bin_path_browse = QPushButton("Browse...")
        bin_path_browse.clicked.connect(self.browse_output_path)
        
        add_bin_button = QPushButton("Add Bin")
        add_bin_button.clicked.connect(self.add_bin_to_list)
        
        # Add Batch button
        batch_add_button = QPushButton("Add Multiple...")
        batch_add_button.clicked.connect(self.batch_add_bins)
        
        add_bin_layout.addWidget(QLabel("Name:"))
        add_bin_layout.addWidget(self.bin_name_entry)
        add_bin_layout.addWidget(QLabel("Path:"))
        add_bin_layout.addWidget(self.bin_path_entry)
        add_bin_layout.addWidget(bin_path_browse)
        add_bin_layout.addWidget(add_bin_button)
        add_bin_layout.addWidget(batch_add_button)
        
        # Buttons for managing the bin list
        bin_actions_layout = QHBoxLayout()
        remove_bin_button = QPushButton("Remove Selected")
        remove_bin_button.clicked.connect(self.remove_selected_bins)
        
        clear_bins_button = QPushButton("Clear All")
        clear_bins_button.clicked.connect(self.clear_all_bins)
        
        # Batch creation options
        batch_options_layout = QHBoxLayout()
        
        self.add_extension_checkbox = QCheckBox("Auto-add .avb extension")
        self.add_extension_checkbox.setChecked(True)
        
        self.sequence_checkbox = QCheckBox("Create sequence")
        
        self.sequence_start = QLineEdit("1")
        self.sequence_start.setMaximumWidth(60)
        
        self.sequence_end = QLineEdit("10")
        self.sequence_end.setMaximumWidth(60)
        
        sequence_pattern_label = QLabel("Pattern:")
        self.sequence_pattern = QLineEdit("Bin_{}")
        self.sequence_pattern.setToolTip("Use {} where the number should appear")
        
        batch_options_layout.addWidget(self.add_extension_checkbox)
        batch_options_layout.addWidget(self.sequence_checkbox)
        batch_options_layout.addWidget(QLabel("From:"))
        batch_options_layout.addWidget(self.sequence_start)
        batch_options_layout.addWidget(QLabel("To:"))
        batch_options_layout.addWidget(self.sequence_end)
        batch_options_layout.addWidget(sequence_pattern_label)
        batch_options_layout.addWidget(self.sequence_pattern)
        
        generate_sequence_button = QPushButton("Generate Sequence")
        generate_sequence_button.clicked.connect(self.generate_sequence)
        batch_options_layout.addWidget(generate_sequence_button)
        
        bin_actions_layout.addWidget(remove_bin_button)
        bin_actions_layout.addWidget(clear_bins_button)
        
        bins_inner_layout.addLayout(cwd_layout)
        bins_inner_layout.addLayout(add_bin_layout)
        bins_inner_layout.addLayout(batch_options_layout)
        bins_inner_layout.addWidget(self.bins_table)
        bins_inner_layout.addLayout(bin_actions_layout)
        
        # Create button
        create_button = QPushButton("Create All Bins")
        create_button.setMinimumHeight(40)
        create_button.clicked.connect(self.create_bins)
        
        # Add all components to bins tab layout
        bins_layout.addWidget(template_group)
        bins_layout.addWidget(bins_group)
        bins_layout.addWidget(create_button)
    
    def browse_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Template Bin", "", "Avid Bin Files (*.avb)")
        
        if file_path:
            self.template_path.setText(file_path)
            self.update_template_info(file_path)
    
    def browse_output_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory")
        
        if directory:
            self.bin_path_entry.setText(directory)
    
    def batch_add_bins(self):
        """Open dialog to add multiple bins at once"""
        dialog = BatchAddDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            bin_names = dialog.get_bin_names()
            output_path = dialog.get_output_path()
            
            if not bin_names:
                self.log("No valid bin names entered.", error=True)
                return
            
            # Add all bin names to the table
            for bin_name in bin_names:
                row_position = self.bins_table.rowCount()
                self.bins_table.insertRow(row_position)
                
                self.bins_table.setItem(row_position, 0, QTableWidgetItem(bin_name))
                self.bins_table.setItem(row_position, 1, QTableWidgetItem(output_path))
            
            self.log(f"Added {len(bin_names)} bins to the list.")
    
    def update_template_info(self, path):
        try:
            # Get bin view settings
            bin_view, view_mode, bin_display = get_binview_from_file(path)
            
            # Display the information
            info_text = f"Template: {os.path.basename(path)}\n"
            info_text += f"View Setting: {bin_view.get('name', 'Untitled')}\n"
            info_text += f"View Mode: {view_mode.name.title()}\n"
            
            # Display options
            options = BinDisplays.get_options(bin_display)
            if options:
                option_names = [' '.join(opt.name.split('_')).title() for opt in options]
                info_text += f"Display Options: {', '.join(option_names)}"
            
            self.template_info.setText(info_text)
            self.log(f"Template '{os.path.basename(path)}' loaded successfully.")
        
        except Exception as e:
            self.template_info.setText(f"Error loading template: {str(e)}")
            self.log(f"Error loading template: {str(e)}", error=True)
    
    def add_bin_to_list(self):
        bin_name = self.bin_name_entry.text().strip()
        output_path = self.bin_path_entry.text().strip()
        
        if not bin_name:
            self.log("Please enter a bin name.", error=True)
            return
        
        # Add .avb extension if needed and checkbox is checked
        if self.add_extension_checkbox.isChecked() and not bin_name.lower().endswith('.avb'):
            bin_name = f"{bin_name}.avb"
        
        # Insert into table
        row_position = self.bins_table.rowCount()
        self.bins_table.insertRow(row_position)
        
        self.bins_table.setItem(row_position, 0, QTableWidgetItem(bin_name))
        self.bins_table.setItem(row_position, 1, QTableWidgetItem(output_path))
        
        # Clear input fields
        self.bin_name_entry.clear()
        
        self.log(f"Added bin '{bin_name}' to the list.")
    
    def remove_selected_bins(self):
        selected_rows = set()
        for item in self.bins_table.selectedItems():
            selected_rows.add(item.row())
        
        # Remove rows in descending order to avoid index shifting
        for row in sorted(selected_rows, reverse=True):
            bin_name = self.bins_table.item(row, 0).text()
            self.bins_table.removeRow(row)
            self.log(f"Removed bin '{bin_name}' from the list.")
    
    def clear_all_bins(self):
        self.bins_table.setRowCount(0)
        self.log("Cleared all bins from the list.")
    
    def generate_sequence(self):
        if not self.sequence_checkbox.isChecked():
            return
        
        try:
            start = int(self.sequence_start.text())
            end = int(self.sequence_end.text())
            pattern = self.sequence_pattern.text()
            
            if not '{}' in pattern:
                self.log("Pattern must contain {} placeholder for the number.", error=True)
                return
            
            # Clear current bins if requested
            if self.bins_table.rowCount() > 0:
                reply = QMessageBox.question(self, 'Confirmation', 
                    "Do you want to clear existing bins before generating the sequence?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    self.clear_all_bins()
            
            # Add sequence of bins
            output_path = self.bin_path_entry.text().strip()
            for i in range(start, end + 1):
                bin_name = pattern.format(i)
                if self.add_extension_checkbox.isChecked() and not bin_name.lower().endswith('.avb'):
                    bin_name = f"{bin_name}.avb"
                
                row_position = self.bins_table.rowCount()
                self.bins_table.insertRow(row_position)
                
                self.bins_table.setItem(row_position, 0, QTableWidgetItem(bin_name))
                self.bins_table.setItem(row_position, 1, QTableWidgetItem(output_path))
            
            self.log(f"Generated sequence of {end-start+1} bins.")
        
        except ValueError:
            self.log("Please enter valid numbers for sequence start and end.", error=True)
    
    def create_bins(self):
        if self.bins_table.rowCount() == 0:
            self.log("No bins in the list to create.", error=True)
            return
        
        # Get template path if provided
        template_path = self.template_path.text().strip()
        template_data = None
        view_mode = None
        bin_display = None
        
        if template_path:
            try:
                template_data, view_mode, bin_display = get_binview_from_file(template_path)
                self.log(f"Using template '{os.path.basename(template_path)}'.")
            except Exception as e:
                self.log(f"Error loading template: {str(e)}", error=True)
                return
        
        # Process each bin in the table
        success_count = 0
        error_count = 0
        
        for row in range(self.bins_table.rowCount()):
            bin_name = self.bins_table.item(row, 0).text()
            output_path = self.bins_table.item(row, 1).text()
            
            full_path = bin_name
            if output_path:
                full_path = os.path.join(output_path, bin_name)
            
            try:
                path = resolve_path(full_path, allow_existing=False)
                create_bin(path, template_data, view_mode, bin_display)
                self.log(f"Created bin at {path}")
                success_count += 1
            except Exception as e:
                self.log(f"Error creating bin '{bin_name}': {str(e)}", error=True)
                error_count += 1
        
        self.log(f"Bin creation completed. Successfully created {success_count} bins with {error_count} errors.")
    
    def clear_log(self):
        self.log_area.clear()
    
    def log(self, message, error=False):
        """Add message to log area"""
        if error:
            self.log_area.append(f"ERROR: {message}")
        else:
            self.log_area.append(message)
        # Auto-scroll to bottom
        cursor = self.log_area.textCursor()
        cursor.movePosition(cursor.End)
        self.log_area.setTextCursor(cursor)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BinsmithGUI()
    window.show()
    sys.exit(app.exec_())