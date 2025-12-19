import cv2
import time
from PySide6.QtCore import Slot, Signal, QObject, Qt
from tracker.tracker import tracker
from overlay.overlayRenderer import OverlayRenderer


class CameraThread(QObject):
    frame_ready = Signal(object)              # frame z overlay
    threshold_ready = Signal(object)          # threshold ROI
    centroid_ready = Signal(tuple, float, float)  # centroid, err_x, err_y
    res_signal = Signal(int, int)

    def __init__(self, cam_index=0, width=1920, height=1080):
        super().__init__()

        self.running = False

        self.cap = cv2.VideoCapture(cam_index)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # logika wątku
        self.tracker = tracker()
        self.overlay = OverlayRenderer()

        # parametry z GUI
        self.tracking_enabled = False
        self.target_pos = None
        self.roi_size = 200
        self.arcsec = 1.0

        self.roi_mark_size = 20
        self.mark_type = cv2.MARKER_CROSS
        self.center_mark = True
        self.roi_mark = True

        self.res_signal.connect(self._change_resolution, Qt.DirectConnection)

    @Slot()
    def run(self):
        self.running = True

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # --- TRACKER (czysty obraz) ---
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            centroid = self.tracker.track_in_roi(
                frame,
                gray,
                self.tracking_enabled,
                self.target_pos,
                self.roi_size
            )

            # --- błąd kątowy ---
            error_x = error_y = 0.0
            if centroid is not None:
                self.target_pos = centroid   # <<< TO JEST KLUCZ
                h, w = gray.shape
                error_x = (centroid[0] - w // 2) * self.arcsec / 3600.0
                error_y = (h // 2 - centroid[1]) * self.arcsec / 3600.0
                self.centroid_ready.emit(centroid, error_x, error_y)
                


            # --- overlay ---
            overlay_frame = self.overlay.apply_overlay(
                frame.copy(),
                centroid,
                self.roi_size,
                self.roi_mark_size,
                self.mark_type,
                self.center_mark,
                self.roi_mark
            )

            # --- GUI ---
            self.frame_ready.emit(overlay_frame)

            self.threshold_ready.emit(
                self.tracker.last_threshold.copy()
                if self.tracker.last_threshold is not None
                else None
            )

            time.sleep(0.001)

    # ================= GUI → THREAD =================

    def set_tracking_params(self, enabled, target_pos, roi_size, arcsec):
        self.tracking_enabled = enabled
        self.target_pos = target_pos
        self.roi_size = roi_size
        self.arcsec = arcsec


    def set_roi_size(self, roi_size):
        self.roi_size = roi_size
    def set_overlay_params(self, roi_mark_size, mark_type, center_mark, roi_mark):
        self.roi_mark_size = roi_mark_size
        self.mark_type = mark_type
        self.center_mark = center_mark
        self.roi_mark = roi_mark

    def change_exposure(self, value):
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        self.cap.set(cv2.CAP_PROP_EXPOSURE, value)

    def change_brightness(self, value):
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, value)

    def change_contrast(self, value):
        self.cap.set(cv2.CAP_PROP_CONTRAST, value)

    def change_saturation(self, value):
        self.cap.set(cv2.CAP_PROP_SATURATION, value)

    @Slot(int, int)
    def _change_resolution(self, w, h):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    def stop(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()