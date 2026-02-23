"""
Pattern Display Module
Renders animated keystroke patterns as a visual timeline
"""

import cv2
import numpy as np
import time
from typing import List, Dict, Optional, Tuple
from enum import Enum


class HitAccuracy(Enum):
    """Enum for hit accuracy feedback"""
    PERFECT = "PERFECT"
    GOOD = "GOOD"
    OK = "OK"
    MISS = "MISS"


class KeyNote:
    """Represents a single key note on the timeline"""
    
    def __init__(self, frame: int, key: str, screen_height: int = 720):
        """
        Initialize a key note
        
        Args:
            frame: Frame number when key should be pressed
            key: Key character/name
            screen_height: Screen height for positioning
        """
        self.frame = frame
        self.key = key
        self.screen_height = screen_height
        self.hit = False
        self.hit_frame = None
        self.accuracy = None
        
    def get_x_position(self, current_frame: int, lookahead_frames: int = 150, 
                       screen_width: int = 1280, center_x_ratio: float = 0.5) -> Optional[int]:
        """
        Calculate X position of note on screen
        
        Args:
            current_frame: Current frame number
            lookahead_frames: Frame window visible on timeline (frames shown ahead)
            screen_width: Screen width
            center_x_ratio: Where the center target line is (0-1)
            
        Returns:
            X pixel position or None if off-screen
        """
        frames_until_press = self.frame - current_frame
        
        # If too far in the past or future, off screen
        if frames_until_press < -15 or frames_until_press > lookahead_frames:
            return None
        
        # Calculate center position
        center_x = int(screen_width * center_x_ratio)
        
        # Map frames to x position:
        # frames_until_press = 0 -> x = center_x (time to press!)
        # frames_until_press = lookahead_frames -> x = screen_width (far right)
        # frames_until_press = -15 -> x = 0 (far left, just passed)
        
        # Linear interpolation from center
        if frames_until_press >= 0:
            # Future: between center and right edge
            # Map [0, lookahead_frames] to [center_x, screen_width]
            x = center_x + int((frames_until_press / lookahead_frames) * (screen_width - center_x))
        else:
            # Past: between left edge and center
            # Map [-15, 0] to [0, center_x]
            x = center_x + int((frames_until_press / 15) * center_x)
        
        return max(0, min(x, screen_width - 1))
        
    def is_in_hit_window(self, current_frame: int, window_frames: int = 5) -> bool:
        """
        Check if current frame is in the hit window for this note
        
        Args:
            current_frame: Current frame number
            window_frames: Frame window before/after target frame
            
        Returns:
            True if in hit window
        """
        return abs(current_frame - self.frame) <= window_frames
        
    def get_distance_from_center(self, current_frame: int) -> int:
        """Get how far from center target this note is (frames)"""
        return abs(current_frame - self.frame)


class PatternDisplay:
    """Renders visual pattern display with animated keys"""
    
    # Visual constants
    TIMELINE_HEIGHT = 120
    KEY_SIZE = 60
    CENTER_X_RATIO = 0.5  # Where center target is on screen (0-1)
    HIT_FEEDBACK_DURATION = 0.3  # How long hit feedback shows (seconds)
    
    # Colors (BGR format for OpenCV)
    COLOR_BG = (20, 20, 20)  # Dark background
    COLOR_TIMELINE = (50, 50, 50)  # Timeline bar color
    COLOR_CENTER = (0, 255, 0)  # Green center target line
    COLOR_KEY_UPCOMING = (100, 149, 237)  # Cornflower blue for upcoming
    COLOR_KEY_CLOSE = (255, 200, 0)  # Cyan for keys near center
    COLOR_KEY_HIT = (0, 255, 0)  # Green for successful hit
    COLOR_KEY_MISS = (0, 0, 255)  # Red for miss
    COLOR_TEXT = (200, 200, 200)  # Light gray text
    
    def __init__(self, screen_width: int = 1280, screen_height: int = 720):
        """
        Initialize pattern display
        
        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.notes: List[KeyNote] = []
        self.pressed_keys = set()  # Currently held keys
        self.recent_hits: List[Tuple[float, str, HitAccuracy]] = []  # (time, key, accuracy)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.lookahead_frames = 150  # Frames of timeline visible ahead (5 sec @ 30fps)
        self.key_metadata: Dict[str, Dict] = {}
        self.thumbnail_cache: Dict[str, Optional[np.ndarray]] = {}
        self.default_pause_before_seconds = 1.0

    def set_key_metadata(self, key_metadata: Dict[str, Dict]):
        """
        Set key metadata for pause timing and thumbnails.

        Expected format:
            {
                'key': {
                    'pause_before_seconds': 1.0,
                    'template_path': '/path/to/image.png'
                },
                ...
            }
        """
        self.key_metadata = key_metadata or {}
        self.thumbnail_cache.clear()

    def _get_pause_lead_frames(self, key: str, fps: float) -> int:
        pause_time = self.default_pause_before_seconds
        meta = self.key_metadata.get(key)
        if meta and 'pause_before_seconds' in meta:
            pause_time = meta['pause_before_seconds']
        return int(pause_time * fps)

    def _load_thumbnail(self, key: str) -> Optional[np.ndarray]:
        if key in self.thumbnail_cache:
            return self.thumbnail_cache[key]

        meta = self.key_metadata.get(key)
        if not meta or 'template_path' not in meta:
            self.thumbnail_cache[key] = None
            return None

        path = meta['template_path']
        if not path or not isinstance(path, str):
            self.thumbnail_cache[key] = None
            return None

        image = cv2.imread(path)
        if image is None:
            self.thumbnail_cache[key] = None
            return None

        # Resize thumbnail to fit note size
        size = int(self.KEY_SIZE * 0.9)
        image = cv2.resize(image, (size, size))
        self.thumbnail_cache[key] = image
        return image

    def _frame_to_x(self, target_frame: int, current_frame: int,
                    screen_width: int, center_x_ratio: float) -> int:
        """Map an arbitrary frame to x position, clamped to screen bounds."""
        frames_until = target_frame - current_frame
        center_x = int(screen_width * center_x_ratio)

        if frames_until >= 0:
            x = center_x + int((frames_until / self.lookahead_frames) * (screen_width - center_x))
        else:
            x = center_x + int((frames_until / 15) * center_x)

        return max(0, min(x, screen_width - 1))
        
    def add_notes(self, key_presses: List[Dict]):
        """
        Add notes from pattern
        
        Args:
            key_presses: List of {frame, key} or {time, key} dictionaries
        """
        notes = []
        for kp in key_presses:
            if 'frame' in kp:
                notes.append(KeyNote(kp['frame'], kp['key'], self.screen_height))
            elif 'time' in kp:
                # Convert time to approximate frame (30 fps assumed)
                frame = int(kp['time'] * 30)
                notes.append(KeyNote(frame, kp['key'], self.screen_height))
        self.notes = notes
        
    def reset(self):
        """Reset display state"""
        self.notes = []
        self.pressed_keys.clear()
        self.recent_hits.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        
    def register_key_press(self, key: str, current_frame: int) -> HitAccuracy:
        """
        Register a key press and evaluate accuracy
        
        Args:
            key: Key that was pressed
            current_frame: Frame number of the press
            
        Returns:
            Hit accuracy result
        """
        self.pressed_keys.add(key)
        
        # Find the most recent unhit note for this key
        accuracy = HitAccuracy.MISS
        best_distance = float('inf')
        best_note = None
        
        for note in self.notes:
            if note.hit or note.key != key:
                continue
                
            distance = note.get_distance_from_center(current_frame)
            if distance < best_distance:
                best_distance = distance
                best_note = note
                
        if best_note:
            # Evaluate accuracy based on frame timing (at 30fps: 2 frames ~ 0.067s)
            if best_distance < 3:  # ~0.1s
                accuracy = HitAccuracy.PERFECT
                self.score += 100
            elif best_distance < 5:  # ~0.167s
                accuracy = HitAccuracy.GOOD
                self.score += 75
            elif best_distance < 8:  # ~0.267s
                accuracy = HitAccuracy.OK
                self.score += 25
            else:
                accuracy = HitAccuracy.MISS
                
            if accuracy != HitAccuracy.MISS:
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                best_note.hit = True
                best_note.hit_frame = current_frame
                best_note.accuracy = accuracy
            else:
                self.combo = 0
        else:
            # No valid note to hit (early press or wrong key)
            accuracy = HitAccuracy.MISS
            self.combo = 0
            
        # Add to recent hits for display feedback
        self.recent_hits.append((current_frame, key, accuracy))
        
        # Keep only recent hits for display
        if len(self.recent_hits) > 20:
            self.recent_hits.pop(0)
            
        return accuracy
        
    def register_key_release(self, key: str):
        """Register a key release"""
        self.pressed_keys.discard(key)
        
    def _draw_timeline_bar(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """Draw the horizontal timeline bar"""
        y_start = self.screen_height - self.TIMELINE_HEIGHT
        
        # Timeline background
        cv2.rectangle(frame, (0, y_start), (self.screen_width, self.screen_height),
                     self.COLOR_TIMELINE, -1)
        
        # Center target line (where keys should be hit)
        center_x = int(self.screen_width * self.CENTER_X_RATIO)
        cv2.line(frame, (center_x, y_start), (center_x, self.screen_height),
                self.COLOR_CENTER, 3)
        
        # Draw target zone around center
        zone_width = 20
        cv2.rectangle(frame, (center_x - zone_width, y_start), 
                     (center_x + zone_width, y_start + 15),
                     self.COLOR_CENTER, 1)
        
        return frame
        
    def _draw_notes(self, frame: np.ndarray, current_frame: int, fps: float) -> np.ndarray:
        """Draw all active key notes on the timeline"""
        y_center = self.screen_height - self.TIMELINE_HEIGHT // 2
        center_x = int(self.screen_width * self.CENTER_X_RATIO)
        
        for note in self.notes:
            x = note.get_x_position(current_frame, self.lookahead_frames, self.screen_width, self.CENTER_X_RATIO)
            
            if x is None:
                continue
                
            # Determine color based on note state
            if note.hit:
                if note.accuracy == HitAccuracy.PERFECT:
                    color = (0, 255, 100)  # Bright green
                elif note.accuracy == HitAccuracy.GOOD:
                    color = (0, 255, 200)  # Light green
                else:
                    color = self.COLOR_KEY_HIT
            else:
                # Check if in hit zone
                distance_from_center = abs(x - center_x)
                if distance_from_center < 40:
                    color = self.COLOR_KEY_CLOSE  # Cyan - very close to center
                else:
                    color = self.COLOR_KEY_UPCOMING  # Blue - normal

            # Draw lead-time bar from pause moment to actual event
            lead_frames = self._get_pause_lead_frames(note.key, fps)
            pause_frame = note.frame - lead_frames
            frames_until_pause = pause_frame - current_frame
            frames_until_event = note.frame - current_frame
            # Only draw if any part is within visible window
            if (
                not (frames_until_pause > self.lookahead_frames and frames_until_event > self.lookahead_frames)
                and not (frames_until_pause < -15 and frames_until_event < -15)
            ):
                pause_x = self._frame_to_x(pause_frame, current_frame, self.screen_width, self.CENTER_X_RATIO)
                event_x = self._frame_to_x(note.frame, current_frame, self.screen_width, self.CENTER_X_RATIO)
                bar_y = y_center - self.KEY_SIZE // 2
                bar_height = self.KEY_SIZE
                x1, x2 = sorted([pause_x, event_x])
                # Stop bar at the left edge of the event box to avoid covering it
                if event_x >= pause_x:
                    x2 = min(x2, event_x - (self.KEY_SIZE // 2))
                else:
                    x1 = max(x1, event_x + (self.KEY_SIZE // 2))
                cv2.rectangle(frame, (x1, bar_y), (x2, bar_y + bar_height), color, -1)
                cv2.rectangle(frame, (x1, bar_y), (x2, bar_y + bar_height), (0, 0, 0), 1)
                    
            # Draw key note outline at event position
            size = self.KEY_SIZE
            cv2.rectangle(frame, (x - size//2, y_center - size//2),
                         (x + size//2, y_center + size//2),
                         color, 2)

            # Place thumbnail at pause start (offset) position
            thumb = self._load_thumbnail(note.key)
            if thumb is not None:
                th, tw = thumb.shape[:2]
                icon_x = (pause_x + (tw // 2)) if 'pause_x' in locals() else x
                x1 = max(0, icon_x - tw // 2)
                y1 = max(0, y_center - th // 2)
                x2 = min(self.screen_width, x1 + tw)
                y2 = min(self.screen_height, y1 + th)

                roi = frame[y1:y2, x1:x2]
                thumb_crop = thumb[0:(y2 - y1), 0:(x2 - x1)]
                if roi.shape == thumb_crop.shape:
                    frame[y1:y2, x1:x2] = thumb_crop

            # Draw key label at event position (where action is recorded)
            key_text = str(note.key).upper()
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 1
            text_size = cv2.getTextSize(key_text, font, font_scale, thickness)[0]
            text_x = x - text_size[0] // 2
            text_y = y_center + text_size[1] // 2
            cv2.putText(frame, key_text, (text_x, text_y), font, 
                       font_scale, color, thickness)
            
        return frame
        
    def _draw_score_panel(self, frame: np.ndarray) -> np.ndarray:
        """Draw score, combo, and time information"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        color = self.COLOR_TEXT
        
        # Score
        score_text = f"Score: {self.score}"
        cv2.putText(frame, score_text, (10, 30), font, font_scale, color, thickness)
        
        # Combo
        combo_text = f"Combo: {self.combo}"
        combo_color = (0, 255, 0) if self.combo > 0 else (100, 100, 100)
        cv2.putText(frame, combo_text, (10, 70), font, font_scale, combo_color, thickness)
        
        # Max Combo
        max_combo_text = f"Max: {self.max_combo}"
        cv2.putText(frame, max_combo_text, (10, 110), font, font_scale, color, thickness)
        
        return frame
        
    def _draw_hit_feedback(self, frame: np.ndarray, current_frame: int, fps: float = 30.0) -> np.ndarray:
        """Draw recent hit feedback"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        
        # Show most recent hit
        if self.recent_hits:
            hit_frame, hit_key, accuracy = self.recent_hits[-1]
            elapsed_frames = current_frame - hit_frame
            elapsed = elapsed_frames / fps
            
            if elapsed < self.HIT_FEEDBACK_DURATION:
                # Fade out effect
                alpha = 1.0 - (elapsed / self.HIT_FEEDBACK_DURATION)
                
                text = accuracy.value
                color = {
                    HitAccuracy.PERFECT: (0, 255, 100),
                    HitAccuracy.GOOD: (0, 255, 200),
                    HitAccuracy.OK: (100, 200, 255),
                    HitAccuracy.MISS: (0, 0, 255),
                }[accuracy]
                
                # Semi-transparent drawing
                feedback_y = self.screen_height // 2 - 50
                text_size = cv2.getTextSize(text, font, font_scale * 2, thickness)[0]
                text_x = self.screen_width // 2 - text_size[0] // 2
                
                cv2.putText(frame, text, (text_x, feedback_y), font, 
                           font_scale * 2, color, thickness)
                
        return frame
        
    def render(self, frame: np.ndarray, current_frame: int, fps: float = 30.0) -> np.ndarray:
        """
        Render pattern display overlay on frame
        
        Args:
            frame: Video frame to render on
            current_frame: Current frame number
            fps: Frames per second for time calculation
            
        Returns:
            Frame with pattern display rendered
        """
        current_time = current_frame / fps
        
        # Draw timeline bar
        frame = self._draw_timeline_bar(frame, current_time)
        
        # Draw notes
        frame = self._draw_notes(frame, current_frame, fps)
        
        # Draw score panel
        frame = self._draw_score_panel(frame)
        
        # Draw hit feedback
        frame = self._draw_hit_feedback(frame, current_frame, fps)
        
        # Draw time and frame display
        font = cv2.FONT_HERSHEY_SIMPLEX
        time_text = f"Time: {current_time:.2f}s | Frame: {current_frame}"
        cv2.putText(frame, time_text, (self.screen_width - 350, 70),
                   font, 0.7, self.COLOR_TEXT, 2)
        
        # Draw help text
        help_text = "ESC: Exit | R: Restart | SPACE: Play/Pause"
        cv2.putText(frame, help_text, (self.screen_width - 400, 30),
                   font, 0.5, self.COLOR_TEXT, 1)
        
        return frame
