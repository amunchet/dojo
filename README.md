# Dojo - Gaming Training Application

Train your mechanical skills for World of Warcraft boss encounters using video playback and keystroke recording.

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### macOS Setup
- **ffmpeg**: Required for downloading YouTube videos. Install via Homebrew:
  ```bash
  brew install ffmpeg
  ```
- **Keyboard Input Permission**: On first run, macOS will require you to grant accessibility permission for keyboard event monitoring:
  1. Go to **System Settings** → **Privacy & Security** → **Accessibility**
  2. Click the **+** button and select **Terminal** (or your code editor)
  3. Close and reopen Terminal/Editor
  4. Run `python dojo.py` again

## Usage (Stage 1)

Run the application:
```bash
python dojo.py
```

### Controls
- **Space**: Play/Pause video
- **ESC**: Stop recording and exit
- **R**: Reset and restart

### Recording Session
1. Enter YouTube URL when prompted
2. Video will load and begin playing
3. Your keystrokes are automatically recorded with timestamps
4. Recording saves to `data/recordings/` when you exit

## Recorded Data Format

Recordings are saved as JSON files with the following structure:
```json
{
    "video_url": "https://youtube.com/watch?v=...",
    "duration": 300.5,
    "recording_date": "2026-01-14T10:30:00",
    "keystrokes": [
        {"time": 1.234, "key": "1", "action": "press"},
        {"time": 1.456, "key": "1", "action": "release"},
        ...
    ]
}
```

## Requirements
- Python 3.8+
- Internet connection (for YouTube video download)
- Sufficient disk space for video caching

## Roadmap
- [x] Stage 1: Video playback and keystroke recording
- [ ] Stage 2: Ideal pattern display (OSU/DDR style)
- [ ] Stage 3: Minimap analysis and mouse rotation detection
