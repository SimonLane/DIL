# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 2025
@author: sil1r12

# compatible with firmware v2 (musical)

# =============================================================================
# Z-Stack SCRIPT
+ folder management, channel sub-folders
+ closed loop for stage and filter movement
+ visible laser integration
+ filter integration
+ hardware connection error management
+ camera timeout error handling
+ multi-channel imaging
+ experiment metadata creation and log file
+ musical mode
+ MaiTai
# =============================================================================
"""

# =============================================================================
# PARAMETERS - can edit
# =============================================================================
musical = False
multi_photon = True  # If not using the MaiTai, set this false so it does not try to connect

#  channels
#               on/off     power(%)    exp(ms)     name         wavelength   filter positon
_405        =  [0,         100,        50,         'Hoechst',       405,         1]
_488        =  [0,         100,        50,         'alexa 488',     488,         2]
_561        =  [0,         100,        50,         'alexa 561',     561,         3]
_660        =  [0,         100,        50,         '660nm',         660,         4]
_MaiTai1    =  [1,         10,         50,         '2P NADH',       730,         1]
_MaiTai2    =  [0,         10,         50,         '2P FAD',        810,         2]
_scatter    =  [0,         10,         50,         'scatter',       561,         6]
# TODO - add MaiTai here too

lasers = [_405,_488,_561,_660,_MaiTai1,_MaiTai2,_scatter] # change order here to change channel order

nZ          = 20        # Number of slices
sZ          = 1      # slice separation (micrometers)

# experiment name
name        = "SL_test"

root_location = r"D:/Light_Sheet_Images/Data/"
verbose = True     #for debugging

# ================ Filter Wheel =================================================
# TODO - make this an external file so it can be loaded by different scripts/GUIs etc
# names of filters in the wheel
filter_names = [
    '420+-20',          #p1
    '520+-20',          #p2
    'filter 3',         #p3
    'filter 4',         #p4
    'filter 5',         #p5
    'filter 6'          #p6
                ]

# ================ Don't Edit often =================================================
GO_COM              = 'COM7'
DIL_COM             = 'COM6'
Filter_COM          = 'COM5'
Vis_COM             = 'COM9'
MaiTai_COM          = 'COM4'
codec               = 'utf8'
board_num           = 0             # Visible laser board number
calibrations = "Calibration files" # local folder containing calibration files (lasers and filters)

hsize       = 1024           # ROI horizontal size for subarray (pixels) max 2048
hpos        = 512            # ROI horizontal start position (pixel no.) range: 0 - 2047, mid: 1023
vsize       = 1024           # ROI vertical size for subarray (pixels) max 2048
vpos        = 512            # ROI vertical start position (pixel no.) range: 0 - 2047, mid: 1023

stage_speed = 4000
stage_ac_dc = 500

binning = 1

peak_exposure_ratio = 100


# =============================================================================
#  IMPORTS
# =============================================================================
# camera 
from pylablib.devices import DCAM

# general 
import datetime, os, time ,serial, sys, re
import pandas as pd

# image saving
import imageio
import numpy as np

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
    # print("TO %s0.0;\r\n" %(axis))
    # print("TI %s%s;\r\n" %(axis,float(step)))
    GO.write(bytes("TO %s0.0;\r\n" %(axis), codec))
    GO.write(bytes("TI %s%s;\r\n"  %(axis,float(step)), codec))
    # set speed and acceleration
    GO.write(bytes("SP  %s%s;\r\n" %(axis, stage_speed), codec))
    GO.write(bytes("AC  %s%s;\r\n" %(axis, stage_ac_dc), codec))
    GO.write(bytes("DC  %s%s;\r\n" %(axis, stage_ac_dc), codec))
            
def cam_settings(line_interval, line_exposure, bin_=None, bits=None, trigger=None):
    if trigger!=None:   trigger_mode(trigger)
        
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
       CAM.set_attribute_value('sensor_mode', 12)               # 1: Area;      12: Progressive (LIGHTSHEET);    14: Split View;     16: Dual Lightsheet;
       #CAM.set_attribute_value('timing_exposure', 1)          # 1: After Readout;     3: Rolling;
       CAM.set_attribute_value('image_pixel_type',2)           # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3
       CAM.set_attribute_value('buffer_pixel_type',2)          # 'MONO8': 1, 'MONO16': 2, 'MONO12': 3
       CAM.set_attribute_value('readout_direction',2)           # 1: Forwards (progressive sensor mode); 2: Backwards(progressive); 5: Diverging (Area sensor mode)
       CAM.set_attribute_value('subarray_mode',2)              # 1: Off; 2: On; 
       CAM.set_attribute_value('subarray_hsize', hsize)        # Horizontal size of subarray ROI, starting at hpos (pixels)
       CAM.set_attribute_value('subarray_hpos', hpos)          # Subarray horizontal starting position (pixel number)
       CAM.set_attribute_value('subarray_vsize', vsize)        # Horizontal size of subarray ROI, starting at vpos (pixels)        
       CAM.set_attribute_value('subarray_vpos', vpos)          # Subarray vertical starting position (pixel number)
       
   #OUTPUT settings
       # oscilloscope shows that kind needs to be 'trigger ready'
       CAM.set_attribute_value('output_trigger_source[0]', 2)      #Start on input trigger (6), start on readout (2)
       CAM.set_attribute_value('output_trigger_polarity[0]', 2)    #Positive
       CAM.set_attribute_value('output_trigger_kind[0]', 4)        #trigger ready = 4
       CAM.set_attribute_value('output_trigger_base_sensor[0]', 16) # All views???
       CAM.set_attribute_value('output_trigger_active[0]', 1)      # edge
       CAM.set_attribute_value('output_trigger_delay[0]', 0)      # 
       CAM.set_attribute_value('output_trigger_period[0]', 0.001)      # 
       
    
def create_empty_frame(): # for when there is a camera timeout, or frame grab error, insert an ampty frame to prevent aborting the script
    return np.zeros((2048, 2048), dtype=np.uint16)

def new_folder(root, sZ, name):
    now = datetime.datetime.now()
    units = 'um'
    if(sZ<1): #step size is sub-micron, change units to nm
        sZ = sZ*1000
        units = 'nm'
    folder = r"%s%s-%s-%s %s_%s_%s (z-%s%s) - %s" %(root,now.year, now.month, now.day,   
                                                        now.hour,now.minute,now.second, 
                                                        sZ,units, name)
    os.makedirs(folder)
    return folder

# =============================================================================
# Filter functions
# =============================================================================
def filter_setup():
    while Filter.inWaiting(): # clear buffer
         Filter.readlines()
    Filter.write(b"speed=1\r") # 1: high speed, 0: slow speed!!
    # time.sleep(0.05)
    Filter.write(b"trig=1\r") # 0: TTL input trigger, (low trigger), 1: TTL output, high when position reached
    # time.sleep(0.05)
    set_filter_position(channels[0][5]) # set to filter required for first channel
    # time.sleep(0.05)
    Filter.write(b"sensors=0\r") # 0:turn off internal IR sensor when not moving
    # time.sleep(0.05)

def set_filter_position(p):
    DIL.write(bytes("/filter;\r" , codec)) #setup DIL controller to listen for filter TTL signal
    string = "pos=%s\r" %(p)
    Filter.write(string.encode())

def get_filter_position():
    Filter.write(b"pos?\r") # query position
    time.sleep(0.05)
    while Filter.inWaiting(): 
        f = Filter.readline()    
        print('from filter:', f)
        matches = re.findall(rb'pos=(\d+)', f)  # Look for 'pos=' followed by numbers
        positions = [int(m) for m in matches]  # Convert to integers
        if len(positions) > 0: 
            return positions[0]
    return -1
                
def wait_for_filter(): #wait for the DIL (teensy) to report the filter wheel TTL signal
    for i in range(20): # 2 second polling timeout
        
        while DIL.inWaiting():
            line = DIL.readline()
            # print(' from DIL...', line)
            if(b"Filter_True" in line):
                # print("filter wheel completed move")
                return
        if(i==19):
            print("timeout waiting for filter wheel")
            return
        time.sleep(0.1)
        
def load_filters(filter_file_location):
    with open('%s/filters.txt' %(filter_file_location), 'r') as file:
        # Read each line, strip the newline character, and store it in a list
        filters = [line.strip() for line in file]
        
    return filters
        
# =============================================================================
# Laser functions    
# =============================================================================
def set_laser_power(A_channel_number, D_channel_number, v):
    ul.a_out(0,A_channel_number,ao_range,v) # send the 16-bit value for the DAC
    if(D_channel_number > 0):
        if(v>0): ul.d_bit_out(0, port.type, D_channel_number, 1)
    
def percent_to_16_bit(p, _min, _max): #percentage, min 16-bit value, max 16-bit value    
    if(p==0):  v=0
    else:        
        m = (_max-_min)/(100) # map percentage to 16-bit value
        v = int((m*p) + _min)
    return v

def shutter(): # turn all visible lines off
    for laser in [[0,-1],[2,2],[4,4],[6,6]]: #analog and digital pins for each visible laser
        set_laser_power(laser[0], laser[1], 0)
    
# =============================================================================
# metadata functions
# =============================================================================
def log_append(string, channel=None, z=None):
    with open(r"%s/metadata.txt" %(folder), "a") as file:
        now = datetime.datetime.now()
        line = "%sh %sm %ss %sms: " %(now.hour,now.minute,now.second,int(now.microsecond/1000))
        if(not channel is None): line = line + "C%s " %(channel)
        if(not z is None): line = line + "z%04d,\t" %(channel)
        line = line + string + "\n"
        file.write(line)


# =============================================================================
# MaiTai functions
# =============================================================================
def MaiTai_get_wavelength():
    pass

def MaiTai_set_wavelength(w):
    if w < 1000 and w > 710:
        pass
    
def MaiTai_shutter(v):
    if v==0: # close the shutter
        pass
    if v==1: # open the shutter
        pass

def MaiTai_warmup():
    pass

def MaiTai_laser_stable():
    pass

def MaiTai_shutdown():
    pass


# =============================================================================
# handle connections        
# =============================================================================
# connect all devices or go home, prevents messy situations when one device is not connected
con_laser   = False
con_filter  = False
con_stage   = False
con_DIL     = False
con_cam     = False
con_MaiTai  = False

# close connections to any open devices, then exit script
def close_all_coms(exception=None):     
    if(exception is not None): 
        print("hardware connection error: ") 
        print(exception)   
    if con_laser: 
        shutter()
        ul.release_daq_device(board_num)
        print("shuttered and closed visible lasers")
    if con_filter:  
        Filter.close()
        print("closed filter wheel")
    if con_stage:   
        GO.close()
        print("closed GO stage")
    if con_DIL:
        DIL.write(bytes("/stop;\r" , codec))
        DIL.write(bytes("/galvo.0;\r", codec)) # park the laser beam off sample
        DIL.close()
        print("closed DIL controller")    
    if con_cam:     
        CAM.close()
        print("closed camera")
    if con_MaiTai:
        MaiTai_shutter(0) # close the internal shutter
        MaiTai.close()
        print("closed MaiTai")
    sys.exit()
    
# =============================================================================
# SCRIPT
# =============================================================================
# make the parent folder
folder = new_folder(root_location, sZ, name)
print('Expt. saved to: ', folder)

# load in vis-laser calibration
vis_laser_dataframe = pd.read_csv("%s/LaserCalibration.txt" %(calibrations), header=0, index_col=0, sep ='\t') 
channels = []
#build array with data for selected channels
print('selected channels: ') 
C_num = 0
for item in lasers:  
    if item[0]:
        row = []
        laser = vis_laser_dataframe[vis_laser_dataframe['wav.'] == item[4]] # find the calibration data for the chosen wavelength
        # convert the power to DAC value using laser calibration
        v = percent_to_16_bit(item[1], laser['minVal'].values[0], laser['maxVal'].values[0])
        row.append(C_num)                   #0,channel number
        row.append(item[3])                 #1,channel name
        row.append(item[4])                 #2,wavelength
        row.append(item[1])                 #3,power (%)
        row.append(item[2])                 #4,exposure
        row.append(item[5])                 #5,filter pos
        row.append(laser['Ach'].values[0])  #6,Ach number
        row.append(laser['Dch'].values[0])  #7,Dch number
        row.append(v)                       #8,DAC value
        # make subfolder for channel
        sub_folder = r"%s/C%s_%s" %(folder, row[0],row[1]) # channel number and name
        os.makedirs(sub_folder)
        row.append(sub_folder)              #9,save directory
        channels.append(row)
        
        if(verbose): print(row[:-1]) # print out channel vital info (not directory)
        C_num += 1

# =============================================================================
# SETUP HARDWARE
# =============================================================================
# connection error to any one device causes other devices to disconnect 
# and the script to exit

# DIL control board 
if(verbose):print('connecting hardware: ', 'DIL controller')
try:
    DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
    con_DIL = True
    print("connected DIL controller")
except Exception as e: close_all_coms(exception = e)

# VIS LASER BANK
if(verbose):print('connecting hardware: ', 'vis laser')
try:
    devices = ul.get_daq_device_inventory(InterfaceType.ANY)
    ul.create_daq_device(board_num, devices[0])
    daq_dev_info = DaqDeviceInfo(board_num)
    # setup analog
    ao_info = daq_dev_info.get_ao_info()
    ao_range = ao_info.supported_ranges[0]
    # setup digital
    dio_info = daq_dev_info.get_dio_info()
    port = next((port for port in dio_info.port_info if port.supports_output),None)
    ul.d_config_port(0,port.type, DigitalIODirection.OUT)
    shutter() # turn off all visible lasers
    con_laser = True
    print("connected visible lasers")
except Exception as e: close_all_coms(exception = e)

# FILTER
if(verbose):print('connecting hardware: ', 'filter')
try:
    Filter = serial.Serial(port=Filter_COM, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=0.07)
    con_filter = True
    print("connected filter wheel")
    filter_names = load_filters(calibrations)
    filter_setup()
except Exception as e: close_all_coms(exception = e)

# STAGE
if(verbose):print('connecting hardware: ', 'stage')
try:
    GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
    con_stage = True
    print("connected GO stage")
except Exception as e: close_all_coms(exception = e)

# CAMERA
if(verbose):print('connecting hardware: ', 'camera')
try:
    CAM = DCAM.DCAMCamera()
    con_cam = True 
    print("connected camera")
except Exception as e: close_all_coms(exception = e)

#get start position
SPx = get_position('x')
SPy = get_position('y')
SPz = get_position('z')
print('Stage start position:', SPx, SPy, SPz,'um')

# make metadata file with channels, exposures, filters, names, dates etc.

if(verbose):print('creating metadata file')
now = datetime.datetime.now()
with open(r"%s/metadata.txt" %(folder), "w") as file: # populate metadata file
    file.write("Experiment name:\t\t%s\n" %(name))
    file.write("Experiment date:\t\t%s-%s-%s\n" %(now.year, now.month, now.day))
    file.write("Experiment time:\t\t%s:%s:%s\n" %(now.hour,now.minute,now.second))
    file.write("Number of channels:\t\t%s\n" %(len(channels)))
    file.write("Number of z slices:\t\t%s\n" %(nZ))
    file.write("Camera Binning:\t\t\t%s\n" %(binning))

    if sZ < 1:
        file.write("Z step size:\t\t%s (nm)\n" %(sZ*1000))
    else:
        file.write("Z step size:\t\t\t%s (um)\n" %(sZ))
    file.write("\n")
    file.write("Stage position:\n")
    file.write("\t\t\t\tX:%s\n" %(SPx))
    file.write("\t\t\t\tY:%s\n" %(SPy))
    file.write("\t\t\t\tZ:%s\n" %(SPz))
    file.write("Stage speed:\t\t\t%s (mm/s)\n" %(stage_speed))
    file.write("Stage acceleration:\t\t%s (mm/s/s)\n" %(stage_ac_dc))
    
    for channel in channels:
        line_interval = (channel[4]/1000.0)/vsize   # Exposure time (ms) converted to s, divided by number of pixels
        line_exposure = (peak_exposure_ratio*line_interval) # Time each sensor row is exposed (us) 
        
        file.write("\n")
        file.write("Channel %s:\n" %(channel[0]))
        file.write("\tChannel name:\t\t%s\n" %(channel[1]))
        file.write("\tExposure:\t\t%s\n" %(channel[4]))
        file.write("\tCamera line interval:\t%s\n" %(line_interval))
        file.write("\tCamera line exposure:\t%s\n" %(line_exposure))
        file.write("\tLaser:\t\t\t%snm\n" %(channel[2]))
        file.write("\tLaser power:\t\t%s" %(channel[3]) + "(%)\n")
        file.write("\tLaser DAC value:\t%s\n" %(channel[8]))
        file.write("\tFilter position:\t%s\n" %(channel[5]))
        file.write("\tFilter name:\t\t%s\n" %(filter_names[channel[5]-1]))
        file.write("\tSave location:\t\t%s\n" %(channel[9]))
    file.write("\nExperiment Log:\n")

# channels data format:     0: channel number, 1: name, 2: wavelength, 3: power , 4: exp, 5: filter, 
#                           6: laserAnalog, 7: laserDigital, 8: laserDAC, 9: sub_folder_dir

for channel in channels:
    if(verbose):print('starting channel: ', channel[0])
    log_append("starting channel", channel = channel[0])
    t0channel = time.time()
    
# filter setup
    if(verbose):print('set filter: ', channel[5])
    set_filter_position(channel[5]) # set first as is slowest device
    
# camera setup
    if(verbose):print('setup camera: ', channel[4])
    line_interval = (channel[4]/1000.0)/vsize   # Exposure time converted to s, divided by number of pixels
    line_exposure = (peak_exposure_ratio*line_interval) # Time each sensor row is exposed (us) 
    cam_settings(line_interval, line_exposure, bin_= binning, trigger='hardware')
    CAM.setup_acquisition(mode="sequence", nframes = nZ)

# stage to start position. Perform z-stack centered around current position
    if(verbose):print('setup stage: d =', sZ)
    go_to_position(z=SPz + (((nZ-1)*sZ)/-2.0)) # start position minus half of the range
    set_stage_triggers('z', sZ)
    tstart = time.time()
    clear_buffer()
    while(stage_movement('z')==1): 
        if(time.time() > tstart + 2): break
        pass
    
# check for filter position
    if(verbose):print('wait for filter: ')
    wait_for_filter()
    
    CAM.start_acquisition() 
    time.sleep(0.1)  # delay needed to make sure camera is ready before the DIL controler starts triggering
    
# turn on laser
    if(verbose):print('laser on: ', channel[2], channel[3])
    set_laser_power(channel[6], channel[7], channel[8]) 
    while(DIL.inWaiting()):
        print("DIL", DIL.readline())

# setup the DIL controller  
    if(verbose):print('start DIL: ', channel[4])  
    DIL.write(bytes("/stop;\r" , codec))
    DIL.write(bytes("/stack.%s.%s;\r" %(int(channel[4]),nZ), codec))
    if musical:DIL.write(bytes("/musical.1;\r", codec))
    else:DIL.write(bytes("/musical.0;\r", codec))
    
    t0stack = time.time()
    if(verbose): print('hardware setup time: ', t0stack - t0channel)
    log_append('hardware setup time: {}'.format(t0stack - t0channel), channel=channel[0])
    
    # z-stack loop
    for i in range(nZ):
        t0 = time.time() 
        
        while(DIL.inWaiting()):
            print("DIL:", DIL.readline())
        try:
            CAM.wait_for_frame(timeout=5.0)
        except:
            print("camera timeout error caught")
            log_append("camera timeout error", channel=channel[0], z=i)
            frame = create_empty_frame() # create empty frame
            imageio.imwrite('%s\\z%04d.tif' %(channel[9],i), frame) #save empty frame
            log_append("inserted empty frame", channel=channel[0], z=i)
            continue
            
        
        frame = CAM.read_oldest_image()
        if(frame is None): 
            print("empty frame error")
            log_append("Null frame detected, inserted empty frame", channel=channel[0], z=i)
            frame = create_empty_frame() # create empty frame
            
        imageio.imwrite('%s\\z%04d.tif' %(channel[9],i), frame)
        while(DIL.inWaiting()):
            print("DIL", DIL.readline())

        if(verbose): print("__________ z=%s, frame capture time: %03f (ms)__________" %(i,(time.time() - t0)*1000.0)) 
        
# turn off laser
    set_laser_power(channel[6], channel[7], 0)  
    
    if(verbose): print("Stack time: ", time.time() - t0stack, "(s)") 
    log_append("Stack time: {} (s)".format( time.time() - t0stack))
    if(verbose): print("Channel time: ", time.time() - t0channel, "(s)") 
    log_append("Channel time: {} (s)".format( time.time() - t0channel))
    
    CAM.stop_acquisition()

DIL.write(bytes("/stop;\r" , codec))
DIL.write(bytes("/galvo.0;\r", codec)) # park the laser beam off sample

# # return stage to central start position
go_to_position(z=SPz, x=SPx, y=SPy)
while(stage_movement('z')==1): pass
print('return position:', get_position('z'))

# =============================================================================
# close connections
# =============================================================================
close_all_coms()