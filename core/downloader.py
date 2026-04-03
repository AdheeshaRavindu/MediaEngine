from pathlib import Path


def download_media(
    url: str,
    output_dir: str,
    download_kind: str = "Video",
    download_format: str = "mp4",
    download_quality: str = "Best",
) -> str:
    from yt_dlp import YoutubeDL

    output_template = str(Path(output_dir) / "%(title)s.%(ext)s")

    ydl_options: dict[str, object] = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if download_kind == "Audio":
        ydl_options["format"] = "bestaudio/best"
        ydl_options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": download_format,
                "preferredquality": "192",
            }
        ]
        if download_quality and download_quality != "Best":
            ydl_options["postprocessors"][0]["preferredquality"] = download_quality.replace("k", "")
    else:
        quality_map = {
            "Best": "bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        }
        ydl_options["format"] = quality_map.get(download_quality, quality_map["Best"])
        ydl_options["merge_output_format"] = download_format

    with YoutubeDL(ydl_options) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title") if isinstance(info, dict) else None
        ext = download_format if download_kind == "Audio" else download_format
        if title:
            return str(Path(output_dir) / f"{title}.{ext}")
        return output_dir