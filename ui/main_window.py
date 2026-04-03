import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QStringListModel
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QProgressBar,
    QLineEdit,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.converter import run_convert
from core.downloader import download_media
from core.enhancer import run_enhance
from core.metadata import run_reveal_metadata, run_strip_metadata
from core.optimizer import run_optimize
from core.queue_manager import QueueWorker
from core.utils import detect_file_type, is_python_module_available, is_tool_available
from core.job import Job


class MainWindow(QMainWindow):
    ACTIONS = [
        "Convert",
        "Download",
        "Optimize",
        "Enhance",
        "Metadata",
    ]

    IMAGE_FORMATS = ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "pdf"]
    AUDIO_FORMATS = ["mp3", "wav", "aac", "flac", "ogg", "m4a"]
    VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm"]
    OPTIMIZE_MODES = ["Compress", "Reduce PDF Size", "Batch Resize"]
    ENHANCE_MODES = [
        "Sharpen Image",
        "Denoise Image",
        "Upscale Image",
        "Normalize Audio Volume",
    ]
    VIDEO_PRESETS = [
        ("High Quality", "high_quality"),
        ("Balanced", "balanced"),
        ("Small Size", "small_size"),
    ]

    PRESETS = [
        "Custom",
        "WhatsApp",
        "Instagram",
        "YouTube",
        "Metadata-Free Export",
    ]

    PRESET_CONFIG = {
        "Custom": {"action": None, "format": None, "metadata_mode": None},
        "WhatsApp": {"action": "Convert", "format": "jpg", "metadata_mode": None},
        "Instagram": {"action": "Convert", "format": "jpg", "metadata_mode": None},
        "YouTube": {"action": "Convert", "format": "mp4", "metadata_mode": None},
        "Metadata-Free Export": {"action": "Metadata", "format": None, "metadata_mode": "Strip Metadata"},
    }

    TAB_INDEX = {
        "Convert": 0,
        "Download": 1,
        "Optimize": 2,
        "Enhance": 3,
        "Metadata": 4,
    }

    def __init__(self):
        super().__init__()
        self.settings = QSettings("MediaEngine", "MediaEngine")
        self.setWindowTitle("MediaEngine")
        self.resize(1100, 700)
        self.setAcceptDrops(True)

        self.worker: QueueWorker | None = None
        self.files: list[str] = []
        self.output_dir: str = os.getcwd()

        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)

        self.split = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.split)

        # Center panel
        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.drop_label = QLabel("Drop Files Here\n\n(Drag and drop one or more files)")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(180)
        self.drop_label.setStyleSheet(
            "border: 2px dashed #4a4a4a;"
            "border-radius: 10px;"
            "padding: 28px;"
            "font-size: 16px;"
            "font-weight: 600;"
            "background-color: rgba(255, 255, 255, 0.02);"
        )
        center_layout.addWidget(self.drop_label)

        add_section_label = QLabel("Add Files Section")
        add_section_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        center_layout.addWidget(add_section_label)

        add_hint = QLabel("Use the button below or drag files into the area above.")
        add_hint.setStyleSheet("color: #888;")
        center_layout.addWidget(add_hint)

        add_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Add Files")
        self.btn_add.setMinimumHeight(36)
        add_row.addWidget(self.btn_add)
        add_row.addStretch(1)
        center_layout.addLayout(add_row)

        self.file_list = QListWidget()
        center_layout.addWidget(self.file_list)

        center_btns = QHBoxLayout()
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_clear = QPushButton("Clear")
        center_btns.addWidget(self.btn_remove)
        center_btns.addWidget(self.btn_clear)
        center_layout.addLayout(center_btns)

        self.split.addWidget(center)

        # Right panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.preset_label = QLabel("Smart Preset")
        right_layout.addWidget(self.preset_label)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.PRESETS)
        right_layout.addWidget(self.preset_combo)

        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)

        self.convert_tab = QWidget()
        self.download_tab = QWidget()
        self.optimize_tab = QWidget()
        self.enhance_tab = QWidget()
        self.metadata_tab = QWidget()

        self.tabs.addTab(self.convert_tab, "Convert")
        self.tabs.addTab(self.download_tab, "Download")
        self.tabs.addTab(self.optimize_tab, "Optimize")
        self.tabs.addTab(self.enhance_tab, "Enhance")
        self.tabs.addTab(self.metadata_tab, "Metadata")

        self._build_convert_tab()
        self._build_download_tab()
        self._build_optimize_tab()
        self._build_enhance_tab()
        self._build_metadata_tab()

        self.tabs.currentChanged.connect(self.on_tab_changed)

        right_layout.addWidget(QLabel("Output Folder"))
        self.output_label = QLabel(self.output_dir)
        self.output_label.setWordWrap(True)
        right_layout.addWidget(self.output_label)
        self.btn_output = QPushButton("Choose Output Folder")
        right_layout.addWidget(self.btn_output)

        self.runtime_status_label = QLabel()
        self.runtime_status_label.setWordWrap(True)
        self.runtime_status_label.setStyleSheet("font-size: 12px; color: #d0d0d0;")
        right_layout.addWidget(self.runtime_status_label)

        right_layout.addWidget(QLabel("Logs"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        right_layout.addWidget(self.log_box)

        self.split.addWidget(right)
        self.split.setSizes([700, 400])

        # Bottom queue actions
        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label = QLabel("Ready")
        self.btn_start = QPushButton("Start")
        self.btn_cancel = QPushButton("Cancel")
        bottom.addWidget(self.progress)
        bottom.addWidget(self.status_label)
        bottom.addWidget(self.btn_start)
        bottom.addWidget(self.btn_cancel)
        main_layout.addLayout(bottom)

        self.btn_add.clicked.connect(self.pick_files)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_files)
        self.btn_output.clicked.connect(self.choose_output_folder)
        self.btn_start.clicked.connect(self.start_queue)
        self.btn_cancel.clicked.connect(self.cancel_queue)
        self.optimize_mode_combo.currentTextChanged.connect(self.on_optimize_mode_changed)
        self.enhance_mode_combo.currentTextChanged.connect(self.on_enhance_mode_changed)
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        self.file_list.itemSelectionChanged.connect(self.on_file_selection_changed)
        self.download_kind_combo.currentTextChanged.connect(self.on_download_kind_changed)

        self.refresh_format_options()
        self.refresh_optimize_options()
        self.refresh_download_options()
        self.refresh_runtime_status()
        self.load_settings()
        self.on_tab_changed(self.tabs.currentIndex())

    def _build_convert_tab(self):
        layout = QVBoxLayout(self.convert_tab)

        self.format_label = QLabel("Output Format")
        layout.addWidget(self.format_label)

        self.format_combo = QComboBox()
        self.format_combo.setEditable(True)
        self.format_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        layout.addWidget(self.format_combo)

        self.format_model = QStringListModel()
        self.format_completer = QCompleter(self.format_model, self)
        self.format_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.format_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.format_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.format_combo.setCompleter(self.format_completer)
        line_edit = self.format_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Search format (e.g. mp4, webp, pdf)")

        layout.addStretch(1)

    def _build_download_tab(self):
        layout = QVBoxLayout(self.download_tab)

        self.download_url_label = QLabel("YouTube Link")
        layout.addWidget(self.download_url_label)

        self.download_url_edit = QLineEdit()
        self.download_url_edit.setPlaceholderText("Paste a YouTube link here")
        layout.addWidget(self.download_url_edit)

        self.download_kind_label = QLabel("Download Type")
        layout.addWidget(self.download_kind_label)

        self.download_kind_combo = QComboBox()
        self.download_kind_combo.addItems(["Video", "Audio"])
        layout.addWidget(self.download_kind_combo)

        self.download_format_label = QLabel("Output Format")
        layout.addWidget(self.download_format_label)

        self.download_format_combo = QComboBox()
        self.download_format_combo.setEditable(True)
        self.download_format_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        layout.addWidget(self.download_format_combo)

        self.download_format_model = QStringListModel()
        self.download_format_completer = QCompleter(self.download_format_model, self)
        self.download_format_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.download_format_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.download_format_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.download_format_combo.setCompleter(self.download_format_completer)

        self.download_quality_label = QLabel("Quality")
        layout.addWidget(self.download_quality_label)

        self.download_quality_combo = QComboBox()
        layout.addWidget(self.download_quality_combo)

        self.download_hint_label = QLabel("Paste a link, choose video or audio, then download.")
        self.download_hint_label.setWordWrap(True)
        layout.addWidget(self.download_hint_label)

        layout.addStretch(1)

    def _build_optimize_tab(self):
        layout = QVBoxLayout(self.optimize_tab)

        self.optimize_mode_label = QLabel("Optimize Mode")
        layout.addWidget(self.optimize_mode_label)

        self.optimize_mode_combo = QComboBox()
        self.optimize_mode_combo.addItems(self.OPTIMIZE_MODES)
        layout.addWidget(self.optimize_mode_combo)

        self.image_quality_label = QLabel("Image/PDF Quality (1-100)")
        layout.addWidget(self.image_quality_label)
        self.image_quality_spin = QSpinBox()
        self.image_quality_spin.setRange(1, 100)
        self.image_quality_spin.setValue(80)
        layout.addWidget(self.image_quality_spin)

        self.video_preset_label = QLabel("Video Codec Preset")
        layout.addWidget(self.video_preset_label)
        self.video_preset_combo = QComboBox()
        for label, key in self.VIDEO_PRESETS:
            self.video_preset_combo.addItem(label, key)
        layout.addWidget(self.video_preset_combo)

        resize_row = QHBoxLayout()
        self.resize_w_label = QLabel("Resize W")
        resize_row.addWidget(self.resize_w_label)
        self.resize_w_spin = QSpinBox()
        self.resize_w_spin.setRange(16, 8192)
        self.resize_w_spin.setValue(1280)
        resize_row.addWidget(self.resize_w_spin)
        self.resize_h_label = QLabel("H")
        resize_row.addWidget(self.resize_h_label)
        self.resize_h_spin = QSpinBox()
        self.resize_h_spin.setRange(16, 8192)
        self.resize_h_spin.setValue(720)
        resize_row.addWidget(self.resize_h_spin)
        layout.addLayout(resize_row)

        layout.addStretch(1)

    def _build_enhance_tab(self):
        layout = QVBoxLayout(self.enhance_tab)

        self.enhance_mode_label = QLabel("Enhance Mode")
        layout.addWidget(self.enhance_mode_label)

        self.enhance_mode_combo = QComboBox()
        self.enhance_mode_combo.addItems(self.ENHANCE_MODES)
        layout.addWidget(self.enhance_mode_combo)

        self.enhance_strength_label = QLabel("Strength (1-100)")
        layout.addWidget(self.enhance_strength_label)
        self.enhance_strength_spin = QSpinBox()
        self.enhance_strength_spin.setRange(1, 100)
        self.enhance_strength_spin.setValue(50)
        layout.addWidget(self.enhance_strength_spin)

        self.upscale_factor_label = QLabel("Upscale Factor")
        layout.addWidget(self.upscale_factor_label)
        self.upscale_factor_combo = QComboBox()
        self.upscale_factor_combo.addItems(["2", "3", "4"])
        layout.addWidget(self.upscale_factor_combo)

        self.enhance_hint_label = QLabel("")
        self.enhance_hint_label.setWordWrap(True)
        layout.addWidget(self.enhance_hint_label)

        layout.addStretch(1)

    def _build_metadata_tab(self):
        layout = QVBoxLayout(self.metadata_tab)

        self.metadata_mode_label = QLabel("Metadata Mode")
        layout.addWidget(self.metadata_mode_label)

        self.metadata_mode_combo = QComboBox()
        self.metadata_mode_combo.addItems(["Reveal Metadata", "Strip Metadata"])
        layout.addWidget(self.metadata_mode_combo)

        layout.addStretch(1)

    def refresh_runtime_status(self):
        checks = [
            ("ffmpeg", is_tool_available("ffmpeg")),
            ("ImageMagick", is_tool_available("magick")),
            ("ExifTool", is_tool_available("exiftool")),
            ("yt-dlp", is_python_module_available("yt_dlp")),
        ]
        missing = [name for name, ok in checks if not ok]
        if missing:
            self.runtime_status_label.setText("Missing runtime dependencies: " + ", ".join(missing))
            self.runtime_status_label.setStyleSheet("font-size: 12px; color: #ffb3b3;")
        else:
            self.runtime_status_label.setText("Runtime dependencies detected: ffmpeg, ImageMagick, ExifTool, yt-dlp")
            self.runtime_status_label.setStyleSheet("font-size: 12px; color: #bff0bf;")

    def load_settings(self):
        output_dir_value = self.settings.value("output_dir", self.output_dir)
        if isinstance(output_dir_value, str) and output_dir_value:
            self.output_dir = output_dir_value
        self.output_label.setText(self.output_dir)

        preset = self.settings.value("preset", self.preset_combo.currentText())
        if isinstance(preset, str) and preset in self.PRESETS:
            self.preset_combo.setCurrentText(preset)

        download_kind = self.settings.value("download_kind", self.download_kind_combo.currentText())
        if isinstance(download_kind, str) and download_kind in [self.download_kind_combo.itemText(i) for i in range(self.download_kind_combo.count())]:
            self.download_kind_combo.setCurrentText(download_kind)

        convert_format = self.settings.value("convert_format", self.format_combo.currentText())
        if isinstance(convert_format, str) and convert_format:
            self.format_combo.setCurrentText(convert_format)

        optimize_mode = self.settings.value("optimize_mode", self.optimize_mode_combo.currentText())
        if isinstance(optimize_mode, str) and optimize_mode:
            self.optimize_mode_combo.setCurrentText(optimize_mode)

        enhance_mode = self.settings.value("enhance_mode", self.enhance_mode_combo.currentText())
        if isinstance(enhance_mode, str) and enhance_mode in [self.enhance_mode_combo.itemText(i) for i in range(self.enhance_mode_combo.count())]:
            self.enhance_mode_combo.setCurrentText(enhance_mode)

        metadata_mode = self.settings.value("metadata_mode", self.metadata_mode_combo.currentText())
        if isinstance(metadata_mode, str) and metadata_mode in [self.metadata_mode_combo.itemText(i) for i in range(self.metadata_mode_combo.count())]:
            self.metadata_mode_combo.setCurrentText(metadata_mode)

        download_format = self.settings.value("download_format", self.download_format_combo.currentText())
        if isinstance(download_format, str) and download_format:
            self.download_format_combo.setCurrentText(download_format)

        download_quality = self.settings.value("download_quality", self.download_quality_combo.currentText())
        if isinstance(download_quality, str) and download_quality:
            self.download_quality_combo.setCurrentText(download_quality)

        tab_value = self.settings.value("active_tab", self.tabs.currentIndex())
        tab_index = int(tab_value) if isinstance(tab_value, (int, str)) else self.tabs.currentIndex()
        tab_index = max(0, min(tab_index, self.tabs.count() - 1))
        self.tabs.setCurrentIndex(tab_index)

    def save_settings(self):
        self.settings.setValue("output_dir", self.output_dir)
        self.settings.setValue("active_tab", self.tabs.currentIndex())
        self.settings.setValue("preset", self.preset_combo.currentText())
        self.settings.setValue("download_kind", self.download_kind_combo.currentText())
        self.settings.setValue("download_format", self.download_format_combo.currentText())
        self.settings.setValue("download_quality", self.download_quality_combo.currentText())
        self.settings.setValue("convert_format", self.format_combo.currentText())
        self.settings.setValue("optimize_mode", self.optimize_mode_combo.currentText())
        self.settings.setValue("enhance_mode", self.enhance_mode_combo.currentText())
        self.settings.setValue("metadata_mode", self.metadata_mode_combo.currentText())

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        self.add_files(paths)
        event.acceptProposedAction()

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files")
        self.add_files(paths)

    def add_files(self, paths: list[str]):
        added = 0
        for path in paths:
            if path and path not in self.files and os.path.isfile(path):
                self.files.append(path)
                item = QListWidgetItem(f"{Path(path).name}   [{detect_file_type(path)}]\n{path}")
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.file_list.addItem(item)
                added += 1
        if added:
            self.log(f"Added {added} file(s)")
            self.refresh_format_options()
            self.refresh_optimize_options()
            self.update_feature_visibility()

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self.files:
                self.files.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        self.refresh_format_options()
        self.refresh_optimize_options()
        self.update_feature_visibility()

    def clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self.refresh_format_options()
        self.refresh_optimize_options()
        self.update_feature_visibility()

    def choose_output_folder(self):
        selected = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_dir)
        if selected:
            self.output_dir = selected
            self.output_label.setText(selected)
            self.save_settings()

    def current_action(self) -> str:
        return self.tabs.tabText(self.tabs.currentIndex())

    def selected_or_all_paths(self) -> list[str]:
        selected_items = self.file_list.selectedItems()
        if selected_items:
            return [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        return list(self.files)

    def validate_queue_inputs(self, jobs: list[Job]) -> str | None:
        output_path = Path(self.output_dir)
        if not output_path.exists():
            return "Choose an existing output folder."
        if not os.access(self.output_dir, os.W_OK):
            return "The chosen output folder is not writable."
        if not jobs:
            return "Nothing is ready to process."

        for job in jobs:
            if job.action == "Download":
                if not job.download_url:
                    return "Paste a YouTube link first."
                if not is_python_module_available("yt_dlp"):
                    return "yt-dlp is missing from the active Python environment."
                allowed_formats = {"mp4", "mkv", "webm"} if job.download_kind == "Video" else {"mp3", "m4a", "wav", "flac", "ogg"}
                allowed_qualities = {"Best", "1080p", "720p", "480p", "360p"} if job.download_kind == "Video" else {"Best", "320k", "192k", "128k"}
                if job.download_format and job.download_format not in allowed_formats:
                    return f"Unsupported download format: {job.download_format}"
                if job.download_quality and job.download_quality not in allowed_qualities:
                    return f"Unsupported download quality: {job.download_quality}"
                continue

            file_type = detect_file_type(job.input_path)
            if file_type == "unknown":
                return f"Unsupported file type: {Path(job.input_path).name}"

            if job.action == "Convert":
                target_format = (job.output_format or "").strip().lower()
                if target_format and target_format != "auto":
                    if target_format not in self.allowed_formats_for_type(file_type):
                        return f"{Path(job.input_path).name} cannot be converted to {target_format}."
            elif job.action == "Optimize":
                if job.optimize_mode == "compress" and file_type not in {"image", "video"}:
                    return f"Compress supports image/video files only: {Path(job.input_path).name}"
                if job.optimize_mode == "pdf_reduce" and file_type != "pdf":
                    return f"Reduce PDF size supports PDF files only: {Path(job.input_path).name}"
                if job.optimize_mode == "resize" and file_type not in {"image", "video"}:
                    return f"Resize supports image/video files only: {Path(job.input_path).name}"
            elif job.action == "Enhance":
                if job.enhance_mode in {"Sharpen Image", "Denoise Image", "Upscale Image"} and file_type != "image":
                    return f"{job.enhance_mode} supports image files only: {Path(job.input_path).name}"
                if job.enhance_mode == "Normalize Audio Volume" and file_type not in {"audio", "video"}:
                    return f"Normalize audio volume supports audio/video files only: {Path(job.input_path).name}"
            elif job.action == "Metadata":
                if file_type == "unknown":
                    return f"Metadata tools do not support this file: {Path(job.input_path).name}"

        return None

    def allowed_formats_for_type(self, source_type: str) -> set[str]:
        if source_type in {"image", "pdf"}:
            return set(self.IMAGE_FORMATS)
        if source_type in {"audio", "video"}:
            # FFmpeg transcode path supports audio and video targets for both.
            return set(self.AUDIO_FORMATS + self.VIDEO_FORMATS)
        return set()

    def build_jobs(self) -> list[Job]:
        action = self.current_action()
        if action == "Download":
            url = self.download_url_edit.text().strip()
            if not url:
                return []
            return [
                Job(
                    input_path=url,
                    action=action,
                    output_dir=self.output_dir,
                    download_url=url,
                    download_kind=self.download_kind_combo.currentText(),
                    download_format=(self.download_format_combo.currentText().strip().lower() or "mp4"),
                    download_quality=self.download_quality_combo.currentText(),
                )
            ]

        selected_format = self.format_combo.currentText().strip().lower()
        output_format = None if not selected_format or selected_format == "Auto" else selected_format
        metadata_mode = self.metadata_mode_combo.currentText()
        enhance_mode = self.enhance_mode_combo.currentText()
        enhance_strength = self.enhance_strength_spin.value()
        upscale_factor = int(self.upscale_factor_combo.currentText())
        optimize_mode_label = self.optimize_mode_combo.currentText()
        optimize_mode = {
            "Compress": "compress",
            "Reduce PDF Size": "pdf_reduce",
            "Batch Resize": "resize",
        }.get(optimize_mode_label, "compress")
        image_quality = self.image_quality_spin.value()
        video_preset = self.video_preset_combo.currentData()
        resize_width = self.resize_w_spin.value()
        resize_height = self.resize_h_spin.value()

        if action != "Convert":
            output_format = None
        if action != "Metadata":
            metadata_mode = None
        if action != "Enhance":
            enhance_mode = None
        if action != "Optimize":
            optimize_mode = None
        return [
            Job(
                input_path=p,
                action=action,
                output_dir=self.output_dir,
                output_format=output_format,
                metadata_mode=metadata_mode,
                enhance_mode=enhance_mode,
                enhance_strength=enhance_strength,
                upscale_factor=upscale_factor,
                optimize_mode=optimize_mode,
                image_quality=image_quality,
                video_preset=video_preset,
                resize_width=resize_width,
                resize_height=resize_height,
            )
            for p in self.files
        ]

    def process_job(self, job: Job, progress_callback=None) -> str:
        if job.action == "Download":
            return download_media(
                url=job.download_url or job.input_path,
                output_dir=job.output_dir,
                download_kind=job.download_kind or "Video",
                download_format=job.download_format or "mp4",
                download_quality=job.download_quality or "Best",
                progress_callback=progress_callback,
            )
        if job.action == "Convert":
            return run_convert(job.input_path, job.output_dir, job.output_format)
        if job.action == "Optimize":
            return run_optimize(
                job.input_path,
                job.output_dir,
                optimize_mode=job.optimize_mode or "compress",
                image_quality=job.image_quality,
                video_preset=job.video_preset,
                resize_width=job.resize_width,
                resize_height=job.resize_height,
            )
        if job.action == "Enhance":
            return run_enhance(
                job.input_path,
                job.output_dir,
                enhance_mode=job.enhance_mode or "Sharpen Image",
                enhance_strength=job.enhance_strength,
                upscale_factor=job.upscale_factor,
            )
        if job.action == "Metadata":
            if job.metadata_mode == "Reveal Metadata":
                return run_reveal_metadata(job.input_path, job.output_dir)
            return run_strip_metadata(job.input_path, job.output_dir)
        raise ValueError(f"Unknown action: {job.action}")

    def on_tab_changed(self, index: int):
        self.update_feature_visibility()
        if self.current_action() == "Convert":
            self.refresh_format_options()
        if self.current_action() == "Optimize":
            self.refresh_optimize_options()
        if self.current_action() == "Download":
            self.refresh_download_options()

    def on_file_selection_changed(self):
        # Aggressive filtering: when specific files are selected, filter options by those files only.
        if self.current_action() == "Convert":
            self.refresh_format_options()
        if self.current_action() == "Optimize":
            self.refresh_optimize_options()
        self.update_feature_visibility()

    def on_action_changed(self, action: str):
        if action in self.TAB_INDEX:
            self.tabs.setCurrentIndex(self.TAB_INDEX[action])

    def on_optimize_mode_changed(self, mode: str):
        self.update_feature_visibility()

    def on_enhance_mode_changed(self, mode: str):
        self.update_feature_visibility()

    def on_download_kind_changed(self, kind: str):
        self.refresh_download_options()
        self.update_feature_visibility()

    def on_preset_changed(self, preset_name: str):
        config = self.PRESET_CONFIG.get(preset_name, self.PRESET_CONFIG["Custom"])
        preset_action = config.get("action")
        preset_format = config.get("format")
        preset_metadata_mode = config.get("metadata_mode")

        if preset_action:
            if preset_action in self.TAB_INDEX:
                self.tabs.setCurrentIndex(self.TAB_INDEX[preset_action])

        self.refresh_format_options()
        self.refresh_download_options()

        if preset_format and self.current_action() == "Convert":
            available = [self.format_combo.itemText(i) for i in range(self.format_combo.count())]
            if preset_format in available:
                self.format_combo.setCurrentText(preset_format)
            else:
                self.format_combo.setCurrentText("Auto")
        elif self.current_action() == "Convert":
            self.format_combo.setCurrentText("Auto")

        if preset_metadata_mode and self.current_action() == "Metadata":
            self.metadata_mode_combo.setCurrentText(preset_metadata_mode)
        elif self.current_action() == "Metadata":
            self.metadata_mode_combo.setCurrentText("Reveal Metadata")

        self.update_feature_visibility()
        self.log(f"Preset selected: {preset_name}")

    def refresh_format_options(self):
        # Keep dropdown tightly scoped to Convert mode.
        if self.current_action() != "Convert":
            return

        options = ["Auto"]

        paths = self.selected_or_all_paths()
        detected = [detect_file_type(p) for p in paths if p]
        detected = [t for t in detected if t in {"image", "audio", "video", "pdf"}]

        if not detected:
            detected = ["image", "audio", "video", "pdf"]

        allowed_sets = [self.allowed_formats_for_type(t) for t in detected]
        allowed_sets = [s for s in allowed_sets if s]

        # Aggressive rule: show formats compatible with ALL selected files.
        if allowed_sets:
            common = set.intersection(*allowed_sets)
        else:
            common = set()

        if not common and allowed_sets:
            # If no intersection exists for mixed file families, fall back to the first family
            # so the dropdown remains useful while still narrowed.
            common = allowed_sets[0]

        ordered_pool = self.IMAGE_FORMATS + self.AUDIO_FORMATS + self.VIDEO_FORMATS
        options.extend([fmt for fmt in ordered_pool if fmt in common])

        # Keep order, remove duplicates
        deduped = list(dict.fromkeys(options))

        current = self.format_combo.currentText().strip().lower()
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItems(deduped)
        self.format_model.setStringList(deduped)
        self.format_combo.blockSignals(False)

        if current and current in deduped:
            self.format_combo.setCurrentText(current)
        else:
            self.format_combo.setCurrentIndex(-1)
            line_edit = self.format_combo.lineEdit()
            if line_edit is not None:
                line_edit.clear()

    def refresh_optimize_options(self):
        detected = {detect_file_type(p) for p in self.files}
        if not detected:
            detected = {"image", "audio", "video", "pdf"}

        options = []
        if "image" in detected or "video" in detected:
            options.extend(["Compress", "Batch Resize"])
        if "pdf" in detected:
            options.append("Reduce PDF Size")

        if not options:
            options = ["No optimize options"]

        current = self.optimize_mode_combo.currentText()
        self.optimize_mode_combo.blockSignals(True)
        self.optimize_mode_combo.clear()
        self.optimize_mode_combo.addItems(list(dict.fromkeys(options)))
        self.optimize_mode_combo.blockSignals(False)

        if current in options:
            self.optimize_mode_combo.setCurrentText(current)
        else:
            self.optimize_mode_combo.setCurrentIndex(0)

    def refresh_download_options(self):
        if self.current_action() != "Download":
            return

        if self.download_kind_combo.currentText() == "Audio":
            formats = ["mp3", "m4a", "wav", "flac", "ogg"]
            qualities = ["Best", "320k", "192k", "128k"]
        else:
            formats = ["mp4", "mkv", "webm"]
            qualities = ["Best", "1080p", "720p", "480p", "360p"]

        current_format = self.download_format_combo.currentText().strip().lower()
        current_quality = self.download_quality_combo.currentText().strip()

        self.download_format_combo.blockSignals(True)
        self.download_format_combo.clear()
        self.download_format_combo.addItems(formats)
        self.download_format_model.setStringList(formats)
        self.download_format_combo.blockSignals(False)

        if current_format in formats:
            self.download_format_combo.setCurrentText(current_format)
        else:
            self.download_format_combo.setCurrentIndex(0)

        self.download_quality_combo.blockSignals(True)
        self.download_quality_combo.clear()
        self.download_quality_combo.addItems(qualities)
        self.download_quality_combo.blockSignals(False)

        if current_quality in qualities:
            self.download_quality_combo.setCurrentText(current_quality)
        else:
            self.download_quality_combo.setCurrentIndex(0)

    def update_feature_visibility(self):
        detected = {detect_file_type(p) for p in self.files}
        if not detected:
            detected = {"image", "audio", "video", "pdf"}

        action = self.current_action()
        optimize_mode = self.optimize_mode_combo.currentText()
        enhance_mode = self.enhance_mode_combo.currentText()

        show_quality = False
        show_video_preset = False
        show_resize = False

        if action == "Optimize":
            if optimize_mode == "Compress":
                show_quality = "image" in detected or "pdf" in detected
                show_video_preset = "video" in detected
            elif optimize_mode == "Reduce PDF Size":
                show_quality = "pdf" in detected
            elif optimize_mode == "Batch Resize":
                show_resize = "image" in detected or "video" in detected

        self.image_quality_label.setVisible(action == "Optimize" and show_quality)
        self.image_quality_spin.setVisible(action == "Optimize" and show_quality)

        self.video_preset_label.setVisible(action == "Optimize" and show_video_preset)
        self.video_preset_combo.setVisible(action == "Optimize" and show_video_preset)

        self.resize_w_label.setVisible(action == "Optimize" and show_resize)
        self.resize_w_spin.setVisible(action == "Optimize" and show_resize)
        self.resize_h_label.setVisible(action == "Optimize" and show_resize)
        self.resize_h_spin.setVisible(action == "Optimize" and show_resize)

        enhance_visible = action == "Enhance"
        download_visible = action == "Download"
        image_modes = {"Sharpen Image", "Denoise Image"}
        is_upscale = enhance_mode == "Upscale Image"
        is_audio_norm = enhance_mode == "Normalize Audio Volume"

        self.enhance_mode_label.setVisible(enhance_visible)
        self.enhance_mode_combo.setVisible(enhance_visible)
        self.enhance_strength_label.setVisible(enhance_visible and enhance_mode in image_modes)
        self.enhance_strength_spin.setVisible(enhance_visible and enhance_mode in image_modes)
        self.upscale_factor_label.setVisible(enhance_visible and is_upscale)
        self.upscale_factor_combo.setVisible(enhance_visible and is_upscale)

        if enhance_visible and enhance_mode in image_modes and "image" not in detected:
            self.enhance_hint_label.setText("This mode requires image files.")
            self.enhance_hint_label.setVisible(True)
        elif enhance_visible and is_upscale and "image" not in detected:
            self.enhance_hint_label.setText("Upscale requires image files.")
            self.enhance_hint_label.setVisible(True)
        elif enhance_visible and is_audio_norm and not ({"audio", "video"} & detected):
            self.enhance_hint_label.setText("Normalize audio volume requires audio/video files.")
            self.enhance_hint_label.setVisible(True)
        else:
            self.enhance_hint_label.setVisible(False)

            self.download_url_label.setVisible(download_visible)
            self.download_url_edit.setVisible(download_visible)
            self.download_kind_label.setVisible(download_visible)
            self.download_kind_combo.setVisible(download_visible)
            self.download_format_label.setVisible(download_visible)
            self.download_format_combo.setVisible(download_visible)
            self.download_quality_label.setVisible(download_visible)
            self.download_quality_combo.setVisible(download_visible)
            self.download_hint_label.setVisible(download_visible)

        # Convert and Metadata tabs already isolate their controls; only the relevant options inside them remain.
        self.format_label.setVisible(action == "Convert")
        self.format_combo.setVisible(action == "Convert")
        self.metadata_mode_label.setVisible(action == "Metadata")
        self.metadata_mode_combo.setVisible(action == "Metadata")
        self.optimize_mode_label.setVisible(action == "Optimize")
        self.optimize_mode_combo.setVisible(action == "Optimize")

    def start_queue(self):
        jobs = self.build_jobs()
        error_message = self.validate_queue_inputs(jobs)
        if error_message:
            QMessageBox.warning(self, "Cannot start queue", error_message)
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Busy", "A queue is already running.")
            return

        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.status_label.setText("Queue starting...")
        self.worker = QueueWorker(jobs, self.process_job)
        self.worker.job_started.connect(self.on_job_started)
        self.worker.job_progress.connect(self.on_job_progress)
        self.worker.progress.connect(self.on_progress)
        self.worker.log.connect(self.log)
        self.worker.job_done.connect(self.on_job_done)
        self.worker.finished_summary.connect(self.on_finished_summary)
        self.worker.start()
        self.log(f"Started {len(jobs)} job(s)")

    def cancel_queue(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.log("Cancel requested...")

    def on_progress(self, done: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def on_job_started(self, index: int, total: int, action: str, input_path: str):
        name = input_path if action == "Download" else Path(input_path).name
        self.status_label.setText(f"{action} {index}/{total}: {name}")

    def on_job_progress(self, message: str):
        self.status_label.setText(message)

    def on_job_done(self, input_path: str, ok: bool, detail: str):
        name = Path(input_path).name
        status = "OK" if ok else "FAIL"
        self.log(f"{status}: {name} -> {detail}")

    def on_finished_summary(self, success: int, failed: int):
        self.status_label.setText("Queue finished")
        QMessageBox.information(self, "Queue finished", f"Success: {success} | Failed: {failed}")

    def log(self, text: str):
        self.log_box.append(text)


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
