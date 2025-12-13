import sys
import cv2
import time
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QSlider, QTabWidget, QComboBox, QLineEdit, QSizePolicy,
    QCheckBox, QSplitter, QFrame
)

import numpy as np
import serial
import serial.tools.list_ports

from PySide6.QtCore import Qt, QTimer, QThread, QObject, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

import pyqtgraph as pg
import glob

def detect_cameras():
    devices = glob.glob('/dev/video*')
    available = []
    for dev in devices:
        cap = cv2.VideoCapture(dev)
        if cap.isOpened():
            available.append(dev)
            cap.release()
    return available

class DemoUI(QWidget):
    def __init__(self):
        super().__init__()
        self.overlay = OverlayRenderer()
        self.plotter = plotter()
        self.tracker = tracker()
        self.serialMenager = serialMenager()
        self.cameraThread = cameraThread()

        self.setWindowTitle("StarFinder")
        self.resize(1200, 800)

        # ===================
        # LAYOUT INTERFACE
        # ===================




        # === ELEMENTY UI ===

        #tabs
        self.tab1 = QTabWidget()


        ####TRACKER TAB

        self.tracking_enabled = False
        self.roi_size = 200  # wielkość ROI (px)
        self.target_pos = None  # (x, y) klikniętej gwiazdy
        self.focal = 190
        self.pixel_s = 2.9
        self.arcsec = 206.265*(self.pixel_s/self.focal)
        self.brate = 115200
        self.port = None
        self.error_time = []
        self.start_time = time.time()  # punkt odniesienia

        self.btn_apply = QPushButton("apply")
        self.roi_input = QLineEdit()
        self.roi_input.setPlaceholderText("set ROI size")


        self.roi_label = QLabel(f"roi size: {self.roi_size}")

        self.roi_slider = QSlider(Qt.Horizontal)
        self.roi_slider.setRange(50, 400)
        self.roi_slider.setValue(200)
        self.roi_slider.valueChanged.connect(self.change_roi)


        self.pixel_size = QLineEdit()
        self.pixel_size.setPlaceholderText("set pixel size")

        self.focal_length = QLineEdit()
        self.focal_length.setPlaceholderText("set focal length")


        self.plot_timer = QTimer()
        self.plot_timer.setInterval(100)  # 10 Hz
        self.plot_timer.timeout.connect(self.update_error_plot)
        self.plot_timer.start()
        self.error_plot = pg.PlotWidget()
        self.error_plot.setTitle("tracking error")
        self.error_plot.setLabel("left", "ERROR [deg]")
        self.error_plot.setLabel("bottom", "TIME[min]")
        self.error_plot.showGrid(x=True, y=True)
        self.error_plot.setBackground((40, 40, 40))
        self.error_plot.addLegend(pen= 'w')  # <-- dodaje legendę
        self.error_plot.getAxis('left').enableAutoSIPrefix(False)

        self.error_data = []  # lista do przechowywania wartości błędu
        self.error_x_data = []
        self.error_y_data = []
        self.error_x = self.error_plot.plot(pen="r", name='x')
        self.error_y = self.error_plot.plot(pen="g", name='y')

        
        ####CAMERA SETTINGS TAB
        self.slider1 = QSlider(Qt.Horizontal)
        self.slider1.setRange(0, 2000)
        self.slider1.setValue(50)
        self.slider1.valueChanged.connect(self.change_exposure)
        self.exposure_val = 50
        self.exposure_label = QLabel(f"exposure: {self.exposure_val}")

        self.slider4 = QSlider(Qt.Horizontal)
        self.slider4.setRange(-127/2, 127/2)
        self.slider4.setValue(0)
        self.slider4.valueChanged.connect(self.change_brightness)
        self.brightness_val = 50
        self.brightness_label = QLabel(f"brightness: {self.brightness_val}")

        self.slider2 = QSlider(Qt.Horizontal)
        self.slider2.setRange(0, 50)
        self.slider2.setValue(25)
        self.slider2.valueChanged.connect(self.change_contrast)
        self.contrast_val = 50
        self.contrast_label = QLabel(f"contrast: {self.contrast_val}")

        self.slider3 = QSlider(Qt.Horizontal)
        self.slider3.setRange(0, 127)
        self.slider3.setValue(50)
        self.slider3.valueChanged.connect(self.change_saturation)
        self.saturation_val = 50
        self.saturation_label = QLabel(f"saturation: {self.saturation_val}")
        
        self.combo = QComboBox()
        self.combo.addItems(["choose resolution","1920x1080", "1280x720", "640x480"])

        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["choose camera"])

        
        cameras = detect_cameras()
        for cam in cameras:
            self.camera_combo.addItem(f"camera {cam}", cam)



        ####MAIN SETTINGS TAB
        self.manual_check = QCheckBox("manual")
        self.manual_check.setChecked(False)

        self.mark_check = QCheckBox("cross")
        self.mark_check.setChecked(True)

        self.roi_box_check = QCheckBox("ROI box")
        self.roi_box_check.setChecked(True)



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

        # # Kamera i timer
        # self.cap = cv2.VideoCapture(2)  # 0 to domyślna kamera
        # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        self.camera_thread = QThread()
        

        self.cameraThread.moveToThread(self.camera_thread)

        self.camera_thread.started.connect(self.cameraThread.run)
        self.cameraThread.frame_ready.connect(self.on_new_frame)

        self.camera_thread.start()




        self.serial_combo = QComboBox()
        self.serial_combo.clear()
        self.serial_combo.addItems(["select port"])

        self.baudrate = QLineEdit()
        self.baudrate.setText("115200")
        ports = self.serialMenager.detect_serial_ports()
        for device, desc in ports:
            self.serial_combo.addItem(f"{device}  ({desc})", device)



    #     # === UKŁADY ===

        # 1. Lewy panel - sterowanie (z ramką)
        self.left_frame = QFrame()
        self.left_frame.setMinimumWidth(300)  # np. 300 px
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



        tab_general_layout.addWidget(self.manual_check)
        tab_general_layout.addWidget(self.mark_check)
        tab_general_layout.addWidget(self.roi_box_check)

        tab_general_layout.addStretch()
        tab_general.setLayout(tab_general_layout)


        # ---------------- TAB 2: KAMERA ----------------
        tab_camera = QWidget()
        tab_camera_layout = QVBoxLayout()

        tab_camera_layout.addWidget(QLabel("camera:"))
        tab_camera_layout.addWidget(self.camera_combo)

        tab_camera_layout.addWidget(QLabel("Resolution:"))
        tab_camera_layout.addWidget(self.combo)

        tab_camera_layout.addWidget(self.exposure_label)
        tab_camera_layout.addWidget(self.slider1)

        tab_camera_layout.addWidget(self.brightness_label)
        tab_camera_layout.addWidget(self.slider4)

        tab_camera_layout.addWidget(self.contrast_label)
        tab_camera_layout.addWidget(self.slider2)

        tab_camera_layout.addWidget(self.saturation_label)
        tab_camera_layout.addWidget(self.slider3)

        tab_camera_layout.addStretch()
        tab_camera.setLayout(tab_camera_layout)


        # ---------------- TAB 3: TRACKING ----------------
        tab_tracking = QWidget()
        tab_tracking_layout = QVBoxLayout()
        tab_tracking_layout.addWidget(QLabel("set region of interest size"))

        tab_tracking_layout.addWidget(self.roi_label)
        tab_tracking_layout.addWidget(self.roi_slider)

        tab_tracking_layout.addWidget(QLabel("Set pixel size [um]:"))
        tab_tracking_layout.addWidget(self.pixel_size)
        tab_tracking_layout.addWidget(QLabel("Set focal length [mm]:"))
        tab_tracking_layout.addWidget(self.focal_length)
        # tu później można dodać suwak ROI, opcje trackera itd.
        tab_tracking_layout.addWidget(self.btn_apply)

        tab_tracking_layout.addStretch()
        tab_tracking.setLayout(tab_tracking_layout)


        # Dodanie zakładek do widgetu tabs
        self.tabs.addTab(tab_general, "Settings")
        self.tabs.addTab(tab_camera, "Camera")
        self.tabs.addTab(tab_tracking, "Tracking")

        ####COM TAB 

        self.com_frame = QFrame()
        self.com_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.com_frame.setLineWidth(2)

        self.com_tabs = QTabWidget()
        com_tab = QWidget()
        com_tab_layout = QVBoxLayout()
        com_tab_layout.addWidget(QLabel("Select port:"))
        com_tab_layout.addWidget(self.serial_combo)
        com_tab_layout.addWidget(QLabel("baudrate:"))
        com_tab_layout.addWidget(self.baudrate)
        com_buttons =QHBoxLayout()
        self.btn_open = QPushButton("open")
        self.btn_close = QPushButton("close")
        com_buttons.addWidget(self.btn_open)
        com_buttons.addWidget(self.btn_close)
        com_tab_layout.addLayout(com_buttons)
        com_tab_layout.addStretch()
        com_tab.setLayout(com_tab_layout)
        self.com_tabs.addTab(com_tab, "com tab")


        # Dodanie QTabWidget do lewego layoutu
        left_layout.addWidget(self.tabs)
        left_layout.addWidget(self.com_tabs)
        #left_layout.addStretch()

        

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
        self.btn_apply.clicked.connect(self.on_apply)
        self.combo.currentTextChanged.connect(self.change_res)
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        self.roi_slider.valueChanged.connect(self.change_roi)
        self.serial_combo.currentTextChanged.connect(self.change_port)
        self.btn_open.clicked.connect(self.on_open)
        self.btn_close.clicked.connect(self.on_close)

    # === OBSŁUGA ZDARZEŃ ===

    def update_error_plot(self):
        if not self.error_time:
            return
        self.error_x.setData(self.error_time, self.error_x_data)
        self.error_y.setData(self.error_time, self.error_y_data)

        self.error_plot.setXRange(
            max(0, self.error_time[-1]-20),
            self.error_time[-1]
        )

    def change_port(self, text):
        sel = self.serial_combo.currentData()
        self.port = sel
        print(self.port)

    def baudrate_change(self, value):
        self.brate = value
        print(self.brate)
    def on_apply(self):
        self.focal = int(self.focal_length.text())
        self.pixel_s = float(self.pixel_size.text())

        self.arcsec = 206.265*(self.pixel_s/self.focal)

    def on_open(self):
        text = int(self.baudrate.text())
        self.serialMenager.open_serial_port(self.port,text)

    def on_close(self):
        self.serialMenager.close_serial_port()
        
    def change_roi(self, value):
        self.roi_size = value 
        self.roi_label.setText(f"roi size: {self.roi_size}")  # Aktualizuj etykietę

        self.roi_label.setText(f"roi size: {self.roi_size}")  # Aktualizuj etykietę
        
    #WYLACZYC TRYBY AUTO KAMERY
    def change_exposure(self, value):
        v = value 
        self.cameraThread.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # wyłącz auto
        self.cameraThread.cap.set(cv2.CAP_PROP_EXPOSURE, v) 
        self.exposure_label.setText(f"exposure: {v}")  # Aktualizuj etykietę 

    def change_brightness(self, value):
        v = value 
        self.cameraThread.cap.set(cv2.CAP_PROP_BRIGHTNESS, v)
        self.brightness_label.setText(f"brightness: {v}")  # Aktualizuj etykietę 

    def change_contrast(self, value):
        v = value 
        self.cameraThread.cap.set(cv2.CAP_PROP_CONTRAST, v)
        self.contrast_label.setText(f"contrast: {v}")  # Aktualizuj etykietę

    def change_saturation(self, value):
        v = value 
        self.cameraThread.cap.set(cv2.CAP_PROP_SATURATION, v)
        self.saturation_label.setText(f"saturation: {v}")  # Aktualizuj etykietę


    def manual_checkbox(self, state):
        # print("state:", state)
        # if state == 2:
        #     self.cap.set(cv2.CAP_PROP_AUTO_WB, 0) 
        #     self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 128) 
        #     self.cap.set(cv2.CAP_PROP_CONTRAST, 128)
        #     self.cap.set(cv2.CAP_PROP_SATURATION, 128)
        #     self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
        # else:
        #     self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 0) 
        #     self.cap.set(cv2.CAP_PROP_CONTRAST, 0)
        #     self.cap.set(cv2.CAP_PROP_SATURATION, 0)
        #     self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        pass
       

    def change_res(self, text):
        if text == "choose resolution":
            return
        w, h = map(int, text.split('x'))

        # zatrzymaj wątek
        self.cameraThread.stop()
        self.camera_thread.quit()
        self.camera_thread.wait()
        
        # stwórz nowy obiekt VideoCapture z nową rozdzielczością
        cam_index = self.camera_combo.currentData()
        self.cameraThread = cameraThread(cam_index, width=w, height=h)
        
        # nowy wątek
        self.camera_thread = QThread()
        self.cameraThread.moveToThread(self.camera_thread)
        self.cameraThread.frame_ready.connect(self.on_new_frame)
        self.camera_thread.started.connect(self.cameraThread.run)
        self.camera_thread.start()
       

    def change_camera(self, index):
        if index == 0:
            return

        # zatrzymaj stary wątek
        self.cameraThread.stop()
        self.camera_thread.quit()
        self.camera_thread.wait()
        del self.cameraThread

        # nowy wątek
        self.camera_thread = QThread()
        self.cameraThread = cameraThread(cam_index=self.camera_combo.currentData())
        self.cameraThread.moveToThread(self.camera_thread)
        self.camera_thread.started.connect(self.cameraThread.run)
        self.cameraThread.frame_ready.connect(self.on_new_frame)
        self.camera_thread.start()




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

    def closeEvent(self, event):
        self.cameraThread.stop()
        self.camera_thread.quit()
        self.camera_thread.wait()
        event.accept()

    @Slot(object)
    def on_new_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        self.frame_h, self.frame_w, _ = frame.shape

        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        centroid = self.tracker.track_in_roi(
            frame, gray, self.tracking_enabled,
            self.target_pos, self.roi_size
        )

        if centroid is not None:
            self.target_pos = centroid
            cx, cy = centroid
            h, w, _ = frame.shape
            error_x = (cx - w//2) * self.arcsec / 3600
            error_y = (h//2 - cy) * self.arcsec / 3600
            t = time.time() - self.start_time

            self.error_time.append(t)
            self.error_x_data.append(error_x)
            self.error_y_data.append(error_y)

            # ograniczamy do ostatnich 20 sekund
            while self.error_time and t - self.error_time[0] > 20:
                self.error_time.pop(0)
                self.error_x_data.pop(0)
                self.error_y_data.pop(0)

            self.plotter.update(
                self.error_x,
                self.error_y,
                self.error_time,
                self.error_x_data,
                self.error_y_data
            )

        frame = self.overlay.apply_overlay(
            frame, centroid, self.roi_size,
            self.mark_check.isChecked(),
            self.roi_box_check.isChecked()
            )

        
    # --- wykres ---
        

        if self.tracker.last_threshold is not None:
            th = self.tracker.last_threshold

            th_rgb = cv2.cvtColor(th, cv2.COLOR_GRAY2RGB)
            th_rgb = np.ascontiguousarray(th_rgb)

            rh, rw, _ = th_rgb.shape
            bytes_per_line = 3 * rw

            qimg_roi = QImage(
                th_rgb.data,
                rw,
                rh,
                bytes_per_line,
                QImage.Format_RGB888
            )

            qimg_roi = qimg_roi.copy()  # bardzo ważne!

            pix = QPixmap.fromImage(qimg_roi)

            self.threshold_image.setPixmap(
                pix.scaled(
                    self.threshold_image.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        else:
            self.threshold_image.setPixmap(QPixmap())

        # QImage
        h, w, ch = frame.shape
        qimg = QImage(frame.data, w, h, ch*w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        self.image_label.setPixmap(
            pix.scaled(
                self.image_label.size(),
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
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (120, 255, 0), 3)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (120, 255, 0), 3)

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

    
    def apply_overlay(self, frame, centroid, roi_size, center_mark_enabled=True, roi_mark_enabled=True):
        frame = self.draw_tracking_marker(frame, centroid)
        frame = self.draw_error_line(frame, centroid)
    
        if center_mark_enabled:
            frame = self.draw_center_mark(frame)
            

        if roi_mark_enabled:
            frame = self.draw_roi_box(frame, centroid, roi_size)
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
    def error_calc(self, frame, centroid, arcs):
        h, w, _ = frame.shape
        cx, cy = centroid
        error = ((cx - w//2)**2 + (cy - h//2)**2)**0.5
        error_x = cx - w//2
        error_y = h//2 - cy
        error_x = (error_x*arcs)/3600
        error_y = (error_y*arcs)/3600

        return error_x, error_y

class plotter:
    def __init__(self):
        pass
        # self.error_time = []
        # self.start_time = time.time()  # punkt odniesienia

    
    def update(self, curve_x, curve_y, error_time, error_x_data, error_y_data):
        curve_x.setData(error_time, error_x_data)
        curve_y.setData(error_time, error_y_data)

class serialMenager:
    def __init__(self):
        
        self.ser = None


    def detect_serial_ports(self):

        ports = serial.tools.list_ports.comports()
        available = []

        accepted_keywords = [
            "USB", "UART", "ACM", "CH340", "CH910",
            "CP210", "FTDI", "FT232", "Arduino",
            "STM", "ESP", "Silicon Labs"
        ]

        for port in ports:
            desc = port.description.upper()
            if any(keyword in desc for keyword in accepted_keywords):
                available.append((port.device, port.description))

        return available

    def open_serial_port(self, port, brate=115200):
        if self.ser is not None:
            self.ser.close()
       
        try:
            self.ser = serial.Serial(port, baudrate = brate, timeout = 1)
            print("port opened")
            return True 
        except Exception as e:
            print(f"[SerialManager] Error opening port: {e}")
            self.ser = None
            return False
        

    def close_serial_port(self):
        if self.ser and not self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                print(f"[SerialMenager] Error closing port: {e}")
        self.ser = None

    def serial_send(self, data_a, data_b, precision = 3):
        if not self.ser or not self.ser.is_open:
            return False
        
        try:
            data = f"{data_a:.{precision}f} {data_b:.{precision}f}\n"
            data = data.encode('utf-8')
            self.ser.write(data)
            response = self.ser.readline().decode('utf-8').strip()
            print("Odpowiedź z ESP32:", response)
            return True
        except Exception as e:
            print(f"[SerialMenager] Error sending data: {e}")
            return False


class cameraThread(QObject):
    frame_ready = Signal(object)
    def __init__(self, cam_index=0, width=1920, height=1080):
        super().__init__()
        self.running = False
        self.cap = cv2.VideoCapture(cam_index)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    @Slot()
    def run(self):
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_ready.emit(frame)
            time.sleep(0.001)  # NIE busy-loop

    def stop(self):
        self.running = False
        self.cap.release()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoUI()
    window.show()
    sys.exit(app.exec())





## arcsec/pixel = 206.265*(pixel size (2.9um)/focal length)