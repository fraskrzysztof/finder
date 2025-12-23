import time
from PySide6.QtCore import QObject, Qt, Slot, Signal
from serialMenager.serialMenager import serialMenager



class shutterThread(QObject):
    start_data = Signal(int, float, float)
    progress = Signal(int, float, float)
    finished = Signal()


   
    def __init__(self):
        super().__init__()
        self._running = False
        self.start_data.connect(self.start)
        self.serialMenager = serialMenager()

    @Slot(int, float, float)
    def start(self, frames, expTime, rlsFreq):
        print(frames, expTime, rlsFreq)
        self._running = True
        start_time = time.time()
        current_frames = 0
        predicted_time = frames*rlsFreq
        while self._running:
            now = time.time()
            elapsed = now - start_time
            remaining = predicted_time - elapsed

            self.serialMenager.serial_send_mode(f"shutter {expTime}\n")

            current_frames += 1
            self.progress.emit(current_frames, round(elapsed, 2), round(remaining, 2))

            if current_frames >= frames:
                break
            
            time.sleep(rlsFreq)

        self.finished.emit()


    def stop(self):
        print("remote shutter stopped")
        return 0