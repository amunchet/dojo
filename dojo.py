"""
Dojo - Gaming Training Application
Stage 1: Video Playback and Keystroke Recording
Stage 2: Pattern Display with Visual Timeline
"""

import os
import json
import cv2
import time
from datetime import datetime
from video_player_24fps import VideoPlayer
from input_recorder import InputRecorder
from pattern_manager import PatternManager
from pattern_display import PatternDisplay
from visual_trigger import VisualTrigger
from trigger_library import VisualTriggerLibrary
from pynput import keyboard


class DojoApp:
    """Main application class for Dojo training system"""
    
    def __init__(self):
        self.video_player = VideoPlayer()
        self.input_recorder = InputRecorder()
        self.pattern_manager = PatternManager()
        self.pattern_display = None
        self.visual_trigger = VisualTrigger(threshold=25.0)
        self.trigger_library = VisualTriggerLibrary()
        self.running = False
        self.video_url = None
        self.stage = 1  # Current stage
        self.keyboard_listener = None
        self.pending_trigger_frame = None  # Frame waiting for key assignment
        
        # Create data directories
        os.makedirs("data/recordings", exist_ok=True)
        os.makedirs("data/cache", exist_ok=True)
        
    def save_recording(self):
        """Save recorded keystroke data to JSON file"""
        if not self.input_recorder.keystrokes:
            print("No keystrokes recorded")
            return
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/recordings/recording_{timestamp}.json"
        
        # Prepare data
        data = {
            'video_url': self.video_url,
            'duration': self.video_player.duration,
            'recording_date': datetime.now().isoformat(),
            'keystrokes': self.input_recorder.get_recording()
        }
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Recording saved to: {filename}")
        print(f"Total keystrokes: {len(data['keystrokes'])}")
        
    def handle_escape(self):
        """Handle ESC key press - stop recording and exit"""
        print("\nESC pressed - stopping...")
        self.running = False
        
    def _select_stage(self) -> int:
        """
        Display stage selection menu
        
        Returns:
            Selected stage number
        """
        print("\n" + "=" * 50)
        print("SELECT TRAINING STAGE")
        print("=" * 50)
        print("1 - Stage 1: Record Keystrokes (Create New Pattern)")
        print("2 - Stage 2: Practice with Pattern (Play Recorded Pattern)")
        print("3 - Manage Trigger Library")
        print("=" * 50)
        
        while True:
            choice = input("\nEnter choice (1, 2, or 3): ").strip()
            if choice in ['1', '2', '3']:
                return int(choice)
            print("Invalid choice. Please enter 1, 2, or 3.")
            
    def run_stage2_practice(self):
        """Run Stage 2 - Pattern practice mode"""
        print("\n" + "=" * 50)
        print("STAGE 2 - Pattern Practice Mode")
        print("=" * 50)
        
        # List available recordings
        recordings = self.pattern_manager.list_recordings()
        if not recordings:
            print("No recordings found. Please record a pattern in Stage 1 first.")
            return
            
        print("\nAvailable patterns:")
        for i, recording in enumerate(recordings, 1):
            print(f"{i} - {os.path.basename(recording)}")
            
        while True:
            try:
                choice = int(input("\nSelect pattern (number): ")) - 1
                if 0 <= choice < len(recordings):
                    break
                print("Invalid choice.")
            except ValueError:
                print("Please enter a valid number.")
                
        # Load pattern
        print(f"\nLoading pattern: {os.path.basename(recordings[choice])}")
        if not self.pattern_manager.load_pattern(recordings[choice]):
            print("Error loading pattern.")
            return
            
        pattern = self.pattern_manager.current_pattern
        
        # Download/load video
        print(f"\nVideo URL: {pattern.video_url}")
        try:
            print("Preparing video...")
            video_path = self.video_player.download_video(pattern.video_url)
            
            if not self.video_player.load_video(video_path):
                print("Error: Failed to load video")
                return
        except Exception as e:
            print(f"Error loading video: {e}")
            return
            
        # Initialize pattern display
        self.pattern_display = PatternDisplay(
            screen_width=int(self.video_player.frame_width),
            screen_height=int(self.video_player.frame_height)
        )
        # Provide trigger metadata (pause offsets and thumbnails) to the pattern display
        key_metadata = {}
        for trigger in self.trigger_library.list_triggers():
            key_metadata[trigger['key']] = {
                'pause_before_seconds': trigger.get('pause_before_seconds', 1.0),
                'template_path': trigger.get('template_path')
            }
        self.pattern_display.set_key_metadata(key_metadata)
        self.pattern_display.add_notes(pattern.get_key_presses())
        
        # Reset video to frame 0
        self.video_player.current_frame = 0
        self.video_player.start_time = 0
        
        print("\nControls:")
        print("  Press required key to start (shown on screen)")
        print("  R     - Restart")
        print("  ESC   - Exit")
        print("\nReady to play. Video will pause 1 second before each key event.")
        
        try:
            # --- Setup for Stage 2: pause before key events, require correct key press ---
            notes = self.pattern_display.notes if self.pattern_display else []
            note_frames = sorted([note.frame for note in notes])
            fps = self.video_player.fps if self.video_player else 30
            next_pause_idx = 0
            paused_for_event = False
            required_key = None
            
            # Build a lookup map: key -> pause_before_seconds from library
            key_to_pause_time = {}
            for trigger in self.trigger_library.list_triggers():
                key_to_pause_time[trigger['key']] = trigger['pause_before_seconds']

            def get_required_key():
                if next_pause_idx < len(notes):
                    return notes[next_pause_idx].key
                return None
            
            def get_pause_lead_frames(key):
                """Get pause lead time in frames for a given key, based on library or default"""
                pause_time = key_to_pause_time.get(key, 1.0)  # Default to 1.0 if not in library
                return int(pause_time * fps)

            def on_practice_key_press(key):
                nonlocal paused_for_event, next_pause_idx, required_key
                try:
                    if key == keyboard.Key.esc:
                        self.running = False
                        return False
                    key_str = None
                    try:
                        key_str = key.char
                    except AttributeError:
                        key_str = str(key).replace('Key.', '')
                    
                    print(f"DEBUG: Key pressed: '{key_str}' (type: {type(key_str)})")
                    
                    # Only allow resume if paused for event and correct key OR space is pressed
                    if paused_for_event and required_key is not None:
                        print(f"DEBUG: Paused for event, required_key='{required_key}', key_str='{key_str}'")
                        # Accept the required key, space character, or 'space' string
                        if key_str == required_key or key_str == ' ' or key_str == 'space':
                            if key_str == required_key:
                                print(f">>> Correct! '{required_key.upper()}' pressed. Continuing...\n")
                            else:
                                print(f">>> SPACE pressed. Continuing...\n")
                            print(f"DEBUG: Calling video_player.play()")
                            self.video_player.play()
                            print(f"DEBUG: is_paused is now {self.video_player.is_paused}")
                            next_pause_idx += 1
                            paused_for_event = False
                            required_key = None
                        else:
                            print(f">>> Wrong key! You pressed '{key_str.upper()}', need '{required_key.upper()}' or SPACE")
                        return
                    # If not paused for event, allow space to start/unpause the video initially
                    if key_str == ' ' or key_str == 'space':
                        if self.video_player.is_paused:
                            print("DEBUG: Space pressed, starting video")
                            self.video_player.play()
                        return
                    # Otherwise, normal key registration if not paused for event
                    if not self.video_player.is_paused and self.pattern_display:
                        current_frame = self.video_player.get_displayed_frame_number()
                        self.pattern_display.register_key_press(key_str, current_frame)
                except Exception as e:
                    print(f"DEBUG: Exception in on_practice_key_press: {e}")
                    import traceback
                    traceback.print_exc()

            def on_practice_key_release(key):
                try:
                    key_str = None
                    try:
                        key_str = key.char
                    except AttributeError:
                        key_str = str(key).replace('Key.', '')
                    if self.pattern_display:
                        self.pattern_display.register_key_release(key_str)
                except:
                    pass

            # Ensure any previous listener is stopped
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
            # Start the listener ONCE from the main thread, before entering the loop
            self.keyboard_listener = keyboard.Listener(on_press=on_practice_key_press, on_release=on_practice_key_release)
            self.keyboard_listener.start()

            self.video_player.is_playing = True
            self.video_player.is_paused = True
            self.running = True
            
            while self.running:
                ret, frame = self.video_player.get_frame()
                
                if ret and frame is not None:
                    displayed_frame = self.video_player.get_displayed_frame_number()
                    
                    # Check if we need to pause before the next note
                    # Dynamically calculate pause_lead_frames based on the key in the library
                    if (next_pause_idx < len(note_frames)
                        and not self.video_player.is_paused
                        and not paused_for_event):
                        next_key = get_required_key()
                        pause_lead_frames = get_pause_lead_frames(next_key)
                        
                        if displayed_frame >= note_frames[next_pause_idx] - pause_lead_frames:
                            self.video_player.pause()
                            paused_for_event = True
                            required_key = next_key
                            pause_time = key_to_pause_time.get(required_key, 1.0)
                            print(f"\n{'='*50}")
                            print(f">>> PAUSED {pause_time}s BEFORE KEY EVENT <<<")
                            print(f">>> PRESS THE '{required_key.upper()}' KEY TO CONTINUE <<<")
                            print(f"{'='*50}\n")
                    
                    # Render pattern display
                    frame = self.pattern_display.render(frame, displayed_frame, self.video_player.fps)
                    
                    # Draw required key in upper left above timeline if paused for event
                    if paused_for_event and required_key is not None:
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 1.2
                        thickness = 3
                        text = f"Press: {required_key.upper()}"
                        # Place above timeline (assume timeline at bottom 120px)
                        x, y = 30, self.video_player.frame_height - 160
                        cv2.putText(frame, text, (x, y), font, font_scale, (0, 255, 255), thickness, cv2.LINE_AA)
                        # Also print to console periodically so user always sees it
                        if displayed_frame % 30 == 0:  # Print every ~1 second at 30fps
                            print(f">>> Waiting for '{required_key.upper()}' key to continue...")
                    
                    # Display frame
                    cv2.imshow('Dojo - Training Mode', frame)
                    
                # Handle keyboard input (only for ESC/restart)
                delay = 1  # 1ms for responsive input
                key = cv2.waitKey(delay) & 0xFF
                
                if key == ord('r') or key == ord('R'):
                    # Restart
                    self.video_player.current_frame = 0
                    self.video_player.start_time = time.time()
                    self.video_player.total_paused_time = 0.0
                    self.video_player.is_paused = True
                    self.pattern_display.reset()
                    self.pattern_display.add_notes(pattern.get_key_presses())
                    # Reset pause logic
                    notes = self.pattern_display.notes if self.pattern_display else []
                    note_frames = sorted([note.frame for note in notes])
                    next_pause_idx = 0
                    paused_for_event = False
                    required_key = None
                elif key == 27:  # ESC
                    break
                    
                if not self.video_player.is_playing:
                    print("\nVideo ended")
                    print(f"\nFinal Score: {self.pattern_display.score}")
                    print(f"Max Combo: {self.pattern_display.max_combo}")
                    break
                    
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
            self.video_player.cleanup()
            
    def _start_practice_listener(self):
        """Start keyboard listener for pattern practice mode"""
        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    self.running = False
                    return False
                    
                # Get key character
                key_str = None
                try:
                    key_str = key.char
                except AttributeError:
                    key_str = str(key).replace('Key.', '')
                    
                if not self.video_player.is_paused and self.pattern_display:
                    # Use OpenCV's ground truth for the displayed frame
                    current_frame = self.video_player.get_displayed_frame_number()
                    self.pattern_display.register_key_press(key_str, current_frame)
            except:
                pass
                
        def on_release(key):
            try:
                key_str = None
                try:
                    key_str = key.char
                except AttributeError:
                    key_str = str(key).replace('Key.', '')
                    
                if self.pattern_display:
                    self.pattern_display.register_key_release(key_str)
            except:
                pass
                
        self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keyboard_listener.start()
        
    def _stop_practice_listener(self):
        """Stop keyboard listener"""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            
    def _start_recording_listener(self):
        """Start keyboard listener for recording mode (frame-based)"""
        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    self.running = False
                    return False
                    
                # Get key character
                key_str = None
                try:
                    key_str = key.char
                except AttributeError:
                    key_str = str(key).replace('Key.', '')
                    
                # Don't record space bar presses (used for playback control)
                if key_str == ' ' or key_str == 'space':
                    return
                    
                if not self.video_player.is_paused:
                    # Record using OpenCV's ground truth frame number
                    current_frame = self.video_player.get_displayed_frame_number()
                    self.input_recorder.record_frame_based_keystroke(current_frame, key_str, 'press')
            except:
                pass
                
        def on_release(key):
            try:
                key_str = None
                try:
                    key_str = key.char
                except AttributeError:
                    key_str = str(key).replace('Key.', '')
                    
                # Don't record space bar releases
                if key_str == ' ' or key_str == 'space':
                    return
                    
                if not self.video_player.is_paused:
                    # Record using OpenCV's ground truth frame number
                    current_frame = self.video_player.get_displayed_frame_number()
                    self.input_recorder.record_frame_based_keystroke(current_frame, key_str, 'release')
            except:
                pass
                
        self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keyboard_listener.start()
        
    def _stop_recording_listener(self):
        """Stop recording keyboard listener"""
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            
    def _mouse_callback_recording(self, event, x, y, flags, param):
        """Mouse callback for ROI selection in recording mode"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.visual_trigger.start_selection(x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            self.visual_trigger.update_selection(x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.visual_trigger.finish_selection()
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.visual_trigger.cancel_selection()
        
    def manage_trigger_library(self):
        """Manage the visual trigger library"""
        while True:
            print("\n" + "=" * 50)
            print("TRIGGER LIBRARY MANAGEMENT")
            print("=" * 50)
            triggers = self.trigger_library.list_triggers()
            
            if not triggers:
                print("\nNo triggers in library yet.")
            else:
                print(f"\nTotal triggers: {len(triggers)}\n")
                for i, trigger in enumerate(triggers, 1):
                    print(f"{i}. {trigger['spell_name']} (Key: {trigger['key']}, "
                          f"Pause: {trigger['pause_before_seconds']}s)")
                    print(f"   ID: {trigger['id']}")
                    print(f"   Created: {trigger.get('created_at', 'Unknown')}\n")
            
            print("Options:")
            print("1 - Delete a trigger")
            print("2 - Update trigger details")
            print("3 - Back to main menu")
            
            choice = input("\nEnter choice: ").strip()
            
            if choice == '1' and triggers:
                # Delete trigger
                idx = input("Enter trigger number to delete: ").strip()
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(triggers):
                        trigger_id = triggers[idx]['id']
                        confirm = input(f"Delete '{triggers[idx]['spell_name']}'? (y/n): ").strip().lower()
                        if confirm == 'y':
                            self.trigger_library.delete_trigger(trigger_id)
                            print("Trigger deleted.")
                except:
                    print("Invalid input.")
                    
            elif choice == '2' and triggers:
                # Update trigger
                idx = input("Enter trigger number to update: ").strip()
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(triggers):
                        trigger = triggers[idx]
                        print(f"\nUpdating: {trigger['spell_name']}")
                        
                        spell_name = input(f"Spell name [{trigger['spell_name']}]: ").strip()
                        key = input(f"Key [{trigger['key']}]: ").strip()
                        pause = input(f"Pause before (s) [{trigger['pause_before_seconds']}]: ").strip()
                        
                        updates = {}
                        if spell_name:
                            updates['spell_name'] = spell_name
                        if key:
                            updates['key'] = key
                        if pause:
                            try:
                                updates['pause_before_seconds'] = float(pause)
                            except:
                                pass
                        
                        if updates:
                            self.trigger_library.update_trigger(trigger['id'], **updates)
                            print("Trigger updated.")
                except:
                    print("Invalid input.")
                    
            elif choice == '3':
                break
    
    def run(self):
        """Main application loop"""
        print("=" * 50)
        print("DOJO - Gaming Training Application")
        print("=" * 50)
        
        # Select stage
        self.stage = self._select_stage()
        
        if self.stage == 1:
            self.run_stage1_recording()
        elif self.stage == 2:
            self.run_stage2_practice()
        elif self.stage == 3:
            self.manage_trigger_library()
            
    def run_stage1_recording(self):
        """Run Stage 1 - Keystroke recording mode"""
        print("\n" + "=" * 50)
        print("STAGE 1 - Keystroke Recording")
        print("=" * 50)
        
        # Get YouTube URL from user
        self.video_url = input("\nEnter YouTube URL: ").strip()
        
        if not self.video_url:
            print("Error: No URL provided")
            return
            
        try:
            # Download and load video
            print("\nPreparing video...")
            video_path = self.video_player.download_video(self.video_url)
            
            if not self.video_player.load_video(video_path):
                print("Error: Failed to load video")
                return
                
            print("\nControls:")
            print("  SPACE - Play/Pause")
            print("  ESC   - Stop and save recording")
            print("  Click & Drag - Select ROI for visual triggers")
            print("  C     - Clear ROI")
            print("\nReady to record. Press SPACE to start.")
            
            # Set mouse callback for ROI selection
            cv2.setMouseCallback('Dojo - Training Mode', self._mouse_callback_recording)
            
            # Set escape callback
            self.input_recorder.set_escape_callback(self.handle_escape)
            
            # Setup frame-based keyboard listener for recording
            self._start_recording_listener()
            
            # Video starts paused, don't record until user presses play
            self.video_player.is_playing = True  # Enable frame rendering
            self.video_player.is_paused = True   # But start paused
            self.video_player.start_time = time.time()
            
            self.running = True
            recording_started = False
            was_paused = True
            visual_trigger_mode = False  # Whether we're waiting for key input after trigger
            
            # Main loop
            while self.running:
                # Get and display next frame
                ret, frame = self.video_player.get_frame()
                
                if ret and frame is not None:
                    # Use OpenCV's actual frame position as ground truth
                    displayed_frame = self.video_player.get_displayed_frame_number()
                    current_time = displayed_frame / self.video_player.fps
                    
                    # Check for visual trigger if ROI is set and recording
                    if recording_started and not self.video_player.is_paused and self.visual_trigger.has_roi():
                        if self.visual_trigger.detect_change(frame):
                            # Visual change detected - check library first
                            self.video_player.pause()
                            self.pending_trigger_frame = displayed_frame
                            
                            # Check if this matches a known trigger in the library
                            matched_trigger = self.trigger_library.find_matching_trigger(
                                frame, self.visual_trigger.roi, threshold=0.75
                            )
                            
                            if matched_trigger:
                                # Found a match! Use the saved key automatically
                                key_char = matched_trigger['key']
                                spell_name = matched_trigger['spell_name']
                                print(f"\n>>> Visual trigger matched: '{spell_name}' (Key: {key_char}, Match: {matched_trigger['match_score']:.2f})")
                                print(f">>> Auto-recording '{key_char}' for frame {displayed_frame}")
                                self.input_recorder.record_frame_based_keystroke(displayed_frame, key_char, 'press')
                                self.pending_trigger_frame = None
                                self.video_player.play()
                            else:
                                # Unknown trigger - ask user for key
                                visual_trigger_mode = True
                                print(f"\n>>> NEW visual trigger at frame {displayed_frame}! Enter key to associate (or ESC to skip): ", end='', flush=True)
                    
                    # Display frame info
                    frame_copy = frame.copy()
                    
                    # Draw ROI if set
                    self.visual_trigger.draw_roi(frame_copy)
                    
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    time_text = f"Time: {current_time:.2f}s | Frame: {displayed_frame}"
                    cv2.putText(frame_copy, time_text, (10, frame.shape[0] - 20), 
                               font, 0.7, (255, 255, 255), 2)
                    
                    if visual_trigger_mode:
                        status = "WAITING FOR KEY"
                        color = (0, 255, 255)  # Yellow
                    elif recording_started:
                        status = "RECORDING"
                        color = (0, 0, 255)  # Red
                    else:
                        status = "PAUSED"
                        color = (0, 255, 255)  # Cyan
                        
                    cv2.putText(frame_copy, status, (10, 30), 
                               font, 0.7, color, 2)
                    
                    if self.visual_trigger.has_roi():
                        cv2.putText(frame_copy, "ROI Active", (10, 60), 
                                   font, 0.6, (0, 255, 0), 2)
                    
                    cv2.imshow('Dojo - Training Mode', frame_copy)
                    
                # Handle keyboard input for video control
                # Use minimal delay - frame timing is handled by video player's elapsed time calculation
                delay = 1  # 1ms delay for responsive input
                key = cv2.waitKey(delay) & 0xFF
                
                # Handle visual trigger key input
                if visual_trigger_mode and key != 255:
                    if key == 27:  # ESC - skip this trigger
                        print("Skipped")
                        visual_trigger_mode = False
                        self.pending_trigger_frame = None
                        self.video_player.play()
                    else:
                        # Record the key for this frame
                        key_char = chr(key) if 32 <= key <= 126 else f"key_{key}"
                        self.input_recorder.record_frame_based_keystroke(self.pending_trigger_frame, key_char, 'press')
                        print(f"'{key_char}' recorded for frame {self.pending_trigger_frame}")
                        
                        # Ask if user wants to save this as a library trigger
                        print("\nSave this visual trigger to library? (y/n): ", end='', flush=True)
                        save_choice = input().strip().lower()
                        
                        if save_choice == 'y':
                            # Get spell name
                            spell_name = input("Enter spell/ability name: ").strip()
                            pause_before = input("Pause before (seconds, default 1.0): ").strip()
                            try:
                                pause_before = float(pause_before) if pause_before else 1.0
                            except:
                                pause_before = 1.0
                            
                            # Extract ROI image from current frame
                            x, y, w, h = self.visual_trigger.roi
                            roi_image = frame[y:y+h, x:x+w].copy()
                            
                            # Save to library
                            trigger_id = self.trigger_library.add_trigger(
                                roi_image, self.visual_trigger.roi, 
                                key_char, spell_name, pause_before
                            )
                            print(f"Trigger saved! ID: {trigger_id}\n")
                        
                        visual_trigger_mode = False
                        self.pending_trigger_frame = None
                        self.video_player.play()
                    continue
                
                if key == ord(' '):
                    # Space bar - toggle pause
                    was_paused = self.video_player.is_paused
                    self.video_player.toggle_pause()
                    
                    # Start recording when video transitions from paused to playing
                    if was_paused and not self.video_player.is_paused and not recording_started:
                        recording_started = True
                        print("Recording started at frame", self.video_player.get_displayed_frame_number())
                    
                elif key == ord('c') or key == ord('C'):
                    # Clear ROI
                    self.visual_trigger.clear_roi()
                    
                elif key == 27:  # ESC key
                    break
                    
                # Check if video ended
                if not self.video_player.is_playing:
                    print("\nVideo ended")
                    break
                    
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Cleanup
            print("\nCleaning up...")
            self._stop_recording_listener()
            self.input_recorder.stop()
            self.video_player.cleanup()
            
            # Save recording
            self.save_recording()
            
        print("\nDojo session complete!")


def main():
    """Entry point for Dojo application"""
    app = DojoApp()
    app.run()


if __name__ == "__main__":
    main()
