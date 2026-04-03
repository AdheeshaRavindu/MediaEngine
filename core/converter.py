from core.utils import build_output_path, detect_file_type
from engines import ffmpeg_wrapper, imagemagick_wrapper


IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "pdf"}
VIDEO_FORMATS = {"mp4", "mkv", "avi", "mov", "webm"}
AUDIO_FORMATS = {"mp3", "wav", "aac", "flac", "ogg", "m4a"}


def _normalize_ext(fmt: str | None) -> str | None:
    if not fmt:
        return None
    value = fmt.strip().lower()
    if value.startswith("."):
        value = value[1:]
    return value or None


def run_convert(input_path: str, output_dir: str, output_format: str | None = None) -> str:
    file_type = detect_file_type(input_path)
    target_ext = _normalize_ext(output_format)

    if file_type in {"video", "audio"}:
        if target_ext is None:
            target_ext = "mp4" if file_type == "video" else "mp3"
        if target_ext not in VIDEO_FORMATS and target_ext not in AUDIO_FORMATS:
            raise ValueError(f"Unsupported media output format: {target_ext}")
        output_path = build_output_path(input_path, output_dir, "_converted", f".{target_ext}")
        ffmpeg_wrapper.transcode_media(input_path, output_path)
        return output_path

    if file_type in {"image", "pdf"}:
        if target_ext is None:
            target_ext = "jpg" if file_type == "image" else "pdf"
        if target_ext not in IMAGE_FORMATS:
            raise ValueError(f"Unsupported image/pdf output format: {target_ext}")
        output_path = build_output_path(input_path, output_dir, "_converted", f".{target_ext}")
        imagemagick_wrapper.convert_image(input_path, output_path)
        return output_path

    raise ValueError("Unsupported file type for convert")
