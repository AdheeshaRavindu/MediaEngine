import os
import shutil
import sys
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}


def detect_file_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    if ext == ".pdf":
        return "pdf"
    return "unknown"


def get_tool_path(tool_name: str) -> str:
    # 1) bundled in PyInstaller temp folder
    base = getattr(sys, "_MEIPASS", None)
    if base:
        exe_name = tool_name + (".exe" if os.name == "nt" else "")
        candidate = os.path.join(base, exe_name)
        if os.path.exists(candidate):
            return candidate

    # 2) local tools folder in project
    exe_name = tool_name + (".exe" if os.name == "nt" else "")
    local_candidate = Path(__file__).resolve().parents[1] / "tools" / exe_name
    if local_candidate.exists():
        return str(local_candidate)

    # 3) system PATH
    found = shutil.which(tool_name)
    if found:
        return found

    return tool_name


def build_output_path(input_path: str, output_dir: str, suffix: str, new_ext: str | None = None) -> str:
    src = Path(input_path)
    ext = new_ext if new_ext else src.suffix
    return str(Path(output_dir) / f"{src.stem}{suffix}{ext}")
