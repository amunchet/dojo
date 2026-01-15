"""
Dojo - Gaming Training Application
Stage 1: Video Playback and Keystroke Recording
"""

import os
import json
import cv2
import time
from datetime import datetime
from video_player import VideoPlayer
from input_recorder import InputRecorder


class DojoApp:
    """Main application class for Dojo training system"""
    
    def __init__(self):
        self.video_player = VideoPlayer()
        self.input_recorder = InputRecorder()
        self.running = False
        self.video_url = None
        
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
        
    def run(self):
        """Main application loop"""
        print("=" * 50)
        print("DOJO - Stage 1: Video Playback & Recording")
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
            print("\nStarting in 3 seconds...")
            time.sleep(3)
            
            # Start recording (video starts paused)
            self.input_recorder.set_escape_callback(self.handle_escape)
            self.input_recorder.start()
            self.video_player.is_playing = True  # Enable frame rendering
            self.video_player.is_paused = True   # But start paused
            self.video_player.start_time = time.time()
            
            self.running = True
            
            # Main loop
            while self.running:
                # Get and display next frame
                ret, frame = self.video_player.get_frame()
                
                if ret and frame is not None:
                    self.video_player.display_frame(frame)
                    
                # Handle keyboard input for video control
                # Wait time based on fps for proper playback speed
                delay = int(1000 / self.video_player.fps) if not self.video_player.is_paused else 1
                key = cv2.waitKey(delay) & 0xFF
                
                if key == ord(' '):
                    # Space bar - toggle pause
                    self.video_player.toggle_pause()
                    
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
