import sys
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, QAbstractItemView, QProgressBar, QMessageBox
from PySide6.QtCore import Qt, Signal, QThread


class Worker(QThread):
	progress = Signal(int)
	set_max = Signal(int)
	status = Signal(str)
	error = Signal(str)
	finished = Signal()

	def __init__(self, queue):
		super().__init__()
		# share the queue list reference; main thread may append while worker runs
		self.queue = queue
		self.is_cancelled = False

	def cancel(self):
		"""Request cancellation from the main thread."""
		self.is_cancelled = True

	def run(self):
		processed = 0
		# initial maximum
		self.set_max.emit(len(self.queue) if len(self.queue) > 0 else 1)
		while True:
			# check cancellation before starting next job
			if self.is_cancelled:
				self.status.emit("Cancelled")
				break
			if not self.queue:
				break
			job = self.queue.pop(0)
			path = job.get("path")
			action = job.get("action")
			self.status.emit(f"Processing: {Path(path).name}")
			try:
				if action == "convert":
					success, msg = convert_file(path)
				elif action == "compress":
					success, msg = compress_image(path)
				elif action == "view_metadata":
					success, msg = view_metadata(path)
				elif action == "remove_metadata":
					success, msg = remove_metadata(path)
				else:
					print(f"Unknown action: {action} for {path}")
					success, msg = True, ""
			except Exception as exc:
				print(f"Error processing {path}: {exc}")
				success, msg = False, str(exc)
			if not success:
				# emit error message to main thread for popup
				self.error.emit(msg)
			processed += 1
			self.progress.emit(processed)
			# check cancellation after finishing current job
			if self.is_cancelled:
				self.status.emit("Cancelled")
				break
		# signal finished
		self.finished.emit()


def convert_file(input_path):
	input_file = Path(input_path)
	output_file = input_file.with_name(f"{input_file.stem}_converted.mp4")

	print(f"Converting: {input_path}")
	try:
		subprocess.run(
			["ffmpeg", "-y", "-i", str(input_file), str(output_file)],
			check=True,
			capture_output=True,
			text=True,
		)
		print(f"Success: {output_file}")
		return True, f"Success: {output_file}"
	except subprocess.CalledProcessError as exc:
		error_message = (exc.stderr or str(exc)).strip()
		print(f"Error: {error_message}")
		return False, error_message
	except FileNotFoundError as exc:
		print(f"Error: {exc}")
		return False, str(exc)


def compress_image(input_path):
	input_file = Path(input_path)
	output_file = input_file.with_name(f"{input_file.stem}_compressed{input_file.suffix}")

	print(f"Compressing: {input_path}")
	try:
		subprocess.run(
			["magick", str(input_file), "-quality", "80", str(output_file)],
			check=True,
			capture_output=True,
			text=True,
		)
		print(f"Success: {output_file}")
		return True, f"Success: {output_file}"
	except subprocess.CalledProcessError as exc:
		error_message = (exc.stderr or str(exc)).strip()
		print(f"Error: {error_message}")
		return False, error_message
	except FileNotFoundError as exc:
		print(f"Error: {exc}")
		return False, str(exc)


def view_metadata(input_path):
	input_file = Path(input_path)

	print(f"Metadata for: {input_file}")
	print("-" * 60)
	try:
		result = subprocess.run(
			["exiftool", str(input_file)],
			check=True,
			capture_output=True,
			text=True,
		)
		output = (result.stdout or "").strip()
		if output:
			print(output)
		else:
			print("No metadata output returned")
		return True, output
	except subprocess.CalledProcessError as exc:
		error_message = (exc.stderr or str(exc)).strip()
		print(f"Error: {error_message}")
		return False, error_message
	except FileNotFoundError as exc:
		print(f"Error: {exc}")
		return False, str(exc)
	finally:
		print("-" * 60)


def remove_metadata(input_path):
	input_file = Path(input_path)
	print(f"Cleaning metadata: {input_file}")
	try:
		subprocess.run(
			["exiftool", "-all=", "-overwrite_original", str(input_file)],
			check=True,
			capture_output=True,
			text=True,
		)
		print("Success")
		return True, "Success"
	except subprocess.CalledProcessError as exc:
		error_message = (exc.stderr or str(exc)).strip()
		print(f"Error: {error_message}")
		return False, error_message
	except FileNotFoundError as exc:
		print(f"Error: {exc}")
		return False, str(exc)


class DropWindow(QWidget):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("MediaEngine")
		self.resize(500, 300)
		self.setAcceptDrops(True)

		# stored file paths
		self.file_paths = []

		# job queue: list of {'path': ..., 'action': ...}
		self.queue = []
		# processing flag
		self.is_processing = False

		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignCenter)

		self.label = QLabel("Drag & Drop Files Here")
		self.label.setAlignment(Qt.AlignCenter)
		layout.addWidget(self.label)

		# list widget to display dropped files (hidden until files are added)
		self.list_widget = QListWidget()
		self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
		self.list_widget.hide()
		layout.addWidget(self.list_widget)

		# action buttons (horizontal layout)
		h_buttons = QHBoxLayout()
		h_buttons.setSpacing(12)
		h_buttons.setContentsMargins(0, 8, 0, 0)
		self.btn_convert = QPushButton("Convert")
		self.btn_compress = QPushButton("Compress")
		self.btn_view_meta = QPushButton("View Metadata")
		self.btn_remove_meta = QPushButton("Remove Metadata")
		self.btn_cancel = QPushButton("Cancel")
		# add buttons to layout
		h_buttons.addWidget(self.btn_convert)
		h_buttons.addWidget(self.btn_compress)
		h_buttons.addWidget(self.btn_view_meta)
		h_buttons.addWidget(self.btn_remove_meta)
		h_buttons.addWidget(self.btn_cancel)
		self.btn_convert.clicked.connect(self.handle_convert_clicked)
		self.btn_compress.clicked.connect(self.handle_compress_clicked)
		self.btn_view_meta.clicked.connect(self.handle_view_metadata_clicked)
		self.btn_remove_meta.clicked.connect(self.handle_remove_metadata_clicked)
		self.btn_cancel.clicked.connect(self.handle_cancel_clicked)
		# buttons visible by default
		layout.addLayout(h_buttons)

		# status label at the bottom
		self.status_label = QLabel("Ready")
		self.status_label.setAlignment(Qt.AlignCenter)
		layout.addWidget(self.status_label)

		# progress bar below status
		self.progress_bar = QProgressBar()
		self.progress_bar.setValue(0)
		layout.addWidget(self.progress_bar)

	def handle_convert_clicked(self):
		selected_items = self.list_widget.selectedItems()
		if not selected_items:
			print("No files selected")
			return

		# enqueue convert jobs
		selected_paths = [item.text() for item in selected_items]
		for path in selected_paths:
			self.queue.append({"path": path, "action": "convert"})
		added = len(selected_paths)
		print(f"Queued {added} convert job(s)")
		self.status_label.setText(f"Queued: {len(self.queue)} job(s)")
		QApplication.processEvents()
		if not self.is_processing:
			self.process_queue()
		else:
			# if already processing, expand progress maximum
			self.progress_bar.setMaximum(self.progress_bar.maximum() + added)
			QApplication.processEvents()

	def process_queue(self):
		# start background worker to process the queue
		if self.is_processing:
			return

		if not self.queue:
			self.status_label.setText("No jobs in queue")
			QApplication.processEvents()
			return

		# prepare UI
		self.is_processing = True
		self.progress_bar.setMaximum(len(self.queue) if len(self.queue) > 0 else 1)
		self.progress_bar.setValue(0)
		QApplication.processEvents()

		# create and start worker
		self.worker = Worker(self.queue)
		self.worker.progress.connect(lambda v: self.progress_bar.setValue(v))
		self.worker.set_max.connect(lambda m: self.progress_bar.setMaximum(m))
		self.worker.status.connect(lambda s: self.status_label.setText(s))
		self.worker.error.connect(lambda m: QMessageBox.critical(self, "Error", m))
		self.worker.finished.connect(self._on_worker_finished)
		self.worker.start()


	def _on_worker_finished(self):
		self.is_processing = False
		# show Cancelled if worker was cancelled, otherwise Done
		if hasattr(self, 'worker') and getattr(self.worker, 'is_cancelled', False):
			self.status_label.setText("Cancelled")
		else:
			self.status_label.setText("Done")
			# show success popup
			QMessageBox.information(self, "Success", "Operation completed successfully")
		QApplication.processEvents()
		# reset progress
		self.progress_bar.setValue(0)
		self.progress_bar.setMaximum(100)
		QApplication.processEvents()

	def handle_compress_clicked(self):
		selected_items = self.list_widget.selectedItems()
		if not selected_items:
			print("No files selected")
			return

		# enqueue compress jobs (skip unsupported extensions)
		supported_extensions = {".jpg", ".jpeg", ".png", ".webp"}
		selected_paths = [item.text() for item in selected_items]
		added = 0
		for path in selected_paths:
			extension = Path(path).suffix.lower()
			if extension not in supported_extensions:
				print(f"Skipping unsupported file: {path}")
				continue
			self.queue.append({"path": path, "action": "compress"})
			added += 1
		print(f"Queued {added} compress job(s)")
		self.status_label.setText(f"Queued: {len(self.queue)} job(s)")
		QApplication.processEvents()
		if not self.is_processing:
			self.process_queue()
		else:
			# expand progress maximum if already processing
			self.progress_bar.setMaximum(self.progress_bar.maximum() + added)
			QApplication.processEvents()

	def handle_view_metadata_clicked(self):
		selected_items = self.list_widget.selectedItems()
		if not selected_items:
			print("No files selected")
			return

		# enqueue view metadata jobs
		selected_paths = [item.text() for item in selected_items]
		for path in selected_paths:
			self.queue.append({"path": path, "action": "view_metadata"})
		added = len(selected_paths)
		print(f"Queued {added} metadata view job(s)")
		self.status_label.setText(f"Queued: {len(self.queue)} job(s)")
		QApplication.processEvents()
		if not self.is_processing:
			self.process_queue()
		else:
			self.progress_bar.setMaximum(self.progress_bar.maximum() + added)
			QApplication.processEvents()

	def handle_remove_metadata_clicked(self):
		selected_items = self.list_widget.selectedItems()
		if not selected_items:
			print("No files selected")
			return

		# enqueue remove metadata jobs
		selected_paths = [item.text() for item in selected_items]
		for path in selected_paths:
			self.queue.append({"path": path, "action": "remove_metadata"})
		added = len(selected_paths)
		print(f"Queued {added} metadata removal job(s)")
		self.status_label.setText(f"Queued: {len(self.queue)} job(s)")
		QApplication.processEvents()
		if not self.is_processing:
			self.process_queue()
		else:
			self.progress_bar.setMaximum(self.progress_bar.maximum() + added)
			QApplication.processEvents()

	def handle_cancel_clicked(self):
		# request worker cancellation if running
		if hasattr(self, 'worker') and getattr(self, 'worker', None) is not None:
			if self.worker.isRunning():
				self.worker.cancel()
				self.status_label.setText('Cancelling...')
				QApplication.processEvents()
				return
		# no active worker
		self.status_label.setText('No active worker')
		QApplication.processEvents()

	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.acceptProposedAction()
		else:
			event.ignore()

	def dropEvent(self, event):
		urls = event.mimeData().urls()
		paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
		if paths:
			# add new files without removing existing ones, prevent duplicates
			added = 0
			for p in paths:
				if p not in self.file_paths:
					self.file_paths.append(p)
					self.list_widget.addItem(p)
					added += 1
			# print all stored file paths to console
			print("Files loaded (total): {}".format(len(self.file_paths)))
			for p in self.file_paths:
				print(p)
			# update UI: hide the label and show the list
			self.label.hide()
			self.list_widget.show()
		event.acceptProposedAction()


def main():
	app = QApplication(sys.argv)
	win = DropWindow()
	win.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()

