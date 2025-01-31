# -*- coding: utf-8 -*-
"""
Created on Sun Sept 24 16:06:51 2024
@author: sil1r12

# =============================================================================
# Z-Stack SCRIPT
+ folder management
+ function to delay for stage movement
+ visible laser integration
# =============================================================================
"""

# =============================================================================
# PARAMETERS - can edit
# =============================================================================

#  channels
#               on/off     power(%)    exp(ms)     name         wavelength   filter positon
_405        =  [0,         100,        50,         '405nm',     405,         1]
_488        =  [1,         100,        50,         '488nm',     488,         2]
_561        =  [1,         100,        50,         '561nm',     561,         3]
_660        =  [0,         100,        50,         '660nm',     660,         4]
_scatter    =  [1,         10,         50,         'scatter',   561,         6]



nZ          = 10        # Number of slices
sZ          = 1      # slice separation (micrometers)

# experiment name
name        = "SL_test"

root_location = r"D:/Light_Sheet_Images/Data/"
verbose = True     #for debugging

# ================ Don't Edit =================================================
GO_COM              = 'COM7'
DIL_COM             = 'COM6'
Filter_COM          = 'COM5'  # to check!
codec               = 'utf8'
board_num           = 0             # Visible laser board number
vis_connection      = False         # keeps track of whether visible laser bank is connected
cal_txt = "C:/Local/GitHub/DIL/VisBank/"

lasers = [_405,_488,_561,_660, _scatter]


# =============================================================================
#  IMPORTS
# =============================================================================
# camera 
from pylablib.devices import DCAM

#  general 
import serial, time, datetime, os
import pandas as pd

# image saving
import imageio

#imports for USB-3103 laser control board
from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import InterfaceType, DigitalIODirection



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
    GO.write(bytes("AC  %s1000;\r\n" %(axis), codec))
    GO.write(bytes("DC  %s1000;\r\n" %(axis), codec))
            
def cam_settings(exp=None,bin_=None, bits=None, trigger=None):
    if trigger!=None:   trigger_mode(trigger)
    
    if exp!=None:       
        CAM.set_attribute_value("EXPOSURE TIME", exp) 
        line_time = (exp*1000)/2048                                     # Exposure time converted to us, divided by number of pixels
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
# =============================================================================
# Filter functions
# =============================================================================

def go_to(position):
    Filter.write("pos=%s\r" %(position))
    
def filter_setup():
    Filter.write("speed=1\r")
    Filter.write("trig=1\r")
    Filter.write("sensors=0\r")
    
def get_position():
    Filter.write("pos?\r")
    while Filter.inWaiting(): Filter.readlines()  #clear buffer
    p = Filter.readlines()[0].split('\r')[1]
    if isinstance(p, (int)):
        position = p
        return int(position)
    else:
        return -1
    
# =============================================================================
# Laser functions    
# =============================================================================


def set_power(A_channel_number, D_channel_number, w, v):
    if vis_connection:
        ul.a_out(0,A_channel_number,ao_range,v) # send the 16-bit value for the DAC
        if(D_channel_number > 0):
            if(v>0): ul.d_bit_out(0, port.type, D_channel_number, 1)
        print("setting %snm laser to %s" %(w,v))

def percent_to_16_bit(p, _min, _max): #percentage, min 16-bit value, max 16-bit value    
    if(p==0):  v=0
    else:        
        m = (_max-_min)/(100) # map percentage to 16-bit value
        v = int((m*p) + _min)
    return v

# =============================================================================
# SCRIPT
# =============================================================================
# load in vis-laser calibration
dataframe = pd.read_csv("%sLaserCalibration.txt" %(cal_txt), header=0, index_col=0, sep ='\t') 
channels = []
#build array with data for selected channels
print('selected channels: ') 
C_num = 0
for item in lasers:
    
    if item[0]:
        row = []
        laser = dataframe[dataframe['wav.'] == item[4]] # find the calibration data for the chosen wavelength
        # convert the power to DAC value using laser calibration
        v = percent_to_16_bit(item[1], laser['minVal'].values[0], laser['maxVal'].values[0])
        row.append(C_num)
        row.append(item[3])
        row.append(item[4])
        row.append(item[1])
        row.append(item[2])
        row.append(item[5])
        row.append(laser['Ach'].values[0])
        row.append(laser['Dch'].values[0])
        row.append(v)

        channels.append(row)
        print(row)
        C_num += 1



stage_error = False
# =============================================================================
# SETUP HARDWARE
# =============================================================================
# VIS LASER BANK

# devices = ul.get_daq_device_inventory(InterfaceType.ANY)
# ul.create_daq_device(board_num, devices[0])
# daq_dev_info = DaqDeviceInfo(board_num)
# # setup analog
# ao_info = daq_dev_info.get_ao_info()
# ao_range = ao_info.supported_ranges[0]
# # setup digital
# dio_info = daq_dev_info.get_dio_info()
# port = next((port for port in dio_info.port_info if port.supports_output),None)
# ul.d_config_port(0,port.type, DigitalIODirection.OUT)
# print('Vis laser bank connected')



# # FILTER
# Filter = serial.Serial(port=Filter_COM, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=0.07)
# filter_setup()

# # STAGE
# GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
# # DIL control board 
# DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
# # CAMERA
# CAM = DCAM.DCAMCamera()



# cam_settings(exp=exp, bin_=1, trigger='hardware')

# CAM.setup_acquisition(mode="sequence", nframes = nZ)

# folder = new_folder(root_location,sZ,exp, name)
# print('Expt. saved to: ', folder)

# # move to start position. Perform z-stack centered around current position
# #get start position
# SPx = get_position('x')
# SPy = get_position('y')
# SPz = get_position('z')
# print('Stage start position:', SPx, SPy, SPz,'um')

# for channel in channels:
#     go_to_position(z=SPz + (((nZ-1)*sZ)/-2.0)) # start position minus half of the range
    
    
    
#     set_stage_triggers('z', sZ)
#     # delay for stage movement
#     tstart = time.time()
#     #poll for stage status
    
#     clear_buffer()
    
#     while(stage_movement('z')==1): 
#         if(time.time() > tstart + 2): break
#         pass
#     while(stage_movement('z')==1): 
#         if(time.time() > tstart + 2): break
#         pass
    
#     CAM.start_acquisition() 
#     time.sleep(0.1)  # delay needed to make sure camera is ready fefore he DIL controller starts triggering
    
#     while(DIL.inWaiting()):
#         print("DIL", DIL.readline())
    
#     DIL.write(bytes("/stop;\r" , codec))
#     DIL.write(bytes("/stack.%s.%s;\r" %(exp,nZ), codec))
      
#     t0 = tstart
    
#     # z-stack loop
#     for i in range(nZ):
       
#         if(verbose): print("__________ z=%s, frame interval: %03f (ms)__________" %(i,(time.time() - t0)*1000.0)) 
#         t0 = time.time() 
#         while(DIL.inWaiting()):
#             print("DIL:", DIL.readline())
#         try:
#             CAM.wait_for_frame(timeout=5.0)
#         except:
#             print("camera timeout error caught")
#             break
    
#         frame = CAM.read_oldest_image()
#         if(frame is None): print("empty frame error")
#         imageio.imwrite('%s\\z%s.tif' %(folder,i), frame)
#         while(DIL.inWaiting()):
#             print("DIL", DIL.readline())
    
#     if(verbose): print("total time: ", time.time() - tstart, "(s)")    
    
#     CAM.stop_acquisition()
#     go_to_position(z=SPz, x=SPx, y=SPy)
#     while(stage_movement('z')==1): pass

# DIL.write(bytes("/stop;\r" , codec))
# DIL.write(bytes("/galvo.0;\r", codec))
# # # return camera to start position
# go_to_position(z=SPz, x=SPx, y=SPy)
# while(stage_movement('z')==1): pass
# print('return position:', get_position('z'))
# # =============================================================================
# # close connections
# # =============================================================================


# ul.release_daq_device(board_num)
# GO.close()
# DIL.close()
# CAM.close()
# Filter.close()