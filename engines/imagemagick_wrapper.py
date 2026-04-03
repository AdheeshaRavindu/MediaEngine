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


def sharpen_image(input_path: str, output_path: str, strength: int = 50) -> None:
    radius = max(0.5, min(3.0, strength / 30.0))
    sigma = max(0.8, min(2.0, strength / 40.0))
    cmd = [
        get_tool_path("magick"),
        input_path,
        "-unsharp",
        f"0x{sigma}+{radius}+0",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def denoise_image(input_path: str, output_path: str, strength: int = 50) -> None:
    blur = max(0.5, min(2.5, strength / 40.0))
    cmd = [
        get_tool_path("magick"),
        input_path,
        "-noise",
        "1",
        "-blur",
        f"0x{blur}",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def upscale_image(input_path: str, output_path: str, factor: int = 2) -> None:
    factor = max(2, min(4, factor))
    cmd = [
        get_tool_path("magick"),
        input_path,
        "-filter",
        "Lanczos",
        "-resize",
        f"{factor * 100}%",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
