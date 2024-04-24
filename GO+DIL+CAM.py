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

nZ          = 15    #Number of slices
sZ          = 1    #slice separation (micrometers)
exp         = 100   #camera exposure time (ms)

# =============================================================================
GO_COM = 'COM4'
DIL_COM = 'COM5'
codec = 'utf8'
# =============================================================================
#  IMPORTS
# =============================================================================
from pylablib.devices import DCAM
import serial, time

# =============================================================================
# FUNCTIONS
# =============================================================================

def clear_buffer():
    print('clear buffer', GO.inWaiting(), 'bytes')
    while GO.inWaiting() > 0: GO.read()
    print('clear buffer', GO.inWaiting(), 'bytes')
    
def stage_movement(axis): #tests stage to make sure movement is complete
    #get stage status
    GO.write(bytes("RS%s\n" %axis, codec))
    Status = GO.readline()[1:]
    # print("stage status raw:", Status)
    Status = Status.decode(codec).split(axis)[1][0]
    stage_OK = ["0","2","4"]
    if(Status in stage_OK): return 0  #if stage is stationary
    if(Status == "9"): 
        GO.write(bytes("RE%s\n" %axis, codec))
        Error = GO.readline().decode(codec).split(axis)[1][0]
        print('Stage Error code:', Error)
        return 2
    else: return 1   # stage moving, or error

def get_position(axis):
    GO.write(bytes("RP%s\n" %axis, codec))
    return float(GO.readline().decode(codec).split(axis)[1][:-1])

def go_to_position(x=None, y=None, z=None):
    string = "GT"
    if(x != None): 
        string = string + ' '
        string = string + 'x'
        string = string + str(x)
    if(y != None): 
        string = string + ' '
        string = string + 'y'
        string = string + str(y)                                  
    if(z != None):                                                        
        string = string + ' '
        string = string + 'z'
        string = string + str(z)
    string= string + ';\n'
    GO.write(bytes(string, "utf8"))
    
def set_stage_triggers(axis, step):
    GO.write(bytes("TO %s%s;\n" %(axis,float(step)), codec))
    GO.write(bytes("TI %s%s;\n" %(axis,float(step)), codec))
        
def cam_settings(exp=None,bin_=None):
    if exp!=None:   CAM.set_attribute_value("EXPOSURE TIME", exp)
    if bin_!=None:  CAM.set_attribute_value("BINNING", bin_)
# =============================================================================
# SCRIPT
# =============================================================================
stage_error = False
# SETUP 
GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
print('n cameras:', DCAM.get_cameras_number())
CAM = DCAM.DCAMCamera()

cam_settings(exp=0.1, bin_=1, trigger='hardware')
CAM.setup_acquisition(mode="sequence", nframes = nZ)


# move to start position. Perform z-stack centered around current position
#get start position
SPz = get_position('z')
print('Stage start position:', SPz, 'um')

go_to_position(z=SPz + (((nZ-1)*sZ)/-2.0)) # start position minus half of the range

# delay for stage movement
while(stage_movement('z')==1): pass
    
    
# Activate Z-step on DIL controller
for i in range(nZ):
    print(i, get_position('z'))
    #trigger image 
    
    # get image
    CAM.wait_for_frame()
    frame = CAM.read_oldest_image()
    # advance stage
    DIL.write(b"/Z;\r")
    while(stage_movement('z')==1): pass
        
    

# # poll camera for images
# # start timer

# # return camera to start position
go_to_position(z=SPz, x=100, y=100)
while(stage_movement('z')==1): pass
print('return position:', get_position('z'))
# =============================================================================
# close connections
# =============================================================================

GO.close()
DIL.close()
CAM.close()