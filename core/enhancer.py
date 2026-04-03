from core.utils import build_output_path, detect_file_type
from engines import imagemagick_wrapper


def run_enhance(input_path: str, output_dir: str) -> str:
    file_type = detect_file_type(input_path)
    if file_type != "image":
        raise ValueError("Enhance currently supports image files only")

    output_path = build_output_path(input_path, output_dir, "_enhanced", ".jpg")
    imagemagick_wrapper.enhance_image(input_path, output_path)
    return output_path
