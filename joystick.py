from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtCore import Qt, QPointF, QTimer
import sys
import math

class JoystickWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 200)
        self.joystick_radius = 40
        self.is_dragging = False
        self.joystick_center = QPointF(self.width() / 2, self.height() / 2)
        self.current_position = self.joystick_center

        self.x = 0
        self.y = 0
        self.d_x = 0
        self.d_y = 0

        self.initUI()
        self.initTimer()

    def initUI(self):
        layout = QVBoxLayout()
        self.label = QLabel("Joystick Coordinates: (0, 0)")
        layout.addWidget(self.label)
        self.setLayout(layout)

    def initTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.output_coordinates)
        self.timer.start(100)

    def resizeEvent(self, event):
        # Update joystick center when the widget is resized
        self.joystick_center = QPointF(self.width() / 2, self.height() / 2)
        if not self.is_dragging:
            self.current_position = self.joystick_center
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw the base circle
        base_radius = min(self.width(), self.height()) / 2 - 10
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        painter.drawEllipse(int(self.width() / 2 - base_radius), int(self.height() / 2 - base_radius), int(base_radius * 2), int(base_radius * 2))
        
        # Draw the joystick
        painter.setBrush(QBrush(QColor(100, 100, 255)))
        painter.drawEllipse(self.current_position, self.joystick_radius, self.joystick_radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_within_joystick(event.pos()):
                self.is_dragging = True

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta_x = event.x() - self.width() / 2
            delta_y = event.y() - self.height() / 2
            distance = math.sqrt(delta_x ** 2 + delta_y ** 2)
            max_radius = min(self.width(), self.height()) / 2 - 10 - self.joystick_radius

            if distance > max_radius:
                angle = math.atan2(delta_y, delta_x)
                delta_x = math.cos(angle) * max_radius
                delta_y = math.sin(angle) * max_radius

            self.current_position = QPointF(self.width() / 2 + delta_x, self.height() / 2 + delta_y)
            self.update()
            self.d_x = delta_x / max_radius
            self.d_y = delta_y / max_radius

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.current_position = self.joystick_center
            self.d_x = 0
            self.d_y = 0 
            self.update()

    def is_within_joystick(self, pos):
        return (pos - self.current_position).manhattanLength() <= self.joystick_radius

    def output_coordinates(self):
        if self.d_x != 0 or self.d_y != 0: 
            self.x += self.d_x
            self.y += self.d_y
            print(f"Joystick Coordinates: x={self.x:.2f}, y={self.y:.2f}")
            self.label.setText(f"Joystick Coordinates: ({self.d_x:.2f}, {self.d_y:.2f})")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    joystick = JoystickWidget()
    joystick.show()
    sys.exit(app.exec_())

