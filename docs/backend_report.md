# Backend Report

## `backend/__init__.py`
- **What it does:** Marks the backend package.
- **What works:** Imports cleanly.
- **What doesn't:** N/A.

## `backend/clips.py`
- **What it does:** Uses Selenium to scrape Twitch clip links for a streamer, downloads clip MP4s, and optionally overlays streamer name on the first clip.
- **What works:** Clip link discovery, download threads, overlay pipeline (when MoviePy/ffmpeg are available).
- **What doesn't / risks:**
  - Twitch page selectors are fragile and may break as the UI changes.
  - Requires Firefox + geckodriver; download/overlay depends on ffmpeg.
  - Download logic relies on thread start timing and may be flaky on slow networks.
  - Filename conventions are tightly coupled to `oneVideo.py`.

## `backend/oneVideo.py`
- **What it does:** Compiles clips in `currentVideos/` into a single montage and writes time stamps + streamer links.
- **What works:** Clip concatenation, timestamp generation, streamer link output for filenames that follow the expected pattern.
- **What doesn't / risks:**
  - Assumes filename format with digits + streamer name.
  - Hard-coded defaults for resolution and montage length.
  - Requires ffmpeg; corrupted clips can break compilation.

## `backend/overlay.py`
- **What it does:** Simple overlay helper to add text to a video.
- **What works:** Function-based overlay rendering.
- **What doesn't / risks:** No usage in main pipeline; depends on ffmpeg for output.

## `backend/transition.py`
- **What it does:** Generates a text-based transition clip.
- **What works:** Generates a simple transition to an output directory.
- **What doesn't / risks:** Not wired into the main flow; depends on ffmpeg.
