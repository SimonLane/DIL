# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 12:06:08 2025

@author: mbp20
"""

import serial
from time import sleep


def get_wavelength():
    maitai.write(b"WAV?\n")
    sleep(0.1)                  #important, need this delay
    while maitai.in_waiting:
        frommt = maitai.readline()
        try:
            wav = int(frommt[:-3])
            return wav
        except:
            pass

def set_wavelength(w):
    w = int(w)
    if w<710 or w>990:
        print('wavelength not in correct range')
        return False
    command = "WAV %s\n" %w
    maitai.write(command.encode('ascii'))
    return True    


def open_shutter():
    command = "SHUT 1\n"
    maitai.write(command.encode('ascii'))

def close_shutter():
    command = "SHUT 0\n"
    maitai.write(command.encode('ascii'))
    
def get_shutter():
    command = "SHUT?\n"
    maitai.write(command.encode('ascii'))
    s = maitai.readline()
    return int(s)

def wait_for_shutter(open_close):
    print('setting shutter to:', open_close)
    for i in range(30):  # 3 second timeout
        s = get_shutter()
        # print(i, s)
        if s == open_close: 
            print('shutter state:', open_close, '(', i*100, 'ms )')
            return 1
        sleep(0.1)
    return -1

def wait_for_laser(): # for use in laser tuning during timelapse (blocking)
    # This function will not return for at least 1 second, could the 'sleep' be reduced?
    count = 0
    try:
        while count < 2:
            maitai.write("READ:AHIS?\n")
            history = maitai.readline().split(' ')
            for i, item in enumerate(history):      # find first instance of '43'
                if item[0:2] == '43': break
            if history[i][2] == '1':                # test if stable
                count = count + 1                   # if stable then increment counter and wait before next test
                sleep(0.5)                          # this works for the thread but it can't be used from the main GUI due to blocking
            else:
                return False                        # if not then exit False
        return True                                 # if counter reaches 2 exit True
    except:
        return False



maitai =  serial.Serial(port='COM8', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.5, xonxoff=0, rtscts=0)
sleep(1)

print(maitai.readlines())

maitai.write(b"WAV?\n")
maitai.write(b"READ:POW?\n")
maitai.write(b"READ:PCTW?\n")
sleep(0.2)
print(maitai.readlines())

open_shutter()
wait_for_shutter(1)

sleep(0.1)
close_shutter()
wait_for_shutter(0)

set_wavelength(750)
wait_for_laser()

maitai.close()
