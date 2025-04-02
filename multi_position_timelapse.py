# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 2025
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
+ MaiTai closed loop tuning
+ Timelapse
+ Multi-position
# =============================================================================
"""

# =============================================================================
# MULTIPOSITION SETTINGS
# =============================================================================

do_multi_positon = True     # True: load in multiple positions
                            # False: use the current stage position
                            
position_list = [           # FORMAT: COMMA SEPARATED (X, Y, Z) (IN MICRONS)
    (57.024, -1000.486, 5667.738),
    # (57.024, 1000.486, 5667.738)
    ]

# =============================================================================
# TIMELAPSE SETTINGS
# =============================================================================
timelapse = False
time_loop_interval  = 30 #(s)
nTs = 3

# =============================================================================
# PARAMETERS - can edit
# =============================================================================
musical = False  

#  channels
#               on/off     power(%)    exp(ms)     name                     wavelength   filter positon
_405        =  [0,         100,        50,         'Hoechst',               405,         1]
_488        =  [1,         100,        10,        '200nm_Bead',            488,         2]
_561        =  [0,         100,        10,         'alexa 561',             561,         3]
_660        =  [0,         100,        50,         '660nm',                 660,         4]
_MaiTai1    =  [0,         10,         100,       '2P NADH',               730,         4]
_MaiTai2    =  [0,         10,         100,       '2P FAD',                875,         5]
_scatter    =  [0,         4,          10,         'scatter',               488,         6]

lasers = [_405,_488,_561,_660,_MaiTai1,_MaiTai2,_scatter] # change order here to change channel order

nZ          = 50        # Number of slices
sZ          = 0.5      # slice separation (micrometers)

# experiment name
name        = "SL_test"

root_location = r"D:/Light_Sheet_Images/Data/"
verbose = False     #for debugging
do_hot_pixel_correction = True

# ================ Filter Wheel =================================================
# TODO - make this an external file so it can be loaded by different scripts/GUIs etc
# names of filters in the wheel
filter_names = [
    '420+-20',          #p1
    '520+-20',          #p2
    '600+-20',          #p3
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
stage_ac_dc = 250

binning = 1
stage_timeout_limit = 10
peak_exposure_ratio = 100

# Detection characteristics
objective_magnification = 20    # detection
tube_lens_f             = 200   # mm
pixel_physical_size     = 6.5   # microns

hot_pixel_list = [[635,731]] # list of pixels to be corrected, NOTE, can't use edge pixels!


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
# STAGE FUNCTIONS
# =============================================================================

def clear_stage_buffer():
    while GO.inWaiting() > 0: GO.read()
    
def stage_stable(axis): #tests stage to make sure movement is complete
    #get stage status
    GO.write(bytes("RS%s\n" %axis, codec))
    Status = GO.readline()[1:]
    # print("stage status raw:", Status)
    Status = Status.decode(codec).split(axis)[1][0]
    stage_OK = ["0","2","4"]
    if(Status in stage_OK): return True  #if stage is stationary
    if(Status == "9"): 
        GO.write(bytes("RE%s\n" %axis, codec))
        Error = GO.readline().decode(codec).split(axis)[1][0]
        print('Stage Error code:', Error)
        return 2
    else: return False   # stage moving, or error

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
    
def set_stage_triggers_stack(step): # Setup triggers for z-stack. 
    GO.write(bytes("TO z0.0;\r\n", codec))                  # stage output trigger on arrival. Step 0 = disable; step 0.0 = trigger at target
    GO.write(bytes("TI z%s;\r\n"  %(float(step)), codec))   # stage input trigger to move 'step' distance
    
def set_stage_triggers_move():     # Turn off triggers for moving between positions, don't want to trigger the DIL board
    GO.write(bytes("TO x0;\r\n", codec))            # turn off
    GO.write(bytes("TI x0;\r\n", codec))            # turn off
    GO.write(bytes("TO y0;\r\n", codec))            # turn off
    GO.write(bytes("TI y0;\r\n", codec))            # turn off
    GO.write(bytes("TO z0;\r\n", codec))            # turn off
    GO.write(bytes("TI z0;\r\n", codec))            # turn off
    
def set_stage_speed(axis, stage_speed, stage_ac_dc):    # set speed and acceleration
    GO.write(bytes("SP  %s%s;\r\n" %(axis, stage_speed), codec))
    GO.write(bytes("AC  %s%s;\r\n" %(axis, stage_ac_dc), codec))
    GO.write(bytes("DC  %s%s;\r\n" %(axis, stage_ac_dc), codec))


# =============================================================================
# CAMERA FUNCTIONS            
# =============================================================================
def cam_settings(line_interval, line_exposure, bin_=None, bits=None, trigger=None):
    if trigger!=None:   trigger_mode(trigger)
        
    if verbose: print('line interval:', line_interval)
    CAM.set_attribute_value("internal_line_interval", line_interval)
    if verbose: print(CAM.get_attribute_value("internal_line_interval"))
    if verbose: print('line exposure:', line_exposure)
    CAM.set_attribute_value("EXPOSURE TIME", line_exposure)          # Line exposure time (s)
    if verbose: print(CAM.get_attribute_value("EXPOSURE TIME"))  
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
    return np.zeros((hsize, vsize), dtype=np.uint16)

def hot_pixel_correction(frame, pixel_list):
    for pixel in pixel_list:
        neighborhood = frame[pixel[0]-1:pixel[0]+2, pixel[1]-1:pixel[1]+2]
        surrounding = np.delete(neighborhood.flatten(), 4) # remove central px
        frame[pixel] = int(surrounding.mean())
    return frame
        
# =============================================================================
# FILE HANDLING
# =============================================================================
def new_folder(root, name):
    now = datetime.datetime.now()
    folder = r"%s%s-%02d-%02d %02d_%02d_%02d - %s" %(root,
             now.year, now.month,now.day, now.hour,now.minute,now.second, name)
    os.makedirs(folder)
    return folder

# =============================================================================
# FILTER FUNCTIONS
# =============================================================================
def filter_setup():
    while Filter.inWaiting(): # clear buffer
         Filter.readlines()
    Filter.write(b"speed=1\r") # 1: high speed, 0: slow speed!!
    Filter.write(b"trig=1\r") # 0: TTL input trigger, (low trigger), 1: TTL output, high when position reached
    set_filter_position(channels[0][5]) # set to filter required for first channel
    Filter.write(b"sensors=0\r") # 0:turn off internal IR sensor when not moving


def set_filter_position(p):
    DIL.write(bytes("/filter;\r" , codec)) #setup DIL controller to listen for filter TTL signal
    string = "pos=%s\r" %(p)
    Filter.write(string.encode())

def get_filter_position():
    Filter.write(b"pos?\r") # query position
    time.sleep(0.05)
    while Filter.inWaiting(): 
        f = Filter.readline()    
        if verbose: print('from filter:', f)
        matches = re.findall(rb'pos=(\d+)', f)  # Look for 'pos=' followed by numbers
        positions = [int(m) for m in matches]  # Convert to integers
        if len(positions) > 0: 
            return positions[0]
    return -1
                
def wait_for_filter(): #wait for the DIL (teensy) to report the filter wheel TTL signal
    for i in range(20): # 2 second polling timeout
        while DIL.inWaiting():
            line = DIL.readline()
            if(b"Filter_True" in line):
                return
        if(i==19):
            print("timeout waiting for filter wheel")
            return
        time.sleep(0.1)
        
def load_filters(filter_file_location):
    with open('%s/filters.txt' %(filter_file_location), 'r') as file:
        filters = [line.strip() for line in file]  # Read each line, strip the newline character, and store it in a list
    return filters

def clear_DIL_buffer():
    if verbose:
        while DIL.inWaiting(): print(DIL.readline())
    else:
        while DIL.inWaiting(): DIL.readline()
# =============================================================================
# VISIBLE LASER FUNCTIONS
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
# METADATA FUNCTIONS
# =============================================================================
def log_append(string, channel=None, z=None, indent=0):
    with open(r"%s/metadata.txt" %(folder), "a") as file:
        now = datetime.datetime.now()
        line = "%02dh %02dm %02ds %03dms: " %(now.hour,now.minute,now.second,int(now.microsecond/1000))
        if(not channel is None): line = line + "C%s " %(channel)
        if(not z is None): line = line + "z%04d,\t" %(channel)
        for i in range(indent): line = line + "\t"
        line = line + string + "\n"
        file.write(line)


# =============================================================================
# MAITAI FUNCTIONS
# =============================================================================
maitai = None                           # place holder for serial connection

def get_wavelength():
    clear_maitai_buffer()
    maitai.write(b"WAV?\n")
    time.sleep(0.05)                     #important, need this delay
    while maitai.in_waiting:
        frommt = maitai.readline()
        try:
            wav = int(frommt[:-3])
            return wav
        except:
            pass

def set_wavelength(w):
    w = int(w)
    if w<710 or w>990:
        print('wavelength not in correct range')
        return False
    command = "WAV %s\n" %w
    maitai.write(command.encode('ascii'))
    return True    

def open_shutter():
    command = "SHUT 1\n"
    maitai.write(command.encode('ascii'))

def close_shutter():
    command = "SHUT 0\n"
    maitai.write(command.encode('ascii'))
    
def get_shutter():
    clear_maitai_buffer()
    command = "SHUT?\n"
    maitai.write(command.encode('ascii'))
    s = maitai.readline()
    return int(s)

def clear_maitai_buffer():
    maitai.readlines()

def wait_for_shutter(open_close):
    clear_maitai_buffer()
    if(verbose): print('\t\tMaitai shutter set:', open_close)
    for i in range(30):  # 3 second timeout
        s = get_shutter()
        if s == open_close: 
            if(verbose): print('\t\tshutter state:', open_close, '(', i*100, 'ms )')
            return 1
        time.sleep(0.1)
    return -1

def laser_stable(): # for use in laser tuning during timelapse (blocking)
    # This function will not return for at least 1 second, could the 'sleep' be reduced?
    clear_maitai_buffer()
    count = 0
    try:
        while count < 2:
            command = "READ:AHIS?\n"
            maitai.write(command.encode('ascii'))
            history = maitai.readline().decode('ascii').split(' ')
            for i, item in enumerate(history):      # find first instance of '43'
                if item[0:2] == '43': break
            if history[i][2] == '1':                # test if stable
                count = count + 1                   # if stable then increment counter and wait before next test
                time.sleep(0.05)                          # this works for the thread but it can't be used from the main GUI due to blocking
            else:
                return False                        # if not then exit False
        return True                                 # if counter reaches 2 exit True
    except Exception as ex:
        print('wait for laser exception:', ex)
        return False

def MaiTai_readout():
    clear_maitai_buffer()
    maitai.write(b"WAV?\n") # commanded wavelength
    maitai.write(b"READ:WAV?\n") #actual wavelength?
    maitai.write(b"READ:POW?\n")
    time.sleep(0.05)
    setpoint = maitai.readline().decode('ascii').strip()
    actual = maitai.readline().decode('ascii').strip()
    power = maitai.readline().decode('ascii').strip()
    stable = laser_stable()
    return setpoint, actual, power, stable


def MaiTai_warm():
    clear_maitai_buffer()
    maitai.write(b"READ:PCTW?\n")
    time.sleep(0.05)
    temp = maitai.readline().decode('ascii').strip()
    if temp[0:3] == '100':
        return True, float(temp[:-1])
    else:
        return False, float(temp[:-1])
    
# =============================================================================
# CONNECTIONS     
# =============================================================================
# connect all devices or go home, prevents messy situations when one device is not connected
con_laser       = False
con_filter      = False
con_stage       = False
con_DIL         = False
con_cam         = False
con_MaiTai      = False
multi_photon    = False

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
        close_shutter() # close the internal shutter
        maitai.close()
        print("closed MaiTai")
    sys.exit()
    
# =============================================================================
# MAIN IMAGING SCRIPT START
# =============================================================================
# make the parent folder
folder = new_folder(root_location, name)
print('Expt. saved to: ', folder)

# load in vis-laser calibration
vis_laser_dataframe = pd.read_csv("%s/LaserCalibration.txt" %(calibrations), header=0, index_col=0, sep ='\t') 
channels = []
first_MT_wav = 0 # place holder for first wavelength to start tuning to, to save time

#build array with data for selected channels
print('selected channels: ') 
C_num = 0
for item in lasers:  
    if item[0]:
        row = []
        row.append(C_num)                       #0,channel number
        row.append(item[3])                     #1,channel name
        row.append(item[4])                     #2,wavelength
        if item[4] < 700: row.append(item[1])   #3,power (%)
        else: row.append('N/A')  
        row.append(item[2])                     #4,exposure
        row.append(item[5])                     #5,filter pos
        if item[4] < 700:
            # convert the power to DAC value using laser calibration
            laser = vis_laser_dataframe[vis_laser_dataframe['wav.'] == item[4]] # find the calibration data for the chosen wavelength
            v = percent_to_16_bit(item[1], laser['minVal'].values[0], laser['maxVal'].values[0])
            row.append(laser['Ach'].values[0])  #6,Ach number
            row.append(laser['Dch'].values[0])  #7,Dch number
            row.append(v)                       #8,DAC value
        else:
            row.append('N/A')                   #6,Ach number
            row.append('N/A')                   #7,Dch number
            row.append('N/A')                   #8,DAC value   
            multi_photon = True                 # MaiTai in use, turn on multiphoton mode
            if first_MT_wav == 0: first_MT_wav = item[4] 
                    
        channel_name = "C{:01d} - {}".format(row[0],row[1])
        row.append(channel_name)              #9,channel name
        channels.append(row)
        
        if(verbose): print(row[:-1]) # print out channel vital info (not directory)
        C_num += 1

if do_multi_positon == False:
    position_list = [(get_position(axis='x'),get_position(axis='y'),get_position(axis='z'))] # use current stage position as the only position
    
# create position, channel folder structure
for p, position in enumerate(position_list): 
    # make folder for each position
    p_folder = "{}/P{:02d}".format(folder, p)
    os.makedirs(p_folder)
    for channel in channels:
        c_folder = "{}/{}".format(p_folder, channel[9])
        os.makedirs(c_folder)

# =============================================================================
# METADADA FILE CREATION
# =============================================================================
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
    file.write("Stage positions:\n")
    for p, position in enumerate(position_list):
        file.write("\t\t\t\tP{:02d} - X:{} Y:{} Z:{}\n".format(p,*position))
    file.write("\n")
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
        file.write("\tChannel name:\t\t%s\n" %(channel[9]))
    file.write("\nExperiment Log:\n")   
     
# =============================================================================
#  HARDWARE CONNECTIONS
# =============================================================================
# connection error to any one device causes other devices to disconnect 
# and the script to exit

# MaiTai
if multi_photon:
    if(verbose):print('connecting hardware: ', 'MaiTai')
    try:
        maitai = serial.Serial(port='COM8', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.5, xonxoff=0, rtscts=0)
        con_MaiTai = True
        print("connected to MaiTai") 
        log_append("MaiTai connection")
        log_append("connected to MaiTai")
        time.sleep(0.05)
        close_shutter()
        # confirm laser warmed up
        warm = MaiTai_warm()
        if warm[0]:
            print("MaiTai warmup complete")
        else:
            print("MaiTai warmup incomplete, ({}%)".format(warm[1]))
            close_all_coms(exception = 'MaiTai laser not warmed up')
        # set MaiTai to first wavelength    
        set_wavelength(first_MT_wav)
    except Exception as e: 
        log_append("MaiTai connection error")
        close_all_coms(exception = e)

# DIL control board 
if(verbose):print('connecting hardware: ', 'DIL controller')
try:
    DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
    con_DIL = True
    print("connected DIL controller")
    log_append("DIL connection")
except Exception as e: 
    log_append("DIL connection error")
    close_all_coms(exception = e)

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
    log_append("Visible lasers connection")
except Exception as e: 
    log_append("Visible Laser connection error")
    close_all_coms(exception = e)

# FILTER
if(verbose):print('connecting hardware: ', 'filter')
try:
    Filter = serial.Serial(port=Filter_COM, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=0.07)
    con_filter = True
    print("connected filter wheel")
    log_append("Filter wheel connection")
    filter_names = load_filters(calibrations)
    filter_setup()
except Exception as e: 
    log_append("filter wheel connection error")
    close_all_coms(exception = e)

# STAGE
if(verbose):print('connecting hardware: ', 'stage')
try:
    GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
    con_stage = True
    print("connected GO stage")
    log_append("GO stage connection")
    # set speeds and accelerations
    for axis in ('x','y','z'):
        set_stage_speed(axis, stage_speed, stage_ac_dc)
    # go to first position
    set_stage_triggers_move()  #turn off stage triggers
    x,y,z = position_list[0]
    go_to_position(x=x, y=y, z=z)
    
except Exception as e: 
    log_append("GO Stage connection error")
    close_all_coms(exception = e)

# CAMERA
if(verbose):print('connecting hardware: ', 'camera')
try:
    CAM = DCAM.DCAMCamera()
    con_cam = True 
    print("connected camera")
    log_append("Camera connection")
except Exception as e: 
    log_append("Camera connection error")
    close_all_coms(exception = e)


# channels data format:     0: channel number, 1: name, 2: wavelength, 3: power , 4: exp, 5: filter, 
#                           6: laserAnalog, 7: laserDigital, 8: laserDAC, 9: channel name

# =============================================================================
# TIMELAPSE LOOP
# =============================================================================
start_time = 0
if timelapse == False: nTs = 1

for t in range(nTs):
    if multi_photon: set_wavelength(first_MT_wav)   
    # go to first stage position
    set_stage_triggers_move()
    x,y,z = position_list[0]
    go_to_position(x=x, y=y, z=z)
    # move the filter wheel
    set_filter_position(channels[0][5])
    remaining_time = start_time + time_loop_interval - time.time()
    if(remaining_time < 0 and remaining_time > -10000):
        print('Warning: Timelapse loop does not leave enough time to complete imaging ({:.2f}s)'.format(remaining_time))
    else: 
        print('\rStarting timepoint {}'.format(t), end = '')
    while(time.time() < start_time + time_loop_interval): 
        print('\rStarting timepoint {}: {:.1f} seconds remaining'.format(t,start_time + time_loop_interval - time.time()), end='')
        time.sleep(0.1)
    print('\rStarting timepoint {}                                                           '.format(t))
    start_time = time.time()
    log_append(f"starting timepoint {t}", indent=1)
    
# =============================================================================
# STAGE POSITION LOOP
# =============================================================================
    for p, position in enumerate(position_list):
        print(f"\tStage Position {p}: {position}")
        # go to XY position, and central z position, no triggers
        set_stage_triggers_move()
        x,y,z = position
        go_to_position(x=x, y=y, z=z)
        # whilst stage is moving, start tuning maitai and setting filter
        set_filter_position(channels[0][5]) 
        if multi_photon: set_wavelength(first_MT_wav)
        # wait for stage movement to complete
        tstart = time.time() 
        clear_stage_buffer()
        x_, y_, z_ = (False, False, False)
        while(True):
            if not x_: x_ = stage_stable('x')
            if not y_: y_ = stage_stable('y')
            if not z_: z_ = stage_stable('z')
            
            if x_ and y_ and z_: break
            if(time.time() > tstart + stage_timeout_limit): # allow 5s before timeout
                log_append("Stage position Timeout", indent=1)
                print("Stage position Timeout")
                break  
            
        log_append(f"Stage Position {p}: {position}", indent=1)
# =============================================================================
# HARDWARE SETUP - CHANNEL LOOP
# =============================================================================
        for channel in channels:
            print('\t\tstarting channel: ', channel[0])
            log_append("starting channel", channel = channel[0], indent=2)
            t0channel = time.time()
        
        # maitai setup
            if multi_photon and channel[2] > 700:   
                if(verbose):print('set MaiTai wavelength: ', channel[2])
                set_wavelength(channel[2])
        
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
            go_to_position(z=position[2] + (((nZ-1)*sZ)/-2.0)) # start position minus half of the range
            
            tstart = time.time()
            clear_stage_buffer()
            while(stage_stable('z')==False): 
                if(time.time() > tstart + 2): break
                pass
            set_stage_triggers_stack(sZ)
        # check for filter position
            if(verbose):print('wait for filter: ')
            wait_for_filter()
            
            CAM.start_acquisition() 
            time.sleep(0.1)  # delay needed to make sure camera is ready before the DIL controler starts triggering
            
        # turn on visible laser (or tune the maitai)
            if channel[2] < 700:                        # visible
                if(verbose):print('laser on: ', channel[2], channel[3])
                set_laser_power(channel[6], channel[7], channel[8]) 
                clear_DIL_buffer()
            if multi_photon and channel[2] > 700:        # MaiTai
                print('\t\twaiting for MaiTai to tune')    
                while True:
                        setpoint,actual,power,stable = MaiTai_readout()
                        if verbose: print('\t\tsetpoint: {}, actual: {}, power: {}, stable: {}'.format(setpoint,actual,power,stable))
                        if stable: 
                            print('\t\tsetpoint: {}, actual: {}, power: {}, stable: {}'.format(setpoint,actual,power,stable))
                            log_append('MaiTai status: setpoint: {}, actual: {}, power: {}'.format(setpoint,actual,power), indent=2)
                            break
                        time.sleep(0.2)
                open_shutter()
                wait_for_shutter(1) #wait for shutter to actually open (highly variable delay)
        
        # setup the DIL controller  
            if(verbose):print('start DIL: ', channel[4])  
            DIL.write(bytes("/stop;\r" , codec))
            DIL.write(bytes("/stack.%s.%s;\r" %(int(channel[4]),nZ), codec))
            if musical: DIL.write(bytes("/musical.1;\r", codec))
            else: DIL.write(bytes("/musical.0;\r", codec))
            
            t0stack = time.time()
            if(verbose): print('hardware setup time: ', t0stack - t0channel)
            log_append('hardware setup time: {}'.format(t0stack - t0channel), indent=2)

# =============================================================================
# ACTUAL IMAGING LOOP
# =============================================================================
            # z-stack loop
            for i in range(nZ):
                t0 = time.time() 
                
                clear_DIL_buffer()
                try:
                    CAM.wait_for_frame(timeout=5.0)
                except:
                    print("camera timeout error caught")
                    log_append("camera timeout error", channel=channel[0], z=i, indent=2)
                    frame = create_empty_frame() # create empty frame
                    imageio.imwrite('%s\\P%02d\\%s\\t%04d_z%04d.tif' %(folder,p,channel[9],t,i), frame) #save empty frame
                    log_append("inserted empty frame", channel=channel[0], z=i, indent=2)
                    continue
                    
                frame = CAM.read_oldest_image()
                if(frame is None): 
                    print("empty frame error")
                    log_append("Null frame detected, inserted empty frame", channel=channel[0], z=i, indent=2)
                    frame = create_empty_frame() # create empty frame
                if do_hot_pixel_correction:
                    frame = hot_pixel_correction(frame, hot_pixel_list)    
                imageio.imwrite('%s\\P%02d\\%s\\t%04d_z%04d.tif' %(folder,p,channel[9],t,i), frame)
                clear_DIL_buffer()
        
                if(verbose): print("__________ z=%s, frame capture time: %03f (ms)__________" %(i,(time.time() - t0)*1000.0)) 
                
        # turn off laser or close shutter 
            if channel[2] < 700:                         # visible
                set_laser_power(channel[6], channel[7], 0)  
            if multi_photon and channel[2] > 700:        # MaiTai 
                close_shutter()
        
        # report timing stats    
            if(verbose): print("Stack time: ", time.time() - t0stack, "(s)") 
            log_append("Stack time: {} (s)".format( time.time() - t0stack), indent=2)

            CAM.stop_acquisition()
            set_stage_triggers_move() # turn off stage triggers
            
            DIL.write(bytes("/stop;\r" , codec))
            DIL.write(bytes("/galvo.0;\r", codec)) # park the laser beam off sample
            
            if(verbose): print("Channel time: ", time.time() - t0channel, "(s)") 
            log_append("Channel time: {} (s)".format( time.time() - t0channel), indent=2)
# =============================================================================
# close connections
# =============================================================================
close_all_coms()