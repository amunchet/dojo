"""
Video Player Module
Pre-decodes video into a fixed 24fps image sequence for deterministic playback
"""

import cv2
import os
import yt_dlp
import time
import json
import subprocess
from typing import Optional, Tuple


class VideoPlayer:
    """YouTube video player with deterministic image-sequence playback"""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = cache_dir
        self.frames_dir = os.path.join(cache_dir, "frames")
        self.video_path: Optional[str] = None
        self.frame_paths = []
        self.is_playing = False
        self.is_paused = False
        self.current_frame = 0
        self.fps = 24
        self.total_frames = 0
        self.duration = 0.0
        self.start_time = 0.0
        self.pause_time = 0.0
        self.total_paused_time = 0.0
        self.frame_width = 1280
        self.frame_height = 720

        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(self.frames_dir, exist_ok=True)

        self._last_frame_idx = None
        self._last_frame = None

    def download_video(self, url: str) -> str:
        print(f"Downloading video from: {url}")

        output_template = os.path.join(self.cache_dir, '%(id)s.%(ext)s')

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'merge_output_format': 'mp4',
            'postprocessor_args': ['-c', 'copy'],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            ext = info['ext']
            video_path = os.path.join(self.cache_dir, f"{video_id}.{ext}")

            if 'format' in info:
                print(f"Downloaded format: {info['format']}")
            if 'resolution' in info:
                print(f"Resolution: {info['resolution']}")
            if 'height' in info:
                print(f"Height: {info['height']}p")

        print(f"Video downloaded to: {video_path}")
        return video_path

    def _frame_cache_dir(self, video_path: str) -> str:
        base = os.path.splitext(os.path.basename(video_path))[0]
        return os.path.join(self.frames_dir, base)

    def _metadata_path(self, frame_dir: str) -> str:
        return os.path.join(frame_dir, "frames_meta.json")

    def _extract_frames(self, video_path: str, frame_dir: str) -> bool:
        os.makedirs(frame_dir, exist_ok=True)

        for f in os.listdir(frame_dir):
            if f.lower().endswith(".png"):
                os.remove(os.path.join(frame_dir, f))

        output_pattern = os.path.join(frame_dir, "frame_%06d.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vf", f"fps={self.fps}",
            "-q:v", "2",
            output_pattern,
        ]

        print("Decoding video to 24fps image sequence...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(result.stderr.decode("utf-8", errors="ignore"))
            return False

        return True

    def _load_frame_paths(self, frame_dir: str):
        self.frame_paths = sorted(
            [os.path.join(frame_dir, f) for f in os.listdir(frame_dir) if f.lower().endswith(".png")]
        )
        self.total_frames = len(self.frame_paths)
        self.duration = self.total_frames / self.fps if self.total_frames else 0.0

        if self.total_frames:
            first = cv2.imread(self.frame_paths[0])
            if first is not None:
                self.frame_height, self.frame_width = first.shape[:2]

    def _write_metadata(self, frame_dir: str):
        data = {
            "fps": self.fps,
            "total_frames": self.total_frames,
            "width": self.frame_width,
            "height": self.frame_height,
        }
        with open(self._metadata_path(frame_dir), "w") as f:
            json.dump(data, f, indent=2)

    def load_video(self, video_path: str) -> bool:
        self.video_path = video_path
        frame_dir = self._frame_cache_dir(video_path)

        if not os.path.exists(frame_dir) or not any(f.endswith(".png") for f in os.listdir(frame_dir)):
            if not self._extract_frames(video_path, frame_dir):
                print("Error: Failed to decode frames")
                return False

        self._load_frame_paths(frame_dir)
        if self.total_frames == 0:
            print("Error: No frames decoded")
            return False

        self._write_metadata(frame_dir)

        self.current_frame = 0
        self.start_time = 0.0
        self.total_paused_time = 0.0
        self.is_playing = False
        self.is_paused = False

        cv2.namedWindow('Dojo - Training Mode', cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty('Dojo - Training Mode', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        print(f"Video loaded: {self.total_frames} frames @ {self.fps} fps, {self.duration:.2f}s")
        return True

    def _load_frame(self, frame_idx: int):
        if self.total_frames == 0:
            return None
        frame_idx = max(0, min(frame_idx, self.total_frames - 1))
        if self._last_frame_idx == frame_idx and self._last_frame is not None:
            return self._last_frame.copy()

        path = self.frame_paths[frame_idx]
        frame = cv2.imread(path)
        if frame is None:
            return None

        self._last_frame_idx = frame_idx
        self._last_frame = frame
        return frame.copy()

    def play(self):
        self.is_playing = True
        was_paused = self.is_paused
        self.is_paused = False

        if was_paused and self.pause_time > 0:
            self.total_paused_time += time.time() - self.pause_time
            self.pause_time = 0.0
        else:
            self.start_time = time.time() - (self.current_frame / self.fps)
            self.total_paused_time = 0.0

        print("Playing...")

    def pause(self):
        self.is_paused = True
        self.pause_time = time.time()
        print("Paused")

    def toggle_pause(self):
        if self.is_paused:
            self.play()
        else:
            self.pause()

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        cv2.destroyAllWindows()
        print("Stopped")

    def get_displayed_frame_number(self) -> int:
        return max(0, self.current_frame)

    def get_current_time(self) -> float:
        if not self.total_frames:
            return 0.0
        return self.current_frame / self.fps

    def get_frame(self) -> Tuple[bool, Optional[any]]:
        if not self.is_playing:
            return False, None

        if self.is_paused:
            frame = self._load_frame(self.current_frame)
            return (frame is not None), frame

        elapsed_time = time.time() - self.start_time - self.total_paused_time
        target_frame = int(elapsed_time * self.fps)
        target_frame = max(0, min(target_frame, self.total_frames - 1))

        if target_frame >= self.total_frames - 1:
            self.stop()
            return False, None

        self.current_frame = target_frame
        frame = self._load_frame(target_frame)
        return (frame is not None), frame

    def cleanup(self):
        cv2.destroyAllWindows()
