"""
Video Player Module
Handles YouTube video downloading and playback using OpenCV and yt-dlp
Uses threaded frame buffering for smooth playback
"""

import cv2
import os
import yt_dlp
import time
import threading
from typing import Optional, Tuple
from queue import Queue, Empty
from collections import deque


class VideoPlayer:
    """YouTube video player with playback controls"""
    
    def __init__(self, cache_dir: str = "./data/cache"):
        """
        Initialize video player with threaded frame buffer
        
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
        self.pause_time = 0.0
        self.total_paused_time = 0.0
        
        # Threaded frame buffer
        self.frame_buffer = {}  # {frame_num: frame_data}
        self.buffer_lock = threading.Lock()
        self.decode_thread = None
        self.stop_decoding = threading.Event()
        self.seek_requested = threading.Event()
        self.target_frame = 0
        self.buffer_size = 90  # Buffer 3 seconds @ 30fps ahead
        
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
        
        # Start frame decode thread
        self._start_decode_thread()
        
        # Set up fullscreen window
        cv2.namedWindow('Dojo - Training Mode', cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty('Dojo - Training Mode', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        print(f"Video loaded: {self.total_frames} frames, {self.fps} fps, {self.duration:.2f}s")
        return True
        
    def _start_decode_thread(self):
        """Start background thread for frame decoding"""
        self.stop_decoding.clear()
        self.seek_requested.clear()
        self.decode_thread = threading.Thread(target=self._decode_frames, daemon=True)
        self.decode_thread.start()
        
    def _decode_frames(self):
        """Background thread that decodes frames ahead of playback"""
        decode_cap = cv2.VideoCapture(self.video_path)
        
        while not self.stop_decoding.is_set():
            # Check if seek was requested
            if self.seek_requested.is_set():
                with self.buffer_lock:
                    # Clear buffer and seek
                    self.frame_buffer.clear()
                    target = self.target_frame
                self.seek_requested.clear()
                decode_cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                
            # If paused or buffer is full enough, wait a bit
            with self.buffer_lock:
                buffer_keys = list(self.frame_buffer.keys())
                current = self.current_frame
                
            if self.is_paused:
                time.sleep(0.01)
                continue
                
            # Check if we have enough frames buffered ahead
            if buffer_keys and max(buffer_keys) >= current + self.buffer_size:
                time.sleep(0.005)
                continue
                
            # Decode next frame
            ret, frame = decode_cap.read()
            if not ret:
                # End of video or error
                time.sleep(0.1)
                continue
                
            frame_num = int(decode_cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            
            # Add to buffer
            with self.buffer_lock:
                self.frame_buffer[frame_num] = frame.copy()
                
                # Cleanup old frames (keep a small window behind)
                frames_to_remove = [f for f in self.frame_buffer.keys() if f < current - 30]
                for f in frames_to_remove:
                    del self.frame_buffer[f]
                    
        decode_cap.release()
        
    def _request_seek(self, frame_num: int):
        """Request the decode thread to seek to a specific frame"""
        self.target_frame = frame_num
        self.seek_requested.set()
        
    def play(self):
        """Start or resume video playback"""
        if not self.cap or not self.cap.isOpened():
            print("Error: No video loaded")
            return
            
        self.is_playing = True
        was_paused = self.is_paused
        self.is_paused = False
        
        if was_paused and self.pause_time > 0:
            # Resuming from pause - add paused duration to total
            self.total_paused_time += time.time() - self.pause_time
            self.pause_time = 0.0
        else:
            # Starting fresh
            self.start_time = time.time()
            self.total_paused_time = 0.0
            
        print("Playing...")
        
    def pause(self):
        """Pause video playback"""
        self.is_paused = True
        self.pause_time = time.time()
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
        
    def get_displayed_frame_number(self) -> int:
        """
        Get the frame number that was just displayed
        
        Returns:
            The frame number of the most recently displayed frame
        """
        # current_frame is the NEXT frame to read, so subtract 1 for displayed frame
        return max(0, self.current_frame - 1)
        """Get current playback time in seconds based on frame position"""
        if not self.cap:
            return 0.0
        
        # Always use frame-based time to stay in sync with actual frames being displayed
        return self.current_frame / self.fps
        
    def get_frame(self) -> Tuple[bool, Optional[any]]:
        """
        Get frame for display from buffer based on elapsed time
        
        Returns:
            Tuple of (success, frame) where frame is the one that should be displayed now
        """
        if not self.cap or not self.is_playing:
            return False, None
            
        # If paused, return current frame from buffer
        if self.is_paused:
            with self.buffer_lock:
                if self.current_frame in self.frame_buffer:
                    return True, self.frame_buffer[self.current_frame].copy()
                # Frame not in buffer, request it
                self._request_seek(self.current_frame)
            time.sleep(0.01)  # Wait for buffer to populate
            return False, None
        
        # Calculate which frame should be displayed based on elapsed time
        elapsed_time = time.time() - self.start_time - self.total_paused_time
        target_frame = int(elapsed_time * self.fps)
        
        # Clamp to valid range
        target_frame = max(0, min(target_frame, self.total_frames - 1))
        
        # Check if video ended
        if target_frame >= self.total_frames - 1:
            self.stop()
            return False, None
        
        # Try to get frame from buffer
        with self.buffer_lock:
            if target_frame in self.frame_buffer:
                frame = self.frame_buffer[target_frame].copy()
                self.current_frame = target_frame + 1
                return True, frame
            
            # Frame not ready yet - check if we're behind or ahead
            available_frames = sorted(self.frame_buffer.keys())
            
            if not available_frames:
                # Buffer empty, request seek
                self._request_seek(target_frame)
                return False, None
                
            # Use closest available frame
            closest = min(available_frames, key=lambda x: abs(x - target_frame))
            frame = self.frame_buffer[closest].copy()
            self.current_frame = closest + 1
            
            # If we're significantly off, request seek
            if abs(closest - target_frame) > 5:
                self._request_seek(target_frame)
                
            return True, frame
        
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
        # Stop decode thread
        self.stop_decoding.set()
        if self.decode_thread and self.decode_thread.is_alive():
            self.decode_thread.join(timeout=1.0)
            
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
