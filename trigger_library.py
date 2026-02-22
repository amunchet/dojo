"""
Trigger Library Module
Manages a library of visual triggers with template matching
"""

import os
import json
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class VisualTriggerLibrary:
    """Manages a library of learned visual triggers for automatic detection"""
    
    def __init__(self, library_path: str = "data/trigger_library.json", 
                 templates_dir: str = "data/templates"):
        """
        Initialize the trigger library
        
        Args:
            library_path: Path to JSON file storing trigger metadata
            templates_dir: Directory to store template images
        """
        self.library_path = library_path
        self.templates_dir = templates_dir
        self.triggers: List[Dict] = []
        
        # Create directories
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(os.path.dirname(library_path), exist_ok=True)
        
        # Load existing library
        self._load_library()
        
    def _load_library(self):
        """Load trigger library from JSON file"""
        if os.path.exists(self.library_path):
            with open(self.library_path, 'r') as f:
                data = json.load(f)
                self.triggers = data.get('triggers', [])
        else:
            self.triggers = []
            
    def _save_library(self):
        """Save trigger library to JSON file"""
        data = {'triggers': self.triggers}
        with open(self.library_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    def add_trigger(self, roi_image: np.ndarray, roi_rect: Tuple[int, int, int, int],
                   key: str, spell_name: str = "", pause_before: float = 1.0) -> str:
        """
        Add a new visual trigger to the library
        
        Args:
            roi_image: Image of the ROI (numpy array)
            roi_rect: ROI rectangle (x, y, w, h)
            key: Key to press when this trigger is detected
            spell_name: Name/description of the spell/ability
            pause_before: Seconds to pause before the key event
            
        Returns:
            Trigger ID
        """
        # Generate unique ID
        trigger_id = f"trigger_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        template_filename = f"{trigger_id}.png"
        template_path = os.path.join(self.templates_dir, template_filename)
        
        # Save template image
        cv2.imwrite(template_path, roi_image)
        
        # Create trigger metadata
        trigger = {
            'id': trigger_id,
            'spell_name': spell_name,
            'key': key,
            'pause_before_seconds': pause_before,
            'template_path': template_path,
            'roi': list(roi_rect),
            'created_at': datetime.now().isoformat()
        }
        
        self.triggers.append(trigger)
        self._save_library()
        
        print(f"Trigger '{spell_name}' (key: {key}) saved with ID: {trigger_id}")
        return trigger_id
        
    def find_matching_trigger(self, frame: np.ndarray, roi_rect: Tuple[int, int, int, int],
                             threshold: float = 0.8) -> Optional[Dict]:
        """
        Find a matching trigger from the library using template matching
        
        Args:
            frame: Current video frame
            roi_rect: ROI rectangle to check (x, y, w, h)
            threshold: Matching threshold (0-1, higher = more strict)
            
        Returns:
            Matching trigger dict or None
        """
        if not self.triggers:
            return None
            
        x, y, w, h = roi_rect
        if y + h > frame.shape[0] or x + w > frame.shape[1]:
            return None
            
        # Extract current ROI
        current_roi = frame[y:y+h, x:x+w]
        current_gray = cv2.cvtColor(current_roi, cv2.COLOR_BGR2GRAY)
        
        best_match = None
        best_score = 0.0
        
        # Compare with all templates
        for trigger in self.triggers:
            # Load template
            template_path = trigger['template_path']
            if not os.path.exists(template_path):
                continue
                
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            
            # Resize template to match current ROI size if needed
            if template.shape != current_gray.shape:
                template = cv2.resize(template, (current_gray.shape[1], current_gray.shape[0]))
            
            # Compare using normalized cross-correlation
            result = cv2.matchTemplate(current_gray, template, cv2.TM_CCOEFF_NORMED)
            score = result[0, 0]
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = trigger.copy()
                best_match['match_score'] = score
                
        return best_match
        
    def list_triggers(self) -> List[Dict]:
        """Get list of all triggers in the library"""
        return self.triggers.copy()
        
    def delete_trigger(self, trigger_id: str) -> bool:
        """
        Delete a trigger from the library
        
        Args:
            trigger_id: ID of trigger to delete
            
        Returns:
            True if deleted successfully
        """
        for i, trigger in enumerate(self.triggers):
            if trigger['id'] == trigger_id:
                # Delete template file
                template_path = trigger['template_path']
                if os.path.exists(template_path):
                    os.remove(template_path)
                    
                # Remove from library
                self.triggers.pop(i)
                self._save_library()
                return True
                
        return False
        
    def update_trigger(self, trigger_id: str, **kwargs) -> bool:
        """
        Update trigger metadata
        
        Args:
            trigger_id: ID of trigger to update
            **kwargs: Fields to update (spell_name, key, pause_before_seconds)
            
        Returns:
            True if updated successfully
        """
        for trigger in self.triggers:
            if trigger['id'] == trigger_id:
                for key, value in kwargs.items():
                    if key in ['spell_name', 'key', 'pause_before_seconds']:
                        trigger[key] = value
                self._save_library()
                return True
                
        return False
