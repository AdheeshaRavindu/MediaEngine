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

## Run
```bash
python app.py
```

## Project Layout
```
app.py
core/
engines/
models/
ui/
tools/
```