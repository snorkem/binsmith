#!/usr/bin/env python3
"""
bin_explorer.py - Module for exploring and extracting metadata from Avid bin files
"""

import os
import sys
import json
from datetime import datetime
import avb
from binsmith import ViewModes, BinDisplays, get_binview_from_file

class BinExplorer:
    """Class for exploring and extracting metadata from Avid bin files"""
    
    def __init__(self, bin_path=None):
        self.bin_path = bin_path
        self.bin_file = None
        self.metadata = {}
    
    def open_bin(self, bin_path=None):
        """Open an Avid bin file and initialize metadata extraction"""
        if bin_path:
            self.bin_path = bin_path
        
        if not self.bin_path:
            raise ValueError("No bin path specified")
        
        try:
            self.bin_file = avb.open(self.bin_path)
            return True
        except Exception as e:
            raise Exception(f"Error opening bin file: {str(e)}")
    
    def close_bin(self):
        """Close the currently open bin file"""
        if self.bin_file:
            self.bin_file.close()
            self.bin_file = None
    
    def extract_basic_info(self):
        """Extract basic information about the bin file"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        basic_info = {
            "filename": os.path.basename(self.bin_path),
            "filepath": self.bin_path,
            "file_size": os.path.getsize(self.bin_path),
            "last_modified": datetime.fromtimestamp(os.path.getmtime(self.bin_path)).strftime("%Y-%m-%d %H:%M:%S"),
            "view_mode": ViewModes(self.bin_file.content.display_mode).name
        }
        
        # Handle display options safely
        try:
            # Only use get_options if display_mask is an IntFlag
            if hasattr(self.bin_file.content, 'display_mask'):
                display_mask = self.bin_file.content.display_mask
                if isinstance(display_mask, int):
                    # Get options safely
                    options = []
                    for opt in BinDisplays:
                        if display_mask & opt.value:
                            options.append(opt.name)
                    basic_info["display_options"] = options
                else:
                    basic_info["display_options"] = []
            else:
                basic_info["display_options"] = []
        except Exception as e:
            basic_info["display_options"] = []
            basic_info["display_options_error"] = str(e)
        
        # Get the bin name and other attributes
        if hasattr(self.bin_file.content, 'name'):
            basic_info["bin_name"] = self.bin_file.content.name
        
        # Get view settings
        if hasattr(self.bin_file.content, 'view_setting') and hasattr(self.bin_file.content.view_setting, 'property_data'):
            view_settings = {}
            
            # Extract view name
            if 'name' in self.bin_file.content.view_setting.property_data:
                view_settings["name"] = self.bin_file.content.view_setting.property_data['name']
            
            # Extract all properties
            for key, value in self.bin_file.content.view_setting.property_data.items():
                # Skip complex objects
                if isinstance(value, (str, int, float, bool)) or value is None:
                    view_settings[key] = value
            
            basic_info["view_settings"] = view_settings
        
        # Extract bin attributes
        if hasattr(self.bin_file.content, 'attributes'):
            attributes = {}
            for key, value in self.bin_file.content.attributes.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    attributes[key] = value
            
            if attributes:
                basic_info["attributes"] = attributes
        
        # Count items by type
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            mob_types = {}
            for mob in mobs_list:
                mob_type = type(mob).__name__
                mob_types[mob_type] = mob_types.get(mob_type, 0) + 1
            
            if mob_types:
                basic_info["item_counts"] = mob_types
                basic_info["total_items"] = len(mobs_list)
        
        # Extract bin creation/modification dates if available
        if hasattr(self.bin_file.content, 'creation_time'):
            basic_info["creation_time"] = self.bin_file.content.creation_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if hasattr(self.bin_file.content, 'last_modified'):
            basic_info["last_modified_bin"] = self.bin_file.content.last_modified.strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to extract Avid version information
        if hasattr(self.bin_file, 'header'):
            header_info = {}
            header = self.bin_file.header
            
            for header_attr in ['major_version', 'minor_version', 'byte_order', 'page_size', 'page_count']:
                if hasattr(header, header_attr):
                    header_info[header_attr] = getattr(header, header_attr)
            
            if header_info:
                basic_info["file_header"] = header_info
        
        self.metadata["basic_info"] = basic_info
        return basic_info
    
    def extract_clips(self):
        """Extract information about clips in the bin"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        clips = []
        
        # Get mob objects (clips, sequences, etc.)
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            for mob in mobs_list:
                # Create a base info dictionary for the mob
                clip_info = {
                    "name": getattr(mob, 'name', 'Unnamed'),
                    "mob_id": str(mob.mob_id) if hasattr(mob, 'mob_id') else None,
                    "type": type(mob).__name__,
                    "creation_time": mob.creation_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'creation_time') else None,
                    "last_modified": mob.last_modified.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'last_modified') else None,
                    "mob_type_id": mob.mob_type_id if hasattr(mob, 'mob_type_id') else None,
                }
                
                # Attempt to extract ALL possible attributes by iterating through 
                # the mob's dictionary, not just the common ones
                if hasattr(mob, '__dict__'):
                    for key, value in mob.__dict__.items():
                        # Skip private attributes
                        if key.startswith('_'):
                            continue
                        
                        # Skip attributes we already processed
                        if key in ['name', 'mob_id', 'creation_time', 'last_modified', 'mob_type_id']:
                            continue
                        
                        # Include simple types directly
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            clip_info[key] = value
                        # For datetime objects, convert to string
                        elif hasattr(value, 'strftime'):
                            try:
                                clip_info[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                pass
                
                # Extract all available attributes from the mob using dir() too
                for attr_name in dir(mob):
                    # Skip private attributes, methods, and already processed ones
                    if attr_name.startswith('_') or callable(getattr(mob, attr_name)) or attr_name in clip_info:
                        continue
                    
                    try:
                        attr_value = getattr(mob, attr_name)
                        # Only include simple types (skip complex objects)
                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                            clip_info[attr_name] = attr_value
                        # For datetime objects, convert to string
                        elif hasattr(attr_value, 'strftime'):
                            clip_info[attr_name] = attr_value.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        # Skip attributes that cause errors
                        pass
                
                # Extract user comments if available
                if hasattr(mob, 'user_comments') and mob.user_comments:
                    try:
                        comments_list = list(mob.user_comments) if hasattr(mob.user_comments, '__iter__') else []
                        clip_info["user_comments"] = {}
                        
                        for comment in comments_list:
                            if hasattr(comment, 'name') and hasattr(comment, 'value'):
                                clip_info["user_comments"][comment.name] = comment.value
                                
                            # Extract all available attributes from each comment
                            for attr_name in dir(comment):
                                if attr_name.startswith('_') or callable(getattr(comment, attr_name)) or attr_name in ['name', 'value']:
                                    continue
                                
                                try:
                                    comment_attr = getattr(comment, attr_name)
                                    if isinstance(comment_attr, (str, int, float, bool)) or comment_attr is None:
                                        clip_info.setdefault("comment_attributes", {}).setdefault(comment.name, {})[attr_name] = comment_attr
                                except Exception:
                                    pass
                    except Exception as e:
                        clip_info["user_comments_error"] = str(e)
                
                # Get media info for clips
                if hasattr(mob, 'media_descriptor') and mob.media_descriptor:
                    media_desc = mob.media_descriptor
                    media_info = {}
                    
                    # Try to extract duration
                    if hasattr(mob, 'length'):
                        media_info["duration_frames"] = mob.length
                    
                    # Try to extract ALL attributes of the media descriptor itself
                    for attr_name in dir(media_desc):
                        if attr_name.startswith('_') or callable(getattr(media_desc, attr_name)) or attr_name == 'descriptor':
                            continue
                        
                        try:
                            attr_value = getattr(media_desc, attr_name)
                            if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                media_info[attr_name] = attr_value
                        except Exception:
                            pass
                    
                    # Extract media descriptor details
                    if hasattr(media_desc, 'descriptor'):
                        desc = media_desc.descriptor
                        
                        # Try to get all attributes from descriptor
                        for desc_attr in dir(desc):
                            if desc_attr.startswith('_') or callable(getattr(desc, desc_attr)):
                                continue
                            
                            try:
                                desc_value = getattr(desc, desc_attr)
                                
                                # Handle simple values
                                if isinstance(desc_value, (str, int, float, bool)) or desc_value is None:
                                    media_info[desc_attr] = desc_value
                                # Handle locators (file paths)
                                elif desc_attr == 'locator':
                                    try:
                                        locators = list(desc_value) if hasattr(desc_value, '__iter__') else []
                                        paths = []
                                        
                                        for locator in locators:
                                            loc_info = {}
                                            
                                            # Extract all attributes from the locator
                                            for loc_attr in dir(locator):
                                                if loc_attr.startswith('_') or callable(getattr(locator, loc_attr)):
                                                    continue
                                                
                                                try:
                                                    loc_val = getattr(locator, loc_attr)
                                                    if isinstance(loc_val, (str, int, float, bool)) or loc_val is None:
                                                        loc_info[loc_attr] = loc_val
                                                except Exception:
                                                    pass
                                            
                                            paths.append(loc_info)
                                        
                                        if paths:
                                            media_info['locators'] = paths
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    
                    # Try to extract physical media (tape) information
                    if hasattr(media_desc, 'physical_media'):
                        try:
                            physical_media = media_desc.physical_media
                            pm_info = {}
                            
                            # Extract all attributes from physical media
                            for pm_attr in dir(physical_media):
                                if pm_attr.startswith('_') or callable(getattr(physical_media, pm_attr)):
                                    continue
                                
                                try:
                                    pm_val = getattr(physical_media, pm_attr)
                                    if isinstance(pm_val, (str, int, float, bool)) or pm_val is None:
                                        pm_info[pm_attr] = pm_val
                                except Exception:
                                    pass
                            
                            if pm_info:
                                media_info['physical_media'] = pm_info
                        except Exception:
                            pass
                    
                    # Save all media info
                    clip_info["media_info"] = media_info
                
                # Get markers if available
                if hasattr(mob, 'markers') and mob.markers:
                    try:
                        # Convert to list if it's an iterator
                        markers_list = list(mob.markers) if hasattr(mob.markers, '__iter__') else []
                        markers = []
                        
                        for marker in markers_list:
                            marker_info = {}
                            
                            # Extract ALL attributes from the marker
                            for marker_attr in dir(marker):
                                if marker_attr.startswith('_') or callable(getattr(marker, marker_attr)):
                                    continue
                                
                                try:
                                    marker_val = getattr(marker, marker_attr)
                                    if isinstance(marker_val, (str, int, float, bool)) or marker_val is None:
                                        marker_info[marker_attr] = marker_val
                                except Exception:
                                    pass
                            
                            markers.append(marker_info)
                        
                        clip_info["markers"] = markers
                    except Exception as e:
                        clip_info["markers_error"] = str(e)
                
                # Try to extract timecode information
                if hasattr(mob, 'timecode'):
                    try:
                        tc = mob.timecode
                        tc_info = {}
                        
                        # Extract ALL attributes from timecode
                        for tc_attr in dir(tc):
                            if tc_attr.startswith('_') or callable(getattr(tc, tc_attr)):
                                continue
                            
                            try:
                                tc_val = getattr(tc, tc_attr)
                                if isinstance(tc_val, (str, int, float, bool)) or tc_val is None:
                                    tc_info[tc_attr] = tc_val
                            except Exception:
                                pass
                        
                        clip_info["timecode"] = tc_info
                    except Exception as e:
                        clip_info["timecode_error"] = str(e)
                
                # Try to extract essence data if available
                if hasattr(mob, 'essence') and mob.essence:
                    try:
                        essence = mob.essence
                        essence_info = {}
                        
                        # Extract ALL attributes from essence
                        for ess_attr in dir(essence):
                            if ess_attr.startswith('_') or callable(getattr(essence, ess_attr)):
                                continue
                            
                            try:
                                ess_val = getattr(essence, ess_attr)
                                if isinstance(ess_val, (str, int, float, bool)) or ess_val is None:
                                    essence_info[ess_attr] = ess_val
                            except Exception:
                                pass
                        
                        if essence_info:
                            clip_info["essence"] = essence_info
                    except Exception as e:
                        clip_info["essence_error"] = str(e)
                
                clips.append(clip_info)
        
        self.metadata["clips"] = clips
        return clips
    
    def extract_sequences(self):
        """Extract information specific to sequences in the bin"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        sequences = []
        
        # Filter for composition mobs (sequences)
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            for mob in mobs_list:
                if type(mob).__name__ == 'CompositionMob':
                    seq_info = {
                        "name": getattr(mob, 'name', 'Unnamed Sequence'),
                        "mob_id": str(mob.mob_id) if hasattr(mob, 'mob_id') else None,
                        "creation_time": mob.creation_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'creation_time') else None,
                        "last_modified": mob.last_modified.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'last_modified') else None,
                    }
                    
                    # Extract all available attributes from the sequence
                    for attr_name in dir(mob):
                        # Skip private attributes and methods
                        if attr_name.startswith('_') or callable(getattr(mob, attr_name)):
                            continue
                        
                        # Skip attributes we've already processed
                        if attr_name in ['name', 'mob_id', 'creation_time', 'last_modified', 'tracks']:
                            continue
                        
                        try:
                            attr_value = getattr(mob, attr_name)
                            # Only include simple types (skip complex objects)
                            if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                seq_info[attr_name] = attr_value
                        except Exception:
                            # Skip attributes that cause errors
                            pass
                    
                    # Extract user comments if available
                    if hasattr(mob, 'user_comments') and mob.user_comments:
                        seq_info["user_comments"] = {
                            comment.name: comment.value 
                            for comment in mob.user_comments 
                            if hasattr(comment, 'name') and hasattr(comment, 'value')
                        }
                    
                    # Try to extract sequence settings
                    if hasattr(mob, 'descriptor'):
                        desc = mob.descriptor
                        settings = {}
                        
                        for setting_attr in ['frame_rate', 'edit_rate', 'format', 'resolution']:
                            if hasattr(desc, setting_attr):
                                settings[setting_attr] = getattr(desc, setting_attr)
                        
                        if settings:
                            seq_info["settings"] = settings
                    
                    # Get track information
                    if hasattr(mob, 'tracks'):
                        # Convert tracks to list if it's an iterator
                        tracks_list = list(mob.tracks) if hasattr(mob.tracks, '__iter__') else []
                        tracks = []
                        
                        for track in tracks_list:
                            track_info = {
                                "name": track.name if hasattr(track, 'name') else None,
                                "type": track.track_type if hasattr(track, 'track_type') else None,
                                "length": track.length if hasattr(track, 'length') else None,
                                "id": track.id if hasattr(track, 'id') else None,
                                "enabled": track.enabled if hasattr(track, 'enabled') else None,
                            }
                            
                            # Extract all available track attributes
                            for track_attr in dir(track):
                                if track_attr.startswith('_') or callable(getattr(track, track_attr)):
                                    continue
                                
                                if track_attr not in ['name', 'track_type', 'length', 'id', 'enabled', 'component']:
                                    try:
                                        attr_value = getattr(track, track_attr)
                                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                            track_info[track_attr] = attr_value
                                    except Exception:
                                        pass
                            
                            # Get clip info from track
                            if hasattr(track, 'component') and track.component:
                                # Get track effects
                                if hasattr(track.component, 'parameters'):
                                    # Convert parameters to list if it's an iterator
                                    params_list = list(track.component.parameters) if hasattr(track.component.parameters, '__iter__') else []
                                    effects = []
                                    
                                    for param in params_list:
                                        effect_info = {
                                            "name": param.name if hasattr(param, 'name') else None,
                                            "value": param.value if hasattr(param, 'value') else None,
                                        }
                                        effects.append(effect_info)
                                    
                                    if effects:
                                        track_info["effects"] = effects
                                
                                # Get clips in the track
                                if hasattr(track.component, 'components'):
                                    # Convert components to list if it's an iterator
                                    components_list = list(track.component.components) if hasattr(track.component.components, '__iter__') else []
                                    clips_in_track = []
                                    
                                    for component in components_list:
                                        component_info = {
                                            "type": type(component).__name__,
                                            "start": component.start_time if hasattr(component, 'start_time') else None,
                                            "length": component.length if hasattr(component, 'length') else None,
                                        }
                                        
                                        # Get source clip information
                                        if hasattr(component, 'mob_id') and component.mob_id:
                                            component_info["source_mob_id"] = str(component.mob_id)
                                        
                                        # Get source position
                                        if hasattr(component, 'source_position'):
                                            component_info["source_position"] = component.source_position
                                        
                                        # Look for transition information
                                        if hasattr(component, 'cutpoint'):
                                            component_info["cutpoint"] = component.cutpoint
                                        
                                        # Look for effect information
                                        if hasattr(component, 'effect_id'):
                                            component_info["effect_id"] = component.effect_id
                                        
                                        # Extract all available component attributes
                                        for comp_attr in dir(component):
                                            if comp_attr.startswith('_') or callable(getattr(component, comp_attr)):
                                                continue
                                            
                                            if comp_attr not in ['start_time', 'length', 'mob_id', 'source_position', 'cutpoint', 'effect_id']:
                                                try:
                                                    attr_value = getattr(component, comp_attr)
                                                    if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                                        component_info[comp_attr] = attr_value
                                                except Exception:
                                                    pass
                                        
                                        clips_in_track.append(component_info)
                                    
                                    track_info["clips"] = clips_in_track
                            
                            tracks.append(track_info)
                        
                        seq_info["tracks"] = tracks
                    
                    # Extract markers if available
                    if hasattr(mob, 'markers') and mob.markers:
                        # Convert markers to list if it's an iterator
                        markers_list = list(mob.markers) if hasattr(mob.markers, '__iter__') else []
                        markers = []
                        
                        for marker in markers_list:
                            marker_info = {
                                "position": marker.position if hasattr(marker, 'position') else None,
                                "color": marker.color if hasattr(marker, 'color') else None,
                                "comment": marker.comment if hasattr(marker, 'comment') else None,
                            }
                            
                            # Extract additional marker attributes
                            for marker_attr in dir(marker):
                                if marker_attr.startswith('_') or callable(getattr(marker, marker_attr)):
                                    continue
                                
                                if marker_attr not in ['position', 'color', 'comment']:
                                    try:
                                        attr_value = getattr(marker, marker_attr)
                                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                            marker_info[marker_attr] = attr_value
                                    except Exception:
                                        pass
                            
                            markers.append(marker_info)
                        
                        seq_info["markers"] = markers
                    
                    sequences.append(seq_info)
        
        self.metadata["sequences"] = sequences
        return sequences
    
    def extract_all_metadata(self):
        """Extract all available metadata from the bin file"""
        try:
            self.extract_basic_info()
            self.extract_clips()
            self.extract_sequences()
        except Exception as e:
            # If an error occurs, log it but continue with what we have
            if "basic_info" not in self.metadata:
                self.metadata["basic_info"] = {"error": str(e)}
            self.metadata["extraction_error"] = str(e)
        
        return self.metadata
    
    def export_metadata_json(self, output_path=None):
        """Export metadata to a JSON file"""
        if not self.metadata:
            self.extract_all_metadata()
        
        if not output_path:
            # Use the bin path with .json extension
            output_path = os.path.splitext(self.bin_path)[0] + "_metadata.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            return output_path
        except Exception as e:
            raise Exception(f"Error writing metadata to JSON: {str(e)}")

# Simple demo function
def demo(bin_path):
    """Demo function to showcase the BinExplorer functionality"""
    explorer = BinExplorer(bin_path)
    explorer.open_bin()
    
    print(f"Exploring bin: {bin_path}")
    
    try:
        # Extract all metadata
        metadata = explorer.extract_all_metadata()
        
        # Print basic info
        basic_info = metadata.get('basic_info', {})
        print("\nBasic Information:")
        print(f"File: {basic_info.get('filename', 'Unknown')}")
        print(f"View Mode: {basic_info.get('view_mode', 'Unknown')}")
        
        display_options = basic_info.get('display_options', [])
        if display_options:
            print(f"Display Options: {', '.join(display_options)}")
        
        # Print clips summary
        clips = metadata.get('clips', [])
        print(f"\nFound {len(clips)} items in bin:")
        for i, clip in enumerate(clips[:5], 1):  # Show first 5 clips only
            print(f"{i}. {clip.get('name', 'Unnamed')} ({clip.get('type', 'Unknown')})")
            if 'media_info' in clip and clip['media_info']:
                media = clip['media_info']
                if 'sampled_width' in media and 'sampled_height' in media:
                    print(f"   Resolution: {media['sampled_width']}x{media['sampled_height']}")
                if 'frame_rate' in media:
                    print(f"   Frame Rate: {media['frame_rate']}")
        
        if len(clips) > 5:
            print(f"... and {len(clips) - 5} more items")
        
        # Print sequences summary
        sequences = metadata.get('sequences', [])
        print(f"\nFound {len(sequences)} sequences:")
        for i, seq in enumerate(sequences, 1):
            print(f"{i}. {seq.get('name', 'Unnamed')}")
            if 'tracks' in seq:
                tracks = seq['tracks']
                print(f"   Tracks: {len(tracks)}")
                track_types = {}
                for track in tracks:
                    track_type = track.get('type', 'Unknown')
                    track_types[track_type] = track_types.get(track_type, 0) + 1
                
                for track_type, count in track_types.items():
                    print(f"   - {track_type}: {count}")
        
        # Export metadata
        json_path = explorer.export_metadata_json()
        print(f"\nMetadata exported to: {json_path}")
        
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
    
    explorer.close_bin()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bin_explorer.py path/to/bin.avb")
        sys.exit(1)
    
    demo(sys.argv[1])#!/usr/bin/env python3
"""
bin_explorer.py - Module for exploring and extracting metadata from Avid bin files
"""

import os
import sys
import json
from datetime import datetime
import avb
from binsmith import ViewModes, BinDisplays, get_binview_from_file

class BinExplorer:
    """Class for exploring and extracting metadata from Avid bin files"""
    
    def __init__(self, bin_path=None):
        self.bin_path = bin_path
        self.bin_file = None
        self.metadata = {}
    
    def open_bin(self, bin_path=None):
        """Open an Avid bin file and initialize metadata extraction"""
        if bin_path:
            self.bin_path = bin_path
        
        if not self.bin_path:
            raise ValueError("No bin path specified")
        
        try:
            self.bin_file = avb.open(self.bin_path)
            return True
        except Exception as e:
            raise Exception(f"Error opening bin file: {str(e)}")
    
    def close_bin(self):
        """Close the currently open bin file"""
        if self.bin_file:
            self.bin_file.close()
            self.bin_file = None
    
    def extract_basic_info(self):
        """Extract basic information about the bin file"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        basic_info = {
            "filename": os.path.basename(self.bin_path),
            "filepath": self.bin_path,
            "file_size": os.path.getsize(self.bin_path),
            "last_modified": datetime.fromtimestamp(os.path.getmtime(self.bin_path)).strftime("%Y-%m-%d %H:%M:%S"),
            "view_mode": ViewModes(self.bin_file.content.display_mode).name
        }
        
        # Handle display options safely
        try:
            # Only use get_options if display_mask is an IntFlag
            if hasattr(self.bin_file.content, 'display_mask'):
                display_mask = self.bin_file.content.display_mask
                if isinstance(display_mask, int):
                    # Get options safely
                    options = []
                    for opt in BinDisplays:
                        if display_mask & opt.value:
                            options.append(opt.name)
                    basic_info["display_options"] = options
                else:
                    basic_info["display_options"] = []
            else:
                basic_info["display_options"] = []
        except Exception as e:
            basic_info["display_options"] = []
            basic_info["display_options_error"] = str(e)
        
        # Get the bin name and other attributes
        if hasattr(self.bin_file.content, 'name'):
            basic_info["bin_name"] = self.bin_file.content.name
        
        # Get view settings
        if hasattr(self.bin_file.content, 'view_setting') and hasattr(self.bin_file.content.view_setting, 'property_data'):
            view_settings = {}
            
            # Extract view name
            if 'name' in self.bin_file.content.view_setting.property_data:
                view_settings["name"] = self.bin_file.content.view_setting.property_data['name']
            
            # Extract all properties
            for key, value in self.bin_file.content.view_setting.property_data.items():
                # Skip complex objects
                if isinstance(value, (str, int, float, bool)) or value is None:
                    view_settings[key] = value
            
            basic_info["view_settings"] = view_settings
        
        # Extract bin attributes
        if hasattr(self.bin_file.content, 'attributes'):
            attributes = {}
            for key, value in self.bin_file.content.attributes.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    attributes[key] = value
            
            if attributes:
                basic_info["attributes"] = attributes
        
        # Count items by type
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            mob_types = {}
            for mob in mobs_list:
                mob_type = type(mob).__name__
                mob_types[mob_type] = mob_types.get(mob_type, 0) + 1
            
            if mob_types:
                basic_info["item_counts"] = mob_types
                basic_info["total_items"] = len(mobs_list)
        
        # Extract bin creation/modification dates if available
        if hasattr(self.bin_file.content, 'creation_time'):
            basic_info["creation_time"] = self.bin_file.content.creation_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if hasattr(self.bin_file.content, 'last_modified'):
            basic_info["last_modified_bin"] = self.bin_file.content.last_modified.strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to extract Avid version information
        if hasattr(self.bin_file, 'header'):
            header_info = {}
            header = self.bin_file.header
            
            for header_attr in ['major_version', 'minor_version', 'byte_order', 'page_size', 'page_count']:
                if hasattr(header, header_attr):
                    header_info[header_attr] = getattr(header, header_attr)
            
            if header_info:
                basic_info["file_header"] = header_info
        
        self.metadata["basic_info"] = basic_info
        return basic_info
    
    def extract_clips(self):
        """Extract information about clips in the bin"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        clips = []
        
        # Get mob objects (clips, sequences, etc.)
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            for mob in mobs_list:
                clip_info = {
                    "name": getattr(mob, 'name', 'Unnamed'),
                    "mob_id": str(mob.mob_id) if hasattr(mob, 'mob_id') else None,
                    "type": type(mob).__name__,
                    "creation_time": mob.creation_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'creation_time') else None,
                    "last_modified": mob.last_modified.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'last_modified') else None,
                    "mob_type_id": mob.mob_type_id if hasattr(mob, 'mob_type_id') else None,
                }
                
                # Extract all available attributes from the mob
                for attr_name in dir(mob):
                    # Skip private attributes and methods
                    if attr_name.startswith('_') or callable(getattr(mob, attr_name)):
                        continue
                    
                    # Skip attributes we've already processed
                    if attr_name in ['name', 'mob_id', 'creation_time', 'last_modified', 'mob_type_id',
                                    'user_comments', 'media_descriptor', 'length', 'markers', 'tracks']:
                        continue
                    
                    try:
                        attr_value = getattr(mob, attr_name)
                        # Only include simple types (skip complex objects)
                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                            clip_info[attr_name] = attr_value
                    except Exception:
                        # Skip attributes that cause errors
                        pass
                
                # Extract user comments if available
                if hasattr(mob, 'user_comments') and mob.user_comments:
                    clip_info["user_comments"] = {
                        comment.name: comment.value 
                        for comment in mob.user_comments 
                        if hasattr(comment, 'name') and hasattr(comment, 'value')
                    }
                
                # Get media info for master clips
                if hasattr(mob, 'media_descriptor') and mob.media_descriptor:
                    media_desc = mob.media_descriptor
                    media_info = {}
                    
                    # Try to extract duration
                    if hasattr(mob, 'length'):
                        media_info["duration_frames"] = mob.length
                    
                    # Extract all available attributes from media descriptor
                    if hasattr(media_desc, 'descriptor'):
                        desc = media_desc.descriptor
                        
                        # Common video attributes
                        for video_attr in ['frame_rate', 'frame_layout', 'video_line_map', 
                                          'sampled_width', 'sampled_height', 'displayed_width', 
                                          'displayed_height', 'aspect_ratio', 'pixel_layout',
                                          'compression_id', 'horizontal_subsampling', 
                                          'vertical_subsampling', 'color_range']:
                            if hasattr(desc, video_attr):
                                media_info[video_attr] = getattr(desc, video_attr)
                        
                        # Common audio attributes
                        for audio_attr in ['audio_sampling_rate', 'num_channels', 'bits_per_sample',
                                          'block_align', 'average_bytes_per_second']:
                            if hasattr(desc, audio_attr):
                                media_info[audio_attr] = getattr(desc, audio_attr)
                        
                        # Get codec information if available
                        if hasattr(desc, 'codec_id'):
                            media_info['codec_id'] = desc.codec_id
                        
                        # Try to extract file path
                        if hasattr(desc, 'locator'):
                            # Convert to list if it's an iterator
                            locators = list(desc.locator) if hasattr(desc.locator, '__iter__') else []
                            for locator in locators:
                                if hasattr(locator, 'path'):
                                    media_info['file_path'] = locator.path
                                    break
                    
                    # Try to extract tape name/source information
                    if hasattr(media_desc, 'physical_media'):
                        physical_media = media_desc.physical_media
                        if hasattr(physical_media, 'name'):
                            media_info['tape_name'] = physical_media.name
                    
                    clip_info["media_info"] = media_info
                
                # Get markers if available
                if hasattr(mob, 'markers') and mob.markers:
                    # Convert to list if it's an iterator
                    markers_list = list(mob.markers) if hasattr(mob.markers, '__iter__') else []
                    markers = []
                    for marker in markers_list:
                        marker_info = {
                            "position": marker.position if hasattr(marker, 'position') else None,
                            "color": marker.color if hasattr(marker, 'color') else None,
                            "comment": marker.comment if hasattr(marker, 'comment') else None,
                        }
                        
                        # Extract additional marker attributes
                        for marker_attr in dir(marker):
                            if marker_attr.startswith('_') or callable(getattr(marker, marker_attr)):
                                continue
                            
                            if marker_attr not in ['position', 'color', 'comment']:
                                try:
                                    attr_value = getattr(marker, marker_attr)
                                    if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                        marker_info[marker_attr] = attr_value
                                except Exception:
                                    pass
                        
                        markers.append(marker_info)
                    
                    clip_info["markers"] = markers
                
                # Try to extract timecode information
                if hasattr(mob, 'timecode'):
                    tc_info = {}
                    tc = mob.timecode
                    
                    for tc_attr in ['start', 'fps', 'drop', 'timecode_format']:
                        if hasattr(tc, tc_attr):
                            tc_info[tc_attr] = getattr(tc, tc_attr)
                    
                    clip_info["timecode"] = tc_info
                
                clips.append(clip_info)
        
        self.metadata["clips"] = clips
        return clips
    
    def extract_sequences(self):
        """Extract information specific to sequences in the bin"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        sequences = []
        
        # Filter for composition mobs (sequences)
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            for mob in mobs_list:
                if type(mob).__name__ == 'CompositionMob':
                    seq_info = {
                        "name": getattr(mob, 'name', 'Unnamed Sequence'),
                        "mob_id": str(mob.mob_id) if hasattr(mob, 'mob_id') else None,
                        "creation_time": mob.creation_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'creation_time') else None,
                        "last_modified": mob.last_modified.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'last_modified') else None,
                    }
                    
                    # Extract all available attributes from the sequence
                    for attr_name in dir(mob):
                        # Skip private attributes and methods
                        if attr_name.startswith('_') or callable(getattr(mob, attr_name)):
                            continue
                        
                        # Skip attributes we've already processed
                        if attr_name in ['name', 'mob_id', 'creation_time', 'last_modified', 'tracks']:
                            continue
                        
                        try:
                            attr_value = getattr(mob, attr_name)
                            # Only include simple types (skip complex objects)
                            if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                seq_info[attr_name] = attr_value
                        except Exception:
                            # Skip attributes that cause errors
                            pass
                    
                    # Extract user comments if available
                    if hasattr(mob, 'user_comments') and mob.user_comments:
                        seq_info["user_comments"] = {
                            comment.name: comment.value 
                            for comment in mob.user_comments 
                            if hasattr(comment, 'name') and hasattr(comment, 'value')
                        }
                    
                    # Try to extract sequence settings
                    if hasattr(mob, 'descriptor'):
                        desc = mob.descriptor
                        settings = {}
                        
                        for setting_attr in ['frame_rate', 'edit_rate', 'format', 'resolution']:
                            if hasattr(desc, setting_attr):
                                settings[setting_attr] = getattr(desc, setting_attr)
                        
                        if settings:
                            seq_info["settings"] = settings
                    
                    # Get track information
                    if hasattr(mob, 'tracks'):
                        # Convert tracks to list if it's an iterator
                        tracks_list = list(mob.tracks) if hasattr(mob.tracks, '__iter__') else []
                        tracks = []
                        
                        for track in tracks_list:
                            track_info = {
                                "name": track.name if hasattr(track, 'name') else None,
                                "type": track.track_type if hasattr(track, 'track_type') else None,
                                "length": track.length if hasattr(track, 'length') else None,
                                "id": track.id if hasattr(track, 'id') else None,
                                "enabled": track.enabled if hasattr(track, 'enabled') else None,
                            }
                            
                            # Extract all available track attributes
                            for track_attr in dir(track):
                                if track_attr.startswith('_') or callable(getattr(track, track_attr)):
                                    continue
                                
                                if track_attr not in ['name', 'track_type', 'length', 'id', 'enabled', 'component']:
                                    try:
                                        attr_value = getattr(track, track_attr)
                                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                            track_info[track_attr] = attr_value
                                    except Exception:
                                        pass
                            
                            # Get clip info from track
                            if hasattr(track, 'component') and track.component:
                                # Get track effects
                                if hasattr(track.component, 'parameters'):
                                    # Convert parameters to list if it's an iterator
                                    params_list = list(track.component.parameters) if hasattr(track.component.parameters, '__iter__') else []
                                    effects = []
                                    
                                    for param in params_list:
                                        effect_info = {
                                            "name": param.name if hasattr(param, 'name') else None,
                                            "value": param.value if hasattr(param, 'value') else None,
                                        }
                                        effects.append(effect_info)
                                    
                                    if effects:
                                        track_info["effects"] = effects
                                
                                # Get clips in the track
                                if hasattr(track.component, 'components'):
                                    # Convert components to list if it's an iterator
                                    components_list = list(track.component.components) if hasattr(track.component.components, '__iter__') else []
                                    clips_in_track = []
                                    
                                    for component in components_list:
                                        component_info = {
                                            "type": type(component).__name__,
                                            "start": component.start_time if hasattr(component, 'start_time') else None,
                                            "length": component.length if hasattr(component, 'length') else None,
                                        }
                                        
                                        # Get source clip information
                                        if hasattr(component, 'mob_id') and component.mob_id:
                                            component_info["source_mob_id"] = str(component.mob_id)
                                        
                                        # Get source position
                                        if hasattr(component, 'source_position'):
                                            component_info["source_position"] = component.source_position
                                        
                                        # Look for transition information
                                        if hasattr(component, 'cutpoint'):
                                            component_info["cutpoint"] = component.cutpoint
                                        
                                        # Look for effect information
                                        if hasattr(component, 'effect_id'):
                                            component_info["effect_id"] = component.effect_id
                                        
                                        # Extract all available component attributes
                                        for comp_attr in dir(component):
                                            if comp_attr.startswith('_') or callable(getattr(component, comp_attr)):
                                                continue
                                            
                                            if comp_attr not in ['start_time', 'length', 'mob_id', 'source_position', 'cutpoint', 'effect_id']:
                                                try:
                                                    attr_value = getattr(component, comp_attr)
                                                    if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                                        component_info[comp_attr] = attr_value
                                                except Exception:
                                                    pass
                                        
                                        clips_in_track.append(component_info)
                                    
                                    track_info["clips"] = clips_in_track
                            
                            tracks.append(track_info)
                        
                        seq_info["tracks"] = tracks
                    
                    # Extract markers if available
                    if hasattr(mob, 'markers') and mob.markers:
                        # Convert markers to list if it's an iterator
                        markers_list = list(mob.markers) if hasattr(mob.markers, '__iter__') else []
                        markers = []
                        
                        for marker in markers_list:
                            marker_info = {
                                "position": marker.position if hasattr(marker, 'position') else None,
                                "color": marker.color if hasattr(marker, 'color') else None,
                                "comment": marker.comment if hasattr(marker, 'comment') else None,
                            }
                            
                            # Extract additional marker attributes
                            for marker_attr in dir(marker):
                                if marker_attr.startswith('_') or callable(getattr(marker, marker_attr)):
                                    continue
                                
                                if marker_attr not in ['position', 'color', 'comment']:
                                    try:
                                        attr_value = getattr(marker, marker_attr)
                                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                            marker_info[marker_attr] = attr_value
                                    except Exception:
                                        pass
                            
                            markers.append(marker_info)
                        
                        seq_info["markers"] = markers
                    
                    sequences.append(seq_info)
        
        self.metadata["sequences"] = sequences
        return sequences
    
    def extract_all_metadata(self):
        """Extract all available metadata from the bin file"""
        try:
            self.extract_basic_info()
            self.extract_clips()
            self.extract_sequences()
        except Exception as e:
            # If an error occurs, log it but continue with what we have
            if "basic_info" not in self.metadata:
                self.metadata["basic_info"] = {"error": str(e)}
            self.metadata["extraction_error"] = str(e)
        
        return self.metadata
    
    def export_metadata_json(self, output_path=None):
        """Export metadata to a JSON file"""
        if not self.metadata:
            self.extract_all_metadata()
        
        if not output_path:
            # Use the bin path with .json extension
            output_path = os.path.splitext(self.bin_path)[0] + "_metadata.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            return output_path
        except Exception as e:
            raise Exception(f"Error writing metadata to JSON: {str(e)}")

# Simple demo function
def demo(bin_path):
    """Demo function to showcase the BinExplorer functionality"""
    explorer = BinExplorer(bin_path)
    explorer.open_bin()
    
    print(f"Exploring bin: {bin_path}")
    
    try:
        # Extract all metadata
        metadata = explorer.extract_all_metadata()
        
        # Print basic info
        basic_info = metadata.get('basic_info', {})
        print("\nBasic Information:")
        print(f"File: {basic_info.get('filename', 'Unknown')}")
        print(f"View Mode: {basic_info.get('view_mode', 'Unknown')}")
        
        display_options = basic_info.get('display_options', [])
        if display_options:
            print(f"Display Options: {', '.join(display_options)}")
        
        # Print clips summary
        clips = metadata.get('clips', [])
        print(f"\nFound {len(clips)} items in bin:")
        for i, clip in enumerate(clips[:5], 1):  # Show first 5 clips only
            print(f"{i}. {clip.get('name', 'Unnamed')} ({clip.get('type', 'Unknown')})")
            if 'media_info' in clip and clip['media_info']:
                media = clip['media_info']
                if 'sampled_width' in media and 'sampled_height' in media:
                    print(f"   Resolution: {media['sampled_width']}x{media['sampled_height']}")
                if 'frame_rate' in media:
                    print(f"   Frame Rate: {media['frame_rate']}")
        
        if len(clips) > 5:
            print(f"... and {len(clips) - 5} more items")
        
        # Print sequences summary
        sequences = metadata.get('sequences', [])
        print(f"\nFound {len(sequences)} sequences:")
        for i, seq in enumerate(sequences, 1):
            print(f"{i}. {seq.get('name', 'Unnamed')}")
            if 'tracks' in seq:
                tracks = seq['tracks']
                print(f"   Tracks: {len(tracks)}")
                track_types = {}
                for track in tracks:
                    track_type = track.get('type', 'Unknown')
                    track_types[track_type] = track_types.get(track_type, 0) + 1
                
                for track_type, count in track_types.items():
                    print(f"   - {track_type}: {count}")
        
        # Export metadata
        json_path = explorer.export_metadata_json()
        print(f"\nMetadata exported to: {json_path}")
        
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
    
    explorer.close_bin()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bin_explorer.py path/to/bin.avb")
        sys.exit(1)
    
    demo(sys.argv[1])#!/usr/bin/env python3
"""
bin_explorer.py - Module for exploring and extracting metadata from Avid bin files
"""

import os
import sys
import json
from datetime import datetime
import avb
from binsmith import ViewModes, BinDisplays, get_binview_from_file

class BinExplorer:
    """Class for exploring and extracting metadata from Avid bin files"""
    
    def __init__(self, bin_path=None):
        self.bin_path = bin_path
        self.bin_file = None
        self.metadata = {}
    
    def open_bin(self, bin_path=None):
        """Open an Avid bin file and initialize metadata extraction"""
        if bin_path:
            self.bin_path = bin_path
        
        if not self.bin_path:
            raise ValueError("No bin path specified")
        
        try:
            self.bin_file = avb.open(self.bin_path)
            return True
        except Exception as e:
            raise Exception(f"Error opening bin file: {str(e)}")
    
    def close_bin(self):
        """Close the currently open bin file"""
        if self.bin_file:
            self.bin_file.close()
            self.bin_file = None
    
    def extract_basic_info(self):
        """Extract basic information about the bin file"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        basic_info = {
            "filename": os.path.basename(self.bin_path),
            "filepath": self.bin_path,
            "file_size": os.path.getsize(self.bin_path),
            "last_modified": datetime.fromtimestamp(os.path.getmtime(self.bin_path)).strftime("%Y-%m-%d %H:%M:%S"),
            "view_mode": ViewModes(self.bin_file.content.display_mode).name
        }
        
        # Handle display options safely
        try:
            # Only use get_options if display_mask is an IntFlag
            if hasattr(self.bin_file.content, 'display_mask'):
                display_mask = self.bin_file.content.display_mask
                if isinstance(display_mask, int):
                    # Get options safely
                    options = []
                    for opt in BinDisplays:
                        if display_mask & opt.value:
                            options.append(opt.name)
                    basic_info["display_options"] = options
                else:
                    basic_info["display_options"] = []
            else:
                basic_info["display_options"] = []
        except Exception as e:
            basic_info["display_options"] = []
            basic_info["display_options_error"] = str(e)
        
        # Get the bin name and other attributes
        if hasattr(self.bin_file.content, 'name'):
            basic_info["bin_name"] = self.bin_file.content.name
        
        # Get view settings
        if hasattr(self.bin_file.content, 'view_setting') and hasattr(self.bin_file.content.view_setting, 'property_data'):
            view_settings = {}
            
            # Extract view name
            if 'name' in self.bin_file.content.view_setting.property_data:
                view_settings["name"] = self.bin_file.content.view_setting.property_data['name']
            
            # Extract all properties
            for key, value in self.bin_file.content.view_setting.property_data.items():
                # Skip complex objects
                if isinstance(value, (str, int, float, bool)) or value is None:
                    view_settings[key] = value
            
            basic_info["view_settings"] = view_settings
        
        # Extract bin attributes
        if hasattr(self.bin_file.content, 'attributes'):
            attributes = {}
            for key, value in self.bin_file.content.attributes.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    attributes[key] = value
            
            if attributes:
                basic_info["attributes"] = attributes
        
        # Count items by type
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            mob_types = {}
            for mob in mobs_list:
                mob_type = type(mob).__name__
                mob_types[mob_type] = mob_types.get(mob_type, 0) + 1
            
            if mob_types:
                basic_info["item_counts"] = mob_types
                basic_info["total_items"] = len(mobs_list)
        
        # Extract bin creation/modification dates if available
        if hasattr(self.bin_file.content, 'creation_time'):
            basic_info["creation_time"] = self.bin_file.content.creation_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if hasattr(self.bin_file.content, 'last_modified'):
            basic_info["last_modified_bin"] = self.bin_file.content.last_modified.strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to extract Avid version information
        if hasattr(self.bin_file, 'header'):
            header_info = {}
            header = self.bin_file.header
            
            for header_attr in ['major_version', 'minor_version', 'byte_order', 'page_size', 'page_count']:
                if hasattr(header, header_attr):
                    header_info[header_attr] = getattr(header, header_attr)
            
            if header_info:
                basic_info["file_header"] = header_info
        
        self.metadata["basic_info"] = basic_info
        return basic_info
    
    def extract_clips(self):
        """Extract information about clips in the bin"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        clips = []
        
        # Get mob objects (clips, sequences, etc.)
        if hasattr(self.bin_file.content, 'mobs'):
            # Convert mobs to list if it's a generator
            mobs_list = list(self.bin_file.content.mobs) if hasattr(self.bin_file.content.mobs, '__iter__') else []
            
            for mob in mobs_list:
                # Create a base info dictionary for the mob
                clip_info = {
                    "name": getattr(mob, 'name', 'Unnamed'),
                    "mob_id": str(mob.mob_id) if hasattr(mob, 'mob_id') else None,
                    "type": type(mob).__name__,
                    "creation_time": mob.creation_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'creation_time') else None,
                    "last_modified": mob.last_modified.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'last_modified') else None,
                    "mob_type_id": mob.mob_type_id if hasattr(mob, 'mob_type_id') else None,
                }
                
                # Attempt to extract ALL possible attributes by iterating through 
                # the mob's dictionary, not just the common ones
                if hasattr(mob, '__dict__'):
                    for key, value in mob.__dict__.items():
                        # Skip private attributes
                        if key.startswith('_'):
                            continue
                        
                        # Skip attributes we already processed
                        if key in ['name', 'mob_id', 'creation_time', 'last_modified', 'mob_type_id']:
                            continue
                        
                        # Include simple types directly
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            clip_info[key] = value
                        # For datetime objects, convert to string
                        elif hasattr(value, 'strftime'):
                            try:
                                clip_info[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                pass
                
                # Extract all available attributes from the mob using dir() too
                for attr_name in dir(mob):
                    # Skip private attributes, methods, and already processed ones
                    if attr_name.startswith('_') or callable(getattr(mob, attr_name)) or attr_name in clip_info:
                        continue
                    
                    try:
                        attr_value = getattr(mob, attr_name)
                        # Only include simple types (skip complex objects)
                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                            clip_info[attr_name] = attr_value
                        # For datetime objects, convert to string
                        elif hasattr(attr_value, 'strftime'):
                            clip_info[attr_name] = attr_value.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        # Skip attributes that cause errors
                        pass
                
                # Extract user comments if available
                if hasattr(mob, 'user_comments') and mob.user_comments:
                    try:
                        comments_list = list(mob.user_comments) if hasattr(mob.user_comments, '__iter__') else []
                        clip_info["user_comments"] = {}
                        
                        for comment in comments_list:
                            if hasattr(comment, 'name') and hasattr(comment, 'value'):
                                clip_info["user_comments"][comment.name] = comment.value
                                
                            # Extract all available attributes from each comment
                            for attr_name in dir(comment):
                                if attr_name.startswith('_') or callable(getattr(comment, attr_name)) or attr_name in ['name', 'value']:
                                    continue
                                
                                try:
                                    comment_attr = getattr(comment, attr_name)
                                    if isinstance(comment_attr, (str, int, float, bool)) or comment_attr is None:
                                        clip_info.setdefault("comment_attributes", {}).setdefault(comment.name, {})[attr_name] = comment_attr
                                except Exception:
                                    pass
                    except Exception as e:
                        clip_info["user_comments_error"] = str(e)
                
                # Get media info for clips
                if hasattr(mob, 'media_descriptor') and mob.media_descriptor:
                    media_desc = mob.media_descriptor
                    media_info = {}
                    
                    # Try to extract duration
                    if hasattr(mob, 'length'):
                        media_info["duration_frames"] = mob.length
                    
                    # Try to extract ALL attributes of the media descriptor itself
                    for attr_name in dir(media_desc):
                        if attr_name.startswith('_') or callable(getattr(media_desc, attr_name)) or attr_name == 'descriptor':
                            continue
                        
                        try:
                            attr_value = getattr(media_desc, attr_name)
                            if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                media_info[attr_name] = attr_value
                        except Exception:
                            pass
                    
                    # Extract media descriptor details
                    if hasattr(media_desc, 'descriptor'):
                        desc = media_desc.descriptor
                        
                        # Try to get all attributes from descriptor
                        for desc_attr in dir(desc):
                            if desc_attr.startswith('_') or callable(getattr(desc, desc_attr)):
                                continue
                            
                            try:
                                desc_value = getattr(desc, desc_attr)
                                
                                # Handle simple values
                                if isinstance(desc_value, (str, int, float, bool)) or desc_value is None:
                                    media_info[desc_attr] = desc_value
                                # Handle locators (file paths)
                                elif desc_attr == 'locator':
                                    try:
                                        locators = list(desc_value) if hasattr(desc_value, '__iter__') else []
                                        paths = []
                                        
                                        for locator in locators:
                                            loc_info = {}
                                            
                                            # Extract all attributes from the locator
                                            for loc_attr in dir(locator):
                                                if loc_attr.startswith('_') or callable(getattr(locator, loc_attr)):
                                                    continue
                                                
                                                try:
                                                    loc_val = getattr(locator, loc_attr)
                                                    if isinstance(loc_val, (str, int, float, bool)) or loc_val is None:
                                                        loc_info[loc_attr] = loc_val
                                                except Exception:
                                                    pass
                                            
                                            paths.append(loc_info)
                                        
                                        if paths:
                                            media_info['locators'] = paths
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    
                    # Try to extract physical media (tape) information
                    if hasattr(media_desc, 'physical_media'):
                        try:
                            physical_media = media_desc.physical_media
                            pm_info = {}
                            
                            # Extract all attributes from physical media
                            for pm_attr in dir(physical_media):
                                if pm_attr.startswith('_') or callable(getattr(physical_media, pm_attr)):
                                    continue
                                
                                try:
                                    pm_val = getattr(physical_media, pm_attr)
                                    if isinstance(pm_val, (str, int, float, bool)) or pm_val is None:
                                        pm_info[pm_attr] = pm_val
                                except Exception:
                                    pass
                            
                            if pm_info:
                                media_info['physical_media'] = pm_info
                        except Exception:
                            pass
                    
                    # Save all media info
                    clip_info["media_info"] = media_info
                
                # Get markers if available
                if hasattr(mob, 'markers') and mob.markers:
                    try:
                        # Convert to list if it's an iterator
                        markers_list = list(mob.markers) if hasattr(mob.markers, '__iter__') else []
                        markers = []
                        
                        for marker in markers_list:
                            marker_info = {}
                            
                            # Extract ALL attributes from the marker
                            for marker_attr in dir(marker):
                                if marker_attr.startswith('_') or callable(getattr(marker, marker_attr)):
                                    continue
                                
                                try:
                                    marker_val = getattr(marker, marker_attr)
                                    if isinstance(marker_val, (str, int, float, bool)) or marker_val is None:
                                        marker_info[marker_attr] = marker_val
                                except Exception:
                                    pass
                            
                            markers.append(marker_info)
                        
                        clip_info["markers"] = markers
                    except Exception as e:
                        clip_info["markers_error"] = str(e)
                
                # Try to extract timecode information
                if hasattr(mob, 'timecode'):
                    try:
                        tc = mob.timecode
                        tc_info = {}
                        
                        # Extract ALL attributes from timecode
                        for tc_attr in dir(tc):
                            if tc_attr.startswith('_') or callable(getattr(tc, tc_attr)):
                                continue
                            
                            try:
                                tc_val = getattr(tc, tc_attr)
                                if isinstance(tc_val, (str, int, float, bool)) or tc_val is None:
                                    tc_info[tc_attr] = tc_val
                            except Exception:
                                pass
                        
                        clip_info["timecode"] = tc_info
                    except Exception as e:
                        clip_info["timecode_error"] = str(e)
                
                # Try to extract essence data if available
                if hasattr(mob, 'essence') and mob.essence:
                    try:
                        essence = mob.essence
                        essence_info = {}
                        
                        # Extract ALL attributes from essence
                        for ess_attr in dir(essence):
                            if ess_attr.startswith('_') or callable(getattr(essence, ess_attr)):
                                continue
                            
                            try:
                                ess_val = getattr(essence, ess_attr)
                                if isinstance(ess_val, (str, int, float, bool)) or ess_val is None:
                                    essence_info[ess_attr] = ess_val
                            except Exception:
                                pass
                        
                        if essence_info:
                            clip_info["essence"] = essence_info
                    except Exception as e:
                        clip_info["essence_error"] = str(e)
                
                clips.append(clip_info)
        
        self.metadata["clips"] = clips
        return clips
    
    def extract_sequences(self):
        """Extract information specific to sequences in the bin"""
        if not self.bin_file:
            raise ValueError("No bin file is currently open")
        
        sequences = []
        
        # Filter for composition mobs (sequences)
        if hasattr(self.bin_file.content, 'mobs'):
            for mob in self.bin_file.content.mobs:
                if type(mob).__name__ == 'CompositionMob':
                    seq_info = {
                        "name": getattr(mob, 'name', 'Unnamed Sequence'),
                        "mob_id": str(mob.mob_id) if hasattr(mob, 'mob_id') else None,
                        "creation_time": mob.creation_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'creation_time') else None,
                        "last_modified": mob.last_modified.strftime("%Y-%m-%d %H:%M:%S") if hasattr(mob, 'last_modified') else None,
                    }
                    
                    # Extract all available attributes from the sequence
                    for attr_name in dir(mob):
                        # Skip private attributes and methods
                        if attr_name.startswith('_') or callable(getattr(mob, attr_name)):
                            continue
                        
                        # Skip attributes we've already processed
                        if attr_name in ['name', 'mob_id', 'creation_time', 'last_modified', 'tracks']:
                            continue
                        
                        try:
                            attr_value = getattr(mob, attr_name)
                            # Only include simple types (skip complex objects)
                            if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                seq_info[attr_name] = attr_value
                        except Exception:
                            # Skip attributes that cause errors
                            pass
                    
                    # Extract user comments if available
                    if hasattr(mob, 'user_comments') and mob.user_comments:
                        seq_info["user_comments"] = {
                            comment.name: comment.value 
                            for comment in mob.user_comments 
                            if hasattr(comment, 'name') and hasattr(comment, 'value')
                        }
                    
                    # Try to extract sequence settings
                    if hasattr(mob, 'descriptor'):
                        desc = mob.descriptor
                        settings = {}
                        
                        for setting_attr in ['frame_rate', 'edit_rate', 'format', 'resolution']:
                            if hasattr(desc, setting_attr):
                                settings[setting_attr] = getattr(desc, setting_attr)
                        
                        if settings:
                            seq_info["settings"] = settings
                    
                    # Get track information
                    if hasattr(mob, 'tracks'):
                        tracks = []
                        for track in mob.tracks:
                            track_info = {
                                "name": track.name if hasattr(track, 'name') else None,
                                "type": track.track_type if hasattr(track, 'track_type') else None,
                                "length": track.length if hasattr(track, 'length') else None,
                                "id": track.id if hasattr(track, 'id') else None,
                                "enabled": track.enabled if hasattr(track, 'enabled') else None,
                            }
                            
                            # Extract all available track attributes
                            for track_attr in dir(track):
                                if track_attr.startswith('_') or callable(getattr(track, track_attr)):
                                    continue
                                
                                if track_attr not in ['name', 'track_type', 'length', 'id', 'enabled', 'component']:
                                    try:
                                        attr_value = getattr(track, track_attr)
                                        if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                            track_info[track_attr] = attr_value
                                    except Exception:
                                        pass
                            
                            # Get clip info from track
                            if hasattr(track, 'component') and track.component:
                                # Get track effects
                                if hasattr(track.component, 'parameters'):
                                    effects = []
                                    for param in track.component.parameters:
                                        effect_info = {
                                            "name": param.name if hasattr(param, 'name') else None,
                                            "value": param.value if hasattr(param, 'value') else None,
                                        }
                                        effects.append(effect_info)
                                    
                                    if effects:
                                        track_info["effects"] = effects
                                
                                # Get clips in the track
                                if hasattr(track.component, 'components'):
                                    clips_in_track = []
                                    for component in track.component.components:
                                        component_info = {
                                            "type": type(component).__name__,
                                            "start": component.start_time if hasattr(component, 'start_time') else None,
                                            "length": component.length if hasattr(component, 'length') else None,
                                        }
                                        
                                        # Get source clip information
                                        if hasattr(component, 'mob_id') and component.mob_id:
                                            component_info["source_mob_id"] = str(component.mob_id)
                                        
                                        # Get source position
                                        if hasattr(component, 'source_position'):
                                            component_info["source_position"] = component.source_position
                                        
                                        # Look for transition information
                                        if hasattr(component, 'cutpoint'):
                                            component_info["cutpoint"] = component.cutpoint
                                        
                                        # Look for effect information
                                        if hasattr(component, 'effect_id'):
                                            component_info["effect_id"] = component.effect_id
                                        
                                        # Extract all available component attributes
                                        for comp_attr in dir(component):
                                            if comp_attr.startswith('_') or callable(getattr(component, comp_attr)):
                                                continue
                                            
                                            if comp_attr not in ['start_time', 'length', 'mob_id', 'source_position', 'cutpoint', 'effect_id']:
                                                try:
                                                    attr_value = getattr(component, comp_attr)
                                                    if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                                                        component_info[comp_attr] = attr_value
                                                except Exception:
                                                    pass
                                        
                                        clips_in_track.append(component_info)
                                    
                                    track_info["clips"] = clips_in_track
                            
                            tracks.append(track_info)
                        
                        seq_info["tracks"] = tracks
                    
                    # Extract markers if available
                    if hasattr(mob, 'markers') and mob.markers:
                        markers = []
                        for marker in mob.markers:
                            marker_info = {
                                "position": marker.position if hasattr(marker, 'position') else None,
                                "color": marker.color if hasattr(marker, 'color') else None,
                                "comment": marker.comment if hasattr(marker, 'comment') else None,
                            }
                            markers.append(marker_info)
                        
                        seq_info["markers"] = markers
                    
                    sequences.append(seq_info)
        
        self.metadata["sequences"] = sequences
        return sequences
    
    def extract_all_metadata(self):
        """Extract all available metadata from the bin file"""
        self.extract_basic_info()
        self.extract_clips()
        self.extract_sequences()
        return self.metadata
    
    def export_metadata_json(self, output_path=None):
        """Export metadata to a JSON file"""
        if not self.metadata:
            self.extract_all_metadata()
        
        if not output_path:
            # Use the bin path with .json extension
            output_path = os.path.splitext(self.bin_path)[0] + "_metadata.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            return output_path
        except Exception as e:
            raise Exception(f"Error writing metadata to JSON: {str(e)}")

# Simple demo function
def demo(bin_path):
    """Demo function to showcase the BinExplorer functionality"""
    explorer = BinExplorer(bin_path)
    explorer.open_bin()
    
    print(f"Exploring bin: {bin_path}")
    
    # Extract basic info
    basic_info = explorer.extract_basic_info()
    print("\nBasic Information:")
    print(f"File: {basic_info['filename']}")
    print(f"View Mode: {basic_info['view_mode']}")
    print(f"Display Options: {', '.join(basic_info['display_options'])}")
    
    # Extract clips
    clips = explorer.extract_clips()
    print(f"\nFound {len(clips)} items in bin:")
    for i, clip in enumerate(clips[:5], 1):  # Show first 5 clips only
        print(f"{i}. {clip['name']} ({clip['type']})")
        if 'media_info' in clip and clip['media_info']:
            media = clip['media_info']
            if 'width' in media and 'height' in media:
                print(f"   Resolution: {media['width']}x{media['height']}")
            if 'frame_rate' in media:
                print(f"   Frame Rate: {media['frame_rate']}")
    
    if len(clips) > 5:
        print(f"... and {len(clips) - 5} more items")
    
    # Extract sequences
    sequences = explorer.extract_sequences()
    print(f"\nFound {len(sequences)} sequences:")
    for i, seq in enumerate(sequences, 1):
        print(f"{i}. {seq['name']}")
        if 'tracks' in seq:
            print(f"   Tracks: {len(seq['tracks'])}")
            track_types = {}
            for track in seq['tracks']:
                track_type = track.get('type', 'Unknown')
                track_types[track_type] = track_types.get(track_type, 0) + 1
            
            for track_type, count in track_types.items():
                print(f"   - {track_type}: {count}")
    
    # Export metadata
    json_path = explorer.export_metadata_json()
    print(f"\nMetadata exported to: {json_path}")
    
    explorer.close_bin()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bin_explorer.py path/to/bin.avb")
        sys.exit(1)
    
    demo(sys.argv[1])
    
    def extract_all_metadata(self):
        """Extract all available metadata from the bin file"""
        self.extract_basic_info()
        self.extract_clips()
        self.extract_sequences()
        return self.metadata
    
    def export_metadata_json(self, output_path=None):
        """Export metadata to a JSON file"""
        if not self.metadata:
            self.extract_all_metadata()
        
        if not output_path:
            # Use the bin path with .json extension
            output_path = os.path.splitext(self.bin_path)[0] + "_metadata.json"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            return output_path
        except Exception as e:
            raise Exception(f"Error writing metadata to JSON: {str(e)}")

# Simple demo function
def demo(bin_path):
    """Demo function to showcase the BinExplorer functionality"""
    explorer = BinExplorer(bin_path)
    explorer.open_bin()
    
    print(f"Exploring bin: {bin_path}")
    
    # Extract basic info
    basic_info = explorer.extract_basic_info()
    print("\nBasic Information:")
    print(f"File: {basic_info['filename']}")
    print(f"View Mode: {basic_info['view_mode']}")
    print(f"Display Options: {', '.join(basic_info['display_options'])}")
    
    # Extract clips
    clips = explorer.extract_clips()
    print(f"\nFound {len(clips)} items in bin:")
    for i, clip in enumerate(clips[:5], 1):  # Show first 5 clips only
        print(f"{i}. {clip['name']} ({clip['type']})")
        if 'media_info' in clip and clip['media_info']:
            media = clip['media_info']
            if 'width' in media and 'height' in media:
                print(f"   Resolution: {media['width']}x{media['height']}")
            if 'frame_rate' in media:
                print(f"   Frame Rate: {media['frame_rate']}")
    
    if len(clips) > 5:
        print(f"... and {len(clips) - 5} more items")
    
    # Extract sequences
    sequences = explorer.extract_sequences()
    print(f"\nFound {len(sequences)} sequences:")
    for i, seq in enumerate(sequences, 1):
        print(f"{i}. {seq['name']}")
        if 'tracks' in seq:
            print(f"   Tracks: {len(seq['tracks'])}")
            track_types = {}
            for track in seq['tracks']:
                track_type = track.get('type', 'Unknown')
                track_types[track_type] = track_types.get(track_type, 0) + 1
            
            for track_type, count in track_types.items():
                print(f"   - {track_type}: {count}")
    
    # Export metadata
    json_path = explorer.export_metadata_json()
    print(f"\nMetadata exported to: {json_path}")
    
    explorer.close_bin()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bin_explorer.py path/to/bin.avb")
        sys.exit(1)
    
    demo(sys.argv[1])