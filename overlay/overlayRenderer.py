import cv2



class OverlayRenderer:
    def __init__(self):
        pass

    def draw_tracking_marker(self, frame, centroid, size, marker):
        if centroid is None:
            return frame
        
        cx, cy = centroid
        cv2.drawMarker(
            frame,
            (cx, cy),
            (0, 0, 255),
            markerType=marker,
            markerSize=size,
            thickness=2
        )

 
        return frame
    

    def draw_error_line(self, frame, centroid):
        if centroid is None:
            return frame
        
        h, w, _ = frame.shape
        cx, cy = centroid
        cv2.line(frame, (cx,cy), (w // 2, h //2), (255, 255, 0), 1)

        return frame
    
    def draw_center_mark(self, frame):
        h, w, _ = frame.shape
        cx, cy = w // 2, h // 2

        cv2.circle(frame, (cx, cy), radius=40, color=(0, 255, 0), thickness=2)
        # cv2.drawMarker(
        #     frame,
        #     (cx, cy),
        #     (0, 255, 0),
        #     markerType=cv2.MARKER_DIAMOND,
        #     markerSize=40,
        #     thickness=2
        # )

        # cienkie pełne linie
        cv2.line(frame, (0, cy), (w, cy), (120, 255, 0), 1)
        cv2.line(frame, (cx, 0), (cx, h), (120, 255, 0), 1)

        return frame
    
    def draw_roi_box(self, frame, centroid, roi_size):
        if centroid is None:
            return frame
        h, w, _ = frame.shape
        cx, cy = centroid
        cv2. rectangle(frame, (cx-roi_size//2, cy+roi_size//2), (cx+roi_size//2, cy-roi_size//2), (0,255,0), 1)

        return frame

    
    def apply_overlay(self, frame, centroid, roi_size, marker_size, mark_type, center_mark_enabled=True, roi_mark_enabled=True):
        frame = self.draw_tracking_marker(frame, centroid, marker_size, mark_type)
        frame = self.draw_error_line(frame, centroid)
    
        if center_mark_enabled:
            frame = self.draw_center_mark(frame)
            

        if roi_mark_enabled:
            frame = self.draw_roi_box(frame, centroid, roi_size)
        return frame
