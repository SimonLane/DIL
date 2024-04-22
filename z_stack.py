# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 13:06:57 2024
@author: sil1r12

# =============================================================================
# BASIC Z-Stack SCRIPT
# =============================================================================
"""

# =============================================================================
# PARAMETERS
# =============================================================================

nZ          = 10    #Number of slices
sZ          = 10    #slice separation (micrometers)
exp         = 100   #camera exposure time (ms)

# =============================================================================
GO_COM = 'COM3'
DIL_COM = 'COM5'
FILTER_COM = 'COM6'
# =============================================================================
#  IMPORTS
# =============================================================================

from pylablib.devices import DCAM
import serial, time


# =============================================================================
# SCRIPT
# =============================================================================
#CAMERA connection
print('n cameras', DCAM.get_cameras_number())
cam = DCAM.DCAMCamera()

#STAGE serial connection
GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)

#CONTROLLER serial connection
DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)

# SETUP - CAMERA
# allocate buffer
# set mode, binning, exposure
# set up trigger


# SETUP - STAGE
# move to start position. Perform z-stack centered around current position
start_move = nZ*sZ/-2
GO.write(b"MRZ%s" %(start_move))
# set trigger in
GO.write(b"TIZ%s" %(sZ))
# set trigger out
GO.write(b"TOZ5s" %(sZ))
# poll for stage movement
while(stage_movement()):
    time.sleep(0.1)
    
# Activate Z-scan on DIL controller
DIL.write(b"/Stack.%s.%s.%s\r" %(nZ, sZ, exp))

# poll camera for images
# start timer
# =============================================================================
# close connections
# =============================================================================
cam.close()
DIL.close()

# =============================================================================
# FUNCTIONS
# =============================================================================

def stage_movement():
    pass
    #get stage status
    #if moving return True
    #if not moving return false