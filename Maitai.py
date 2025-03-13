# -*- coding: utf-8 -*-
"""
Created on Fri Apr 13 16:04:34 2018

@author: sil1r12
"""
import serial
from PyQt4 import QtGui, QtCore
from time import sleep


class Maitai(QtGui.QWidget):
    def __init__(self, parent, name):
        super(Maitai, self).__init__(parent)
        self.flag_CONNECTED = False
        self.laser_warm = False
        self.wavelength = 710
        self.name = name


    def connect(self):

        self.parent().ConnMaitai.LED_colour('y')
        try:
            sleep(1) #what is this for?
            self.maitai =  serial.Serial(port='COM5', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.5, xonxoff=0, rtscts=0)
            ready = False
            while not ready:
                self.maitai.write("READ:PCTW?\n")
                temp = float(self.maitai.readline()[:-2])
                if temp == 0:
        #            cold start...
                    print "laser cold, issuing ON command"
                    self.maitai.write("ON\n")
                    sleep(2)
                elif temp >0 and temp <100:
                    print "laser warming up, temp: %s%" %temp
        #            wait whilst warming up....
                    sleep(2)
                elif temp == 100:
                    print "temp at 100%, issuing ON command"
        #            ready...
                    ready = True
                    sleep(0.2)
                    self.maitai.write("ON\n")

            ready = False
            while not ready:
                self.maitai.write("READ:POW?\n")
                power = float(self.maitai.readline()[:-2])
                if power < 0.1:
        #            wait...
                    print "power ramping up, power: %sW" %power
                    sleep(2)
                else:
                    print "Power above 0.1W"
                    sleep(1)
                    print "opening shutter"
                    self.maitai.write("SHUT 1\n")
                    ready = True
            self.flag_CONNECTED = True
            self.parent().ConnMaitai.LED_colour('g')
            self.parent().information("Connected to Maitai",1)
            self.parent().illumination_settings(6,self.get_wavelength())
            for item in self.parent().maitai_widgets: item.setEnabled(True)
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(False)
            self.timer.timeout.connect(self.laser_stable_self_report)
            self.timer.start(0.5)

        except Exception, e:
            if self.maitai:
                self.maitai.close()
            self.parent().information("Error starting up Maitai: %s" %e,0)
            self.parent().ConnMaitai.LED_colour('r')
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(True)   #       move to init?
            self.timer.timeout.connect(self.uncheck)   #move to init?
            self.timer.start(1)
            self.flag_CONNECTED = False


    def close(self):  # This closes serial connection only, does not shut down laser.
        if self.flag_CONNECTED == True:
            self.maitai.close()
            self.parent().ConnMaitai.LED_colour('r')
            self.flag_CONNECTED = False
            for item in self.parent().maitai_widgets: item.setEnabled(False)

    def uncheck(self):
        self.parent().ConnMaitai.checkbox.setChecked(False)

    def maitai_shutdown(self):
        print "closing shutter and issuing OFF command"
        self.maitai.write("SHUT 0\n")
        self.maitai.write("OFF\n")
#         how to confirm off?
        power_down = False
        while not power_down:
            self.maitai.write("READ:POW?\n")
            power = float(self.maitai.readline()[:-2])
            if power > 0.01:
    #            wait...
                print "powering down, power: %sW" %power
                sleep(2)
            else:
                print "power < 0.01W"
                power_down = True
                return True
        return False

    def get_wavelength(self):
        self.maitai.write("WAV?\n")
        sleep(0.1)                  #important, need this delay
        while self.maitai.in_waiting:
            frommt = self.maitai.readline()
            try:
                wav = int(frommt[:-3])
            except:
                pass
        self.wavelength = wav
        return wav

    def set_wavelength(self, w):
        if self.flag_CONNECTED == True:
            w = int(w)
            if w<710 or w>990:
                print 'wavelength not in correct range'
                return False
            self.maitai.write("WAV %s\n" %w)
            self.wavelength = w
            return True

    def clear_buffer(self):
        while self.maitai.in_waiting:
            self.maitai.readline()

    def laser_stable(self): # for use in laser tuning during timelapse (blocking)
        # This function will not return for at least 1 second, could the 'sleep' be reduced?
        count = 0
        try:
            while count < 2:
                self.maitai.write("READ:AHIS?\n")
                history = self.maitai.readline().split(' ')
                for i, item in enumerate(history):      # find first instance of '43'
                    if item[0:2] == '43': break
                if history[i][2] == '1':                # test if stable
                    count = count + 1                   # if stable then increment counter and wait before next test
                    sleep(0.5)                          # this works for the thread but it can't be used from the main GUI due to blocking
                else:
#                    self.parent().Maitai_tuned.setPixmap(QtGui.QPixmap('light_r.png'))
                    return False                        # if not then exit False
#            self.parent().Maitai_tuned.setPixmap(QtGui.QPixmap('light_g.png'))
            return True                                 # if counter reaches 2 exit True
        except:
            pass
#            self.parent().Maitai_tuned.setPixmap(QtGui.QPixmap('light_r.png'))
            return False

    def laser_stable_self_report(self): # for use in GUI reporting of laser tuning (non-blocking)
        if not self.parent().in_experiment:
            try:
                self.maitai.write("READ:AHIS?\n")
                history = self.maitai.readline().split(' ')
                for i, item in enumerate(history):      # find first instance of '43'
                    if item[0:2] == '43': break
                if history[i][2] == '1':                # test if stable
                    self.parent().Maitai_tuned.setPixmap(QtGui.QPixmap('light_g.png'))
                    return True
                else:
                    self.parent().Maitai_tuned.setPixmap(QtGui.QPixmap('light_r.png'))
                    return False                        # if not then exit False
            except:
                self.parent().Maitai_tuned.setPixmap(QtGui.QPixmap('light_r.png'))
                return False
        else:
            self.parent().Maitai_tuned.setPixmap(QtGui.QPixmap('light_y.png'))













