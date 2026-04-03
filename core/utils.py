import os
import importlib.util
import shutil
import sys
import re
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


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*]+", "_", name).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return "output"
    if cleaned.upper() in {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}:
        return f"_{cleaned}"
    return cleaned


def unique_path(path: str) -> str:
    candidate = Path(path)
    if not candidate.exists():
        return str(candidate)

    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent
    counter = 1

    while True:
        next_candidate = parent / f"{stem}_{counter}{suffix}"
        if not next_candidate.exists():
            return str(next_candidate)
        counter += 1


def is_tool_available(tool_name: str) -> bool:
    candidate = get_tool_path(tool_name)
    if candidate != tool_name and Path(candidate).exists():
        return True
    return shutil.which(tool_name) is not None


def is_python_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


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
    base_name = sanitize_filename(src.stem)
    return unique_path(str(Path(output_dir) / f"{base_name}{suffix}{ext}"))
