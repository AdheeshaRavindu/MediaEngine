from pathlib import Path

from core.utils import is_python_module_available, sanitize_filename, unique_path


def download_media(
    url: str,
    output_dir: str,
    download_kind: str = "Video",
    download_format: str = "mp4",
    download_quality: str = "Best",
    progress_callback=None,
) -> str:
    if not is_python_module_available("yt_dlp"):
        raise RuntimeError(
            "yt-dlp is not installed for the Python interpreter running this app. "
            "Run: py -m pip install -r requirements.txt"
        )

    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "yt-dlp is not installed for the Python interpreter running this app. "
            "Run: py -m pip install -r requirements.txt"
        ) from exc

    output_template = str(Path(output_dir) / "%(title)s.%(ext)s")
    downloaded_path = None

    def progress_hook(status: dict[str, object]) -> None:
        nonlocal downloaded_path
        if status.get("status") == "finished":
            filename = status.get("filename")
            if isinstance(filename, str) and filename:
                downloaded_path = filename
            if progress_callback:
                progress_callback(f"Download finished: {Path(str(filename)).name if filename else url}")
        elif status.get("status") == "downloading" and progress_callback:
            percent = status.get("_percent_str")
            current = status.get("_downloaded_bytes_str")
            total = status.get("_total_bytes_str") or status.get("_total_bytes_estimate_str")
            name = Path(str(status.get("filename") or url)).name
            pieces = [f"Downloading {name}"]
            if isinstance(percent, str) and percent.strip():
                pieces.append(percent.strip())
            if isinstance(current, str) and isinstance(total, str) and current.strip() and total.strip():
                pieces.append(f"{current.strip()} / {total.strip()}")
            progress_callback(" - ".join(pieces))

    ydl_options: dict[str, object] = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "progress_hooks": [progress_hook],
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
        if downloaded_path:
            return downloaded_path

        title = info.get("title") if isinstance(info, dict) else None
        safe_title = sanitize_filename(title) if isinstance(title, str) and title.strip() else "download"
        ext = download_format.lstrip(".")
        fallback_path = unique_path(str(Path(output_dir) / f"{safe_title}.{ext}"))
        return fallback_path