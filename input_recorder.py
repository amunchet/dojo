"""
Input Recorder Module
Handles keystroke and mouse event recording with timestamps
"""

import time
from pynput import keyboard
from datetime import datetime
from typing import List, Dict, Callable, Optional


class InputRecorder:
    """Records keyboard inputs with precise timestamps"""
    
    def __init__(self, start_time: Optional[float] = None):
        """
        Initialize the input recorder
        
        Args:
            start_time: Reference time for timestamp calculation (default: current time)
        """
        self.keystrokes: List[Dict] = []
        self.start_time = start_time or time.time()
        self.listener = None
        self.is_recording = False
        self.on_escape_callback: Optional[Callable] = None
        
    def start(self):
        """Start recording keyboard inputs"""
        self.is_recording = True
        self.keystrokes = []
        self.start_time = time.time()
        
        # Create and start keyboard listener
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        print("Recording started...")
        
    def stop(self):
        """Stop recording keyboard inputs"""
        self.is_recording = False
        if self.listener:
            self.listener.stop()
            self.listener = None
        print(f"Recording stopped. Captured {len(self.keystrokes)} events.")
        
    def _get_timestamp(self) -> float:
        """Get current timestamp relative to start time"""
        return time.time() - self.start_time
        
    def _key_to_string(self, key) -> str:
        """Convert pynput key to string representation"""
        try:
            # Regular character keys
            return key.char
        except AttributeError:
            # Special keys
            return str(key).replace('Key.', '')
            
    def _on_press(self, key):
        """Handle key press event"""
        if not self.is_recording:
            return
            
        # Check for ESC key to trigger callback
        if key == keyboard.Key.esc and self.on_escape_callback:
            self.on_escape_callback()
            return
            
        timestamp = self._get_timestamp()
        key_str = self._key_to_string(key)
        
        self.keystrokes.append({
            'time': round(timestamp, 3),
            'key': key_str,
            'action': 'press'
        })
        
    def _on_release(self, key):
        """Handle key release event"""
        if not self.is_recording:
            return
            
        timestamp = self._get_timestamp()
        key_str = self._key_to_string(key)
        
        self.keystrokes.append({
            'time': round(timestamp, 3),
            'key': key_str,
            'action': 'release'
        })
        
    def get_recording(self) -> List[Dict]:
        """Get the recorded keystroke data"""
        return self.keystrokes.copy()
        
    def record_frame_based_keystroke(self, frame: int, key: str, action: str):
        """Record a keystroke with frame number instead of time"""
        self.keystrokes.append({
            'frame': frame,
            'key': key,
            'action': action
        })
        
    def set_escape_callback(self, callback: Callable):
        """Set callback function to be called when ESC is pressed"""
        self.on_escape_callback = callback
        
    def clear(self):
        """Clear all recorded keystrokes"""
        self.keystrokes = []
        self.start_time = time.time()
