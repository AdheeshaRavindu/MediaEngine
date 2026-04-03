import subprocess

from core.utils import get_tool_path


def convert_image(input_path: str, output_path: str) -> None:
    cmd = [get_tool_path("magick"), input_path, output_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def compress_image(input_path: str, output_path: str, quality: int = 80) -> None:
    cmd = [get_tool_path("magick"), input_path, "-quality", str(quality), output_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def reduce_pdf_size(input_path: str, output_path: str, quality: int = 70) -> None:
    # PDF optimization via ImageMagick re-encode settings.
    cmd = [
        get_tool_path("magick"),
        input_path,
        "-density",
        "120",
        "-quality",
        str(quality),
        "-compress",
        "zip",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def resize_image(input_path: str, output_path: str, width: int, height: int) -> None:
    cmd = [
        get_tool_path("magick"),
        input_path,
        "-resize",
        f"{width}x{height}>",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def enhance_image(input_path: str, output_path: str) -> None:
    # Basic enhancement pipeline for MVP: auto-level + mild sharpening.
    cmd = [
        get_tool_path("magick"),
        input_path,
        "-auto-level",
        "-unsharp",
        "0x1",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
