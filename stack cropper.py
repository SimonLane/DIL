import os
import numpy as np
import imageio
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph import ImageView
from tkinter import Tk, filedialog

class CropperApp(QtWidgets.QWidget):
    def __init__(self, image_folder):
        super().__init__()
        self.setWindowTitle("Z-Projection Cropper")

        self.image_folder = image_folder
        self.image_paths = sorted([
            os.path.join(image_folder, f)
            for f in os.listdir(image_folder)
            if f.lower().endswith('.tif')
        ])
        if not self.image_paths:
            raise ValueError("No .tif files found in selected folder.")
            
        print(self.image_paths)

        # Load images into 3D stack
        self.stack = np.stack([imageio.imread(p) for p in self.image_paths])
        self.zproj = self.stack.mean(axis=0)

        # GUI elements
        self.view = ImageView()
        self.roi = pg.RectROI([20, 20], [100, 100], pen='r', movable=True, resizable=True)
        self.roi.addScaleHandle([1, 1], [0, 0])  # bottom-right
        self.roi.addScaleHandle([0, 0], [1, 1])  # top-left
        self.roi.addScaleHandle([1, 0], [0, 1])  # top-right
        self.roi.addScaleHandle([0, 1], [1, 0])  # bottom-left

        self.crop_button = QtWidgets.QPushButton("Crop")
        self.info_label = QtWidgets.QLabel()

        # Image + ROI
        self.view.addItem(self.roi)
        self.view.setImage(self.zproj.T)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(self.info_label)
        layout.addWidget(self.crop_button)
        self.setLayout(layout)

        # Signals
        self.crop_button.clicked.connect(self.crop_images)
        self.roi.sigRegionChanged.connect(self.update_info)
        self.update_info()  # initial update

    def update_info(self):
        x, y = self.roi.pos()
        w, h = self.roi.size()
        self.info_label.setText(f"Crop box: X={int(x)}, Y={int(y)}, W={int(w)}, H={int(h)}")

    def crop_images(self):
        x, y = map(int, self.roi.pos())
        w, h = map(int, self.roi.size())

        for i, path in enumerate(self.image_paths):
            img = imageio.imread(path)
            cropped = img[y:y+h, x:x+w]
            imageio.imwrite(path, cropped)  # overwrite original

        QtWidgets.QApplication.quit()

def select_folder_and_run():
    # Hide Tk root window
    root = Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title="Select Folder with .tif Images")
    if not folder:
        return

    app = QtWidgets.QApplication([])
    window = CropperApp(folder)
    window.resize(800, 600)
    window.show()
    app.exec()

if __name__ == "__main__":
    select_folder_and_run()
