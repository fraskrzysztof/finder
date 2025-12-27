import serial
import serial.tools.list_ports
from PySide6.QtCore import Slot, Signal, QObject

class serialMenager(QObject):
    open_port = Signal(str, int)
    close_port = Signal()
    send_shutter = Signal(str)
    send_error = Signal(float, float)
    status = Signal(str)

    def __init__(self):
        super().__init__()
        self.ser = None

        self.open_port.connect(self._open_port)
        self.close_port.connect(self._close_port)
        self.send_shutter.connect(self._send_shutter)
        self.send_error.connect(self._send_error)

    @Slot(str, int)
    def _open_port(self, port, baud):
        self._close_port()
        try:
            self.ser = serial.Serial(port, baud, timeout=0)
            self.status.emit(f"Opened {port}")
        except Exception as e:
            self.ser = None
            self.status.emit(f"Open failed: {e}")

    @Slot()
    def _close_port(self):
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
            self.ser = None
            self.status.emit("Port closed")

    def _write(self, data):
        if not self.ser or not self.ser.is_open:
            return
        try:
            self.ser.write(data.encode())
            self.ser.flush()
        except Exception as e:
            self.status.emit(f"Write error: {e}")

    @Slot(str)
    def _send_shutter(self, cmd):
        self._write(cmd)

    @Slot(float, float)
    def _send_error(self, a, b):
        self._write(f"{a:.3f} {b:.3f}\n")
