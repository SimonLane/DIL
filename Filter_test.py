# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 17:36:55 2025

@author: mbp20
"""

import time, serial, re

def filter_setup():
    time.sleep(0.3)
    while Filter.inWaiting(): # clear buffer
         Filter.readlines()
    Filter.write(b"speed=1\r") # 1: high speed, 0: slow speed!!
    time.sleep(0.1)
    Filter.write(b"trig=1\r") # 0: TTL input trigger, (low trigger), 1: TTL output, high when position reached
    time.sleep(0.1)
    set_filter_position(0) # set to filter required for first channel
    time.sleep(0.1)
    Filter.write(b"sensors=0\r") # 0:turn off internal IR sensor when not moving
    time.sleep(0.1)

def set_filter_position(p):
    string = "pos=%s\r" %(p)
    Filter.write(string.encode())

def get_filter_position():
    Filter.write(b"pos?\r") # query position
    time.sleep(0.05)
    while Filter.inWaiting(): 
        f = Filter.readline()    
        print('from filter:', f)
        matches = re.findall(rb'pos=(\d+)', f)  # Look for 'pos=' followed by numbers
        positions = [int(m) for m in matches]  # Convert to integers
        if len(positions) > 0: 
            return positions[0]
       
    return -1
    
def wait_for_filter(): #wait for the DIL (teensy) to report the filter wheel TTL signal

    for i in range(20): # 2 second polling timeout
        time.sleep(0.1)
        while DIL.inWaiting():
            line = DIL.readline()
            print(' from DIL...', line)
            if(b"Filter_True" in line):
                print("filter wheel completed move")
                return
        if(i==19):
            print("timeout waiting for filter wheel")
            return


DIL_COM             = 'COM6'
Filter_COM          = 'COM5'

DIL = serial.Serial(port=DIL_COM, baudrate=115200, timeout=0.2)
Filter = serial.Serial(port=Filter_COM, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=0.07)
filter_setup()

for i in [1,5,1,1,3]:
    time.sleep(1)
    print('moving to position', i)
    set_filter_position(i)
    wait_for_filter()
    print('after wait', get_filter_position())

Filter.close()
DIL.close()


















