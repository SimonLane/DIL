
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_row = None

    def mousePressEvent(self, event):
        self.start_row = self.rowAt(event.position().toPoint().y())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        end_row = self.rowAt(event.position().toPoint().y())
        if self.start_row is not None and end_row != -1 and end_row != self.start_row:
            self.window().move_dataframe_row(self.start_row, end_row)
            self.window().update_positions_table()
            self.window().save_positions_to_csv()
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
        self.experiment_table = QTableWidget()
        layout.addWidget(self.experiment_table)
        self.experiment_table.cellChanged.connect(self.on_experiment_table_change)

    
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

    def update_channels_table(self):
        self.experiment_table.blockSignals(True)
        self.experiment_table.setRowCount(len(self.experiment_df))
        self.experiment_table.setColumnCount(9)
        self.experiment_table.setHorizontalHeaderLabels(["#", "Name", "Active", "Exp.", "Pow.", "Wav.", "Filter", "Live", "Del."])
        self.experiment_table.verticalHeader().setVisible(False)
    
        for i, row in self.experiment_df.iterrows():
            # Index
            index_item = QTableWidgetItem(str(i + 1))
            index_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.experiment_table.setItem(i, 0, index_item)
    
            # Name (text)
            name_item = QTableWidgetItem(str(row["Name"]) if pd.notna(row["Name"]) else "")
            self.experiment_table.setItem(i, 1, name_item)
    
            # Active (checkbox)
            active_item = QTableWidgetItem()
            active_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            active_item.setCheckState(Qt.CheckState.Checked if row["Active"] else Qt.CheckState.Unchecked)
            self.experiment_table.setItem(i, 2, active_item)
    
            # Exposure (spinbox)
            exposure_item = QTableWidgetItem(str(row["Exposure"]) if pd.notna(row["Exposure"]) else "")
            self.experiment_table.setItem(i, 3, exposure_item)
    
            # Power (spinbox)
            power_item = QTableWidgetItem(str(row["Power"]) if pd.notna(row["Power"]) else "")
            self.experiment_table.setItem(i, 4, power_item)
    
            # Wavelength (spinbox)
            wavelength_item = QTableWidgetItem(str(row["Wavelength"]) if pd.notna(row["Wavelength"]) else "")
            self.experiment_table.setItem(i, 5, wavelength_item)
    
            # Filter (dropdown)
            filter_box = QComboBox()
            filter_box.addItems(self.filter_names)
            if pd.notna(row["Filter"]):
                filter_box.setCurrentText(str(row["Filter"]))
            filter_box.currentTextChanged.connect(lambda _, r=i: self.on_experiment_dropdown_change(r))
            self.experiment_table.setCellWidget(i, 6, filter_box)
    
            # Live button
            live_button = QPushButton("Live")
            live_button.clicked.connect(lambda _, r=i: self.on_experiment_live(r))
            self.experiment_table.setCellWidget(i, 7, live_button)
    
            # Delete button
            del_button = QPushButton("Del")
            del_button.clicked.connect(lambda _, r=i: self.delete_channel(r))
            self.experiment_table.setCellWidget(i, 8, del_button)
    
        self.experiment_table.blockSignals(False)
        column_widths = {0: 30,    1: 100,   2: 40,   3: 40,   4: 40,   5: 50,   6: 100  ,   7: 40  ,   8: 40   }
        for col, width in column_widths.items():
            self.experiment_table.setColumnWidth(col, width)

    def on_experiment_table_change(self, row, column):
        if column == 1:  # Name
            value = self.experiment_table.item(row, column).text()
            self.experiment_df.at[row, "Name"] = value
        elif column == 3:
            try:
                self.experiment_df.at[row, "Exposure"] = int(self.experiment_table.item(row, column).text())
            except ValueError:
                pass
        elif column == 4:
            try:
                self.experiment_df.at[row, "Power"] = int(self.experiment_table.item(row, column).text())
            except ValueError:
                pass
        elif column == 5:
            try:
                self.experiment_df.at[row, "Wavelength"] = int(self.experiment_table.item(row, column).text())
            except ValueError:
                pass
        self.save_channels_to_csv()

    def init_positions_section(self):
        positions_box = self.group_boxes["Positions"]
        layout = positions_box.layout()
        
        if os.path.exists("positions.csv"):
            self.positions_df = pd.read_csv("positions.csv")
            self.positions_df["Active"] = self.positions_df["Active"].fillna(False).astype(bool)
        else:
            self.positions_df = pd.DataFrame(columns=["Active", "X", "Y", "Z"])

        self.positions_table = ReorderableTableWidget(self)
        self.positions_table.cellChanged.connect(self.on_table_change)
        self.positions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.positions_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.positions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.positions_table.setStyleSheet("QTableWidget::item:selected { background-color: #a2d5f2; }")

        self.positions_table.setColumnCount(7)
        self.positions_table.setHorizontalHeaderLabels(["#", "Active", "X", "Y", "Z", "Go", "Del"])
        self.positions_table.verticalHeader().setVisible(False)
        self.positions_table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.positions_table.setMaximumWidth(460)  # Optional: narrow table
        
        add_position_button = QPushButton("Add")
        add_position_button.clicked.connect(self.add_position_row)
        add_position_button.setFixedWidth(60)

        load_position_button = QPushButton("Load")
        load_position_button.setFixedWidth(60)
        load_position_button.clicked.connect(self.load_positions_from_file)

        layout.addWidget(self.positions_table,                      0,0,10,5)
        layout.addWidget(add_position_button,                       0,5,1,2)
        layout.addWidget(load_position_button,                      1,5,1,2)
        
        self.update_positions_table()

    def load_positions_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Positions CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                df = pd.read_csv(file_path)
                df["Active"] = df["Active"].fillna(False).astype(bool)
                self.positions_df = df
                self.update_positions_table()
                self.save_positions_to_csv()  # Save imported data to main file
                print(f"Loaded positions from {file_path}")
            except Exception as e:
                print(f"Error loading file: {e}")    
    
    def move_dataframe_row(self, from_row, to_row):
        if from_row == to_row or from_row < 0 or to_row < 0:
            return
        row_data = self.positions_df.iloc[from_row]
        self.positions_df = self.positions_df.drop(index=from_row).reset_index(drop=True)
        self.positions_df = pd.concat([
            self.positions_df.iloc[:to_row],
            pd.DataFrame([row_data]),
            self.positions_df.iloc[to_row:]
        ]).reset_index(drop=True)


    def update_positions_table(self):
        self.positions_table.blockSignals(True)
        self.positions_table.setRowCount(len(self.positions_df))
        for i, row in self.positions_df.iterrows():
            # Index
            index_item = QTableWidgetItem(str(i + 1))
            index_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.positions_table.setItem(i, 0, index_item)

            # Active as checkbox item
            active_item = QTableWidgetItem()
            active_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable |Qt.ItemFlag.ItemIsSelectable |Qt.ItemFlag.ItemIsEnabled)

            active_item.setCheckState(Qt.CheckState.Checked if row["Active"] else Qt.CheckState.Unchecked)
            self.positions_table.setItem(i, 1, active_item)

            # X, Y, Z
            for j, key in enumerate(["X", "Y", "Z"], start=2):
                item = QTableWidgetItem(str(row[key]) if pd.notna(row[key]) else "")
                self.positions_table.setItem(i, j, item)

            # Go Button
            go_button = QPushButton("Go")
            go_button.clicked.connect(lambda _, r=i: self.go_to_position(r))
            self.positions_table.setCellWidget(i, 5, go_button)

            # Del Button
            del_button = QPushButton("Del")
            del_button.clicked.connect(lambda _, r=i: self.delete_position_row(r))
            self.positions_table.setCellWidget(i, 6, del_button)
        self.positions_table.blockSignals(False)
        column_widths = {0: 40,    1: 60,   2: 80,   3: 80,   4: 80,   5: 50,   6: 50  }
        for col, width in column_widths.items():
            self.positions_table.setColumnWidth(col, width)

    def on_table_change(self, row, column):
        if column == 1:
            state = self.positions_table.item(row, column).checkState()
            self.positions_df.at[row, "Active"] = (state == Qt.CheckState.Checked)
            self.save_positions_to_csv()
            return
        elif column in [2, 3, 4]:  # X, Y, Z
            key = ["X", "Y", "Z"][column - 2]
            try:
                value = self.positions_table.item(row, column).text()
                self.positions_df.at[row, key] = float(value)
            except ValueError:
                print(f"Ignored invalid float for {key} at row {row}: {value}")
                return
        self.save_positions_to_csv()

    def add_position_row(self):
        new_row = pd.DataFrame([{"Active": False, "X": 0.0, "Y": 0.0, "Z": 0.0}])
        self.positions_df = pd.concat([self.positions_df, new_row], ignore_index=True)
        self.save_positions_to_csv()
        self.update_positions_table()

    def delete_position_row(self, row_index):
        self.positions_df = self.positions_df.drop(index=row_index).reset_index(drop=True)
        self.save_positions_to_csv()
        self.update_positions_table()

    def on_rows_reordered(self):
        new_order = []
        for row in range(self.positions_table.rowCount()):
            active = self.positions_table.item(row, 1).checkState() == Qt.CheckState.Checked
            try:
                x = float(self.positions_table.item(row, 2).text())
                y = float(self.positions_table.item(row, 3).text())
                z = float(self.positions_table.item(row, 4).text())
            except ValueError:
                continue
            new_order.append({"Active": active, "X": x, "Y": y, "Z": z})
        self.positions_df = pd.DataFrame(new_order)
        self.save_positions_to_csv()
        self.update_positions_table()

    def go_to_position(self, row_index):
        pos = self.positions_df.iloc[row_index]
        print(f"Going to position {row_index + 1}: X={pos['X']}, Y={pos['Y']}, Z={pos['Z']}")

    def save_positions_to_csv(self, filename="positions.csv"):
        self.positions_df.to_csv(filename, index=False)

    def create_group_box(self, title):
        group_box = QGroupBox(title)
        layout = QVBoxLayout()
        label = QLabel(f"{title} content will go here.")
        layout.addWidget(label)
        group_box.setLayout(layout)
        return group_box

def main():
    app = QApplication(sys.argv)
    window = BareBonesGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
