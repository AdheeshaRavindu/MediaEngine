from core.utils import build_output_path
from engines import exiftool_wrapper


def run_reveal_metadata(input_path: str) -> str:
    output = exiftool_wrapper.read_metadata(input_path)
    return output if output else "No metadata found"


def run_strip_metadata(input_path: str, output_dir: str) -> str:
    output_path = build_output_path(input_path, output_dir, "_nometa")
    exiftool_wrapper.strip_metadata(input_path, output_path)
    return output_path
