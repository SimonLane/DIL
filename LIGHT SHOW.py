# -*- coding: utf-8 -*-
"""
Created on Wed Feb 11 14:34:43 2026

@author: mbp20
"""

import serial
from time import sleep

Vis_COM             = 'COM12'
DIL_COM             = 'COM6'
codec               = 'utf8'

# VIS = serial.Serial(port=Vis_COM, baudrate=115200, timeout=0.2)
DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)

i=0

while i<60000:
    for wav in ['405','488','520']: #,'638'
        
        DIL.write(bytes(f"/{wav}.1;\r" , codec)) # disable all visible lasers via TTL
        sleep(0.01)
        # DIL.write(bytes(f"/{wav}.0;\r" , codec)) # disable all visible lasers via TTL
        

    i+=1
    if i%1000 == 0: print(i)
for wav in ['405','488','520','638']:
    print(wav)
    DIL.write(bytes(f"/{wav}.0;\r" , codec)) # disable all visible lasers via TTL

DIL.close()


