# -*- coding: utf-8 -*-
"""
Created on Sun May 05 16:06:51 2024
@author: sil1r12

# =============================================================================
# Z-Stack SCRIPT
+ folder management
# =============================================================================
"""

# =============================================================================
# PARAMETERS
# =============================================================================

nZ          = 500    #Number of slices
sZ          = 0.5   #slice separation (micrometers)
exp         = 1000   #camera exposure time (ms)
root_location = r"D:/Light_Sheet_Images/Data/"
name        = "561nm_VisBank_BP600-40_Organoid_51-4_AgarCart3_1"
# name        = "488nm 500LP-60"
# name        = "561nm 600LP"

verbose = False     #for debugging

# =============================================================================
GO_COM = 'COM7'
DIL_COM = 'COM6'
codec = 'utf8'
# =============================================================================
#  IMPORTS
# =============================================================================
from pylablib.devices import DCAM
import serial, time, datetime, os
import imageio

# =============================================================================
# FUNCTIONS
# =============================================================================

def clear_buffer():
    print('clear buffer', GO.inWaiting(), 'bytes')
    while GO.inWaiting() > 0: GO.read()
    print('clear buffer', GO.inWaiting(), 'bytes')
    

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
    print("TO %s%s;\r\n" %(axis,float(step)))
    print("TI %s%s;\r\n" %(axis,float(step)))
    GO.write(bytes("TO %s%s;\r\n" %(axis,float(step)), codec))
    GO.write(bytes("TI %s%s;\r\n" %(axis,float(step)), codec))
        
def cam_settings(exp=None,bin_=None, bits=None, trigger=None):
    if exp!=None:       CAM.set_attribute_value("EXPOSURE TIME", exp)
    if bin_!=None:      CAM.set_attribute_value("BINNING", bin_)
    if bits!=None:      CAM.set_attribute_value("BIT_PER_CHANNEL", bits)
    if trigger!=None:   trigger_mode(trigger)
    
def trigger_mode(mode):        
    if mode == 'hardware': #hardware
       #INPUT TRIGGER
       CAM.set_attribute_value('TRIGGER SOURCE', 2)            # 1: Internal;  2: External;    3: Software;    4: Master Pulse;
       CAM.set_attribute_value('trigger_mode', 1)              # 1: Normal;    6: Start;
       CAM.set_attribute_value('trigger_polarity', 2)          # 1: Negative;  2: Positive;
       CAM.set_attribute_value('trigger_active', 2)            # 1: Edge;      2: Level;       3: SyncReadout
       CAM.set_attribute_value('trigger_global_exposure', 3)   # 3: Delayed;   5: Global Reset;

       # CAMERA settings
       CAM.set_attribute_value('sensor_mode', 1)               # 1: Area;      12: Progressive;    14: Split View;     16: Dual Lightsheet;
       #CAM.set_attribute_value('timing_exposure', 1)          # 1: After Readout;     3: Rolling;
       CAM.set_attribute_value('image_pixel_type',2)           # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3
       CAM.set_attribute_value('buffer_pixel_type',2)          # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3

       #OUTPUT settings
       # output 1
              # oscilloscope shows that kind needs to be 'trigger ready'
       CAM.set_attribute_value('output_trigger_source[0]', 2)      #Start on input trigger (6), start on readout (2)
       CAM.set_attribute_value('output_trigger_polarity[0]', 2)    #Positive
       CAM.set_attribute_value('output_trigger_kind[0]', 4)        #trigger ready = 4
       CAM.set_attribute_value('output_trigger_base_sensor[0]', 16) # All views???
       CAM.set_attribute_value('output_trigger_active[0]', 1)      # edge
       CAM.set_attribute_value('output_trigger_delay[0]', 0)      # 
       CAM.set_attribute_value('output_trigger_period[0]', 0.001)      # 
    
def new_folder(root, sZ, Exp, name):
    now = datetime.datetime.now()
    units = 'um'
    if(sZ<1): #step size is sub-micron, change units to nm
        sZ = sZ*1000
        units = 'nm'
    folder = r"%s%s-%s-%s %s_%s_%s (%s%s, %sms) - %s" %(root,now.year, now.month, now.day,   
                                                        now.hour,now.minute,now.second, 
                                                        sZ,units, Exp, name)
    os.makedirs(folder)

    return folder

def stage_status(axis): #tests stage to make sure movement is complete
    #get stage status
    GO.write(bytes("RS%s\n" %axis, codec))
    Status = GO.readline()[1:]
    # print("stage status raw:", Status)
    Status = Status.decode(codec).split(axis)[1][0]
    if Status.isdigit():
        return int(Status) 
    
    else: return -1   # not sure what the status is
    
def stage_ready(timeout, axis):
    time.sleep(0.01)                    #needed to prevent stage returning status '2' before the move starts
    t0 = time.time()
    while True:
        s = stage_status(axis)
        # print(s)
        if s==1 or s==3: #stage is still moving, reset timer
            t0 = time.time()
        if s in [2,4]: # stage has stopped
            return True
        if s == 9: #error code
            # print('error code')
            return False
        if(time.time() > t0 + timeout): 
            # print('stage timeout')
            return False
        pass

    
# =============================================================================
# SCRIPT
# =============================================================================
stage_error = False
# SETUP 
GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
print('n cameras:', DCAM.get_cameras_number())
CAM = DCAM.DCAMCamera()

cam_settings(exp=exp, bin_=1, trigger='hardware')

CAM.setup_acquisition(mode="sequence", nframes = nZ)

folder = new_folder(root_location,sZ,exp, name)
print('Expt. saved to: ', folder)

# move to start position. Perform z-stack centered around current position
#get start position
SPx = get_position('x')
SPy = get_position('y')
SPz = get_position('z')
print('Stage start position:', SPx, SPy, SPz,'um')

go_to_position(z=SPz + (((nZ-1)*sZ)/-2.0)) # start position minus half of the range


set_stage_triggers('z', sZ)
# delay for stage movement
t0 = time.time()
#poll for stage status
if(stage_ready(1, 'z')): pass
    
CAM.start_acquisition()    
while(DIL.inWaiting()):
    print("DIL", DIL.readline())

DIL.write(bytes("/Stack.%s.%s;\r" %(nZ,exp), codec))

verbose = True

for i in range(nZ):
    if(verbose): print("_______________") 
     
    while(DIL.inWaiting()):
        print("DIL:", DIL.readline())
    print(i) 
    t0 = time.time()
    CAM.wait_for_frame()
    if(verbose): print("wait for image: \t", time.time() - t0, "(s)")
    t0 = time.time()
    frame = CAM.read_oldest_image()
    if(verbose): print("get frame: \t\t\t", time.time() - t0, "(s)")
    t0 = time.time()
    imageio.imwrite('%s\\z%s.tif' %(folder,i), frame)
    if(verbose): print("save frame: \t\t", time.time() - t0, "(s)")
    t0 = time.time()
    while(DIL.inWaiting()):
        print("DIL", DIL.readline())
    if(verbose): print("check serial: \t\t", time.time() - t0, "(s)")
    
CAM.stop_acquisition()

# # return camera to start position
go_to_position(z=SPz, x=SPx, y=SPy)
if(stage_ready(1, 'z')): pass
print('return position:', get_position('z'))
# =============================================================================
# close connections
# =============================================================================

GO.close()
DIL.close()
CAM.close()