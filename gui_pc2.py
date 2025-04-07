
import sys
import os
import pandas as pd 
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGroupBox, QVBoxLayout,
    QGridLayout, QWidget, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QAbstractItemView, QComboBox, QLineEdit, QFileDialog, QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator, QDoubleValidator, QTextOption



class ReorderableTableWidget(QTableWidget):
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
        self.setWindowTitle("Dual Illumination Lightsheet - User Interface")
        self.root_location = "D:/Light_Sheet_Images/Users"

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
        self.init_timing_section()
        self.init_zstack_section()
        self.init_file_section()

    def add_group_box(self, title, layout, row, col, rowspan, colspan):
        group_box = QGroupBox(title)
        group_box.setLayout(QGridLayout())
        self.group_boxes[title] = group_box
        layout.addWidget(group_box, row, col, rowspan, colspan)


    def init_file_section(self):
        files_box = self.group_boxes["Files"]
        layout = files_box.layout()
    
        layout.addWidget(QLabel("User:"), 0, 0)
        layout.addWidget(QLabel("Experiment name:"), 1, 0)
        layout.addWidget(QLabel("Path preview:"), 2, 0)
    
        # Dropdown with users (subfolders)
        self.user_dropdown = QComboBox()
        if os.path.exists(self.root_location):
            users = [f for f in os.listdir(self.root_location) if os.path.isdir(os.path.join(self.root_location, f))]
            self.user_dropdown.addItems(users)
        self.user_dropdown.currentTextChanged.connect(self.update_filepath_preview)
    
        # Experiment name input
        self.experiment_name_input = QLineEdit()
        self.experiment_name_input.setPlaceholderText("Enter experiment name")
        self.experiment_name_input.textChanged.connect(self.update_filepath_preview)
    
        # Read-only full path preview
        self.file_path_preview = QTextEdit()
        self.file_path_preview.setReadOnly(True)
        self.file_path_preview.setFixedHeight(50)
        self.file_path_preview.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

    
        layout.addWidget(self.user_dropdown, 0, 1)
        layout.addWidget(self.experiment_name_input, 1, 1)
        layout.addWidget(self.file_path_preview, 2, 1)
    
        self.update_filepath_preview()

    def update_filepath_preview(self):
        user = self.user_dropdown.currentText()
        name = self.experiment_name_input.text().strip()
        now = datetime.now()
    
        if user and name:
            preview_path = r"{}/{}/{}-{:02d}-{:02d} {:02d}_{:02d}_{:02d} - {}".format(
                self.root_location, user,
                now.year, now.month, now.day, now.hour, now.minute, now.second, name
            )
            self.file_path_preview.setPlainText(preview_path)
        else:
            self.file_path_preview.setPlainText("")

    def init_zstack_section(self):
        zstack_box = self.group_boxes["Z-stack"]
        layout = zstack_box.layout()
    
        # Labels
        layout.addWidget(QLabel("n Z steps:"), 0, 0)
        layout.addWidget(QLabel("z separation (µm):"), 1, 0)
        layout.addWidget(QLabel("stack size (µm):"), 2, 0)
    
        # Inputs
        self.n_z_steps_input = QLineEdit()
        self.n_z_steps_input.setValidator(QIntValidator(1, 1000))
        self.n_z_steps_input.setText("1")
        self.n_z_steps_input.setFixedWidth(60)
        self.n_z_steps_input.textChanged.connect(lambda: self.update_zstack_from("steps"))
    
        self.z_separation_input = QLineEdit()
        self.z_separation_input.setValidator(QDoubleValidator(0.0001, 100.0, 4))
        self.z_separation_input.setText("1.0")
        self.z_separation_input.setFixedWidth(60)
        self.z_separation_input.textChanged.connect(lambda: self.update_zstack_from("sep"))
    
        self.stack_size_input = QLineEdit()
        self.stack_size_input.setValidator(QDoubleValidator(0.0001, 1000.0, 4))
        self.stack_size_input.setText("1.0")
        self.stack_size_input.setFixedWidth(60)
        self.stack_size_input.textChanged.connect(lambda: self.update_zstack_from("size"))
    
        layout.addWidget(self.n_z_steps_input, 0, 1)
        layout.addWidget(self.z_separation_input, 1, 1)
        layout.addWidget(self.stack_size_input, 2, 1)

        self.update_zstack_from("steps")  # initialize values

    def update_zstack_from(self, changed):
        try:
            steps = int(self.n_z_steps_input.text())
            sep = float(self.z_separation_input.text())
            size = float(self.stack_size_input.text())
        except ValueError:
            return
        if changed == "steps" or changed == "sep":
            size = steps * sep
            self.stack_size_input.blockSignals(True)
            self.stack_size_input.setText(f"{size:.4f}")
            self.stack_size_input.blockSignals(False)
        elif changed == "size":
            if sep != 0:
                steps = max(int(round(size / sep)), 1)
                self.n_z_steps_input.blockSignals(True)
                self.n_z_steps_input.setText(str(steps))
                self.n_z_steps_input.blockSignals(False)
    
        # Store globals
        self.n_z_steps = steps
        self.z_separation = sep
        self.stack_size = size

    def init_timing_section(self):
        timing_box = self.group_boxes["Timing"]
        layout = timing_box.layout()
    
        # Labels
        layout.addWidget(QLabel("n timepoints:"), 0, 0)
        layout.addWidget(QLabel("time interval (s):"), 1, 0)
        layout.addWidget(QLabel("total exp. time:"), 2, 0)
    
        # Editable fields
        self.n_timepoints_input = QLineEdit()
        self.n_timepoints_input.setValidator(QIntValidator(1, 10000))  # adjust max as needed
        self.n_timepoints_input.setText("1")
        self.n_timepoints_input.setFixedWidth(60)
        self.n_timepoints_input.textChanged.connect(self.update_total_exp_time)
    
        self.time_interval_input = QLineEdit()
        self.time_interval_input.setValidator(QIntValidator(1, 3600))  # max 1 hour in seconds
        self.time_interval_input.setText("60")
        self.time_interval_input.setFixedWidth(60)
        self.time_interval_input.textChanged.connect(self.update_total_exp_time)
    
        # Read-only display
        self.total_exp_time_display = QLineEdit()
        self.total_exp_time_display.setFixedWidth(60)
        self.total_exp_time_display.setReadOnly(True)
    
        layout.addWidget(self.n_timepoints_input, 0, 1)
        layout.addWidget(self.time_interval_input, 1, 1)
        layout.addWidget(self.total_exp_time_display, 2, 1)
    
        self.update_total_exp_time()

    def update_total_exp_time(self):
        try:
            self.n_timepoints = int(self.n_timepoints_input.text())
            self.time_interval = int(self.time_interval_input.text())
            total_seconds = self.n_timepoints * self.time_interval
    
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
    
            formatted = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.total_exp_time_display.setText(formatted)
    
        except ValueError:
            self.total_exp_time_display.setText("00:00:00")


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
        self.musical_checkbox = QCheckBox("musical")
        self.musical_checkbox.setChecked(False)  # default unchecked

        layout.addWidget(add_button)
        layout.addWidget(load_button)
        layout.addWidget(self.experiment_table,                         0,0,10,5)
        layout.addWidget(add_button,                                    0,5,1,2)
        layout.addWidget(load_button,                                   1,5,1,2)
        layout.addWidget(self.musical_checkbox,                         2,5,1,2)
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
            active_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
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


    def reorder_positions_rows(self, from_row, to_row):
        self.positions_df = self.move_dataframe_row(self.positions_df, from_row, to_row)
        self.update_positions_table()
        self.save_positions_to_csv()

    def reorder_experiment_rows(self, from_row, to_row):
        self.experiment_df = self.move_dataframe_row(self.experiment_df, from_row, to_row)
        self.update_channels_table()
        self.save_channels_to_csv()

    def init_positions_section(self):
        positions_box = self.group_boxes["Positions"]
        layout = positions_box.layout()
        
        if os.path.exists("positions.csv"):
            self.positions_df = pd.read_csv("positions.csv")
            self.positions_df["Active"] = self.positions_df["Active"].fillna(False).astype(bool)
        else:
            self.positions_df = pd.DataFrame(columns=["Active", "X", "Y", "Z"])

        self.positions_table = ReorderableTableWidget(self, reorder_callback=self.reorder_positions_rows)

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
    
    def move_dataframe_row(self, df, from_row, to_row):
        if from_row == to_row or from_row < 0 or to_row < 0:
            return df
        row_data = df.iloc[from_row]
        df = df.drop(index=from_row).reset_index(drop=True)
        df = pd.concat([
            df.iloc[:to_row],
            pd.DataFrame([row_data]),
            df.iloc[to_row:]
        ]).reset_index(drop=True)
        return df

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
    app.exec()

if __name__ == "__main__":
    main()
