import sys
import cv2
import time
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QSlider, QTabWidget, QComboBox, QLineEdit, QSizePolicy,
    QCheckBox, QFrame
)

import numpy as np


from PySide6.QtCore import Qt, QTimer, QThread, Slot
from PySide6.QtGui import QImage, QPixmap

import pyqtgraph as pg
import glob
from overlay.overlayRenderer import OverlayRenderer
from serialMenager.serialMenager import serialMenager
from tracker.tracker import tracker
from plotter.plotter import plotter
from cameraThread.cameraThread import CameraThread

def detect_cameras():
    devices = glob.glob('/dev/video*')
    available = []
    for dev in devices:
        cap = cv2.VideoCapture(dev)
        if cap.isOpened():
            available.append(dev)
            cap.release()
    return available

class main(QWidget):
    def __init__(self):
        super().__init__()

        # ===================
        # CLASS INIT
        # ===================

        self.overlay = OverlayRenderer()
        self.plotter = plotter()
        self.tracker = tracker()
        self.serialMenager = serialMenager()
        self.cameraThread =  CameraThread()

        # ===================
        # WINDOW SETTINGS
        # ===================

        self.setWindowTitle("StarFinder")
        self.resize(1200, 800)

        # ===================
        # VARIABLES/ FLAGS INIT
        # ===================

        self.tracking_enabled = False
        self.roi_size = 200 
        self.target_pos = None 
        self.focal = 190
        self.pixel_s = 2.9
        self.arcsec = 206.265*(self.pixel_s/self.focal)
        self.brate = 115200
        self.port = None
        self.error_time = []
        self.start_time = time.time() 
        self.error_data = []  
        self.error_x_data = []
        self.error_y_data = []

        # ===========================================================
        # ===================== INTERFACE ===========================
        # ===========================================================



        self.left_frame = QFrame()
        self.left_frame.setMinimumWidth(300)  # np. 300 px
        self.left_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.left_frame.setLineWidth(4)

        left_layout = QVBoxLayout()

        self.tabs = QTabWidget()

        self.tab1 = QTabWidget()


        ####TRACKER TAB

        
        

        self.btn_apply = QPushButton("apply")
        self.roi_label = QLabel(f"roi size: {self.roi_size}")
        self.roi_slider = QSlider(Qt.Horizontal)
        self.roi_slider.setRange(50, 400)
        self.roi_slider.setValue(200)
        self.roi_slider.valueChanged.connect(self.change_roi)


        self.pixel_size = QLineEdit()
        self.pixel_size.setPlaceholderText("set pixel size")

        self.focal_length = QLineEdit()
        self.focal_length.setPlaceholderText("set focal length")
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
        tab_tracking_layout.addWidget(self.btn_apply)

        tab_tracking_layout.addStretch()
        tab_tracking.setLayout(tab_tracking_layout)
        




        ####CAMERA SETTINGS TAB
        self.slider1 = QSlider(Qt.Horizontal)
        self.slider1.setRange(0, 5000)
        self.slider1.setValue(0)
        self.slider1.valueChanged.connect(self.change_exposure)
        self.exposure_val = 50
        self.exposure_label = QLabel(f"exposure:    AUTO")

        self.slider4 = QSlider(Qt.Horizontal)
        self.slider4.setRange(-127/2, 127/2)
        self.slider4.setValue(-127/2)
        self.slider4.valueChanged.connect(self.change_brightness)
        self.brightness_val = 50
        self.brightness_label = QLabel(f"brightness: AUTO")

        self.slider2 = QSlider(Qt.Horizontal)
        self.slider2.setRange(0, 50)
        self.slider2.setValue(0)
        self.slider2.valueChanged.connect(self.change_contrast)
        self.contrast_val = 50
        self.contrast_label = QLabel(f"contrast: AUTO")

        self.slider3 = QSlider(Qt.Horizontal)
        self.slider3.setRange(0, 127)
        self.slider3.setValue(0)
        self.slider3.valueChanged.connect(self.change_saturation)
        self.saturation_val = 50
        self.saturation_label = QLabel(f"saturation: AUTO")
        
        self.combo = QComboBox()
        self.combo.addItems(["choose resolution","1920x1080", "1280x720", "640x480"])

        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["choose camera"])

        # ---------------- TAB 2: KAMERA ----------------
        tab_camera = QWidget()
        tab_camera_layout = QVBoxLayout()

        tab_camera_layout.addWidget(QLabel("camera:"))
        camera_combo_layout = QHBoxLayout()
        self.btn_ref_camera = QPushButton("refresh")
        camera_combo_layout.addWidget(self.camera_combo, stretch=2)
        camera_combo_layout.addWidget(self.btn_ref_camera, stretch=1)
        tab_camera_layout.addLayout(camera_combo_layout)

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

        
        cameras = detect_cameras()
        for cam in cameras:
            self.camera_combo.addItem(f"{cam}", cam)


        ####MAIN SETTINGS TAB

        self.mark_check = QCheckBox("center mark")
        self.mark_check.setChecked(True)

        self.roi_mark_combo = QComboBox()
        self.roi_mark_combo.clear()
        self.roi_mark_combo.addItem("cross", cv2.MARKER_CROSS)
        self.roi_mark_combo.addItem("diamond", cv2.MARKER_DIAMOND)
        self.roi_mark_combo.addItem("star", cv2.MARKER_STAR)
        self.roi_mark_combo.addItem("square", cv2.MARKER_SQUARE)
        self.roi_mark_combo.addItem("tilted cross", cv2.MARKER_TILTED_CROSS)
        self.roi_mark_combo.addItem("triangle down", cv2.MARKER_TRIANGLE_DOWN)
        self.roi_mark_combo.addItem("triangle up", cv2.MARKER_TRIANGLE_UP)

        self.roi_box_check = QCheckBox("ROI box")
        self.roi_box_check.setChecked(True)

        self.slider_roi_mark_size = QSlider(Qt.Horizontal)
        self.slider_roi_mark_size.setRange(10, 50)
        self.slider_roi_mark_size.setValue(20)
        self.slider_roi_mark_size.valueChanged.connect(self.change_roi_mark_size)
        self.roi_mark_size = 20
        self.roi_mark_size_label = QLabel(f"ROI mark size: {self.roi_mark_size}")

        # ---------------- TAB 1: USTAWIENIA ----------------

        tab_general = QWidget()
        tab_general_layout = QVBoxLayout()
        tab_general_layout.addWidget(QLabel("TRACKING MARK SETTINGS"))
        roi_settings_layout = QHBoxLayout()
        roi_settings_layout.addWidget(self.roi_mark_combo, stretch = 2)
        roi_settings_layout.addWidget(self.roi_box_check, stretch = 0)
        tab_general_layout.addLayout(roi_settings_layout)
        tab_general_layout.addWidget(self.roi_mark_size_label)
        tab_general_layout.addWidget(self.slider_roi_mark_size)
        self.slider_roi_mark_size.valueChanged.connect(self.change_roi_mark_size)
        tab_general_layout.addSpacing(20)
        tab_general_layout.addWidget(self.mark_check)
        tab_general_layout.addStretch()
        tab_general.setLayout(tab_general_layout)

        self.tabs.addTab(tab_camera, "Sensor")
        self.tabs.addTab(tab_tracking, "Tracking")
        self.tabs.addTab(tab_general, "GUI Settings")
        ####COM TAB

        self.serial_combo = QComboBox()
        self.serial_combo.clear()
        self.serial_combo.addItems(["select port"])

        self.baudrate = QLineEdit()
        self.baudrate.setText("115200")
        ports = self.serialMenager.detect_serial_ports()
        for device, desc in ports:
            self.serial_combo.addItem(f"{device}  ({desc})", device)

        ####COM TAB 

        self.com_frame = QFrame()
        self.com_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.com_frame.setLineWidth(2)

        self.com_tabs = QTabWidget()
        com_tab = QWidget()
        com_tab_layout = QVBoxLayout()
        com_tab_layout.addWidget(QLabel("Select port:"))
        serial_port_layout = QHBoxLayout()
        serial_port_layout.addWidget(self.serial_combo, stretch= 2)
        self.btn_ref_ports = QPushButton("refresh")
        serial_port_layout.addWidget(self.btn_ref_ports, stretch=1)
        com_tab_layout.addLayout(serial_port_layout)
        com_tab_layout.addWidget(QLabel("baudrate:"))
        com_tab_layout.addWidget(self.baudrate)
        com_buttons =QHBoxLayout()
        self.btn_open = QPushButton("open")
        self.btn_close = QPushButton("close")
        com_buttons.addWidget(self.btn_open)
        com_buttons.addWidget(self.btn_close)
        com_tab_layout.addLayout(com_buttons)

        self.com_status_frame = QFrame()
        self.com_status_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.com_status_frame.setLineWidth(2)

        com_status_frame_layout = QVBoxLayout()
        com_status_line_layout = QHBoxLayout()
        com_status_line_layout.addWidget(QLabel("status: "))
        self.com_status_label = QLabel("CLOSED")
        self.com_status_label.setStyleSheet("color: red;")
        self.com_status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        com_status_line_layout.addWidget(self.com_status_label)

        com_tracking_line_layout = QHBoxLayout()
        com_tracking_line_layout.addWidget(QLabel("tracking: "))
        self.com_tracking_label = QLabel("INACTIVE")
        self.com_tracking_label.setStyleSheet("color: red;")
        self.com_tracking_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        com_tracking_line_layout.addWidget(self.com_tracking_label)

        com_motor_line_layout = QHBoxLayout()
        com_motor_line_layout.addWidget(QLabel("motor status: "))
        self.com_motor_label = QLabel("DISABLED")
        self.com_motor_label.setStyleSheet("color: red;")
        self.com_motor_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        com_motor_line_layout.addWidget(self.com_motor_label)


        self.manual_mode_check = QCheckBox("manual mode")
        self.manual_mode_check.setChecked(True)
        com_status_frame_layout.addLayout(com_status_line_layout)
        com_status_frame_layout.addLayout(com_tracking_line_layout)
        com_status_frame_layout.addLayout(com_motor_line_layout)
        com_status_frame_layout.addWidget(self.manual_mode_check)
        self.com_status_frame.setLayout(com_status_frame_layout)
        com_tab_layout.addWidget(self.com_status_frame)




        com_tab_layout.addStretch()
        com_tab.setLayout(com_tab_layout)
        self.com_tabs.addTab(com_tab, "com tab")

        left_layout.addWidget(self.tabs)
        left_layout.addWidget(self.com_tabs)

        self.left_frame.setLayout(left_layout)

        # =========================================================================
        # ================================== VISUALS ==============================
        # =========================================================================


        self.right_frame = QFrame()
        self.right_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.right_frame.setLineWidth(4)
      
        right_layout = QVBoxLayout()

        #### PLOT INIT
        self.plot_timer = QTimer()
        self.plot_timer.setInterval(100) 
        self.plot_timer.timeout.connect(self.update_error_plot)
        self.plot_timer.start()
        self.error_plot = pg.PlotWidget()
        self.error_plot.setTitle("tracking error")
        self.error_plot.setLabel("left", "Error [deg]")
        self.error_plot.setLabel("bottom", "Time [s]")
        self.error_plot.showGrid(x=True, y=True)
        self.error_plot.setBackground((40, 40, 40))
        self.error_plot.addLegend(pen= 'w')  
        self.error_plot.getAxis('left').enableAutoSIPrefix(False)

        self.error_x = self.error_plot.plot(pen="r", name='x')
        self.error_y = self.error_plot.plot(pen="g", name='y')
        
        #### PLOT FRAME
        self.plot_frame = QFrame()
        self.plot_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.plot_frame.setLineWidth(2)
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.error_plot)
        self.plot_frame.setLayout(plot_layout)

        
        #### CAMERA LABEL
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        #### CAMERA FRAME
        self.camera_frame = QFrame()
        self.camera_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.camera_frame.setLineWidth(2)
        camera_layout = QVBoxLayout()
        camera_layout.addWidget(self.image_label, stretch=10)
        self.camera_frame.setLayout(camera_layout)

        right_layout.addWidget(self.camera_frame, stretch=7) #<-------------- CAMERA STRETCH

        ##### CLICKING

        self.image_label.mousePressEvent = self.on_image_click

        #### THRESHOLD

        self.threshold_image = QLabel()
        self.threshold_image.setAlignment(Qt.AlignCenter)
        self.threshold_image.setStyleSheet("background-color: black;")
        self.threshold_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                
        #### THRESHOLD FRAME
        self.threshold_frame = QFrame()
        self.threshold_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.threshold_frame.setLineWidth(2)
        threshold_layout = QVBoxLayout()
        threshold_layout.addWidget(self.threshold_image)
        self.threshold_frame.setLayout(threshold_layout)
        


        #### BOTTOM FRAME
        self.bottom_frame = QFrame()
        self.bottom_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.bottom_frame.setLineWidth(2)
        bottom_layout = QHBoxLayout()


        #### FRAMES TO BOTTOM LAYOUT
        bottom_layout.addWidget(self.plot_frame, stretch=3)
        bottom_layout.addWidget(self.threshold_frame, stretch=1)
        self.bottom_frame.setLayout(bottom_layout)
        right_layout.addWidget(self.bottom_frame, stretch=3)
        self.right_frame.setLayout(right_layout)

        #### MAIN LAYOUT
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.left_frame, stretch=1)
        main_layout.addWidget(self.right_frame, stretch=4)
        self.setLayout(main_layout)


        # ===  ===
        self.btn_apply.clicked.connect(self.on_apply)
        self.combo.currentTextChanged.connect(self.change_res)
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        self.roi_slider.valueChanged.connect(self.change_roi)
        self.serial_combo.currentTextChanged.connect(self.change_port)
        self.btn_open.clicked.connect(self.on_open)
        self.btn_close.clicked.connect(self.on_close)
        self.btn_ref_ports.clicked.connect(self.on_ref_ports)
        self.btn_ref_camera.clicked.connect(self.on_ref_cameras)

        self.roi_box_check.stateChanged.connect(self.update_overlay_params)
        self.mark_check.stateChanged.connect(self.update_overlay_params)
        self.roi_mark_combo.currentIndexChanged.connect(self.update_overlay_params)


    # ===  ===

    def stop_camera_thread(self):
        if hasattr(self, "cameraThread") and self.cameraThread is not None:
            self.cameraThread.stop()  
            if hasattr(self, "camera_thread"):
                self.camera_thread.quit()
                self.camera_thread.wait()


    def on_ref_cameras(self):
        self.stop_camera_thread()
        cameras = detect_cameras()
        self.camera_combo.clear()
        self.camera_combo.addItem("choose camera")
        for cam in cameras:
            self.camera_combo.addItem(f"{cam}", cam)


    def on_ref_ports(self):
        ports = self.serialMenager.detect_serial_ports()
        self.serial_combo.clear()
        self.serial_combo.addItem("select port")
        for device, desc in ports:
            self.serial_combo.addItem(f"{device}  ({desc})", device)


    def update_error_plot(self):
        if len(self.error_time) < 2:
            return

        self.error_x.setData(self.error_time, self.error_x_data)
        self.error_y.setData(self.error_time, self.error_y_data)

        self.error_plot.setXRange(
            max(0, self.error_time[-1] - 20),
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
        self.com_status_label.setText("OPEN")
        self.com_status_label.setStyleSheet("color: green;")


    def on_close(self):
        self.serialMenager.close_serial_port()
        self.com_status_label.setText("CLOSED")
        self.com_status_label.setStyleSheet("color: red;")
        
    def change_roi(self, value):
        self.roi_size = value
        self.roi_label.setText(f"roi size: {value}")
        self.cameraThread.set_roi_size(self.roi_size)

        


    def change_roi_mark_size(self, value):
        v = value
        self.roi_mark_size = v
        self.roi_mark_size_label.setText(f"ROI mark size: {v}")
        self.update_overlay_params() 

    def change_exposure(self, value):
        v = value 
        self.cameraThread.change_exposure(v)
        self.exposure_label.setText(f"exposure: {v/10} ms")  

    def change_brightness(self, value):
        v = value 
        self.cameraThread.change_brightness(v)
        self.brightness_label.setText(f"brightness: {v}")   

    def change_contrast(self, value):
        v = value 
        self.cameraThread.change_contrast(v)
        self.contrast_label.setText(f"contrast: {v}")  
    def change_saturation(self, value):
        v = value 
        self.cameraThread.change_saturation(v)
        self.saturation_label.setText(f"saturation: {v}")  


    def change_res(self, text):
        if text == "choose resolution":
            return
        try:
            w, h = map(int, text.split('x'))
            if self.cameraThread:
                self.cameraThread.res_signal.emit(w, h)
                print(f"Emitted resolution change to {w}x{h}")
        except ValueError:
            print(f"Invalid resolution format: {text}")


    def change_camera(self, index):
        cam_index = self.camera_combo.currentData()
        if cam_index is None:
            return

        if hasattr(self, "camera_thread") and hasattr(self, "cameraThread"):
            self.cameraThread.stop()
            self.camera_thread.quit()
            self.camera_thread.wait()

        self.camera_thread = QThread()
        self.cameraThread = CameraThread(cam_index=cam_index)
        self.cameraThread.moveToThread(self.camera_thread)

        self.camera_thread.started.connect(self.cameraThread.run)

        self.cameraThread.frame_ready.connect(self.on_frame_ready)
        self.cameraThread.threshold_ready.connect(self.on_threshold_ready)
        self.cameraThread.centroid_ready.connect(self.on_centroid_ready)

        self.camera_thread.start()


    @Slot(object)
    def on_frame_ready(self, frame):
        self.frame_h, self.frame_w, _ = frame.shape

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape

        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        self.image_label.setPixmap(
            pix.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    
    @Slot(tuple, float, float)
    def on_centroid_ready(self, centroid, error_x, error_y):
        if centroid is None:
            return

        t = time.time() - self.start_time

        self.error_time.append(t)
        self.error_x_data.append(error_x)
        self.error_y_data.append(error_y)
        self.serialMenager.serial_send_error(error_x, error_y)

        # limit 20 s
        while self.error_time and t - self.error_time[0] > 20:
            self.error_time.pop(0)
            self.error_x_data.pop(0)
            self.error_y_data.pop(0)
  


    @Slot(object)
    def on_threshold_ready(self, threshold):
        if threshold is None:
            self.threshold_image.setPixmap(QPixmap())
            return
        th = np.ascontiguousarray(threshold)

        h, w = th.shape
        qimg = QImage(
            th.data,
            w,
            h,
            w,
            QImage.Format_Grayscale8
        ).copy()

        pix = QPixmap.fromImage(qimg)

        self.threshold_image.setPixmap(
            pix.scaled(
                self.threshold_image.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    
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

        try:
            # przeliczenie do współrzędnych oryginalnej klatki
            fx = (x - x_off) * self.frame_w / pw
            fy = (y - y_off) * self.frame_h / ph

            self.target_pos = (int(fx), int(fy))
            self.tracking_enabled = True

            # PRZEKAŻ DO CAMERA THREAD
            if hasattr(self, 'cameraThread'):
                self.cameraThread.set_tracking_params(
                    enabled=self.tracking_enabled,
                    target_pos=self.target_pos,
                    roi_size=self.roi_size,
                    arcsec=self.arcsec
                )
        except AttributeError:
            print("Błąd: frame_w lub frame_h nie jest zdefiniowane")
    
    
    # Gdy zmieniasz overlay:
    def update_overlay_params(self):
        self.cameraThread.set_overlay_params(
            roi_mark_size=self.roi_mark_size,
            mark_type=self.roi_mark_combo.currentData(),
            center_mark=self.mark_check.isChecked(),
            roi_mark=self.roi_box_check.isChecked()
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = main()
    window.on_ref_cameras()
    window.show()
    sys.exit(app.exec())


