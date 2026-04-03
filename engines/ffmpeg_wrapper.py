import subprocess

from core.utils import get_tool_path


def convert_video(input_path: str, output_path: str) -> None:
    cmd = [get_tool_path("ffmpeg"), "-y", "-i", input_path, "-c:v", "libx264", "-c:a", "aac", output_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def extract_mp3(input_path: str, output_path: str) -> None:
    cmd = [get_tool_path("ffmpeg"), "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame", output_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def compress_video(input_path: str, output_path: str, crf: int = 30) -> None:
    cmd = [
        get_tool_path("ffmpeg"),
        "-y",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def compress_video_with_preset(input_path: str, output_path: str, preset_key: str = "balanced") -> None:
    preset_map = {
        "high_quality": {"preset": "slow", "crf": 22, "audio_bitrate": "192k"},
        "balanced": {"preset": "medium", "crf": 28, "audio_bitrate": "128k"},
        "small_size": {"preset": "fast", "crf": 32, "audio_bitrate": "96k"},
    }
    config = preset_map.get(preset_key, preset_map["balanced"])
    cmd = [
        get_tool_path("ffmpeg"),
        "-y",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-preset",
        config["preset"],
        "-crf",
        str(config["crf"]),
        "-c:a",
        "aac",
        "-b:a",
        config["audio_bitrate"],
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def resize_video(input_path: str, output_path: str, width: int, height: int) -> None:
    scale = f"scale={width}:{height}:force_original_aspect_ratio=decrease"
    cmd = [
        get_tool_path("ffmpeg"),
        "-y",
        "-i",
        input_path,
        "-vf",
        scale,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "26",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def transcode_media(input_path: str, output_path: str) -> None:
    """Generic FFmpeg transcode based on output extension/container."""
    cmd = [get_tool_path("ffmpeg"), "-y", "-i", input_path, output_path]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def normalize_audio(input_path: str, output_path: str) -> None:
    cmd = [
        get_tool_path("ffmpeg"),
        "-y",
        "-i",
        input_path,
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
