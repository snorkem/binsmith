#!/usr/bin/env python3
"""
bin_explorer_tab.py - GUI tab for exploring Avid bin files
"""

import os
import sys
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QFileDialog, QTextEdit, 
                            QGroupBox, QTreeWidget, QTreeWidgetItem, 
                            QSplitter, QTableWidget, QTableWidgetItem, 
                            QHeaderView, QTabWidget, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap

from bin_explorer import BinExplorer

class BinExplorerTab(QWidget):
    """Tab for exploring Avid bin files"""
    
    def __init__(self, parent=None, log_callback=None):
        super().__init__(parent)
        self.log_callback = log_callback
        self.bin_explorer = BinExplorer()
        self.current_bin_path = None
        self.metadata = None
        
        self.init_ui()
    
    def log(self, message, error=False):
        """Log a message using the parent's log function if available"""
        if self.log_callback:
            self.log_callback(message, error)
        else:
            print(f"{'ERROR: ' if error else ''}{message}")
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Bin file selection section
        input_group = QGroupBox("Bin File")
        input_layout = QVBoxLayout()
        input_group.setLayout(input_layout)
        
        file_layout = QHBoxLayout()
        self.bin_path_field = QLineEdit()
        self.bin_path_field.setPlaceholderText("Path to .avb file")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_bin_file)
        load_btn = QPushButton("Load Bin")
        load_btn.clicked.connect(self.load_bin)
        file_layout.addWidget(self.bin_path_field)
        file_layout.addWidget(browse_btn)
        file_layout.addWidget(load_btn)
        input_layout.addLayout(file_layout)
        
        # Bin summary info
        summary_layout = QHBoxLayout()
        self.bin_summary = QLabel("No bin file loaded")
        self.bin_summary.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.bin_summary)
        input_layout.addLayout(summary_layout)
        
        # Create a splitter for the main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Tree view of metadata
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabel("Bin Structure")
        self.metadata_tree.setMinimumWidth(250)
        self.metadata_tree.itemClicked.connect(self.on_tree_item_clicked)
        content_splitter.addWidget(self.metadata_tree)
        
        # Right side: Tabbed view for details
        details_tabs = QTabWidget()
        
        # Details tab
        self.details_widget = QTextEdit()
        self.details_widget.setReadOnly(True)
        details_tabs.addTab(self.details_widget, "Details")
        
        # Table view tab
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Property", "Value"])
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        details_tabs.addTab(self.table_widget, "Properties")
        
        # JSON view tab
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setFont(QFont("Courier New", 10))
        details_tabs.addTab(self.json_view, "Raw JSON")
        
        content_splitter.addWidget(details_tabs)
        
        # Set initial sizes for splitter
        content_splitter.setSizes([300, 700])
        
        # Export section
        export_layout = QHBoxLayout()
        export_btn = QPushButton("Export Metadata to JSON")
        export_btn.clicked.connect(self.export_metadata)
        export_layout.addStretch()
        export_layout.addWidget(export_btn)
        
        # Add all components to the main layout
        main_layout.addWidget(input_group)
        main_layout.addWidget(content_splitter)
        main_layout.addLayout(export_layout)
        
        # Set stretch factors
        main_layout.setStretch(0, 0)  # Input group
        main_layout.setStretch(1, 1)  # Content splitter
        main_layout.setStretch(2, 0)  # Export button
    
    def browse_bin_file(self):
        """Open file dialog to select an Avid bin file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Avid Bin File", "", "Avid Bin Files (*.avb)")
        
        if file_path:
            self.bin_path_field.setText(file_path)
    
    def load_bin(self):
        """Load the selected bin file and extract metadata"""
        bin_path = self.bin_path_field.text().strip()
        
        if not bin_path:
            self.log("Please select a bin file to load", error=True)
            return
        
        if not os.path.exists(bin_path):
            self.log(f"File does not exist: {bin_path}", error=True)
            return
        
        try:
            # Reset previous state
            self.metadata_tree.clear()
            self.details_widget.clear()
            self.table_widget.setRowCount(0)
            self.json_view.clear()
            
            # Load and extract metadata
            self.bin_explorer = BinExplorer(bin_path)
            self.bin_explorer.open_bin()
            self.metadata = self.bin_explorer.extract_all_metadata()
            self.bin_explorer.close_bin()
            
            # Update UI with basic info
            self.current_bin_path = bin_path
            basic_info = self.metadata.get('basic_info', {})
            bin_name = basic_info.get('filename', os.path.basename(bin_path))
            view_mode = basic_info.get('view_mode', 'Unknown')
            
            self.bin_summary.setText(f"Loaded: {bin_name} ({view_mode} view)")
            
            # Populate tree view
            self.populate_metadata_tree()
            
            # Show basic info in the details view
            self.show_basic_info()
            
            self.log(f"Successfully loaded bin: {bin_path}")
        
        except Exception as e:
            self.log(f"Error loading bin file: {str(e)}", error=True)
            QMessageBox.critical(self, "Error", f"Error loading bin file: {str(e)}")
    
    def populate_metadata_tree(self):
        """Populate the tree view with metadata structure"""
        if not self.metadata:
            return
        
        # Add root items
        basic_info_item = QTreeWidgetItem(self.metadata_tree, ["Bin Information"])
        basic_info_item.setData(0, Qt.UserRole, {"type": "basic_info"})
        basic_info_item.setIcon(0, self.get_icon("bin"))
        
        clips_item = QTreeWidgetItem(self.metadata_tree, ["Clips"])
        clips_item.setData(0, Qt.UserRole, {"type": "clips_root"})
        clips_item.setIcon(0, self.get_icon("clips"))
        
        sequences_item = QTreeWidgetItem(self.metadata_tree, ["Sequences"])
        sequences_item.setData(0, Qt.UserRole, {"type": "sequences_root"})
        sequences_item.setIcon(0, self.get_icon("sequences"))
        
        # Add clips
        clips = self.metadata.get('clips', [])
        for i, clip in enumerate(clips):
            clip_name = clip.get('name', f"Clip {i+1}")
            clip_type = clip.get('type', 'Unknown')
            
            if clip_type == 'CompositionMob':
                # Skip sequences, they'll be added to the sequences section
                continue
            
            clip_item = QTreeWidgetItem(clips_item, [clip_name])
            clip_item.setData(0, Qt.UserRole, {"type": "clip", "index": i})
            
            # Set icon based on clip type
            if clip_type == 'MasterMob':
                clip_item.setIcon(0, self.get_icon("master_clip"))
            elif clip_type == 'SourceMob':
                clip_item.setIcon(0, self.get_icon("source"))
            else:
                clip_item.setIcon(0, self.get_icon("clip"))
            
            # Add child items for clip properties
            if 'media_info' in clip and clip['media_info']:
                media_item = QTreeWidgetItem(clip_item, ["Media Information"])
                media_item.setData(0, Qt.UserRole, {"type": "clip_media", "index": i})
                media_item.setIcon(0, self.get_icon("media"))
            
            if 'markers' in clip and clip['markers']:
                markers_item = QTreeWidgetItem(clip_item, [f"Markers ({len(clip['markers'])})"])
                markers_item.setData(0, Qt.UserRole, {"type": "clip_markers", "index": i})
                markers_item.setIcon(0, self.get_icon("marker"))
            
            if 'user_comments' in clip and clip['user_comments']:
                comments_item = QTreeWidgetItem(clip_item, ["User Comments"])
                comments_item.setData(0, Qt.UserRole, {"type": "clip_comments", "index": i})
                comments_item.setIcon(0, self.get_icon("comment"))
        
        # Add sequences
        sequences = self.metadata.get('sequences', [])
        for i, seq in enumerate(sequences):
            seq_name = seq.get('name', f"Sequence {i+1}")
            seq_item = QTreeWidgetItem(sequences_item, [seq_name])
            seq_item.setData(0, Qt.UserRole, {"type": "sequence", "index": i})
            seq_item.setIcon(0, self.get_icon("sequence"))
            
            # Add tracks
            if 'tracks' in seq and seq['tracks']:
                tracks_item = QTreeWidgetItem(seq_item, [f"Tracks ({len(seq['tracks'])})"])
                tracks_item.setData(0, Qt.UserRole, {"type": "sequence_tracks", "index": i})
                tracks_item.setIcon(0, self.get_icon("tracks"))
                
                # Add individual tracks
                for j, track in enumerate(seq['tracks']):
                    track_name = track.get('name', f"Track {j+1}")
                    track_type = track.get('type', 'Unknown')
                    
                    track_item = QTreeWidgetItem(tracks_item, [f"{track_name} ({track_type})"])
                    track_item.setData(0, Qt.UserRole, {"type": "sequence_track", "seq_index": i, "track_index": j})
                    
                    # Set icon based on track type
                    if track_type == 'video':
                        track_item.setIcon(0, self.get_icon("video_track"))
                    elif track_type == 'audio':
                        track_item.setIcon(0, self.get_icon("audio_track"))
                    else:
                        track_item.setIcon(0, self.get_icon("track"))
        
        # Expand the top-level items
        self.metadata_tree.expandItem(basic_info_item)
        
        # Update counts
        clips_count = len([c for c in clips if c.get('type') != 'CompositionMob'])
        clips_item.setText(0, f"Clips ({clips_count})")
        sequences_item.setText(0, f"Sequences ({len(sequences)})")
    
    def get_icon(self, icon_type):
        """Return an icon for the given type (placeholder for future icons)"""
        # This is a placeholder - in a real app, you would return actual icons
        return QIcon()
    
    def on_tree_item_clicked(self, item, column):
        """Handle clicks on tree items to show appropriate details"""
        if not item:
            return
        
        # Get the item data
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return
        
        item_type = item_data.get('type', '')
        
        # Show different content based on the item type
        if item_type == 'basic_info':
            self.show_basic_info()
        
        elif item_type == 'clips_root':
            self.show_clips_summary()
        
        elif item_type == 'sequences_root':
            self.show_sequences_summary()
        
        elif item_type == 'clip':
            index = item_data.get('index', 0)
            self.show_clip_details(index)
        
        elif item_type == 'clip_media':
            index = item_data.get('index', 0)
            self.show_clip_media(index)
        
        elif item_type == 'clip_markers':
            index = item_data.get('index', 0)
            self.show_clip_markers(index)
        
        elif item_type == 'clip_comments':
            index = item_data.get('index', 0)
            self.show_clip_comments(index)
        
        elif item_type == 'sequence':
            index = item_data.get('index', 0)
            self.show_sequence_details(index)
        
        elif item_type == 'sequence_tracks':
            index = item_data.get('index', 0)
            self.show_sequence_tracks_summary(index)
        
        elif item_type == 'sequence_track':
            seq_index = item_data.get('seq_index', 0)
            track_index = item_data.get('track_index', 0)
            self.show_sequence_track_details(seq_index, track_index)
    
    def show_basic_info(self):
        """Show basic bin information in the details view"""
        if not self.metadata or 'basic_info' not in self.metadata:
            return
        
        basic_info = self.metadata['basic_info']
        
        # Update details text view
        details_text = "# Bin Information\n\n"
        details_text += f"**Filename:** {basic_info.get('filename', 'Unknown')}\n"
        details_text += f"**Path:** {basic_info.get('filepath', 'Unknown')}\n"
        details_text += f"**File Size:** {self.format_file_size(basic_info.get('file_size', 0))}\n"
        details_text += f"**Last Modified:** {basic_info.get('last_modified', 'Unknown')}\n\n"
        details_text += f"**View Mode:** {basic_info.get('view_mode', 'Unknown')}\n"
        
        display_options = basic_info.get('display_options', [])
        if display_options:
            details_text += f"**Display Options:**\n"
            for option in display_options:
                # Format the option name for better readability
                formatted_option = ' '.join(option.split('_')).title()
                details_text += f"- {formatted_option}\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update property table
        self.table_widget.setRowCount(0)
        self.populate_table_from_dict(basic_info)
        
        # Update JSON view
        self.json_view.setText(json.dumps(basic_info, indent=2))
    
    def format_file_size(self, size_bytes):
        """Format file size in a human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def show_clips_summary(self):
        """Show summary of all clips in the bin"""
        if not self.metadata or 'clips' not in self.metadata:
            return
        
        clips = self.metadata['clips']
        clip_types = {}
        
        # Count clip types
        for clip in clips:
            clip_type = clip.get('type', 'Unknown')
            if clip_type == 'CompositionMob':
                continue  # Skip sequences
            clip_types[clip_type] = clip_types.get(clip_type, 0) + 1
        
        # Update details text view
        details_text = "# Clips Summary\n\n"
        details_text += f"**Total Clips:** {sum(clip_types.values())}\n\n"
        details_text += "**Clip Types:**\n"
        for clip_type, count in clip_types.items():
            details_text += f"- {clip_type}: {count}\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update table with all clips
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["Name", "Type", "Creation Date"])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        row = 0
        for clip in clips:
            if clip.get('type') == 'CompositionMob':
                continue  # Skip sequences
                
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(clip.get('name', 'Unnamed')))
            self.table_widget.setItem(row, 1, QTableWidgetItem(clip.get('type', 'Unknown')))
            self.table_widget.setItem(row, 2, QTableWidgetItem(clip.get('creation_time', '')))
            row += 1
        
        # Update JSON view
        clips_list = [clip for clip in clips if clip.get('type') != 'CompositionMob']
        self.json_view.setText(json.dumps(clips_list, indent=2))
    
    def show_sequences_summary(self):
        """Show summary of all sequences in the bin"""
        if not self.metadata or 'sequences' not in self.metadata:
            return
        
        sequences = self.metadata['sequences']
        
        # Update details text view
        details_text = "# Sequences Summary\n\n"
        details_text += f"**Total Sequences:** {len(sequences)}\n\n"
        
        if sequences:
            # Create some basic stats
            track_counts = []
            for seq in sequences:
                if 'tracks' in seq:
                    track_counts.append(len(seq['tracks']))
            
            if track_counts:
                avg_tracks = sum(track_counts) / len(track_counts)
                details_text += f"**Average Tracks per Sequence:** {avg_tracks:.1f}\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update table with all sequences
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["Name", "Tracks", "Creation Date"])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        for row, seq in enumerate(sequences):
            track_count = len(seq.get('tracks', []))
            
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(seq.get('name', 'Unnamed')))
            self.table_widget.setItem(row, 1, QTableWidgetItem(str(track_count)))
            self.table_widget.setItem(row, 2, QTableWidgetItem(seq.get('creation_time', '')))
        
        # Update JSON view
        self.json_view.setText(json.dumps(sequences, indent=2))
    
    def show_clip_details(self, index):
        """Show details for a specific clip"""
        if not self.metadata or 'clips' not in self.metadata:
            return
        
        clips = self.metadata['clips']
        if index >= len(clips):
            return
        
        clip = clips[index]
        
        # Update details text view
        details_text = f"# Clip: {clip.get('name', 'Unnamed')}\n\n"
        details_text += f"**Type:** {clip.get('type', 'Unknown')}\n"
        details_text += f"**Mob ID:** {clip.get('mob_id', 'Unknown')}\n"
        details_text += f"**Creation Time:** {clip.get('creation_time', 'Unknown')}\n\n"
        
        # Add media info if available
        if 'media_info' in clip and clip['media_info']:
            media = clip['media_info']
            details_text += "## Media Information\n\n"
            
            if 'width' in media and 'height' in media:
                details_text += f"**Resolution:** {media['width']}×{media['height']}\n"
            
            if 'frame_rate' in media:
                details_text += f"**Frame Rate:** {media['frame_rate']} fps\n"
            
            if 'duration_frames' in media:
                details_text += f"**Duration:** {media['duration_frames']} frames\n"
            
            if 'frame_layout' in media:
                details_text += f"**Frame Layout:** {media['frame_layout']}\n"
        
        # Add marker count if available
        if 'markers' in clip and clip['markers']:
            marker_count = len(clip['markers'])
            details_text += f"\n**Markers:** {marker_count}\n"
        
        # Add user comments summary if available
        if 'user_comments' in clip and clip['user_comments']:
            comment_count = len(clip['user_comments'])
            details_text += f"\n**User Comments:** {comment_count}\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update property table
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Property", "Value"])
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.populate_table_from_dict(clip)
        
        # Update JSON view
        self.json_view.setText(json.dumps(clip, indent=2))
    
    def show_clip_media(self, index):
        """Show media details for a specific clip"""
        if not self.metadata or 'clips' not in self.metadata:
            return
        
        clips = self.metadata['clips']
        if index >= len(clips) or 'media_info' not in clips[index]:
            return
        
        clip = clips[index]
        media = clip['media_info']
        
        # Update details text view
        details_text = f"# Media Information for: {clip.get('name', 'Unnamed')}\n\n"
        
        if media:
            for key, value in media.items():
                # Format keys for better readability
                key_formatted = ' '.join(key.split('_')).title()
                details_text += f"**{key_formatted}:** {value}\n"
        else:
            details_text += "No media information available for this clip."
        
        self.details_widget.setMarkdown(details_text)
        
        # Update property table
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Property", "Value"])
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.populate_table_from_dict(media)
        
        # Update JSON view
        self.json_view.setText(json.dumps(media, indent=2))
    
    def show_clip_markers(self, index):
        """Show markers for a specific clip"""
        if not self.metadata or 'clips' not in self.metadata:
            return
        
        clips = self.metadata['clips']
        if index >= len(clips) or 'markers' not in clips[index]:
            return
        
        clip = clips[index]
        markers = clip.get('markers', [])
        
        # Update details text view
        details_text = f"# Markers for: {clip.get('name', 'Unnamed')}\n\n"
        details_text += f"**Total Markers:** {len(markers)}\n\n"
        
        if markers:
            details_text += "## Marker List\n\n"
            for i, marker in enumerate(markers):
                pos = marker.get('position', 'Unknown')
                color = marker.get('color', 'Unknown')
                comment = marker.get('comment', '')
                
                details_text += f"### Marker {i+1}\n"
                details_text += f"**Position:** {pos}\n"
                details_text += f"**Color:** {color}\n"
                if comment:
                    details_text += f"**Comment:** {comment}\n"
                details_text += "\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update table with all markers
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["Position", "Color", "Comment"])
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        for row, marker in enumerate(markers):
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(str(marker.get('position', ''))))
            self.table_widget.setItem(row, 1, QTableWidgetItem(marker.get('color', '')))
            self.table_widget.setItem(row, 2, QTableWidgetItem(marker.get('comment', '')))
        
        # Update JSON view
        self.json_view.setText(json.dumps(markers, indent=2))
    
    def show_clip_comments(self, index):
        """Show user comments for a specific clip"""
        if not self.metadata or 'clips' not in self.metadata:
            return
        
        clips = self.metadata['clips']
        if index >= len(clips) or 'user_comments' not in clips[index]:
            return
        
        clip = clips[index]
        comments = clip.get('user_comments', {})
        
        # Update details text view
        details_text = f"# User Comments for: {clip.get('name', 'Unnamed')}\n\n"
        
        if comments:
            for key, value in comments.items():
                details_text += f"**{key}:** {value}\n\n"
        else:
            details_text += "No user comments available for this clip."
        
        self.details_widget.setMarkdown(details_text)
        
        # Update property table
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Field", "Value"])
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.populate_table_from_dict(comments)
        
        # Update JSON view
        self.json_view.setText(json.dumps(comments, indent=2))
    
    def show_sequence_details(self, index):
        """Show details for a specific sequence"""
        if not self.metadata or 'sequences' not in self.metadata:
            return
        
        sequences = self.metadata['sequences']
        if index >= len(sequences):
            return
        
        seq = sequences[index]
        
        # Update details text view
        details_text = f"# Sequence: {seq.get('name', 'Unnamed')}\n\n"
        details_text += f"**Mob ID:** {seq.get('mob_id', 'Unknown')}\n"
        details_text += f"**Creation Time:** {seq.get('creation_time', 'Unknown')}\n\n"
        
        # Add tracks info
        tracks = seq.get('tracks', [])
        details_text += f"**Tracks:** {len(tracks)}\n\n"
        
        if tracks:
            # Count track types
            track_types = {}
            for track in tracks:
                track_type = track.get('type', 'Unknown')
                track_types[track_type] = track_types.get(track_type, 0) + 1
            
            details_text += "## Track Types\n\n"
            for track_type, count in track_types.items():
                details_text += f"- **{track_type}:** {count}\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update property table
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Property", "Value"])
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.populate_table_from_dict(seq)
        
        # Update JSON view
        self.json_view.setText(json.dumps(seq, indent=2))
    
    def show_sequence_tracks_summary(self, index):
        """Show a summary of tracks for a specific sequence"""
        if not self.metadata or 'sequences' not in self.metadata:
            return
        
        sequences = self.metadata['sequences']
        if index >= len(sequences):
            return
        
        seq = sequences[index]
        tracks = seq.get('tracks', [])
        
        # Update details text view
        details_text = f"# Tracks for Sequence: {seq.get('name', 'Unnamed')}\n\n"
        details_text += f"**Total Tracks:** {len(tracks)}\n\n"
        
        if tracks:
            # Count track types
            track_types = {}
            for track in tracks:
                track_type = track.get('type', 'Unknown')
                track_types[track_type] = track_types.get(track_type, 0) + 1
            
            details_text += "## Track Types\n\n"
            for track_type, count in track_types.items():
                details_text += f"- **{track_type}:** {count}\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update table with all tracks
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["Name", "Type", "Length"])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        for row, track in enumerate(tracks):
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(track.get('name', f"Track {row+1}")))
            self.table_widget.setItem(row, 1, QTableWidgetItem(track.get('type', 'Unknown')))
            self.table_widget.setItem(row, 2, QTableWidgetItem(str(track.get('length', ''))))
        
        # Update JSON view
        self.json_view.setText(json.dumps(tracks, indent=2))
    
    def show_sequence_track_details(self, seq_index, track_index):
        """Show details for a specific track in a sequence"""
        if not self.metadata or 'sequences' not in self.metadata:
            return
        
        sequences = self.metadata['sequences']
        if seq_index >= len(sequences):
            return
        
        seq = sequences[seq_index]
        tracks = seq.get('tracks', [])
        
        if track_index >= len(tracks):
            return
        
        track = tracks[track_index]
        
        # Update details text view
        track_name = track.get('name', f"Track {track_index+1}")
        details_text = f"# Track: {track_name}\n\n"
        details_text += f"**Type:** {track.get('type', 'Unknown')}\n"
        details_text += f"**Length:** {track.get('length', 'Unknown')}\n\n"
        
        # Add clips info if available
        clips = track.get('clips', [])
        if clips:
            details_text += f"**Clips in Track:** {len(clips)}\n\n"
            
            details_text += "## Clip List\n\n"
            for i, clip in enumerate(clips):
                details_text += f"### Clip {i+1}\n"
                details_text += f"**Type:** {clip.get('type', 'Unknown')}\n"
                
                if 'start' in clip:
                    details_text += f"**Start:** {clip['start']}\n"
                
                if 'length' in clip:
                    details_text += f"**Length:** {clip['length']}\n"
                
                if 'source_mob_id' in clip:
                    details_text += f"**Source Mob ID:** {clip['source_mob_id']}\n"
                
                details_text += "\n"
        
        self.details_widget.setMarkdown(details_text)
        
        # Update property table
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Property", "Value"])
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.populate_table_from_dict(track)
        
        # Update JSON view
        self.json_view.setText(json.dumps(track, indent=2))
    
    def populate_table_from_dict(self, data_dict):
        """Populate the table widget with key-value pairs from a dictionary"""
        self.table_widget.setRowCount(0)
        
        if not data_dict:
            return
        
        # Add each item to the table
        for row, (key, value) in enumerate(data_dict.items()):
            # Skip nested dictionaries and lists, they're too complex for a simple table
            if isinstance(value, (dict, list)):
                continue
                
            self.table_widget.insertRow(row)
            
            # Format the key for better readability
            if isinstance(key, str):
                key_formatted = ' '.join(key.split('_')).title()
            else:
                key_formatted = str(key)
                
            self.table_widget.setItem(row, 0, QTableWidgetItem(key_formatted))
            self.table_widget.setItem(row, 1, QTableWidgetItem(str(value)))
    
    def export_metadata(self):
        """Export the current metadata to a JSON file"""
        if not self.metadata:
            self.log("No metadata to export", error=True)
            return
        
        if not self.current_bin_path:
            self.log("No bin file currently loaded", error=True)
            return
        
        # Get default output path (same as bin file but with _metadata.json extension)
        default_path = os.path.splitext(self.current_bin_path)[0] + "_metadata.json"
        
        # Open save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Metadata", default_path, "JSON Files (*.json)")
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            
            self.log(f"Metadata exported to: {file_path}")
        except Exception as e:
            self.log(f"Error exporting metadata: {str(e)}", error=True)