"""
Pattern Manager Module
Loads and manages keystroke patterns from recording files
"""

import json
import os
from typing import List, Dict, Optional, Tuple


class Pattern:
    """Represents a keystroke pattern loaded from a recording"""
    
    def __init__(self, filename: str):
        """
        Initialize pattern from a recording file
        
        Args:
            filename: Path to recording JSON file
        """
        self.filename = filename
        self.video_url = ""
        self.duration = 0.0
        self.recording_date = ""
        self.keystrokes: List[Dict] = []
        self._key_presses: List[Dict] = []
        
        self._load_from_file(filename)
        self._extract_key_presses()
        
    def _load_from_file(self, filename: str):
        """Load pattern data from JSON file"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Recording file not found: {filename}")
            
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.video_url = data.get('video_url', '')
        self.duration = data.get('duration', 0.0)
        self.recording_date = data.get('recording_date', '')
        self.keystrokes = data.get('keystrokes', [])
        
    def _extract_key_presses(self):
        """Extract only key press events (not releases)"""
        self._key_presses = [
            ks for ks in self.keystrokes 
            if ks.get('action') == 'press'
        ]
        # Sort by frame or time (support both formats)
        if self._key_presses and 'frame' in self._key_presses[0]:
            self._key_presses.sort(key=lambda x: x.get('frame', 0))
        else:
            self._key_presses.sort(key=lambda x: x.get('time', 0))
        
    def get_key_presses(self) -> List[Dict]:
        """
        Get list of key press events
        
        Returns:
            List of {frame, key} or {time, key} dictionaries
        """
        result = []
        for kp in self._key_presses:
            if 'frame' in kp:
                result.append({'frame': kp['frame'], 'key': kp['key']})
            else:
                result.append({'time': kp['time'], 'key': kp['key']})
        return result
        
    def get_upcoming_keys(self, current_time: float, lookahead: float = 5.0) -> List[Tuple[float, str]]:
        """
        Get keys that are coming up in the near future
        
        Args:
            current_time: Current playback time in seconds
            lookahead: Time window to look ahead (seconds)
            
        Returns:
            List of (time_offset, key) tuples for upcoming keys
        """
        upcoming = []
        for kp in self._key_presses:
            key_time = kp['time']
            if current_time < key_time <= current_time + lookahead:
                upcoming.append((key_time - current_time, kp['key']))
        return upcoming


class PatternManager:
    """Manages pattern collection and loading"""
    
    def __init__(self, recordings_dir: str = "data/recordings"):
        """
        Initialize pattern manager
        
        Args:
            recordings_dir: Directory containing recording files
        """
        self.recordings_dir = recordings_dir
        self.patterns: Dict[str, Pattern] = {}
        self.current_pattern: Optional[Pattern] = None
        
    def load_pattern(self, filename: str) -> bool:
        """
        Load a pattern from file
        
        Args:
            filename: Path to recording JSON file
            
        Returns:
            True if loaded successfully
        """
        try:
            pattern = Pattern(filename)
            self.patterns[filename] = pattern
            self.current_pattern = pattern
            return True
        except Exception as e:
            print(f"Error loading pattern: {e}")
            return False
            
    def list_recordings(self) -> List[str]:
        """
        List all available recording files
        
        Returns:
            List of recording filenames
        """
        if not os.path.exists(self.recordings_dir):
            return []
            
        files = []
        for filename in os.listdir(self.recordings_dir):
            if filename.endswith('.json'):
                files.append(os.path.join(self.recordings_dir, filename))
        return sorted(files)
        
    def select_recording(self, index: int) -> bool:
        """
        Select a recording by index from available recordings
        
        Args:
            index: Index in the recordings list
            
        Returns:
            True if loaded successfully
        """
        recordings = self.list_recordings()
        if 0 <= index < len(recordings):
            return self.load_pattern(recordings[index])
        return False
