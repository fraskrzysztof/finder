import cv2


class tracker:
    def  __init__(self):
        pass
    
        self.last_threshold = None
    
    def track_in_roi(self, frame, gray, tracking_enabled, target_pos, roi_size):
        if not tracking_enabled or target_pos is None:
            return None
        frame_h, frame_w, _ = frame.shape
        tx, ty = target_pos
        s = roi_size // 2

        # wycinamy ROI
        x1 = max(0, tx - s)
        y1 = max(0, ty - s)
        x2 = min(frame_w, tx + s)
        y2 = min(frame_h, ty + s)

        roi = gray[y1:y2, x1:x2]

        
        _, th = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        self.last_threshold = th
        
        cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not cnts:
            return None

        # znajdź kontur najbliższy poprzedniej pozycji
        best = None
        best_dist = 1e12

        for c in cnts:
            M = cv2.moments(c)
            if M["m00"] == 0:
                continue

            cx = int(M["m10"]/M["m00"])
            cy = int(M["m01"]/M["m00"])

            # przesuwamy centroid o offset ROI → koordynaty globalne
            gx = cx + x1
            gy = cy + y1

            d = (gx - tx)**2 + (gy - ty)**2

            if d < best_dist:
                best_dist = d
                best = (gx, gy)

        return best
    def error_calc(self, frame, centroid, arcs):
        h, w, _ = frame.shape
        cx, cy = centroid
        error = ((cx - w//2)**2 + (cy - h//2)**2)**0.5
        error_x = cx - w//2
        error_y = h//2 - cy
        error_x = (error_x*arcs)/3600
        error_y = (error_y*arcs)/3600

        return error_x, error_y