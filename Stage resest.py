# -*- coding: utf-8 -*-
"""
Created on Thu May  2 14:43:37 2024

@author: sil1r12

Script to reset GO stage
"""

GO_COM = 'COM4'
codec = 'utf8'
import serial

GO = serial.Serial(port=GO_COM, baudrate=115200, timeout=0.2)


def get_position(axis):
    GO.write(bytes("RP%s\n" %axis, codec))
    return float(GO.readline().decode(codec).split(axis)[1][:-1])
    
def get_status(axis):
    GO.write(bytes("RS%s\n" %axis, codec))
    return GO.readline().decode(codec)
    
def get_error(axis):
    GO.write(bytes("RE%s\n" %axis, codec))
    return GO.readline().decode(codec)

try:
    
    X = get_position('x')
    print("~~~~~~~~~~~~~~~~ X ~~~~~~~~~~~~~~~~~")
    print("Position:",X)
    print("Status:", get_status('x'))
    print("Error:", get_error('x'))
    print("~~~~~~~~~~~~~~~~ Y ~~~~~~~~~~~~~~~~~")
    Y = get_position('y')
    print("Position:", Y)
    print("Status:", get_status('y'))
    print("Error:", get_error('y'))
    print("~~~~~~~~~~~~~~~~ Z ~~~~~~~~~~~~~~~~~")
    Z = get_position('z')
    print("Position:", Z)
    print("Status:", get_status('z'))
    print("Error:", get_error('z'))
    
except:
    pass

try:
    GO.write(bytes("FRx\n", codec))
    print(GO.readline().decode(codec))
    GO.write(bytes("INx\n", codec))
    print(GO.readline().decode(codec))
    GO.write(bytes("FRy\n", codec))
    print(GO.readline().decode(codec))
    GO.write(bytes("INy\n", codec))
    print(GO.readline().decode(codec))
    GO.write(bytes("FRz\n", codec))
    print(GO.readline().decode(codec))
    GO.write(bytes("INz\n", codec))
    print(GO.readline().decode(codec))
    
    # TO DO wait for movement to stop and home status 
    # send back to original position
    
finally: 
    
    GO.close()