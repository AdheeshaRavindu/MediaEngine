from typing import Callable

from PySide6.QtCore import QThread, Signal

from models.job import Job


class QueueWorker(QThread):
    progress = Signal(int, int)
    log = Signal(str)
    job_done = Signal(str, bool, str)
    finished_summary = Signal(int, int)

    def __init__(self, jobs: list[Job], processor: Callable[[Job], str]):
        super().__init__()
        self._jobs = jobs
        self._processor = processor
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        success = 0
        failed = 0
        total = len(self._jobs)

        for idx, job in enumerate(self._jobs, start=1):
            if self._cancel:
                self.log.emit("Cancelled by user")
                break
            try:
                self.log.emit(f"Running {job.action}: {job.input_path}")
                out_path = self._processor(job)
                success += 1
                self.job_done.emit(job.input_path, True, out_path)
            except Exception as exc:
                failed += 1
                self.job_done.emit(job.input_path, False, str(exc))
            self.progress.emit(idx, total)

        self.finished_summary.emit(success, failed)
