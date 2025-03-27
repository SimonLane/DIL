# -*- coding: utf-8 -*-
"""
Created on Sun Sept 24 16:06:51 2024
@author: sil1r12

Updated on Tues Jan 25
@editor: ar1e23

# =============================================================================
# Z-Stack SCRIPT
+ folder management
+ function to delay for stage movement
+ synchronisation of light sheet mode
# =============================================================================
"""

# =============================================================================
# PARAMETERS
# =============================================================================
musical = False

nZ          = 75      # Number of slices for stack
sZ          = 0.268      # Slice separation for stack (µm)

#nZ         = 10        # Number of slices for quick view
#sZ         = 13.4     # Slice separation for quick view (µm)

exp         = 100        # Exposure time for frame, equiv. to galvo_transit_time (ms) 

hsize       = 1024           # ROI horizontal size for subarray (pixels) max 2048
hpos        = 512            # ROI horizontal start position (pixel no.) range: 0 - 2047, mid: 1023
vsize       = 1024           # ROI vertical size for subarray (pixels) max 2048
vpos        = 512            # ROI vertical start position (pixel no.) range: 0 - 2047, mid: 1023

name         = "Fluoresbrite 200nm_10^6_1"
#name         = "730nm_Organoids_LabelFree_SP650_Only_3"
#name         = "VisBank_488nm_100percent_520-40_Consuelo_3101_2_Full"
#name         = "VisBank_561nm_100percent_600-40_Consuelo_1102_2_Full"
#name         = "Test"
#name         = "VisBank_488nm_100percent_520-40_Organoid_NewZO1Desmin_1"
#name         = "VisBank_561nm_100percent_600-40_Organoid_NewZO1Desmin_1"





root_location = r"D:/Light_Sheet_Images/Data/"

#peak_exposure_ratio = 10*174.08  #Calculated from empirically determined exposure time with highest SNR using 488nm, 50ms exp. 4250/(50000/2048) *multiplier arbitrary for testing
peak_exposure_ratio = 100

line_interval = (exp/1000.0)/vsize   # Exposure time converted to s, divided by number of pixels *multiplier arbitrary for testing
line_exposure = (peak_exposure_ratio*line_interval) # Time each sensor row is exposed (us)

line_exp = line_exposure*1000 #convert line exposure to ms
line_int = line_interval*1000000 #convert line interval to us
live_view = [line_exp, line_int] #settings for live in ms and us respectively


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
        string = string + ' x'
        string = string + str(x)
    if(y != None): 
        string = string + ' y'
        string = string + str(y)                                  
    if(z != None):                                                        
        string = string + ' z'
        string = string + str(z)
    string= string + ';\n'
    GO.write(bytes(string, "utf8"))
    
def set_stage_triggers(axis, step):
    print("TO %s0.0;\r\n" %(axis))
    print("TI %s%s;\r\n" %(axis,float(step)))
    GO.write(bytes("TO %s0.0;\r\n" %(axis), codec))
    GO.write(bytes("TI %s%s;\r\n"  %(axis,float(step)), codec))
    # set speed and acceleration
    GO.write(bytes("SP  %s4000;\r\n" %(axis), codec))
    GO.write(bytes("AC  %s500;\r\n" %(axis), codec))
    GO.write(bytes("DC  %s500;\r\n" %(axis), codec))
        
def cam_settings(exp=None,bin_=None, bits=None, trigger=None):
    if trigger!=None:   trigger_mode(trigger)
    
    if exp!=None:    
        print('line interval:', line_interval)
        CAM.set_attribute_value("internal_line_interval", line_interval)
        print(CAM.get_attribute_value("internal_line_interval"))
        print('line exposure:', line_exposure)
        CAM.set_attribute_value("EXPOSURE TIME", line_exposure)          # Line exposure time (s)
        print(CAM.get_attribute_value("EXPOSURE TIME"))
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
       CAM.set_attribute_value('sensor_mode', 12)              # 1: Area;      12: Progressive (LIGHTSHEET);    14: Split View;     16: Dual Lightsheet;
       #CAM.set_attribute_value('timing_exposure', 1)          # 1: After Readout;     3: Rolling;
       CAM.set_attribute_value('image_pixel_type',2)           # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3
       CAM.set_attribute_value('buffer_pixel_type',2)          # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3
       CAM.set_attribute_value('readout_direction',2)          # 1: Forwards (progressive sensor mode); 2: Backwards(progressive); 5: Diverging (Area sensor mode)
       CAM.set_attribute_value('subarray_mode',2)              # 1: Off; 2: On; 
       CAM.set_attribute_value('subarray_hsize', hsize)        # Horizontal size of subarray ROI, starting at hpos (pixels)
       CAM.set_attribute_value('subarray_hpos', hpos)          # Subarray horizontal starting position (pixel number)
       CAM.set_attribute_value('subarray_vsize', vsize)        # Horizontal size of subarray ROI, starting at vpos (pixels)        
       CAM.set_attribute_value('subarray_vpos', vpos)          # Subarray vertical starting position (pixel number)
     
       #OUTPUT settings
       
       # oscilloscope shows that kind needs to be 'trigger ready'
       CAM.set_attribute_value('output_trigger_source[0]', 2)           # Start on input trigger (6), start on readout end (2)
       CAM.set_attribute_value('output_trigger_polarity[0]', 2)         # Positive
       CAM.set_attribute_value('output_trigger_kind[0]', 4)             # Trigger Ready: 4
       CAM.set_attribute_value('output_trigger_base_sensor[0]', 16)      # 16: All views; 1: View 1; 2: View 2; 15: Any View
       CAM.set_attribute_value('output_trigger_active[0]', 1)           # 1: Edge
       CAM.set_attribute_value('output_trigger_delay[0]', 0)            #
       CAM.set_attribute_value('output_trigger_period[0]', 0.001)       # 
       
def new_folder(root, sZ, Exp, name):
    now = datetime.datetime.now()
    units = 'um'
    if(sZ<1): #step size is sub-micron, change units to nm
        sZ = sZ*1000
        units = 'nm'
    folder = r"%s%s-%s-%s %s_%s_%s (%s%s, %sms, %.2fms) - %s" %(root,now.year, now.month, now.day,   
                                                        now.hour,now.minute,now.second, 
                                                        sZ,units, Exp, line_exposure*1000, name)
    os.makedirs(folder)

    return folder
    
# =============================================================================
# SCRIPT
# =============================================================================
stage_error = False
# SETUP 
GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
print('n cameras:', DCAM.get_cameras_number())
CAM = DCAM.DCAMCamera()

#DIL.write(bytes("/delay.%s;\r" %(cam_trigger_delay), codec)) # Set camera trigger delay (galvo steps)

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
tstart = time.time()
#poll for stage status

clear_buffer()

while(stage_movement('z')==1): 
    if(time.time() > tstart + 2): break
    pass
while(stage_movement('z')==1): 
    if(time.time() > tstart + 2): break
    pass

CAM.start_acquisition() 
time.sleep(0.1)  # delay needed to make sure camera is ready fefore he DIL controller starts triggering

while(DIL.inWaiting()):
    print("DIL", DIL.readline())

DIL.write(bytes("/stop;\r" , codec))
DIL.write(bytes("/stack.%s.%s;\r" %(exp,nZ), codec))

if musical:DIL.write(bytes("/musical.1;\r", codec))
else:DIL.write(bytes("/musical.0;\r", codec))


while(DIL.inWaiting()):
    print("DIL", DIL.readline())
    
t0 = tstart

# z-stack loop
for i in range(nZ):
   
    if(verbose): print("__________ z=%s, frame interval: %03f (ms)__________" %(i,(time.time() - t0)*1000.0)) 
    t0 = time.time() 
    while(DIL.inWaiting()):
        print("DIL:", DIL.readline())
    try:
        CAM.wait_for_frame(timeout=5.0)
    except:
        print("camera timeout error caught")
        break

    frame = CAM.read_oldest_image()
    if(frame is None): 
        print("empty frame error")
    imageio.imwrite('%s\\z%s.tif' %(folder,i), frame)
    while(DIL.inWaiting()):
        print("DIL", DIL.readline())

if(verbose): print("total time: ", time.time() - tstart, "(s)")    

CAM.stop_acquisition()

DIL.write(bytes("/stop;\r" , codec))
DIL.write(bytes("/galvo.0;\r", codec))
# # return camera to start position
go_to_position(z=SPz, x=SPx, y=SPy)
while(stage_movement('z')==1): pass
print('return position:', get_position('z'))
# =============================================================================
# close connections
# =============================================================================

GO.close()
DIL.close()
CAM.close()