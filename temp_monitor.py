# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 11:33:57 2025
TEMP monitor

@author: mbp20
"""

import serial
from time import sleep 

codec               = 'utf8'
DIL_COM             = 'COM6'
GO_COM              = 'COM7'

DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)



def get_room_temp():
    # using the X axis temp as a proxy for room temp, since the stage rarely moves and is under no load
    GO.write(bytes("RTx\n", codec))
    return float(GO.readline().decode(codec).split('x')[1][:-1])


for t in range(100):
    DIL.write(bytes("/temp;\r" , codec))
    sleep(1)
    while DIL.inWaiting():
        line = DIL.readline()
        if(b"Temp" in line):
            print(t, 'Chamber:', line.strip())
    print('Room Temp:', get_room_temp())
            

DIL.close()
GO.close()
