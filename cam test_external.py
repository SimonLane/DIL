# -*- coding: utf-8 -*-
"""
Created on Wed May  1 13:50:19 2024

@author: sil1r12
"""
from pylablib.devices import DCAM
CAM = DCAM.DCAMCamera()
exp=100
nZ=5


def cam_settings(exp=None,bin_=None, bits=None, trigger=None):
    if exp!=None:       CAM.set_attribute_value("EXPOSURE TIME", exp)
    if bin_!=None:      CAM.set_attribute_value("BINNING", bin_)
    if bits!=None:      CAM.set_attribute_value("BIT_PER_CHANNEL", bits)

#print(CAM.get_all_attribute_values()) # list all current values
cam_settings(exp=exp, bin_=1)#, trigger='software')

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
CAM.set_attribute_value('output_trigger_source[0]', 6)      #Start on input trigger
CAM.set_attribute_value('output_trigger_polarity[0]', 2)    #Positive
CAM.set_attribute_value('output_trigger_kind[0]', 4)        #Exposure
CAM.set_attribute_value('output_trigger_base_sensor[0]', 16) # All views???
# output 2
# CAM.set_attribute_value('output_trigger_source[1]', 2)      #ReadoutEnd
# CAM.set_attribute_value('output_trigger_polarity[1]', 2)    #Positive
# CAM.set_attribute_value('output_trigger_kind[1]', 4)        #Readout

# # output 3
# CAM.set_attribute_value('output_trigger_source[2]', 6)      #Start on input trigger
# CAM.set_attribute_value('output_trigger_polarity[2]', 2)    #Positive
# CAM.set_attribute_value('output_trigger_kind[2]', 4)        #Trigger ready




# CAM.setup_acquisition(mode="sequence", nframes = nZ)




CAM.close()