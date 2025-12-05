import sys
import csv
from datetime import datetime, timedelta

import pytesseract
import mss
from PIL import Image, ImageOps

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QLineEdit, QDoubleSpinBox, QHBoxLayout, QVBoxLayout,
    QGroupBox, QFileDialog
)

import pyqtgraph as pg


# ---------------------------------------------------------
# OCR helper
# ---------------------------------------------------------
def ocr_temperature(pil_img):
    img = pil_img.resize((pil_img.width * 6, pil_img.height * 6))
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)

    text = pytesseract.image_to_string(
        img,
        config="--psm 7 -c tessedit_char_whitelist=0123456789.-"
    )
    text = text.strip().replace(" ", "").replace("°", "")

    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------
# Overlay rectangle widget
# ---------------------------------------------------------
class OverlayRectangle(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.rect_width = 40
        self.rect_height = 15

    def set_region(self, x, y, w, h):
        self.rect_width = w
        self.rect_height = h
        self.setGeometry(QRect(x, y, w, h))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(255, 0, 0, 200), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(1, 1, self.rect_width - 2, self.rect_height - 2)


# ---------------------------------------------------------
# Main GUI
# ---------------------------------------------------------
class TempLoggerGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Screen Temperature Logger")
        self.resize(600, 400)

        # Screenshot offset relative to GUI
        self.offset_x = -65
        self.offset_y = 40

        # Capture region size
        self.region_w = 50
        self.region_h = 20  

        # Timers
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(150)  # ~6 FPS

        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.log_temperature)

        # Data storage
        self.timestamps = []
        self.temps = []

        # Overlay
        self.overlay = OverlayRectangle()
        self.overlay.show()

        self.build_ui()

        # Default output file
        self.output_file = "temperature_log.csv"

    # ---------------------------------------------------------
    # UI Setup
    # ---------------------------------------------------------
    def build_ui(self):
        layout = QVBoxLayout(self)

        # --- Controls box ---
        controls = QGroupBox("Controls")
        c_layout = QHBoxLayout()

        # File selection
        self.file_edit = QLineEdit("temperature_log.csv")
        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self.select_file)

        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 999)
        self.duration_spin.setValue(1.0)
        self.duration_spin.setSuffix(" h")

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 3600)
        self.interval_spin.setValue(1.0)
        self.interval_spin.setSuffix(" s")

        self.start_btn = QPushButton("Start Logging")
        self.start_btn.clicked.connect(self.toggle_logging)

        c_layout.addWidget(QLabel("Save to:"))
        c_layout.addWidget(self.file_edit)
        c_layout.addWidget(self.browse_btn)
        c_layout.addWidget(QLabel("Duration:"))
        c_layout.addWidget(self.duration_spin)
        c_layout.addWidget(QLabel("Interval:"))
        c_layout.addWidget(self.interval_spin)
        c_layout.addWidget(self.start_btn)

        controls.setLayout(c_layout)
        layout.addWidget(controls)

        # --- Preview row ---
        pv_layout = QHBoxLayout()

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(240, 120)
        self.preview_label.setStyleSheet("border: 1px solid gray;")

        self.value_label = QLabel("Current: ---")
        self.value_label.setStyleSheet("font-size: 22px; padding-left: 10px;")

        pv_layout.addWidget(self.preview_label)
        pv_layout.addWidget(self.value_label)

        layout.addLayout(pv_layout)

        # --- Graph ---
        self.graph = pg.PlotWidget()
        self.graph.setLabel('left', 'Temperature (°C)')
        self.graph.setLabel('bottom', 'Time (s)')
        self.curve = self.graph.plot([], [], pen='y')
        layout.addWidget(self.graph)

    # ---------------------------------------------------------
    # File picker
    # ---------------------------------------------------------
    def select_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if path:
            self.output_file = path
            self.file_edit.setText(path)

    # ---------------------------------------------------------
    # Start / Stop logging (does NOT affect preview)
    # ---------------------------------------------------------
    def toggle_logging(self):
        if self.capture_timer.isActive():
            self.capture_timer.stop()
            self.start_btn.setText("Start Logging")
            return

        # Prepare for new logging session
        self.timestamps.clear()
        self.temps.clear()

        self.output_file = self.file_edit.text()
        if not self.output_file.endswith(".csv"):
            self.output_file += ".csv"

        # Ensure CSV header
        with open(self.output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "temperature_C"])

        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=self.duration_spin.value())

        self.capture_timer.start(int(self.interval_spin.value() * 1000))
        self.start_btn.setText("Stop Logging")

    # ---------------------------------------------------------
    # Continuous preview + OCR updater
    # ---------------------------------------------------------
    def update_preview(self):
        global_pos = self.mapToGlobal(QPoint(0, 0))
        left = global_pos.x() + self.offset_x
        top = global_pos.y() + self.offset_y

        region = {"left": left, "top": top, "width": self.region_w, "height": self.region_h}

        # Update overlay
        self.overlay.set_region(left, top, self.region_w, self.region_h)

        # Capture region
        with mss.mss() as sct:
            raw = sct.grab(region)

        # Convert MSS BGRA to QImage
        qimg = QImage(raw.bgra, raw.width, raw.height, QImage.Format.Format_ARGB32)

        # Update preview display
        pix = QPixmap.fromImage(qimg).scaled(
            self.preview_label.width(),
            self.preview_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self.preview_label.setPixmap(pix)

        # Also perform continuous OCR
        pil_img = Image.frombytes("RGB", raw.size, raw.rgb)
        temp = ocr_temperature(pil_img)
        self.value_label.setText(f"Current: {temp}")

    # ---------------------------------------------------------
    # Log one temperature reading
    # ---------------------------------------------------------
    def log_temperature(self):
        now = datetime.now()
        if now >= self.end_time:
            self.toggle_logging()
            return

        global_pos = self.mapToGlobal(QPoint(0, 0))
        left = global_pos.x() + self.offset_x
        top = global_pos.y() + self.offset_y

        region = {"left": left, "top": top, "width": self.region_w, "height": self.region_h}

        with mss.mss() as sct:
            raw = sct.grab(region)

        temp = self.get_valid_temperature(region)

        if temp is None:
            print("Warning: failed to read temperature after retries. Skipping this interval.")
            return  # Do NOT append bad data

        timestamp_str = now.strftime("%Y_%m_%d %H:%M:%S")

        # Save to file
        with open(self.output_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp_str, temp])

        # Update graph
        elapsed = (now - self.start_time).total_seconds()
        self.timestamps.append(elapsed)
        if isinstance(temp, (int, float)):
            self.temps.append(temp)
        else:
            return   # skip bad OCR readings

        self.curve.setData(self.timestamps, self.temps)
    
    def get_valid_temperature(self, region, max_retries=5):
        """Try up to max_retries to obtain a valid OCR reading."""
        for _ in range(max_retries):
            with mss.mss() as sct:
                raw = sct.grab(region)
            pil_img = Image.frombytes("RGB", raw.size, raw.rgb)
    
            temp = ocr_temperature(pil_img)
    
            if isinstance(temp, (int, float)):
                return temp  # Success!
    
        return None  # Failed all retries



# ---------------------------------------------------------
# App entry
# ---------------------------------------------------------
if __name__ == "__main__":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    app = QApplication(sys.argv)
    gui = TempLoggerGUI()
    gui.show()
    sys.exit(app.exec())
