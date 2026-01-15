"""
Visual Trigger Module
Detects visual changes in screen regions and associates them with keystrokes
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List


class VisualTrigger:
    """Monitors a region of interest for visual changes"""
    
    def __init__(self, threshold: float = 25.0):
        """
        Initialize visual trigger
        
        Args:
            threshold: Difference threshold to detect change (0-100)
        """
        self.roi = None  # (x, y, w, h)
        self.last_frame_roi = None
        self.threshold = threshold
        self.is_selecting = False
        self.selection_start = None
        self.selection_current = None
        
    def start_selection(self, x: int, y: int):
        """Start selecting ROI"""
        self.is_selecting = True
        self.selection_start = (x, y)
        self.selection_current = (x, y)
        
    def update_selection(self, x: int, y: int):
        """Update selection during drag"""
        if self.is_selecting:
            self.selection_current = (x, y)
            
    def finish_selection(self):
        """Finish ROI selection"""
        if self.is_selecting and self.selection_start and self.selection_current:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_current
            
            # Ensure top-left to bottom-right
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            
            if w > 10 and h > 10:  # Minimum size
                self.roi = (x, y, w, h)
                self.last_frame_roi = None
                print(f"ROI set: {self.roi}")
            else:
                print("ROI too small, selection cancelled")
                
        self.is_selecting = False
        self.selection_start = None
        self.selection_current = None
        
    def cancel_selection(self):
        """Cancel ROI selection"""
        self.is_selecting = False
        self.selection_start = None
        self.selection_current = None
        
    def clear_roi(self):
        """Clear the ROI"""
        self.roi = None
        self.last_frame_roi = None
        print("ROI cleared")
        
    def has_roi(self) -> bool:
        """Check if ROI is set"""
        return self.roi is not None
        
    def get_selection_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Get current selection rectangle during drag"""
        if self.is_selecting and self.selection_start and self.selection_current:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_current
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            return (x, y, w, h)
        return None
        
    def detect_change(self, frame: np.ndarray) -> bool:
        """
        Detect if ROI has changed significantly
        
        Args:
            frame: Current video frame
            
        Returns:
            True if significant change detected
        """
        if not self.roi:
            return False
            
        x, y, w, h = self.roi
        
        # Extract ROI from current frame
        if y + h > frame.shape[0] or x + w > frame.shape[1]:
            return False
            
        current_roi = frame[y:y+h, x:x+w].copy()
        
        # Convert to grayscale for comparison
        current_gray = cv2.cvtColor(current_roi, cv2.COLOR_BGR2GRAY)
        
        # First frame - just store it
        if self.last_frame_roi is None:
            self.last_frame_roi = current_gray
            return False
            
        # Calculate difference
        diff = cv2.absdiff(self.last_frame_roi, current_gray)
        mean_diff = np.mean(diff)
        
        # Update last frame
        self.last_frame_roi = current_gray
        
        # Check if change exceeds threshold
        if mean_diff > self.threshold:
            print(f"Visual change detected: {mean_diff:.2f}")
            return True
            
        return False
        
    def draw_roi(self, frame: np.ndarray, color=(0, 255, 0), thickness=2):
        """
        Draw ROI rectangle on frame
        
        Args:
            frame: Frame to draw on
            color: Rectangle color (BGR)
            thickness: Line thickness
        """
        if self.roi:
            x, y, w, h = self.roi
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
            cv2.putText(frame, "ROI", (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                       
        # Draw selection in progress
        selection = self.get_selection_rect()
        if selection:
            x, y, w, h = selection
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
            cv2.putText(frame, "Selecting...", (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
