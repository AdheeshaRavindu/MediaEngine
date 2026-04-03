# MediaEngine

Phase-1 MVP desktop app using local offline engines.

## Stack
- Python
- PySide6
- FFmpeg
- ImageMagick
- ExifTool

## Features (MVP)
- Drag and drop files
- Detect file type (image/audio/video/pdf/unknown)
- Batch queue processing
- YouTube link downloads for video/audio
- Convert (image/audio/video)
- Compress (image/video)
- Strip metadata (via ExifTool)
- Choose output folder

## Install
```bash
pip install -r requirements.txt
```

Ensure external tools are available in `PATH`:
- `ffmpeg`
- `magick`
- `exiftool`
- `soffice` or `libreoffice` for Word document conversions

YouTube downloads use `yt-dlp` and ffmpeg.
The app now performs a startup health check for those dependencies and shows missing items in the UI.
Word/PDF/image round-trips use LibreOffice plus `python-docx`.

## Run
```bash
python app.py
```

The app remembers the last output folder, selected tab, and commonly used queue settings between launches.

Outputs are automatically collision-safe, so repeated runs will create unique filenames instead of overwriting existing exports.

## Project Layout
```
app.py
core/
engines/
ui/
tools/
```