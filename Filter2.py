#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 17 15:30:06 2018

@author: sil1r12
"""

from PyQt4 import QtGui, QtCore
import serial, time


class Filter2(QtGui.QWidget):
    def __init__(self, parent, name, port):
        super(Filter2, self).__init__(parent)
        self.flag_CONNECTED = False
        self.position = -1
        self.port = port
        self.name = name
        

    def connect(self):
        try:
            self.parent().ConnFilter.LED_colour('y')
            self.filter = serial.Serial(port=self.port, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=0.07)
            time.sleep(1)
            while self.filter.inWaiting():
                 self.filter.readlines()
            self.filter.write("speed=1\r")
            time.sleep(0.1)
            self.filter.write("trig=1\r")
            time.sleep(0.1)
            self.filter.write("pos=1\r")
            time.sleep(0.1)
            self.filter.write("sensors=0\r")
            time.sleep(0.1)
            for i in range(3):
                try:
                    while self.filter.inWaiting():
                         self.filter.readlines()
                    self.filter.write("trig?\r")
                    time.sleep(0.5)
                    responce =  self.filter.readlines()[0].split('\r')
                    if int(responce[-2]) == 1: print 'filter wheel in external mode'
                    break
                except:
                    print 'connecting to filter, attempt:', i
            self.flag_CONNECTED = True
            self.parent().ConnFilter.LED_colour('g')
            self.parent().information("Instalised filter '%s'" %self.name,1)
#            self.get_position()
#            set current filter position to GUI
#            self.parent().setFilter.setCurrentIndex(self.position)
            for item in self.parent().filter_widgets: item.setEnabled(True)
            self.parent().Arduino.reset_filter_flag()
            
        except Exception,e:
            self.parent().information("Error connecting to Filter Wheel: %s" %e,0)
            self.filter.close()
            self.parent().ConnFilter.LED_colour('r')
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(True)   #       move to init?
            self.timer.timeout.connect(self.uncheck)   #move to init?
            self.timer.start(1)

    def close(self):
        if self.flag_CONNECTED == True:
            self.filter.close()
            self.flag_CONNECTED = False
            self.parent().ConnFilter.LED_colour('r')
            for item in self.parent().filter_widgets: item.setEnabled(False)

    def uncheck(self):
        self.parent().ConnFilter.checkbox.setChecked(False)

    def set_position(self,n):
        if self.flag_CONNECTED:
            n=int(n)
            self.filter.write("pos=%s\r" %(n+1))
            self.position = n
        else: print "Filter wheel not connected"

    def get_position(self):
        self.filter.write("pos?\r")
        while self.filter.inWaiting(): self.filter.readlines()  #clear buffer
        p = self.filter.readlines()[0].split('\r')[1]
        if isinstance(p, (int)):
            self.position = p
            return int(self.position)
        else:
            return -1
        



