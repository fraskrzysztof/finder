import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QSlider, QTabWidget, QComboBox, QLineEdit, QSizePolicy,
    QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

import pyqtgraph as pg

class DemoUI(QWidget):
    def __init__(self):
        super().__init__()
        self.overlay = OverlayRenderer()
        self.plotter = plotter()
        self.tracker = tracker()

        self.setWindowTitle("Finder")
        self.resize(1200, 800)

        # === ELEMENTY UI ===

        self.label = QLabel("Witaj w prostym GUI!")
        self.label.setAlignment(Qt.AlignCenter)

        self.btn_ok = QPushButton("OK")
        self.btn_clear = QPushButton("Wyczyść")

        

        self.slider1 = QSlider(Qt.Horizontal)
        self.slider1.setRange(0, 255)
        self.slider1.setValue(50)
        self.slider1.valueChanged.connect(self.change_brightness)

        self.slider2 = QSlider(Qt.Horizontal)
        self.slider2.setRange(0, 255)
        self.slider2.setValue(50)
        self.slider2.valueChanged.connect(self.change_contrast)

        self.slider3 = QSlider(Qt.Horizontal)
        self.slider3.setRange(0, 255)
        self.slider3.setValue(50)
        self.slider3.valueChanged.connect(self.change_saturation)
        
        self.combo = QComboBox()
        self.combo.addItems(["640x480", "1280x720", "Opcja C"])

        self.manual_check = QCheckBox("manual")
        self.manual_check.setChecked(False)

        self.mark_check = QCheckBox("cross")
        self.mark_check.setChecked(True)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Wpisz coś...")

        # Label do wyświetlania obrazu z kamery
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        #self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.mousePressEvent = self.on_image_click



        # Kamera i timer
        self.cap = cv2.VideoCapture(3)  # 0 to domyślna kamera
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera)
        self.timer.start(1000/60)  


        # --- Tracking ---
        self.tracking_enabled = False
        self.roi_size = 200  # wielkość ROI (px)
        self.target_pos = None  # (x, y) klikniętej gwiazdy

        self.error_plot = pg.PlotWidget()
        self.error_plot.setTitle("Błąd śledzenia")
        self.error_plot.setLabel("left", "Błąd (px)")
        self.error_plot.setLabel("bottom", "Klatka")
        self.error_plot.showGrid(x=True, y=True)
        self.error_plot.setBackground((50, 50, 50))

        self.error_data = []  # lista do przechowywania wartości błędu


        # === UKŁADY ===
        main_layout = QHBoxLayout()
        interface_layout = QVBoxLayout()

        interface_layout.addWidget(self.label, stretch=0)
        interface_layout.addWidget(self.input, stretch=0)

        # guziki obok siebie
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_clear)
        interface_layout.addLayout(btn_row, stretch=0)

        interface_layout.addWidget(self.manual_check)
        interface_layout.addWidget(self.mark_check)

        interface_layout.addWidget(QLabel("brightness:"), stretch=0)
        interface_layout.addWidget(self.slider1, stretch=0)
        interface_layout.addWidget(QLabel("contrast:"), stretch=0)
        interface_layout.addWidget(self.slider2, stretch=0)
        interface_layout.addWidget(QLabel("saturation:"), stretch=0)
        interface_layout.addWidget(self.slider3, stretch=0)

        interface_layout.addWidget(QLabel("Lista rozwijana:"), stretch=0)
        interface_layout.addWidget(self.combo, stretch=0)
        interface_layout.addStretch()

        image_layout = QVBoxLayout()

        image_layout.addWidget(QLabel("Podgląd kamery:"), stretch=0)
        image_layout.addWidget(self.image_label, stretch=10)  # większość przestrzeni dla obrazu

        image_layout.addWidget(self.error_plot, stretch=3)


        main_layout.addLayout(interface_layout,stretch=0)
        main_layout.addLayout(image_layout,stretch=1)
        self.setLayout(main_layout)

        # === SYGNAŁY ===
        self.btn_ok.clicked.connect(self.on_ok)
        self.btn_clear.clicked.connect(self.on_clear)
        self.slider1.valueChanged.connect(self.on_slider_change)
        self.slider2.valueChanged.connect(self.on_slider_change)
        self.slider3.valueChanged.connect(self.on_slider_change)
        self.combo.currentTextChanged.connect(self.on_combo_change)
        self.manual_check.stateChanged.connect(self.manual_checkbox)

    # === OBSŁUGA ZDARZEŃ ===
    def on_ok(self):
        text = self.input.text()
        self.label.setText(f"Naciśnięto OK: {text}")

    def on_clear(self):
        self.input.clear()
        self.label.setText("Wyczyszczono")

    def on_slider_change(self, value):
        self.label.setText(f"Suwak: {value}")
    #WYLACZYC TRYBY AUTO KAMERY
    def change_brightness(self, value):
        v = value 
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, v)

    def change_contrast(self, value):
        v = value 
        self.cap.set(cv2.CAP_PROP_CONTRAST, v)

    def change_saturation(self, value):
        v = value 
        self.cap.set(cv2.CAP_PROP_SATURATION, v)

    def on_combo_change(self, text):
        self.label.setText(f"Wybrano: {text}")

    def manual_checkbox(self, state):
        if state == Qt.Checked:
            print("asd")
        else:
            print("asdasd")




    def on_image_click(self, event):
        if self.image_label.pixmap() is None:
            return

        x = int(event.position().x())
        y = int(event.position().y())

        pix = self.image_label.pixmap()
        pw = pix.width()
        ph = pix.height()

        lw = self.image_label.width()
        lh = self.image_label.height()

        # offset czarnych pasów przy KeepAspectRatio
        x_off = (lw - pw) // 2
        y_off = (lh - ph) // 2

        # sprawdzenie, czy kliknięto w obraz
        if not (x_off <= x <= x_off + pw and y_off <= y <= y_off + ph):
            return

        # przeliczenie do współrzędnych oryginalnej klatki
        fx = (x - x_off) * self.frame_w / pw
        fy = (y - y_off) * self.frame_h / ph

        self.target_pos = (int(fx), int(fy))
        self.tracking_enabled = True

        print("Wybrano punkt:", self.target_pos)

    

    def update_camera(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # oryginalny, kolorowy obraz
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # zapis wymiarów dla trackera
        self.frame_h, self.frame_w, _ = frame.shape

        # --- TRACKING (punkt 4) ---
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)  # osobna kopia grayscale


        centroid = self.tracker.track_in_roi(frame, gray, self.tracking_enabled, self.target_pos, self.roi_size)              # None albo (cx,cy)
        if centroid is not None:
            self.target_pos = centroid

        frame = self.overlay.apply_overlay(frame, centroid, self.roi_size, center_mark_enabled=self.mark_check.isChecked())
        self.plotter.plotter(frame, self.target_pos, centroid, self.error_data, self.error_plot)


        # --- KONWERSJA NA QPIXMAP I WYŚWIETLENIE ---
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        self.image_label.setPixmap(
            pix.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

class OverlayRenderer:
    def __init__(self):
        pass

    def draw_tracking_marker(self, frame, centroid):
        if centroid is None:
            return frame
        
        cx, cy = centroid
        cv2.drawMarker(
            frame,
            (cx, cy),
            (255, 0, 0),
            markerType=cv2.MARKER_CROSS,
            markerSize=20,
            thickness=2
        )
        return frame
    

    def draw_error_line(self, frame, centroid):
        if centroid is None:
            return frame
        
        h, w, _ = frame.shape
        cx, cy = centroid
        cv2.line(frame, (cx,cy), (w // 2, h //2), (0, 255, 255), 1)

        return frame
    
    def draw_center_mark(self, frame):
        h, w, _ = frame.shape
        cx, cy = w // 2, h // 2

        # gruby krzyż
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (120, 255, 0), 2)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (120, 255, 0), 2)

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

    
    def apply_overlay(self, frame, centroid, roi_size, center_mark_enabled=True):
        frame = self.draw_tracking_marker(frame, centroid)
        frame = self.draw_error_line(frame, centroid)
        frame = self.draw_roi_box(frame, centroid, roi_size)
    
        if center_mark_enabled:
            frame = self.draw_center_mark(frame)
        
        return frame

class tracker:
    def  __init__(self):
        pass
    
    
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

class plotter:
    def __init__(self):
        pass
    
    def plotter(self, frame, target_pos, centroid, error_data, error_plot):
        if target_pos is not None and centroid is not None:
            tx, ty = target_pos
            cx, cy = centroid
            h, w, _ = frame.shape
            error = ((cx - w//2)**2 + (cy - h//2)**2)**0.5
            error_data.append(error)

            if len(error_data) > 1000:
                error_data.pop(0)

            error_plot.plot(error_data, clear=True, pen='r')



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoUI()
    window.show()
    sys.exit(app.exec())
