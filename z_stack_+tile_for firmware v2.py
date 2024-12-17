# -*- coding: utf-8 -*-
"""
Created on Sun Sept 24 16:06:51 2024
@author: sil1r12

# =============================================================================
# Z-Stack SCRIPT
+ folder management
+ function to delay for stage movement
+ tiles
# =============================================================================
"""

# =============================================================================
# PARAMETERS
# =============================================================================
# stack settings
nZ              = 5          # Number of slices
sZ              = 10          # slice separation (micrometers)

# Camera settings
exp             = 50            # camera exposure time (ms)

# Tile settings
FOV             = 549.2        # ums
tiles           = 2            # [1,2,3...]  1x1, 2x2 or 3x3 tiles etc
tile_overlap    = 0.1          # 0.1 = 10% overlap, req for post acquisition stitching

# save settings 
root_location   = r"D:/Light_Sheet_Images/Data/"
name            = "hoechst tile test"


verbose = True     #for debugging

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
    
    if step == 0:
        print('Stage triggers disabled')
        GO.write(bytes("TO %s0;\r\n" %(axis), codec)) 
        GO.write(bytes("TI %s0;\r\n"  %(axis), codec))
    else:
        print('stage trigger distance: %sum' %(step))
        GO.write(bytes("TO %s0.0;\r\n" %(axis), codec)) # trigger at target
        GO.write(bytes("TI %s%s;\r\n"  %(axis,float(step)), codec))
           
def cam_settings(exp=None,bin_=None, bits=None, trigger=None):
    if trigger!=None:   trigger_mode(trigger)
    
    if exp!=None:       
        CAM.set_attribute_value("EXPOSURE TIME", exp) 
        line_time = (exp*1000)/2024
        print('line interval:', line_time)
        CAM.set_attribute_value("internal_line_interval", line_time)
    if bin_!=None:      CAM.set_attribute_value("BINNING", bin_)
    if bits!=None:      CAM.set_attribute_value("BIT_PER_CHANNEL", bits)
    
    
def trigger_mode(mode):        
    if mode == 'hardware': #hardware
       #INPUT TRIGGER
       CAM.set_attribute_value('TRIGGER SOURCE', 2)            # 1: Internal;  2: External;    3: Software;    4: Master Pulse;
       CAM.set_attribute_value('trigger_mode', 1)              # 1: Normal;    6: Start;
       CAM.set_attribute_value('trigger_polarity', 2)          # 1: Negative;  2: Positive;
       CAM.set_attribute_value('trigger_active', 1)            # 1: Edge;      2: Level;       3: SyncReadout
       CAM.set_attribute_value('trigger_global_exposure', 3)   # 3: Delayed;   5: Global Reset;

       # CAMERA settings
       CAM.set_attribute_value('sensor_mode', 12)               # 1: Area;      12: Progressive (LIGHTSHEET);    14: Split View;     16: Dual Lightsheet;
       #CAM.set_attribute_value('timing_exposure', 1)          # 1: After Readout;     3: Rolling;
       CAM.set_attribute_value('image_pixel_type',2)           # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3
       CAM.set_attribute_value('buffer_pixel_type',2)          # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3
       CAM.set_attribute_value('readout_direction',2)           # 1: Forwards (progressive sensor mode); 2: Backwards(progressive); 5: Diverging (Area sensor mode)
       

       #OUTPUT settings
       
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
    
def setup_tile():
    x_ori = get_position('x')
    y_ori = get_position('y')

    #generate tile x,y positions    
    tile_list = []
    center = ((tiles-1)*FOV*(1-tile_overlap))/2  # offset center position to account for required overlap, n tiles, and FOV
    
    for x in range(tiles):
        for y in range(tiles):
            tile_list.append([(x*FOV*(1-tile_overlap))-center+x_ori,(y*FOV*(1-tile_overlap))-center+y_ori])
            
    return tile_list

    
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

tile_list = setup_tile()

folder = new_folder(root_location,sZ,exp, name)
print('Expt. saved to: ', folder)
f=0
for position in tile_list:
    sub_folder = folder + "\\P%s_X%s_Y%s" %(f, int(position[0]), int(position[1]))
    os.makedirs(sub_folder)
    f+=1
# move to start position. Perform z-stack centered around current position
#get start position
SPx = get_position('x')
SPy = get_position('y')
SPz = get_position('z')
print('Stage start position:', SPx, SPy, SPz,'um')


for p, position in enumerate(tile_list):
    print("¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬¬tile position: ", p)
    go_to_position(z=SPz + (((nZ-1)*sZ)/-2.0)) # start position minus half of the z range
    go_to_position(x=position[0], y=position[1])

    sub_folder = folder + "\\P%s_X%s_Y%s" %(p, int(position[0]), int(position[1]))


    # delay for stage movement
    t0 = time.time()
    #poll for stage status
    while(stage_movement('z')==1): 
        if(time.time() > t0 + 2): break
        pass
    
    set_stage_triggers('z', sZ)         # send '0.0' to trigger at target, or value for specific distance
    CAM.start_acquisition()    
    while(DIL.inWaiting()):
        print("DIL", DIL.readline())
    
    DIL.write(bytes("/stack.%s.%s;\r" %(exp,nZ), codec))
    
    
    
    for z in range(nZ):
        if(verbose): print("_______________") 
        while(DIL.inWaiting()):
            print("DIL:", DIL.readline())
        print(z) 
        t0 = time.time()
        CAM.wait_for_frame()
        if(verbose): print("wait for imaage: ", time.time() - t0, "(s)")
        t0 = time.time()
        frame = CAM.read_oldest_image()
        if(verbose): print("get frame: ", time.time() - t0, "(s)")
        t0 = time.time()
        imageio.imwrite('%s\\z%s.tif' %(sub_folder,z), frame)
        if(verbose): print("save frame: ", time.time() - t0, "(s)")
        t0 = time.time()
        while(DIL.inWaiting()):
            print("DIL", DIL.readline())
        if(verbose): print("check serial: ", time.time() - t0, "(s)")
        
    CAM.stop_acquisition()
    set_stage_triggers('z', '0')        # send '0' to disable trigger
    
# # return camera to start position
go_to_position(z=SPz, x=SPx, y=SPy)
while(stage_movement('z')==1): pass
print('return position:', get_position('x'),get_position('y'),get_position('z'))
# =============================================================================
# close connections
# =============================================================================

GO.close()
DIL.close()
CAM.close()