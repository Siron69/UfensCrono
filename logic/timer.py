import time
from PyQt6.QtCore import QThread, pyqtSignal


class CronoThread(QThread):
    tick = pyqtSignal(int)   # ms trascorsi dall'avvio

    def __init__(self, start_ts: float):
        super().__init__()
        self._start_ts = start_ts
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            elapsed_ms = round((time.perf_counter() - self._start_ts) * 1000)
            self.tick.emit(elapsed_ms)
            time.sleep(0.05)   # ~20 fps; non influisce sulla precisione degli arrivi

    def stop(self) -> None:
        self._running = False
        self.wait()
