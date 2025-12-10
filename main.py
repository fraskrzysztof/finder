import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QSlider, QTabWidget, QComboBox, QLineEdit, QSizePolicy,
    QCheckBox, QSplitter, QFrame
)

import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

import pyqtgraph as pg

class DemoUI(QWidget):
    def __init__(self):
        super().__init__()
        self.overlay = OverlayRenderer()
        self.plotter = plotter()
        self.tracker = tracker()

        self.setWindowTitle("StarFinder")
        self.resize(1200, 800)

        # === ELEMENTY UI ===

        #tabs
        self.tab1 = QTabWidget()

        self.label = QLabel("StarFinder")
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

        #clicking
        self.image_label.mousePressEvent = self.on_image_click

        self.threshold_image = QLabel()
        self.threshold_image.setAlignment(Qt.AlignCenter)
        self.threshold_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        self.error_x_data = []
        self.error_y_data = []
        self.error_x = self.error_plot.plot(pen="r")
        self.error_y = self.error_plot.plot(pen="g")

    #     # === UKŁADY ===

# 1. Lewy panel - sterowanie (z ramką)
        # self.left_frame = QFrame()
        # self.left_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        # self.left_frame.setLineWidth(4)
       
       
        # left_layout = QVBoxLayout()
        # left_layout.addWidget(self.label, stretch=0)
        # left_layout.addWidget(self.input, stretch=0)

        # btn_row = QHBoxLayout()
        # btn_row.addWidget(self.btn_ok)
        # btn_row.addWidget(self.btn_clear)

        # left_layout.addLayout(btn_row, stretch=0)
        # left_layout.addWidget(self.manual_check)
        # left_layout.addWidget(self.mark_check)
        # left_layout.addWidget(QLabel("brightness:"), stretch=0)
        # left_layout.addWidget(self.slider1, stretch=0)
        # left_layout.addWidget(QLabel("contrast:"), stretch=0)
        # left_layout.addWidget(self.slider2, stretch=0)
        # left_layout.addWidget(QLabel("saturation:"), stretch=0)
        # left_layout.addWidget(self.slider3, stretch=0)
        # left_layout.addWidget(QLabel("Lista rozwijana:"), stretch=0)
        # left_layout.addWidget(self.combo, stretch=0)
        # left_layout.addStretch()

        # self.left_frame.setLayout(left_layout)
        # 1. Lewy panel - sterowanie (z ramką)
        self.left_frame = QFrame()
        self.left_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.left_frame.setLineWidth(4)

        left_layout = QVBoxLayout()

        # ===============================================
        #                 TABS
        # ===============================================
        self.tabs = QTabWidget()

        # ---------------- TAB 1: USTAWIENIA ----------------
        tab_general = QWidget()
        tab_general_layout = QVBoxLayout()

        tab_general_layout.addWidget(self.label)
        tab_general_layout.addWidget(self.input)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_clear)
        tab_general_layout.addLayout(btn_row)

        tab_general_layout.addWidget(self.manual_check)
        tab_general_layout.addWidget(self.mark_check)

        tab_general_layout.addStretch()
        tab_general.setLayout(tab_general_layout)


        # ---------------- TAB 2: KAMERA ----------------
        tab_camera = QWidget()
        tab_camera_layout = QVBoxLayout()

        tab_camera_layout.addWidget(QLabel("Brightness"))
        tab_camera_layout.addWidget(self.slider1)

        tab_camera_layout.addWidget(QLabel("Contrast"))
        tab_camera_layout.addWidget(self.slider2)

        tab_camera_layout.addWidget(QLabel("Saturation"))
        tab_camera_layout.addWidget(self.slider3)

        tab_camera_layout.addWidget(QLabel("Rozdzielczość"))
        tab_camera_layout.addWidget(self.combo)

        tab_camera_layout.addStretch()
        tab_camera.setLayout(tab_camera_layout)


        # ---------------- TAB 3: TRACKING ----------------
        tab_tracking = QWidget()
        tab_tracking_layout = QVBoxLayout()

        tab_tracking_layout.addWidget(QLabel("Tracking:"))
        tab_tracking_layout.addWidget(QLabel("Kliknij na obraz, aby wybrać gwiazdę"))

        # tu później można dodać suwak ROI, opcje trackera itd.

        tab_tracking_layout.addStretch()
        tab_tracking.setLayout(tab_tracking_layout)


        # Dodanie zakładek do widgetu tabs
        self.tabs.addTab(tab_general, "Ustawienia")
        self.tabs.addTab(tab_camera, "Kamera")
        self.tabs.addTab(tab_tracking, "Tracking")


        # Dodanie QTabWidget do lewego layoutu
        left_layout.addWidget(self.tabs)
        left_layout.addStretch()

        self.left_frame.setLayout(left_layout)


        # 2. Prawy panel - obraz i wykresy (z ramką)
        self.right_frame = QFrame()
        self.right_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.right_frame.setLineWidth(4)
      
        right_layout = QVBoxLayout()


        self.camera_frame = QFrame()
        self.camera_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.camera_frame.setLineWidth(2)
        camera_layout = QVBoxLayout()
        camera_layout.addWidget(self.image_label, stretch=10)
        self.camera_frame.setLayout(camera_layout)

        right_layout.addWidget(self.camera_frame, stretch=7)

        self.bottom_frame = QFrame()
        self.bottom_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.bottom_frame.setLineWidth(2)

        bottom_layout = QHBoxLayout()

        # Ramka na wykres
        self.plot_frame = QFrame()
        self.plot_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.plot_frame.setLineWidth(2)
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.error_plot)
        self.plot_frame.setLayout(plot_layout)

        # Ramka na obraz threshold
        self.threshold_frame = QFrame()
        self.threshold_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.threshold_frame.setLineWidth(2)
        threshold_layout = QVBoxLayout()
        threshold_layout.addWidget(self.threshold_image)
        self.threshold_frame.setLayout(threshold_layout)

        # Dodanie obu ramek do głównego bottom_layout
        bottom_layout.addWidget(self.plot_frame, stretch=3)
        bottom_layout.addWidget(self.threshold_frame, stretch=1)

        self.bottom_frame.setLayout(bottom_layout)

        right_layout.addWidget(self.bottom_frame, stretch=3)

        self.right_frame.setLayout(right_layout)

        # 3. Główny layout z dwoma ramkami obok siebie
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.left_frame, stretch=1)
        main_layout.addWidget(self.right_frame, stretch=4)
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
        self.plotter.plotter(frame, self.target_pos, centroid, self.error_data, self.error_x_data, self.error_y_data, self.error_x, self.error_y)


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

        if self.tracker.last_threshold is not None:
            th = self.tracker.last_threshold

            th_rgb = cv2.cvtColor(th, cv2. COLOR_GRAY2RGB)
            th_rgb = np.ascontiguousarray(th_rgb)
            rh, rw, _ = th_rgb.shape
            bytes_per_line = 3 * rw
            qimg_roi = QImage(th_rgb.data, rw, rh, bytes_per_line, QImage.Format_RGB888)
            qimg_roi = qimg_roi.copy()
            pix = QPixmap.fromImage(qimg_roi)

            self.threshold_image.setPixmap(
                pix.scaled(
                    self.threshold_image.width(),
                    self.threshold_image.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        else:
            self.threshold_image.setText("brak ROI")
            self.threshold_image.setPixmap(QPixmap())

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

class plotter:
    def __init__(self):
        pass

    
    def plotter(self, frame, target_pos, centroid, error_data, error_x_data, error_y_data, curve_x, curve_y):
        if target_pos is not None and centroid is not None:
            tx, ty = target_pos
            cx, cy = centroid
            h, w, _ = frame.shape
            error = ((cx - w//2)**2 + (cy - h//2)**2)**0.5
            error_x = cx - w//2
            error_y = h//2 - cy
            error_data.append(error)
            error_x_data.append(error_x)
            error_y_data.append(error_y)

            if len(error_data) > 100:
                error_data.pop(0)
                error_y_data.pop(0)
                error_x_data.pop(0)

            curve_x.setData(error_x_data)
            curve_y.setData(error_y_data)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoUI()
    window.show()
    sys.exit(app.exec())
