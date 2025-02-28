# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 13:22:31 2025

@author: ar1e23
"""

w = 800 #Wavelength (nm)

MaiTai_COM = 'COM8'
codec = 'utf8'

import serial
from time import sleep

     
MaiTai = serial.Serial(port=MaiTai_COM, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.5, xonxoff=0, rtscts=0)

ready = False
while not ready:
    MaiTai.write(bytes("READ:PCTW?\n", codec))
    temp = float(MaiTai.readline()[:-2])
    if temp == 0:                                # cold start...
        print("laser cold, issuing ON command")
        MaiTai.write("ON\n")
        sleep(2)
    elif temp >0 and temp <100:                  # wait whilst warming up....
        print("laser warming up, temp: %s" %(temp))
        sleep(2)
    elif temp == 100:                            # ready...
        print("temp at 100%, issuing ON command")
        ready = True
        sleep(0.2)
        MaiTai.write("ON\n")

ready = False
while not ready:
    MaiTai.write("READ:POW?\n")
    power = float(MaiTai.readline()[:-2])
    if power < 0.1:                              # wait...                                                
        print("power ramping up, power: %sW" %(power))
        sleep(2)
    else:
        print("Power above 0.1W")
        sleep(1)
        print("opening shutter")
        MaiTai.write("SHUT 1\n")
        ready = True

            
def get_wavelength():
    MaiTai.write("WAV?\n")
    sleep(0.1)                  #important, need this delay
    while MaiTai.in_waiting:
        frommt = MaiTai.readline()
        try:
            wav = int(frommt[:-3])
        except:
            pass
    return wav

def set_wavelength(w):
    if ready == True: # flag connected?
        w = int(w)
        if w<710 or w>990:
            print('Wavelength not in correct range')
            return False
        MaiTai.write("WAV %s\n" %w)
        print("Wavelength set: %snm" %(w))
        return True
    
def laser_stable(): # for use in laser tuning during timelapse (blocking)
    # This function will not return for at least 1 second, could the 'sleep' be reduced?
    count = 0
    try:
        while count < 2:
            MaiTai.write("READ:AHIS?\n")
            history = MaiTai.readline().split(' ')
            for i, item in enumerate(history):      # find first instance of '43'
                if item[0:2] == '43': break
            if history[i][2] == '1':                # test if stable
                count = count + 1                   # if stable then increment counter and wait before next test
                sleep(0.5)                          # this works for the thread but it can't be used from the main GUI due to blocking
            else:
                return False                        # if not then exit False
        return True                                 # if counter reaches 2 exit True
        print("Wavelength stable")
    except:
        pass
        return False
    
MaiTai.close()