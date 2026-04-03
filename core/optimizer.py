from core.utils import build_output_path, detect_file_type
from engines import ffmpeg_wrapper, imagemagick_wrapper


def run_optimize(
    input_path: str,
    output_dir: str,
    optimize_mode: str = "compress",
    image_quality: int = 80,
    video_preset: str = "balanced",
    resize_width: int = 1280,
    resize_height: int = 720,
) -> str:
    file_type = detect_file_type(input_path)

    if optimize_mode == "compress":
        if file_type == "video":
            output_path = build_output_path(input_path, output_dir, "_optimized", ".mp4")
            ffmpeg_wrapper.compress_video_with_preset(input_path, output_path, video_preset)
            return output_path
        if file_type == "image":
            output_path = build_output_path(input_path, output_dir, "_optimized", ".jpg")
            imagemagick_wrapper.compress_image(input_path, output_path, quality=image_quality)
            return output_path
        raise ValueError("Compress supports image/video files")

    if optimize_mode == "pdf_reduce":
        if file_type != "pdf":
            raise ValueError("Reduce PDF size supports PDF files only")
        output_path = build_output_path(input_path, output_dir, "_optimized", ".pdf")
        imagemagick_wrapper.reduce_pdf_size(input_path, output_path, quality=image_quality)
        return output_path

    if optimize_mode == "resize":
        if file_type == "image":
            output_path = build_output_path(input_path, output_dir, "_resized", ".jpg")
            imagemagick_wrapper.resize_image(input_path, output_path, resize_width, resize_height)
            return output_path
        if file_type == "video":
            output_path = build_output_path(input_path, output_dir, "_resized", ".mp4")
            ffmpeg_wrapper.resize_video(input_path, output_path, resize_width, resize_height)
            return output_path
        raise ValueError("Batch resize supports image/video files")

    raise ValueError(f"Unknown optimize mode: {optimize_mode}")


def run_compress(input_path: str, output_dir: str) -> str:
    # Backward-compatible shim
    return run_optimize(input_path, output_dir, optimize_mode="compress")
