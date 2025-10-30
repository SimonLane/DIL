# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 15:14:07 2025

@author: mbp20
"""
#1
xPos = None
yPos = None
zPos = 9000

#2
#xPos = -65.982
#yPos = 1525.334
#zPos = -2830.000

#3
#xPos = -40.276
#yPos = 2564.122
#zPos = -2830.000

GO_COM = 'COM7'
codec = 'utf8'

stage_speed = 4000
stage_ac_dc = 1000


import serial, time, datetime, os

def clear_buffer():
    print('clear buffer', GO.inWaiting(), 'bytes')
    while GO.inWaiting() > 0: GO.read()
    print('clear buffer', GO.inWaiting(), 'bytes')

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
    
def get_position(axis):
    GO.write(bytes("RP%s\n" %axis, codec))
    return float(GO.readline().decode(codec).split(axis)[1][:-1])
    
def set_stage_speed(axis, stage_speed, stage_ac_dc):    # set speed and acceleration
    GO.write(bytes("SP  %s%s;\r\n" %(axis, stage_speed), codec))
    GO.write(bytes("AC  %s%s;\r\n" %(axis, stage_ac_dc), codec))
    GO.write(bytes("DC  %s%s;\r\n" %(axis, stage_ac_dc), codec))  
    
GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)
clear_buffer() 
print('x0 =', get_position('x'))
print('y0 =', get_position('y'))
print('z0 =', get_position('z'))

go_to_position(z = zPos, y = yPos, x = xPos) # start position minus half of the range
time.sleep(1)
print( )
print('x1 =', get_position('x'))
print('y1 =', get_position('y'))
print('z1 =', get_position('z'))

print( )
print('(',get_position('x'),', ',get_position('y'),', ',get_position('z'),')')
GO.close()