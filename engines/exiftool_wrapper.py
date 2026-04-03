import subprocess

from core.utils import get_tool_path


def read_metadata(input_path: str) -> str:
    cmd = [get_tool_path("exiftool"), input_path]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return (result.stdout or "").strip()


def strip_metadata(input_path: str, output_path: str) -> None:
    # Keep original file untouched and write a cleaned copy.
    cmd = [get_tool_path("exiftool"), "-all=", "-o", output_path, input_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
