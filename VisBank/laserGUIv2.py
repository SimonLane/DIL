#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 15:51:20 2024

@author: sil1r12
"""

import sys
import pandas as pd
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import QtCore


#imports for USB-3103 control board
from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import InterfaceType, DigitalIODirection


class laser_line():
    def __init__(self, parent, Ach, Dch, wavelength, minV, maxV, minuW, maxuW, eqn, p1, p2):
        self.parent             = parent
        self.wavelength         = wavelength
        self.A_channel_number   = Ach
        self.D_channel_number   = Dch
        self.min_value          = minV
        self.max_value          = maxV
        self.min_microWatt      = minuW
        self.max_microWatt      = maxuW
        self.equation_type      = eqn
        self.parameter_1        = p1
        self.parameter_2        = p2
        
        self.laser_on           = False
        self.percentage         = 0
        self.microWatts         = 0
        self.value_16           = 0
        
        
        self.label                      = QtWidgets.QLabel('laser power:')
        self.channelSelect              = QtWidgets.QRadioButton()
        self.channelSelect.setChecked(False)
        self.channelSelect.released.connect(self.buttonPress)
        self.power_slider               = QtWidgets.QSlider()
        self.power_slider.setOrientation(QtCore.Qt.Horizontal)
        self.power_slider.setMinimum(0)
        self.power_slider.setMaximum(100)
        self.power_slider.setTickInterval(10)
        self.power_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.power_slider.setValue(0)
        self.power_slider.valueChanged.connect(lambda: self.changePower())
        
        self.label2                     = QtWidgets.QLabel('0 %')
        self.label3                     = QtWidgets.QLabel('(0.00 mW)')

        self.box                        = QtWidgets.QGroupBox('%s nm' %wavelength) #main container
        self.box.setStyleSheet("background: lightgrey")
        self.box.setLayout(QtWidgets.QGridLayout())
        self.box.layout().addWidget(self.label,           0,0,1,2)
        self.box.layout().addWidget(self.power_slider,    0,2,1,5)
        self.box.layout().addWidget(self.label2,          0,7,1,2)
        self.box.layout().addWidget(self.channelSelect,   1,0,1,1)
        self.box.layout().addWidget(self.label3,          1,7,1,2)

    def buttonPress(self): 
        if self.laser_on:#                           laser already on, turn off
            self.parent.changeLaser(wavelength = 0)
            self.parent.set_power(self.A_channel_number, self.D_channel_number, self.wavelength,0)
            
        else:                           #            laser off, turn on, and turn off all others
            self.parent.changeLaser(wavelength = self.wavelength)
            self.laser_on = True
            self.changePower()

    def changePower(self):
        p,v,w = self.percent_to_16_bit()
        self.label2.setText("%s" %p + " %")
        self.label3.setText("(%.2f μW)"%w)
        if self.laser_on:
            self.parent.set_power(self.A_channel_number, self.D_channel_number, self.wavelength,v)


    def percent_to_16_bit(self): #percentage, 16-bit value, wattage    
        p = self.power_slider.value() #percentage
        if(p==0):
            self.microWatts, w = 0,0
            self.percentage, p = 0,0
            self.value_16, v   = 0,0
        else:
            #map percentage to 16-bit value
            m = (self.max_value-self.min_value)/(100)
            v = int((m*p) + self.min_value)
            #convert 16-bit value to power
            if(self.equation_type == 'lin'): 
                w = (v*self.parameter_1) + self.parameter_2
            if(self.equation_type == 'pow'): 
                w = ((pow(v,self.parameter_2)) * self.parameter_1)
                self.microWatts = w
                self.percentage = p
                self.value_16   = v
        return p,v,w
        
class Lasers(QtWidgets.QMainWindow):
    def __init__(self):
        super(Lasers, self).__init__()
  
    # basic properties for the UI
        self.GUI_colour         = QtGui.QColor(75,75,75)
        self.GUI_font           = QtGui.QFont('Times',10)
        self.laserCalibration   = ''
        self.address            = "C:/Local/GitHub/DIL/VisBank/"
        self.board_num          = 0
        self.initUI()
        self.connection         = False
        self.ao_range           = None
        self.port               = ''
        
        try:
            self.connect('C')
        except:
            print('Failed to connect to USB-3101')
            

    def changeLaser(self, wavelength=0): 
        for  l in self.lines:
            #turn off all
            l.box.setStyleSheet("background: lightgrey")
            if l.laser_on: l.laser_on = False
            l.channelSelect.setChecked(False)
            ul.a_out(0,l.A_channel_number,self.ao_range,0)
            # print('setting D channel: ', l.D_channel_number)
            if(l.D_channel_number > 0): ul.d_bit_out(0, self.port.type, l.D_channel_number, 0) # set digital out low
            if l.wavelength == wavelength: #turn on selected (if one selected)
                l.box.setStyleSheet("background: lightgreen")
                l.channelSelect.setChecked(True)

    def set_power(self, A_channel_number, D_channel_number, w, v):
        if self.connection:
            ul.a_out(0,A_channel_number,self.ao_range,v) # send the 16-bit value for the DAC
            if(D_channel_number > 0):
                if(v>0): ul.d_bit_out(0, self.port.type, D_channel_number, 1)
            print("setting %snm laser to %s" %(w,v))
            
    def shutter(self):
        if self.connection:
            for line in self.lines:
                ul.a_out(0, line.A_channel_number,self.ao_range,0)
                if(line.D_channel_number > 0):
                    # print('writing Digital:', line.D_channel_number)
                    ul.d_bit_out(0,self.port.type, line.D_channel_number,0)
            
        self.changeLaser() #use this to turn off all lines from the GUI pov
        
        
    def initUI(self):
        self.setGeometry(0, 50, 300, 1500) # doesn't work, why?
        self.setWindowTitle('Laser Controller')
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Background, self.GUI_colour)
        self.setPalette(palette)
# =============================================================================
# # LASERS TAB        
# =============================================================================
        
        #LOAD IN THE DATA
        self.dataframe = pd.read_csv("%sLaserCalibration.txt" %(self.address), header=0, index_col=0, sep ='\t')
        self.lines = []
        self.lasers = []

        for cn, row in enumerate(range(self.dataframe.shape[0])):
            l = self.dataframe.iloc[row, :]
            self.lasers.append(l)
            #               ['Ach','Dch','Wav.','Min.V','Max.V','Min.uW','Max.uW','Eqn.','P.1','P.2']
            self.lines.append(laser_line(self, l[0],l[1],l[2],l[3],l[4],l[5],l[6],l[7],l[8],l[9]))

        self.button_group = QtWidgets.QButtonGroup()
        for l in self.lines:
            self.button_group.addButton(l.channelSelect)
        self.button_group.setExclusive(False)
            
        self.stopButton = QtWidgets.QPushButton('STOP')
        self.stopButton.pressed.connect(self.shutter)
        self.stopButton.setStyleSheet("background: salmon; font: bold 15pt; color: white;")
        self.stopButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    
        
# =============================================================================
# # settings tab
# =============================================================================

        self.Settings_table = QtWidgets.QTableWidget()
        self.Settings_table.objectName = 'LaserSettings'
        self.Settings_table.setColumnCount(8)
        self.Settings_table.setRowCount(len(self.dataframe.index))
        self.Settings_table.setHorizontalHeaderLabels(
            ['Ach','Dch','Wav.', 'Min.V', 'Max.V', 'Min. uW', 'Max. uW', 'Eqn.', 'P.1', 'P.2'])
        # self.Settings_table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        column_spacing = [40,40,40,40,40,60,60,40,50,50]
        for column in range(10):
            self.Settings_table.setColumnWidth(column, column_spacing[column])
        self.Settings_table.setFixedWidth(380)
        for i in range(len(self.dataframe.index)):
            for j in range(len(self.dataframe.columns)):
                item = QtWidgets.QTableWidgetItem(str(self.dataframe.iloc[i, j]))
                item.setFlags(item.flags() &~ QtCore.Qt.ItemIsEditable)
                self.Settings_table.setItem(i,j,item)

        
#==============================================================================
# Overall assembly
#==============================================================================
      
        self.tabs = QtWidgets.QTabWidget()
        self.tab1 = QtWidgets.QWidget()
        self.tab2 = QtWidgets.QWidget()
        self.tabs.resize(300,500)
        self.tabs.addTab(self.tab1,"Lasers")
        self.tabs.addTab(self.tab2,"Settings")
        self.tab1.layout = QtWidgets.QGridLayout()
        self.tab2.layout = QtWidgets.QGridLayout()

#TAB1
        self.tab1.layout.addWidget(self.stopButton,                         0,0,1,1)

        for i, l in enumerate(self.lines):
            self.tab1.layout.addWidget(self.lines[i].box,                 i+1,0,1,1)

        self.tab1.setLayout(self.tab1.layout)

#TAB2
        self.connectionStatus = QtWidgets.QLabel('No connection')
        self.connectionStatus.setStyleSheet("color: black;")
        
        self.tab2.layout.addWidget(self.connectionStatus,                   0,0,1,1)
        self.tab2.layout.addWidget(self.Settings_table,                     5,0,10,1)
        
        self.setCentralWidget(self.tabs)
        self.tab2.setLayout(self.tab2.layout)
        self.setGeometry(0, 30, 300, (len(self.lines)*100)+150)   
    
    def save_calibration(self):
        headings = ["Ach","Dch","wav.","minVal","maxVal","minPow","maxPow","Eqn.","P1","P2"]
        self.dataframe.to_csv("%sLaserCalibration.txt" %(self.address), mode='w', header=headings, index=True, sep ='\t')


    def connect(self, state, board_num=0):
        if state == "C" and not self.connection:
            
            devices = ul.get_daq_device_inventory(InterfaceType.ANY)
            print(devices)
            if len(devices) == 0:
                print('USB-3103 laser controller not found')
            else:
                # ul.release_daq_device(board_num)
                print(ul)
                # create connection 
                ul.create_daq_device(board_num, devices[0])
                print(2.5)
                daq_dev_info = DaqDeviceInfo(board_num)
                # setup analog
                ao_info = daq_dev_info.get_ao_info()
                self.ao_range = ao_info.supported_ranges[0]
                # setup digital
                dio_info = daq_dev_info.get_dio_info()
                self.port = next((port for port in dio_info.port_info if port.supports_output),None)
                ul.d_config_port(0,self.port.type, DigitalIODirection.OUT)
                print('connected')
                self.connectionStatus.setText('Connected')
                self.connection = True
                
        if state == "D" and self.connection:
            ul.release_daq_device(board_num)
            self.connection = False
            self.connectionStatus.setText('No connection')


    def closeEvent(self, event):
        if self.connection:
            ul.release_daq_device(self.board_num)
            self.save_calibration()

    
if __name__ == '__main__':
    app = 0
    app = QtWidgets.QApplication(sys.argv)
    gui = Lasers()
    gui.show()
    app.exec_()        
        
        
        
        
    