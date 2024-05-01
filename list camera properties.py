# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 10:23:46 2024

@author: sil1r12

List relevent camera properties with values for Hamamatsu camera
"""

from pylablib.devices import DCAM



CAM = DCAM.DCAMCamera()
attributes = CAM.get_all_attributes()

print('properties with dict.~~~~~~~~~~~~~~~~~~~~~~~~~~')
for item in attributes:
    labels = CAM.ca[item].labels
    if len(labels) > 0:
        print(item, labels)
print('properties with values~~~~~~~~~~~~~~~~~~~~~~~~~')
for item in attributes:
    labels = CAM.ca[item].labels
    if len(labels) == 0:
        print(item)
    

    
CAM.close()





