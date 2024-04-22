#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 17 15:02:59 2018

@author: sil1r12
"""
from PyQt4          import QtGui, QtCore

import numpy, time, math
import pyqtgraph as pg



class Camera(QtGui.QWidget):
    def __init__(self, parent, cam_name, mmc):
        super(Camera, self).__init__(parent)
        self.flag_CONNECTED = False
        self.name = cam_name
        self.mmc = mmc
        self.live_imaging = False
#        pos = numpy.array([0., 0.01, 0.011, 0.99, 0.991, 1.])
#        color = numpy.array([[0,0,255,255], [0,0,255,255], [0,0,0,255], [255, 255, 255, 255], [255, 0, 0, 255], [255, 0, 0, 255]], dtype=numpy.ubyte)
#        self.cmap = pg.ColorMap(pos, color)
        self.cmap = pg.ColorMap([0.0,0.25,0.50,0.75,1.0],[[0,0,0,255],[0,0,255,255],[0,255,0,255],[255,0,0,255],[255,255,255],[255,255,255,255]])
#        self.heatmap = pg.ColorMap()

        self.defaultcmap = pg.ColorMap([0.0,1.0],[[0,0,0,255],[255,255,255,255]])
        self.max_pixel_value = 255                                              #default to 255, then update after querying camera
        self.display_mode = 0

#        self.shutter_close_time = 5                                          #50ms opening time (August 2018), 5ms Sept

        self.binning = 1
        self.angle = 22
        self.offset = 0

        pen = QtGui.QPen()
        pen.setWidth(3)
        pen.setColor(QtGui.QColor('red'))

        self.line1 = QtGui.QGraphicsLineItem()
        self.line1.setPen(pen)
        self.line1.setOpacity(0.5)

        self.line2 = QtGui.QGraphicsLineItem()
        self.line2.setPen(pen)
        self.line2.setOpacity(0.5)

        self.line3 = QtGui.QGraphicsLineItem()
        self.line3.setPen(pen)
        self.line3.setOpacity(0.5)
        
    def connect(self):
        try:
            self.parent().ConnCamera.LED_colour('y')
            if self.name == "Flash 4":
                self.mmc.loadDevice("Flash 4", 'HamamatsuHam', 'HamamatsuHam_DCAM')
                time.sleep(1)  #important delay, camera needs time to instalise before it receives subsequent commands
#set cooling to MAX, after each power down camera forgets this setting!
#                self.mmc.setProperty("Flash 4", 'SENSOR COOLER', "MAX") - doesn't work
            else:
                self.mmc.loadDevice("DemoCam", 'DemoCamera', 'DCam')

            self.mmc.initializeDevice("Flash 4")
            self.mmc.setCameraDevice("Flash 4")
            self.mmc.setProperty("Flash 4", "ScanMode","1") #readout mode: [normal, 2, 10ms] or [slow, 1, 33ms]
            self.flag_CONNECTED = True
            self.parent().ConnCamera.LED_colour('g')
            for item in self.parent().camera_widgets:
                item.setEnabled(True)
            self.parent().information("Instalised camera '%s'" %self.name,1)
            self.max_pixel_value = pow(2,self.mmc.getImageBitDepth()) -1
#            print 'camera max value', self.max_pixel_value

        except Exception,e:
            self.parent().ConnCamera.LED_colour('r')
            self.parent().information('Error during %s instalisation: %s' %(self.name,e),0)
            print e
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.uncheck)
            self.timer.start(2500)
            self.flag_CONNECTED = False

    def uncheck(self):
        self.parent().ConnCamera.checkbox.setChecked(False)

    def close(self):
        if self.flag_CONNECTED == True:
            if self.live_imaging:
                try: self.frametimer.stop()
                except: pass
                self.mmc.stopSequenceAcquisition()
                self.mmc.clearCircularBuffer
            for item in self.parent().camera_widgets: item.setEnabled(False)
            self.mmc.unloadDevice("Flash 4")
            self.parent().ConnCamera.LED_colour('r')
            self.timer = QtCore.QTimer()
            self.timer.setSingleShot(True)   #       move to init?
            self.timer.timeout.connect(self.uncheck)   #move to init?
            self.timer.start(1)
            self.flag_CONNECTED = False

    def timelapse_grab(self):
        self.mmc.snapImage()
        return self.mmc.getImage()

    def set_exposure(self, e):
        if self.flag_CONNECTED == True:
            if self.live_imaging: #if live imaging is happeneing then breifly stop and restart with new exposure
                self.mmc.stopSequenceAcquisition()
                self.mmc.setExposure(int(e))
                self.mmc.startContinuousSequenceAcquisition(int(e))
            else: # otherwise simply set exposure
                self.mmc.setExposure(int(e))
        if not self.parent().in_experiment: #don't alter GUI elements from thread
            self.parent().setExposure.setText("%s" %e)


    def set_binning(self, b):
        if not self.parent().in_experiment: #don't alter GUI elements from thread
            self.parent().binningMenu.setCurrentIndex(b)
        if   b == 0: b=1
        elif b == 1: b=2
        elif b == 2: b=4
        self.binning = b
        if self.flag_CONNECTED == True:
            if self.name == "Flash 4":
                b = "%sx%s" %(b,b)     #Only do this on the Hamamatsu camera as it has different binning format
            else:
                b = '%s' %(b)
            if self.live_imaging: #if live imaging is happeneing then breifly stop and restart with new exposure
                self.mmc.stopSequenceAcquisition()

                self.mmc.setProperty("Flash 4", 'Binning', "%s" %b)
                e = self.parent().setExposure.text()
                self.mmc.startContinuousSequenceAcquisition(int(e))
            else: # otherwise simply set directly
                self.mmc.setProperty("Flash 4", 'Binning', "%s" %b)


    def grab_frame(self):
        if self.live_imaging:
            self.live_view()                                  #call live function to stop live imaging
        if self.mmc.isSequenceRunning():
            self.mmc.stopSequenceAcquisition()                #stop sequence acqusition to be sure
        if self.flag_CONNECTED == True:
        #galvo on
            self.parent().USB_HUB.galvo_on()
            time.sleep(0.5)
        #get settings
            exposure = int(self.parent().setExposure.text())
            binning = self.parent().binningMenu.currentIndex()

        #set settings
            self.parent().illumination_source(9) #force current settings (redundency)
            self.set_binning(binning)
            self.set_exposure(exposure)
            
        #grab one image through arduino sync capture function
            self.mmc.setAutoShutter(False)                    #must set before starting acquisition to enforce

            self.external_mode('LEVEL')
            self.mmc.initializeCircularBuffer()
            self.mmc.clearCircularBuffer()
            
            self.mmc.prepareSequenceAcquisition("Flash 4")
            self.mmc.startSequenceAcquisition("Flash 4",1,1,True)
            rc = self.mmc.getRemainingImageCount() #should be zero

            self.parent().Arduino.sync_acquire(exposure)
            
#   To DO - put the await image into a new thread so as not to block the GUI thread. 
#   Meanwhile set gui to enable(false) to avoid conflicts with user interactions during 
#   acqusistion and provide an abort option on the grab button
#   will prevent GUI hanging on long exposures
            
        #await image
            rc = self.mmc.getRemainingImageCount() #should be zero
            while self.mmc.getRemainingImageCount() == rc: pass

            self.current_img = self.mmc.getLastImage()
            self.mmc.stopSequenceAcquisition()

            self.parent().USB_HUB.galvo_off()
            self.parent().Arduino.LEDoff()
            self.parent().Arduino.closeShutter()
            self.display_image(self.current_img)
            self.internal_mode() #reset camera to internal mode


    def live_view(self):
        if self.flag_CONNECTED == True:
            if self.mmc.isSequenceRunning():
                self.mmc.stopSequenceAcquisition()
            if not self.live_imaging:
                self.parent().illumination_source(9) #force current settings
                exposure = self.parent().setExposure.text()
                binning = self.parent().binningMenu.currentIndex()
                self.set_binning(binning)
                
                #galvo on
                self.parent().USB_HUB.galvo_on()
                self.parent().Arduino.openShutter()

                self.mmc.setAutoShutter(False)
                self.mmc.startContinuousSequenceAcquisition(int(exposure))
                self.live_imaging = True
                self.frametimer = QtCore.QTimer()
                self.frametimer.setSingleShot(False)
                self.frametimer.timeout.connect(self.grab_live)
                self.frametimer.start(1)
                self.parent().LiveButton.setText("Stop")

            else:
                self.frametimer.stop()
                self.parent().Arduino.closeShutter()
                self.parent().USB_HUB.galvo_off()
                self.live_imaging = False
                self.parent().LiveButton.setText("Live")
                self.mmc.stopSequenceAcquisition()
                self.mmc.setAutoShutter(True)
                self.mmc.clearCircularBuffer()
                

    def grab_live(self):
        if self.flag_CONNECTED == True:
            if self.mmc.getRemainingImageCount()>0:
                self.current_img = self.mmc.getLastImage()
                self.display_image(self.current_img)

    def displayMode(self):
        self.display_mode = self.parent().view_modes_group.checkedId()
        self.display_colour_mode = self.parent().view_colour_modes_group.checkedId()
        if self.display_colour_mode == 0:
            self.parent().imagewidget.setColorMap(self.defaultcmap)
        if self.display_colour_mode == 1:
            self.parent().imagewidget.setColorMap(self.cmap)

    def updateGuides(self):
        self.angle = int(self.parent().guidesangle.text())
        self.offset = int(self.parent().guidesoffset.text())
        if self.parent().guidescheckbox.isChecked():
            self.parent().imagewidget.getView().addItem(self.line1)
            self.parent().imagewidget.getView().addItem(self.line2)
            self.parent().imagewidget.getView().addItem(self.line3)
        else:
            if self.parent().imagewidget.getView().items > 3:
                self.parent().imagewidget.getView().removeItem(self.line1)
                self.parent().imagewidget.getView().removeItem(self.line2)
                self.parent().imagewidget.getView().removeItem(self.line3)


    def display_image(self, image):
        image = numpy.rot90(numpy.fliplr(image),1) #        image flip (horizontal axis) and rotation (90 deg anti-clockwise)
        #get 'mode' from radio state (manual, auto, saturation check)
        if self.display_mode == 0:
            self.parent().imagewidget.setImage(image, autoLevels=True)
        if self.display_mode == 1:
            self.parent().imagewidget.setImage(image, autoLevels=False)

        


    def external_mode(self, m):
#        print 'setting external mode:', m
        self.mmc.setProperty("Flash 4", 'TRIGGER SOURCE', 'EXTERNAL')
        if m == 'EDGE':  self.mmc.setProperty("Flash 4", 'TRIGGER ACTIVE', 'EDGE')
        if m == 'LEVEL': self.mmc.setProperty("Flash 4", 'TRIGGER ACTIVE', 'LEVEL')
        self.mmc.setProperty("Flash 4", 'Trigger', 'NORMAL')
        self.mmc.setProperty("Flash 4", "TriggerPolarity", "POSITIVE")
        self.mmc.setProperty("Flash 4", "TRIGGER GLOBAL EXPOSURE", "GLOBAL RESET")

# not currently used by arduino during LEVEL mode
        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER KIND[0]', 'TRIGGER READY')
        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER POLARITY[0]', 'POSITIVE')
        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER SOURCE[0]', 'READOUT END')
#        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER KIND[0]', 'EXPOSURE')
#        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER POLARITY[0]', 'POSITIVE')
#        self.mmc.setProperty("Flash 4", 'TRIGGER DELAY', '0')

#OUTPUT 2 - used for timing and debugging
#        output signal corresponding to readout end
#        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER KIND[1]', 'PROGRAMABLE')
#        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER POLARITY[1]', 'POSITIVE')
#        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER SOURCE[1]', 'READOUT END')
#        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER DELAY[1]', '0.0000')

#        output signal high during exposure
        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER KIND[1]', 'EXPOSURE')
        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER POLARITY[1]', 'POSITIVE')
        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER DELAY[1]', '0.0000')


    def internal_mode(self):
        self.mmc.setProperty("Flash 4", 'TRIGGER SOURCE', 'INTERNAL')
        self.mmc.setProperty("Flash 4", 'TRIGGER ACTIVE', 'EDGE')
        self.mmc.setProperty("Flash 4", 'Trigger', 'NORMAL')
        self.mmc.setProperty("Flash 4", "TriggerPolarity", "POSITIVE")
        self.mmc.setProperty("Flash 4", "TRIGGER GLOBAL EXPOSURE", "DELAYED")
        self.mmc.setProperty("Flash 4", 'TRIGGER DELAY', '0')
        self.mmc.setProperty("Flash 4", 'OUTPUT TRIGGER KIND[0]', 'TRIGGER READY')

    def clear_camera_buffer(self):
        self.mmc.clearCircularBuffer()
        return self.mmc.getRemainingImageCount()

    def await_image(self):
        ni =  self.mmc.getRemainingImageCount()
        while self.mmc.getRemainingImageCount() == ni: pass
        return self.mmc.getLastImage()

    def end_external(self):
        self.clear_camera_buffer()
        self.mmc.stopSequenceAcquisition()
        self.mmc.setProperty("Flash 4", 'TRIGGER SOURCE', 'INTERNAL')

    def is_camera_loaded(self):
        f = self.mmc.getLoadedDevices()
        if "Flash 4" in f: return True
        return False









