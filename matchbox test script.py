# -*- coding: utf-8 -*-
"""
Created on Fri Nov 21 13:18:18 2025

@author: mbp20
"""
import serial
from time import sleep

Vis_COM             = 'COM12'
DIL_COM             = 'COM6'
codec               = 'utf8'



VIS = serial.Serial(port=Vis_COM, baudrate=115200, timeout=0.2)
DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)

sleep(0.5)


DIL.write(bytes("/Shutter;\r" , codec)) # disable all visible lasers via TTL
VIS.write("e 1".encode()) # turn on TEC (enable emmission)

sleep(0.5)


current = 80


sleep(0.5)
#set 488 current


for index in range(4):
    print(index+1)
    VIS.write(f"L{index+1}E".encode()) # enable
    command = f"Lc{index+1} {current}"
    VIS.write(command.encode())
    sleep(0.5)

for wav in ['405','488','520','638']:
    print(wav)
    DIL.write(bytes(f"/{wav}.1;\r" , codec)) # disable all visible lasers via TTL
    sleep(0.2)
    DIL.write(bytes(f"/{wav}.0;\r" , codec)) # disable all visible lasers via TTL
    sleep(0.2)
    DIL.write(bytes(f"/{wav}.1;\r" , codec)) # disable all visible lasers via TTL
    sleep(0.2)
    DIL.write(bytes(f"/{wav}.0;\r" , codec)) # disable all visible lasers via TTL
    sleep(0.2)

current = 0
for index in range(4):
    print(index+1)
    VIS.write(f"L{index+1}D".encode()) # enable
    command = f"Lc{index+1} {current}"
    VIS.write(command.encode())
    sleep(0.5)
    
    
VIS.write("e 0".encode())
VIS.close()

DIL.close()






