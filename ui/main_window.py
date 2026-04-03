import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QStringListModel
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
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.converter import run_convert
from core.enhancer import run_enhance
from core.metadata import run_reveal_metadata, run_strip_metadata
from core.optimizer import run_optimize
from core.queue_manager import QueueWorker
from core.utils import detect_file_type
from models.job import Job


class MainWindow(QMainWindow):
    ACTIONS = [
        "Convert",
        "Optimize",
        "Enhance",
        "Metadata",
    ]

    IMAGE_FORMATS = ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "pdf"]
    AUDIO_FORMATS = ["mp3", "wav", "aac", "flac", "ogg", "m4a"]
    VIDEO_FORMATS = ["mp4", "mkv", "avi", "mov", "webm"]
    OPTIMIZE_MODES = ["Compress", "Reduce PDF Size", "Batch Resize"]
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

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MediaEngine")
        self.resize(1100, 700)
        self.setAcceptDrops(True)

        self.worker: QueueWorker | None = None
        self.files: list[str] = []
        self.output_dir = os.getcwd()

        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)

        split = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(split)

        # Left sidebar
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Modules"))
        self.module_list = QListWidget()
        for item in ["Convert", "Optimize", "Enhance", "Metadata", "Batch Jobs", "Settings"]:
            self.module_list.addItem(item)
        self.module_list.setCurrentRow(0)
        left_layout.addWidget(self.module_list)
        split.addWidget(left)

        # Center panel
        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.drop_label = QLabel("Drag and drop files here")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("border: 2px dashed #666; padding: 24px; font-size: 14px;")
        center_layout.addWidget(self.drop_label)

        self.file_list = QListWidget()
        center_layout.addWidget(self.file_list)

        center_btns = QHBoxLayout()
        self.btn_add = QPushButton("Add Files")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_clear = QPushButton("Clear")
        center_btns.addWidget(self.btn_add)
        center_btns.addWidget(self.btn_remove)
        center_btns.addWidget(self.btn_clear)
        center_layout.addLayout(center_btns)

        split.addWidget(center)

        # Right panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Smart Preset"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.PRESETS)
        right_layout.addWidget(self.preset_combo)

        right_layout.addWidget(QLabel("Action"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(self.ACTIONS)
        right_layout.addWidget(self.action_combo)

        right_layout.addWidget(QLabel("Output Format"))
        self.format_combo = QComboBox()
        self.format_combo.setEditable(True)
        self.format_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        right_layout.addWidget(self.format_combo)

        right_layout.addWidget(QLabel("Metadata Mode"))
        self.metadata_mode_combo = QComboBox()
        self.metadata_mode_combo.addItems(["Reveal Metadata", "Strip Metadata"])
        right_layout.addWidget(self.metadata_mode_combo)

        right_layout.addWidget(QLabel("Optimize Mode"))
        self.optimize_mode_combo = QComboBox()
        self.optimize_mode_combo.addItems(self.OPTIMIZE_MODES)
        right_layout.addWidget(self.optimize_mode_combo)

        right_layout.addWidget(QLabel("Image/PDF Quality (1-100)"))
        self.image_quality_spin = QSpinBox()
        self.image_quality_spin.setRange(1, 100)
        self.image_quality_spin.setValue(80)
        right_layout.addWidget(self.image_quality_spin)

        right_layout.addWidget(QLabel("Video Codec Preset"))
        self.video_preset_combo = QComboBox()
        for label, key in self.VIDEO_PRESETS:
            self.video_preset_combo.addItem(label, key)
        right_layout.addWidget(self.video_preset_combo)

        resize_row = QHBoxLayout()
        resize_row.addWidget(QLabel("Resize W"))
        self.resize_w_spin = QSpinBox()
        self.resize_w_spin.setRange(16, 8192)
        self.resize_w_spin.setValue(1280)
        resize_row.addWidget(self.resize_w_spin)
        resize_row.addWidget(QLabel("H"))
        self.resize_h_spin = QSpinBox()
        self.resize_h_spin.setRange(16, 8192)
        self.resize_h_spin.setValue(720)
        resize_row.addWidget(self.resize_h_spin)
        right_layout.addLayout(resize_row)

        # Searchable format dropdown (type to filter suggestions)
        self.format_model = QStringListModel()
        self.format_completer = QCompleter(self.format_model, self)
        self.format_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.format_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.format_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.format_combo.setCompleter(self.format_completer)
        line_edit = self.format_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Search format (e.g. mp4, webp, pdf)")

        right_layout.addWidget(QLabel("Output Folder"))
        self.output_label = QLabel(self.output_dir)
        self.output_label.setWordWrap(True)
        right_layout.addWidget(self.output_label)
        self.btn_output = QPushButton("Choose Output Folder")
        right_layout.addWidget(self.btn_output)

        right_layout.addWidget(QLabel("Logs"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        right_layout.addWidget(self.log_box)

        split.addWidget(right)
        split.setSizes([180, 560, 360])

        # Bottom queue actions
        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.btn_start = QPushButton("Start")
        self.btn_cancel = QPushButton("Cancel")
        bottom.addWidget(self.progress)
        bottom.addWidget(self.btn_start)
        bottom.addWidget(self.btn_cancel)
        main_layout.addLayout(bottom)

        self.btn_add.clicked.connect(self.pick_files)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_files)
        self.btn_output.clicked.connect(self.choose_output_folder)
        self.btn_start.clicked.connect(self.start_queue)
        self.btn_cancel.clicked.connect(self.cancel_queue)
        self.action_combo.currentTextChanged.connect(self.on_action_changed)
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)

        self.refresh_format_options()
        self.on_action_changed(self.action_combo.currentText())

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

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self.files:
                self.files.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        self.refresh_format_options()

    def clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self.refresh_format_options()

    def choose_output_folder(self):
        selected = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_dir)
        if selected:
            self.output_dir = selected
            self.output_label.setText(selected)

    def build_jobs(self) -> list[Job]:
        action = self.action_combo.currentText()
        selected_format = self.format_combo.currentText().strip().lower()
        output_format = None if selected_format == "Auto" else selected_format
        metadata_mode = self.metadata_mode_combo.currentText()
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
        if action != "Optimize":
            optimize_mode = None
        return [
            Job(
                input_path=p,
                action=action,
                output_dir=self.output_dir,
                output_format=output_format,
                metadata_mode=metadata_mode,
                optimize_mode=optimize_mode,
                image_quality=image_quality,
                video_preset=video_preset,
                resize_width=resize_width,
                resize_height=resize_height,
            )
            for p in self.files
        ]

    def process_job(self, job: Job) -> str:
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
            return run_enhance(job.input_path, job.output_dir)
        if job.action == "Metadata":
            if job.metadata_mode == "Reveal Metadata":
                return run_reveal_metadata(job.input_path)
            return run_strip_metadata(job.input_path, job.output_dir)
        raise ValueError(f"Unknown action: {job.action}")

    def on_action_changed(self, action: str):
        convert_mode = action == "Convert"
        metadata_mode = action == "Metadata"
        optimize_mode = action == "Optimize"
        self.format_combo.setEnabled(convert_mode)
        self.metadata_mode_combo.setEnabled(metadata_mode)
        self.optimize_mode_combo.setEnabled(optimize_mode)
        self.image_quality_spin.setEnabled(optimize_mode)
        self.video_preset_combo.setEnabled(optimize_mode)
        self.resize_w_spin.setEnabled(optimize_mode)
        self.resize_h_spin.setEnabled(optimize_mode)
        if convert_mode:
            self.refresh_format_options()

    def on_preset_changed(self, preset_name: str):
        config = self.PRESET_CONFIG.get(preset_name, self.PRESET_CONFIG["Custom"])
        preset_action = config.get("action")
        preset_format = config.get("format")
        preset_metadata_mode = config.get("metadata_mode")

        if preset_action:
            self.action_combo.setCurrentText(preset_action)

        self.refresh_format_options()

        if preset_format and self.action_combo.currentText() == "Convert":
            available = [self.format_combo.itemText(i) for i in range(self.format_combo.count())]
            if preset_format in available:
                self.format_combo.setCurrentText(preset_format)
            else:
                self.format_combo.setCurrentText("Auto")
        elif self.action_combo.currentText() == "Convert":
            self.format_combo.setCurrentText("Auto")

        if preset_metadata_mode and self.action_combo.currentText() == "Metadata":
            self.metadata_mode_combo.setCurrentText(preset_metadata_mode)
        elif self.action_combo.currentText() == "Metadata":
            self.metadata_mode_combo.setCurrentText("Reveal Metadata")

        self.log(f"Preset selected: {preset_name}")

    def refresh_format_options(self):
        options = ["Auto"]
        detected = {detect_file_type(p) for p in self.files}
        if not detected:
            detected = {"image", "audio", "video", "pdf"}

        if "image" in detected or "pdf" in detected:
            options.extend(self.IMAGE_FORMATS)
        if "audio" in detected:
            options.extend(self.AUDIO_FORMATS)
        if "video" in detected:
            options.extend(self.VIDEO_FORMATS)

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
            self.format_combo.setCurrentText("Auto")

    def start_queue(self):
        jobs = self.build_jobs()
        if not jobs:
            QMessageBox.warning(self, "No files", "Add at least one file.")
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Busy", "A queue is already running.")
            return

        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.worker = QueueWorker(jobs, self.process_job)
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

    def on_job_done(self, input_path: str, ok: bool, detail: str):
        name = Path(input_path).name
        status = "OK" if ok else "FAIL"
        self.log(f"{status}: {name} -> {detail}")

    def on_finished_summary(self, success: int, failed: int):
        QMessageBox.information(self, "Queue finished", f"Success: {success} | Failed: {failed}")

    def log(self, text: str):
        self.log_box.append(text)


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
