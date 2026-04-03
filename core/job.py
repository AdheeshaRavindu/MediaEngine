from dataclasses import dataclass


@dataclass
class Job:
    input_path: str
    action: str
    output_dir: str
    output_format: str | None = None
    metadata_mode: str | None = None
    optimize_mode: str | None = None
    image_quality: int = 80
    video_preset: str = "balanced"
    resize_width: int = 1280
    resize_height: int = 720
    enhance_mode: str | None = None
    enhance_strength: int = 50
    upscale_factor: int = 2
