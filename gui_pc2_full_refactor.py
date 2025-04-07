
import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGroupBox, QVBoxLayout,
    QGridLayout, QWidget, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QAbstractItemView, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog

class ReorderableTableWidget(QTableWidget):
    
    def populate_table(self, table, df, columns, column_widgets, button_callbacks, column_widths):
        table.blockSignals(True)
        table.setRowCount(len(df))
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)

        for i, row in df.iterrows():
            for col, col_name in enumerate(columns):
                if col_name in column_widgets:
                    widget_type = column_widgets[col_name]
                    if widget_type == "checkbox":
                        item = QTableWidgetItem()
                        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                        item.setCheckState(Qt.CheckState.Checked if row[col_name] else Qt.CheckState.Unchecked)
                        table.setItem(i, col, item)
                    elif widget_type == "text":
                        item = QTableWidgetItem(str(row[col_name]) if pd.notna(row[col_name]) else "")
                        table.setItem(i, col, item)
                    elif isinstance(widget_type, list):  # Dropdown list
                        combo = QComboBox()
                        combo.addItems(widget_type)
                        combo.setCurrentText(str(row[col_name]) if pd.notna(row[col_name]) else "")
                        table.setCellWidget(i, col, combo)
                elif col_name == "#":
                    item = QTableWidgetItem(str(i + 1))
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    table.setItem(i, col, item)
                elif col_name in button_callbacks:
                    btn = QPushButton(col_name)
                    btn.clicked.connect(lambda _, r=i, c=col_name: button_callbacks[col_name](r))
                    table.setCellWidget(i, col, btn)

        for col, width in column_widths.items():
            table.setColumnWidth(col, width)

        table.blockSignals(False)

    def __init__(self, parent=None, reorder_callback=None):
        super().__init__(parent)
        self.start_row = None
        self.reorder_callback = reorder_callback  # Function to call on reorder

    def mousePressEvent(self, event):
        self.start_row = self.rowAt(event.position().toPoint().y())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        end_row = self.rowAt(event.position().toPoint().y())
        if self.start_row is not None and end_row != -1 and end_row != self.start_row:
            if callable(self.reorder_callback):
                self.reorder_callback(self.start_row, end_row)
        self.start_row = None
        super().mouseReleaseEvent(event)



class BareBonesGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.filter_names = [
            '420+-20',          #p1
            '520+-20',          #p2
            '600+-20',          #p3
            'filter 4',         #p4
            'filter 5',         #p5
            'filter 6']
        
        self.group_boxes = {}
        self.init_ui()

    def init_ui(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        app_width = int(screen_geometry.width() * 0.9)
        app_height = int(screen_geometry.height() * 0.9)
        self.setGeometry(0, 0, app_width, app_height)
        self.setWindowTitle("Bare Bones GUI with GroupBoxes and Custom Layout")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        grid_layout = QGridLayout()

        self.add_group_box("Live View", grid_layout, 0, 0, 60, 100)
        self.add_group_box("Map", grid_layout, 0, 100, 60, 50)
        self.add_group_box("Files", grid_layout, 60, 0, 20, 25)
        self.add_group_box("Timing", grid_layout, 80, 0, 20, 25)
        self.add_group_box("Z-stack", grid_layout, 60, 25, 20, 25)
        self.add_group_box("Connections", grid_layout, 80, 25, 20, 25)
        self.add_group_box("Experiment Builder", grid_layout, 60, 50, 40, 50)
        self.add_group_box("Positions", grid_layout, 60, 100, 40, 50)

        central_widget.setLayout(grid_layout)
        # build the sections of the GUI
        self.init_positions_section()
        self.init_experiment_builder_section()


    def add_group_box(self, title, layout, row, col, rowspan, colspan):
        group_box = QGroupBox(title)
        group_box.setLayout(QGridLayout())
        self.group_boxes[title] = group_box
        layout.addWidget(group_box, row, col, rowspan, colspan)

    def init_experiment_builder_section(self):
        experiment_box = self.group_boxes["Experiment Builder"]
        layout = experiment_box.layout()
        
        # Init empty dataframe with correct columns
        if os.path.exists("experiment.csv"):
            self.experiment_df = pd.read_csv("experiment.csv")
            self.experiment_df["Active"] = self.experiment_df["Active"].fillna(False).astype(bool)
        else:
            self.experiment_df = pd.DataFrame(columns=[
                "Name", "Active", "Exposure", "Power", "Wavelength", "Filter"
            ])

        # Placeholder for now
        self.experiment_table = ReorderableTableWidget(self, reorder_callback=self.reorder_experiment_rows)
        self.experiment_table.cellChanged.connect(self.on_experiment_table_change)

        layout.addWidget(self.experiment_table)
        self.experiment_table.cellChanged.connect(self.on_experiment_table_change)

        self.experiment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.experiment_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.experiment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.experiment_table.setStyleSheet("QTableWidget::item:selected { background-color: #a2d5f2; }")
        
        # Add + Load buttons
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_channel)
        add_button.setFixedWidth(60) 
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_channels_from_file)
        load_button.setFixedWidth(60)
        
        layout.addWidget(add_button)
        layout.addWidget(load_button)
        layout.addWidget(self.experiment_table,                         0,0,10,5)
        layout.addWidget(add_button,                                    0,5,1,2)
        layout.addWidget(load_button,                                   1,5,1,2)
        self.update_channels_table()

    def add_channel(self):
        n = len(self.experiment_df)
        new_row = pd.DataFrame([{
            "Name": "channel {}".format(n+1),
            "Active": False,
            "Exposure": 10,
            "Power": 100,
            "Wavelength": 488,
            "Filter": "1"
        }])
        self.experiment_df = pd.concat([self.experiment_df, new_row], ignore_index=True)
        self.save_channels_to_csv()
        self.update_channels_table()
    
    def delete_channel(self, row_index):
        self.experiment_df = self.experiment_df.drop(index=row_index).reset_index(drop=True)
        self.save_channels_to_csv()
        self.update_channels_table()

    def load_channels_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Experiment CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                df = pd.read_csv(file_path)
                df["Active"] = df["Active"].fillna(False).astype(bool)
                self.experiment_df = df
                self.update_channels_table()
                self.save_channels_to_csv()
            except Exception as e:
                print(e)

    def save_channels_to_csv(self, filename="experiment.csv"):
        self.experiment_df.to_csv(filename, index=False)

    def on_experiment_dropdown_change(self, row_index):
        filter_value = self.experiment_table.cellWidget(row_index, 6).currentText()
        self.experiment_df.at[row_index, "Filter"] = filter_value
        self.save_channels_to_csv()

    def on_experiment_table_change(self, row, column):
        if column == 1:  # Name
            item = self.experiment_table.item(row, column)
            if item:
                self.experiment_df.at[row, "Name"] = item.text()
        elif column == 2:  # Active
            item = self.experiment_table.item(row, column)
            if item:
                self.experiment_df.at[row, "Active"] = item.checkState() == Qt.CheckState.Checked
        elif column in [3, 4, 5]:  # Exposure, Power, Wavelength
            key = ["Exposure", "Power", "Wavelength"][column - 3]
            item = self.experiment_table.item(row, column)
            if item:
                try:
                    self.experiment_df.at[row, key] = int(item.text())
                except ValueError:
                    pass
        self.save_channels_to_csv()

    
    def update_channels_table(self):
        columns = ["#", "Name", "Active", "Exposure", "Power", "Wavelength", "Filter", "Live", "Del"]
        column_widgets = {
            "Name": "text",
            "Active": "checkbox",
            "Exposure": "text",
            "Power": "text",
            "Wavelength": "text",
            "Filter": self.filter_names
        }
        button_callbacks = {
            "Live": self.on_experiment_live,
            "Del": self.delete_channel
        }
        column_widths = {0: 30, 1: 100, 2: 40, 3: 40, 4: 40, 5: 50, 6: 100, 7: 40, 8: 40}

        self.populate_table(self.experiment_table, self.experiment_df, columns, column_widgets, button_callbacks, column_widths)

def main():
    app = QApplication(sys.argv)
    window = BareBonesGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
