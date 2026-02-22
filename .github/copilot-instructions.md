# Copilot Instructions for Dojo

## Project summary
- Dojo is a Python training app with two active stages: Stage 1 records inputs while a YouTube video plays; Stage 2 replays a recorded pattern with a rhythm-style overlay. Entry point is [dojo.py](dojo.py).
- Video handling is centralized in `VideoPlayer` with a threaded frame buffer, OpenCV fullscreen window named “Dojo - Training Mode”, and cached downloads in data/cache via yt-dlp. See [video_player.py](video_player.py).
- Input recording uses frame-based timestamps during Stage 1 (not wall-clock time) to stay aligned with displayed frames; events are persisted as JSON in data/recordings. See [dojo.py](dojo.py) and [input_recorder.py](input_recorder.py).
- Stage 2 loads recordings as “patterns” and renders notes based on frame numbers; scoring and hit windows are frame-based. See [pattern_manager.py](pattern_manager.py) and [pattern_display.py](pattern_display.py).
- Optional visual triggers use an ROI selection on the video frame; when a change is detected, playback pauses and waits for a key mapping. See [visual_trigger.py](visual_trigger.py) and [dojo.py](dojo.py).

## Developer workflows
- Install deps: pip install -r requirements.txt (see [requirements.txt](requirements.txt)).
- Run app: python dojo.py (see [README.md](README.md)).
- Recordings are saved under data/recordings and reused as patterns in Stage 2 (see [pattern_manager.py](pattern_manager.py)).

## Project-specific conventions
- Prefer frame-based timing for anything user-input or scoring related; `VideoPlayer.get_displayed_frame_number()` is the ground truth used for alignment (see [video_player.py](video_player.py) and [dojo.py](dojo.py)).
- The OpenCV window name is hard-coded; if you add new windows, keep this one unchanged because mouse callbacks and fullscreen setup rely on it (see [video_player.py](video_player.py)).
- Pattern display expects notes as {frame, key} (or {time, key} but it is converted to ~30fps frames). Keep frame units consistent with recorded data (see [pattern_display.py](pattern_display.py)).
- Data layout is local (data/cache, data/recordings). Avoid introducing new storage locations without updating Stage 1/2 flows (see [dojo.py](dojo.py)).

## Integration points
- YouTube downloads are handled by yt-dlp; video decoding/playback uses OpenCV. Keep dependencies aligned with [requirements.txt](requirements.txt).
- Input capture uses pynput listeners for background key events; Stage 1 and Stage 2 use separate listeners with different semantics (see [dojo.py](dojo.py)).