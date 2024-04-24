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
codec = 'utf8'
# =============================================================================
#  IMPORTS
# =============================================================================

# from pylablib.devices import DCAM
import serial, time

# =============================================================================
# FUNCTIONS
# =============================================================================

#¬¬¬¬¬STAGE FUNCTIONS¬¬¬¬¬¬¬#
def clear_buffer():
    print('clear buffer', GO.inWaiting(), 'bytes')
    while GO.inWaiting() > 0: GO.read()
    print('clear buffer', GO.inWaiting(), 'bytes')
    
def stage_movement(axis): #tests stage to make sure movement is complete
    #get stage status
    GO.write(bytes("RS%s\n" %axis, codec))
    Status = GO.readline()[1:]
    print("stage status raw:", Status)
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
    ret = GO.readline()
    print(ret)
    return float(ret.decode(codec).split(axis)[1][:-1])

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
    
#¬¬¬¬¬DIL FUNCTIONS¬¬¬¬¬¬¬#



# =============================================================================
# SCRIPT
# =============================================================================
#CAMERA connection
# print('n cameras:', DCAM.get_cameras_number())
# cam = DCAM.DCAMCamera()
stage_error = False
GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
# DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)

# SETUP - CAMERA
# allocate buffer
# set mode, binning, exposure
# set up trigger


# SETUP - STAGE

#get start position
SPz = get_position('z')
print('Stage start position:', SPz, 'um')

go_to_position(z=SPz + (((nZ-1)*sZ)/-2.0)) # start position minus half of the range

# poll for stage movement
while(True):
    sm = stage_movement('z')
    if sm == 0: break  #stage stationary
    if sm == 2: stage_error = True; break  #error
    time.sleep(0.01)
    
if not stage_error:
    # set up stage triggers
    set_stage_triggers('z', 10)  
    
    EPz = get_position('z')
    print("Z end position: %s um" %EPz)
    
    # # poll camera for images
    # # start timer
    
    # # return camera to start position
    go_to_position(z=SPz, x=100, y=100)
# Activate Z-scan on DIL controller
# DIL.write(b"/Stack.%s.%s.%s\r" %(nZ, sZ, exp))

# poll camera for images
# start timer
# =============================================================================
# close connections
# =============================================================================
# cam.close()
# DIL.close()
GO.close()
