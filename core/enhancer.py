from core.utils import build_output_path, detect_file_type
from engines import ffmpeg_wrapper, imagemagick_wrapper


def run_enhance(
    input_path: str,
    output_dir: str,
    enhance_mode: str = "Sharpen Image",
    enhance_strength: int = 50,
    upscale_factor: int = 2,
) -> str:
    file_type = detect_file_type(input_path)

    if enhance_mode == "Sharpen Image":
        if file_type != "image":
            raise ValueError("Sharpen supports image files only")
        output_path = build_output_path(input_path, output_dir, "_sharpened", ".jpg")
        imagemagick_wrapper.sharpen_image(input_path, output_path, enhance_strength)
        return output_path

    if enhance_mode == "Denoise Image":
        if file_type != "image":
            raise ValueError("Denoise supports image files only")
        output_path = build_output_path(input_path, output_dir, "_denoised", ".jpg")
        imagemagick_wrapper.denoise_image(input_path, output_path, enhance_strength)
        return output_path

    if enhance_mode == "Upscale Image":
        if file_type != "image":
            raise ValueError("Upscale supports image files only")
        output_path = build_output_path(input_path, output_dir, "_upscaled", ".jpg")
        imagemagick_wrapper.upscale_image(input_path, output_path, upscale_factor)
        return output_path

    if enhance_mode == "Normalize Audio Volume":
        if file_type not in {"audio", "video"}:
            raise ValueError("Normalize audio volume supports audio/video files")
        output_path = build_output_path(input_path, output_dir, "_normalized")
        ffmpeg_wrapper.normalize_audio(input_path, output_path)
        return output_path

    if enhance_mode == "Improve Video Resolution (Coming Soon)":
        raise NotImplementedError("Improve Video Resolution will be added in a later update")

    raise ValueError(f"Unknown enhance mode: {enhance_mode}")
