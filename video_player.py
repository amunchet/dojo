"""
Video Player Module
Handles YouTube video downloading and playback using OpenCV and yt-dlp
"""

import cv2
import os
import yt_dlp
import time
import threading
from typing import Optional, Tuple


class VideoPlayer:
    """YouTube video player with playback controls"""
    
    def __init__(self, cache_dir: str = "./data/cache"):
        """
        Initialize video player
        
        Args:
            cache_dir: Directory to cache downloaded videos
        """
        self.cache_dir = cache_dir
        self.video_path: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_playing = False
        self.is_paused = False
        self.current_frame = 0
        self.fps = 30
        self.total_frames = 0
        self.duration = 0.0
        self.start_time = 0.0
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
    def download_video(self, url: str) -> str:
        """
        Download YouTube video to cache
        
        Args:
            url: YouTube video URL
            
        Returns:
            Path to downloaded video file
        """
        print(f"Downloading video from: {url}")
        
        # Generate output filename
        output_template = os.path.join(self.cache_dir, '%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'merge_output_format': 'mp4',
            'postprocessor_args': ['-c', 'copy'],  # Fast copy without re-encoding
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            ext = info['ext']
            video_path = os.path.join(self.cache_dir, f"{video_id}.{ext}")
            
            # Print quality info
            if 'format' in info:
                print(f"Downloaded format: {info['format']}")
            if 'resolution' in info:
                print(f"Resolution: {info['resolution']}")
            if 'height' in info:
                print(f"Height: {info['height']}p")
            
        print(f"Video downloaded to: {video_path}")
        return video_path
        
    def load_video(self, video_path: str) -> bool:
        """
        Load video file for playback
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if video loaded successfully
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            print(f"Error: Could not open video file: {video_path}")
            return False
            
        # Get video properties
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps
        
        # Reset frame counter
        self.current_frame = 0
        
        # Set up fullscreen window
        cv2.namedWindow('Dojo - Training Mode', cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty('Dojo - Training Mode', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        print(f"Video loaded: {self.total_frames} frames, {self.fps} fps, {self.duration:.2f}s")
        return True
        
    def play(self):
        """Start or resume video playback"""
        if not self.cap or not self.cap.isOpened():
            print("Error: No video loaded")
            return
            
        self.is_playing = True
        self.is_paused = False
        self.start_time = time.time() - (self.current_frame / self.fps)
        print("Playing...")
        
    def pause(self):
        """Pause video playback"""
        self.is_paused = True
        print("Paused")
        
    def toggle_pause(self):
        """Toggle between play and pause"""
        if self.is_paused:
            self.play()
        else:
            self.pause()
            
    def stop(self):
        """Stop video playback"""
        self.is_playing = False
        self.is_paused = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("Stopped")
        
    def get_current_time(self) -> float:
        """Get current playback time in seconds based on frame position"""
        if not self.cap:
            return 0.0
        
        # Always use frame-based time to stay in sync with actual frames being displayed
        return self.current_frame / self.fps
        
    def get_frame(self) -> Tuple[bool, Optional[any]]:
        """
        Get next frame for display
        
        Returns:
            Tuple of (success, frame)
        """
        if not self.cap or not self.is_playing:
            return False, None
            
        # If paused, return current frame without advancing
        if self.is_paused:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            return ret, frame
            
        # Check if video ended
        if self.current_frame >= self.total_frames:
            self.stop()
            return False, None
            
        ret, frame = self.cap.read()
        if ret:
            self.current_frame += 1
            
        return ret, frame
        
    def display_frame(self, frame):
        """
        Display frame in window
        
        Args:
            frame: Frame to display
        """
        if frame is not None:
            # Add time overlay
            current_time = self.get_current_time()
            time_text = f"Time: {current_time:.2f}s / {self.duration:.2f}s"
            cv2.putText(frame, time_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add recording indicator
            status = "PAUSED" if self.is_paused else "RECORDING"
            color = (0, 255, 255) if self.is_paused else (0, 0, 255)
            cv2.putText(frame, status, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            cv2.imshow('Dojo - Training Mode', frame)
            
    def cleanup(self):
        """Clean up resources"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
