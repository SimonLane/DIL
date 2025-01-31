import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGroupBox, QVBoxLayout,
    QGridLayout, QWidget, QLabel
)

class BareBonesGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Get the screen size
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        app_width = int(screen_geometry.width()*0.9)
        app_height = int(screen_geometry.height()*0.9)

        self.setGeometry(0, 0, app_width, app_height) 

        # Set up the main window
        self.setWindowTitle("Bare Bones GUI with GroupBoxes and Custom Layout")

        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout using QGridLayout
        grid_layout = QGridLayout()

        # Add group boxes with specified positions and spans
        grid_layout.addWidget(self.create_group_box("Live View"), 0, 0, 60, 100)           # Row 0, Column 0, spans 60 rows, 100 columns
        grid_layout.addWidget(self.create_group_box("Map"), 0, 100, 60, 50)                # Row 0, Column 100, spans 60 rows, 50 columns
        grid_layout.addWidget(self.create_group_box("Files"), 60, 0, 20, 25)               # Row 60, Column 0, spans 20 rows, 25 columns
        grid_layout.addWidget(self.create_group_box("Timing"), 80, 0, 20, 25)              # Row 80, Column 0, spans 20 rows, 25 columns
        grid_layout.addWidget(self.create_group_box("Z-stack"), 60, 25, 20, 25)            # Row 60, Column 25, spans 20 rows, 25 columns
        grid_layout.addWidget(self.create_group_box("Connections"), 80, 25, 20, 25)        # Row 80, Column 25, spans 20 rows, 25 columns
        grid_layout.addWidget(self.create_group_box("Experiment Builder"), 60, 50, 40, 50) # Row 60, Column 50, spans 40 rows, 50 columns
        grid_layout.addWidget(self.create_group_box("Positions"), 60, 100, 40, 50)         # Row 60, Column 100, spans 40 rows, 50 columns

        # Set the layout to the central widget
        central_widget.setLayout(grid_layout)

    def create_group_box(self, title):
        """
        Creates a QGroupBox with a given title and placeholder content.
        """
        group_box = QGroupBox(title)
        layout = QVBoxLayout()

        # Placeholder content: Add a label to indicate where widgets can go
        label = QLabel(f"{title} content will go here.")
        layout.addWidget(label)

        group_box.setLayout(layout)
        return group_box

# Main function to run the application
def main():
    app = QApplication(sys.argv)
    window = BareBonesGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
