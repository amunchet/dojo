# Dojo - Gaming Training Application

## Project Overview
Dojo is a Python-based training application designed to help gamers practice and improve their mechanical skills, particularly for World of Warcraft boss encounters.

## Stage Development Plan

### Stage 1: Video Playback & Keystroke Recording (CURRENT)
**Features:**
- Play YouTube video in the background (typically WoW boss kill videos)
- Record user keystrokes during video playback
- Synchronize keystroke timestamps with video timeline
- Save recorded keystroke data for later analysis

**Technical Requirements:**
- YouTube video downloading/streaming
- Video playback with controls (play, pause, seek)
- Keyboard event capture
- Timestamp synchronization
- Data persistence (JSON format for recorded keystrokes)

### Stage 2: Ideal Pattern Display (OSU/DDR Style)
**Features:**
- Load pre-defined "ideal" keystroke patterns
- Display visual indicators for keystrokes/mouse clicks at specific timestamps
- Provide feedback on user accuracy vs ideal pattern
- Score system based on timing accuracy
- Visual cues similar to rhythm games (OSU, DDR)

**Technical Requirements:**
- Pattern file format (JSON with timestamps and actions)
- Visual overlay system
- Timing accuracy calculation
- Scoring algorithm
- Hit/miss feedback visualization

### Stage 3: Minimap Analysis & Mouse Rotation
**Features:**
- Capture and analyze minimap region from video
- Calculate required mouse rotations/camera movements
- Display directional cues for camera positioning
- Advanced pattern learning from video analysis

**Technical Requirements:**
- Video frame capture and region detection
- Image processing for minimap analysis
- Orientation/rotation calculation algorithms
- Computer vision for pattern recognition
- Machine learning for automatic pattern extraction (optional)

## Technology Stack
- **Python 3.8+**
- **Video:** opencv-cv, yt-dlp
- **Input Capture:** pynput
- **GUI:** pygame or tkinter
- **Data:** JSON for storage
- **Computer Vision (Stage 3):** OpenCV, NumPy

## File Structure
```
dojo/
├── PROJECT_SPEC.md          # This file
├── README.md                # Installation and usage guide
├── requirements.txt         # Python dependencies
├── dojo.py                  # Main application entry point
├── video_player.py          # Video playback functionality
├── input_recorder.py        # Keystroke/mouse recording
├── pattern_manager.py       # Pattern loading and management (Stage 2)
├── minimap_analyzer.py      # Minimap processing (Stage 3)
└── data/                    # Storage for recordings and patterns
    ├── recordings/          # User keystroke recordings
    └── patterns/            # Ideal pattern definitions
```

## Current Status
- **Stage 1:** In Development
- **Stage 2:** Planned
- **Stage 3:** Planned
