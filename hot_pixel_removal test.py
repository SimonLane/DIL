# -*- coding: utf-8 -*-
"""
Created on Fri Mar 28 12:49:38 2025

@author: mbp20
"""

import numpy as np
import matplotlib.pyplot as plt

frame = np.random.randint(0,10, size=(600, 600))

hot_pixel_list = [(512,512), (100,300)] # won't work on edge pixels! 

for pixel in hot_pixel_list:
    frame[pixel] = 100


plt.imshow(frame, cmap='viridis', interpolation='none', vmin=0, vmax=100)
plt.colorbar()  # Optional: adds a color scale bar
plt.title("Original")
plt.show()


for pixel in hot_pixel_list:
    neighborhood = frame[pixel[0]-1:pixel[0]+2, pixel[1]-1:pixel[1]+2]
    surrounding = np.delete(neighborhood.flatten(), 4) # remove central px
    frame[pixel] = int(surrounding.mean())
    


plt.imshow(frame, cmap='viridis', interpolation='none', vmin=0, vmax=100)
plt.colorbar()  # Optional: adds a color scale bar
plt.title("corrected")
plt.show()