# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 09:36:47 2024

@author: sil1r12
"""

from pylablib.devices import DCAM
import imageio

save_location = "C:\\Users\\sil1r12\\Documents\\Data\\"

def cam_settings(exp=None,bin_=None):
    if exp!=None:   CAM.set_attribute_value("EXPOSURE TIME", exp)
    if bin_!=None:  CAM.set_attribute_value("BINNING", bin_)

print('n cameras:', DCAM.get_cameras_number())
CAM = DCAM.DCAMCamera()
CAM.set_trigger_mode('ext')
CAM.set_attribute_value('trigger_polarity', 2)
CAM.set_attribute_value('trigger_source', 2)
CAM.set_attribute_value('trigger_active', 2)
cam_settings(exp=0.1, bin_=1)
nFrames = 5
frame_count = 0

# CAM.setup_acquisition(mode="sequence", nframes = nFrames)
# CAM.start_acquisition()
# while frame_count < nFrames:
#     CAM.wait_for_frame()
#     frame = CAM.read_oldest_image()
     
#     imageio.imwrite('%sz%s.tif' %(save_location,frame_count), frame)
#     frame_count+=1








CAM.close()