import cv2
import numpy as np


class tracker:
    def __init__(self):
        self.last_threshold = None

    def track_in_roi(self, frame, gray, tracking_enabled, target_pos, roi_size):
        """
        frame  : BGR (nieużywany, ale zostawiony dla spójności API)
        gray   : obraz w skali szarości
        """

        if not tracking_enabled or target_pos is None:
            return None

        frame_h, frame_w = gray.shape
        tx, ty = target_pos
        s = roi_size // 2

        # granice ROI
        x1 = max(0, tx - s)
        y1 = max(0, ty - s)
        x2 = min(frame_w, tx + s)
        y2 = min(frame_h, ty + s)

        roi = gray[y1:y2, x1:x2]

        if roi.shape[0] < 10 or roi.shape[1] < 10:
            return None

        # threshold
        _, th = cv2.threshold(
            roi, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        self.last_threshold = th

        cnts, _ = cv2.findContours(
            th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not cnts:
            return None

        best = None
        best_dist = 1e12

        for c in cnts:
            M = cv2.moments(c)
            if M["m00"] == 0:
                continue

            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            gx = cx + x1
            gy = cy + y1

            d = (gx - tx) ** 2 + (gy - ty) ** 2
            if d < best_dist:
                best_dist = d
                best = (gx, gy)

        return best
