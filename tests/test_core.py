import tempfile
from pathlib import Path
from unittest import TestCase, mock

from core.converter import run_convert
from core.downloader import download_media
from core.enhancer import run_enhance
from core.metadata import run_reveal_metadata
from core.optimizer import run_optimize
from core.utils import build_output_path, sanitize_filename


class CoreUtilityTests(TestCase):
    def test_sanitize_filename_replaces_invalid_characters(self):
        self.assertEqual(sanitize_filename('A<B>:C/"D\\E|F?*'), 'A_B_C_D_E_F_')

    def test_build_output_path_avoids_collisions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "sample.mp4"
            source.write_text("data", encoding="utf-8")
            first_output = Path(temp_dir) / "sample_converted.mp4"
            first_output.write_text("exists", encoding="utf-8")

            output_path = build_output_path(str(source), temp_dir, "_converted", ".mp4")

            self.assertEqual(Path(output_path).name, "sample_converted_1.mp4")


class CoreWorkflowTests(TestCase):
    @mock.patch("core.converter.ffmpeg_wrapper.transcode_media")
    @mock.patch("core.converter.detect_file_type", return_value="video")
    @mock.patch("core.converter.build_output_path", return_value="/tmp/output.mp4")
    def test_run_convert_routes_video_to_ffmpeg(self, build_path, detect_type, transcode_media):
        result = run_convert("input.mov", "/tmp", "mp4")

        self.assertEqual(result, "/tmp/output.mp4")
        transcode_media.assert_called_once_with("input.mov", "/tmp/output.mp4")

    @mock.patch("core.optimizer.imagemagick_wrapper.reduce_pdf_size")
    @mock.patch("core.optimizer.detect_file_type", return_value="image")
    def test_run_optimize_rejects_wrong_type_for_pdf_reduce(self, detect_type, reduce_pdf_size):
        with self.assertRaises(ValueError):
            run_optimize("input.jpg", "/tmp", optimize_mode="pdf_reduce")

        reduce_pdf_size.assert_not_called()

    @mock.patch("core.enhancer.ffmpeg_wrapper.normalize_audio")
    @mock.patch("core.enhancer.detect_file_type", return_value="audio")
    @mock.patch("core.enhancer.build_output_path", return_value="/tmp/output_normalized")
    def test_run_enhance_normalizes_audio(self, build_path, detect_type, normalize_audio):
        result = run_enhance("input.mp3", "/tmp", enhance_mode="Normalize Audio Volume")

        self.assertEqual(result, "/tmp/output_normalized")
        normalize_audio.assert_called_once_with("input.mp3", "/tmp/output_normalized")

    @mock.patch("core.metadata.exiftool_wrapper.read_metadata", return_value="Camera: Test")
    def test_run_reveal_metadata_writes_text_file(self, read_metadata):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "photo.jpg"
            source.write_text("data", encoding="utf-8")

            output_path = run_reveal_metadata(str(source), temp_dir)
            contents = Path(output_path).read_text(encoding="utf-8")

            self.assertEqual(contents, "Camera: Test")
            self.assertTrue(output_path.endswith("_metadata.txt"))

    @mock.patch("yt_dlp.YoutubeDL")
    def test_download_media_returns_final_download_path(self, youtube_dl_cls):
        class DummyYoutubeDL:
            def __init__(self, options):
                self.options = options

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, url, download=True):
                for hook in self.options["progress_hooks"]:
                    hook({"status": "finished", "filename": str(Path(self.options["outtmpl"]).parent / "sample.mp4")})
                return {"title": "Sample Title"}

        youtube_dl_cls.side_effect = DummyYoutubeDL

        with tempfile.TemporaryDirectory() as temp_dir:
            messages = []
            result = download_media(
                url="https://www.youtube.com/watch?v=123",
                output_dir=temp_dir,
                download_kind="Video",
                download_format="mp4",
                download_quality="Best",
                progress_callback=messages.append,
            )

            self.assertEqual(result, str(Path(temp_dir) / "sample.mp4"))
            self.assertTrue(messages)
            self.assertTrue(messages[-1].startswith("Download finished"))
