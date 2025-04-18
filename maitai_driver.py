import serial, struct, time, collections, threading, re, pdb
#try:
from SerialDevice import SerialDevice, TimeoutError, DataError
#except ValueError:
#    ## relative imports not allowed when running from command prompt, so
#    ## we adjust sys.path when running the script for testing
#    if __name__ == '__main__':
#        import sys, os
#        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#        from SerialDevice import SerialDevice, TimeoutError, DataError


StatusErrorCodesPumpLaser = {
    1: ('Laser ON, Power Mode OK'),
    2: ('Laser ON, CurrentMode OK'),
    3: (' Laser ON, Power Mode Adjust'),
    4: (' Laser ON, Current Mode Adjust'),
    5: (' Laser Diodes OFF, Ready'),
    6: (' Sleep Mode OK'),
    56: ('Watchdog expired, Turn laser key'),
    58: ('Watchdog working normally'),
    88: ('Diode Therm Short'),
    89: (' Diode Therm Open'),
    90: ('Diode MaxT Exceed'),
    91: ('Diode Over Temperature'),
    92: ('Diode Under Temperature'),
    100: ('Diode Temperature'),
    101: ('HSink Over Temperature'),
    102: ('HSink Under Temperature'),
    103: ('HSink Therm Short'),
    104: ('HSink Therm Open'),
    105: ('HSink MaxT Exceed'),
    106: ('Tower Temperature'),
    116: ('Interlocks Cleared'),
    117: ('Fuse Interlock'),
    118: ('System Interlock'),
    119: ('User Interlock'),
    120: ('Key Switch ILK'),
    121: ('Remote Interlock'),
    122: ('Head Interlock'),
    123: ('Boot test Fail'),
    131: ('Head overtemp check chiller'),
    201: ('Current Calibration Diode 1'),
    202: ('Current Calibration Diode 2'),
    205: ('Temperature Calibration Diode 1'),
    206: ('Temperature Calibration Diode 2'),
    209: (' SHG temperature Setting'),
}


StatusErrorCodes = {
    400: ('System just finished boot'),
    405: ('System ON'),
    406: ('System OFF'),
    407: ('command MODE PCUR received'),
    408: ('command MODE PPOW received'),
    409: ('command MODE POW received'),
    421: ('communication error between Mai Tai & Power Supply'),
    430: ('motors are moving'),
    431: ('wavelength is stable, all motors stopped'),
    444: ('P2 is between 10 and 90 %'),
    445: ('P2 (X or Y) is between 1 and 10 % or 90 and 99 %'),
    446: ('P2 (X or Y) is lower than 1 % or greater than 99 %'),
    450: ('M3 is not available'),
    451: ('M3 is disabled'),
    452: ('M3 is inactive'),
    453: ('M3 is active'),
    454: ('M3 are between 10 and 90 %'),
    455: ('M3 (X or Y) is betweeen 1 and 10 % or 90 and 99 %'),
    456: ('M3 (X or Y) is lower than 1 or greater than 99 %'),
    460: ('IR loop is not available'),
    461: ('IR loop disabled'),
    462: ('IR loop is inactive'),
    463: ('IR loop is active'),
    470: ('Tower temperature is correct'),
    471: ('Tower temperature is warm'),
    472: ('Tower temperature is hot'),
    474: ('Tower temperature is cold'),
}
        
class TimeoutError(Exception):
    pass

class MaiTaiError(Exception):
    pass

class MaiTai(SerialDevice):
    """
    Class for communicating with Spectra-Physics Mai Tai laser via serial port.
    
    """
    def __init__(self, port, baud=38400): #9600):
        """
        port: serial COM port (0 => com1)"""

        self.re_float = re.compile(r'\d*\.?\d+')
        self.port = port
        self.baud = baud
        SerialDevice.__init__(self, port=int(self.port), baudrate=self.baud, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,xonxoff=True)
        self.waitTime = 0.5
        print('connected')
        self.modeNames = {'PCUR':'Current %', 'PPOW':'Green Power', 'POW':'IR Power'}
    
    def convertToFloat(self,returnString):
        return float(re.findall(self.re_float,returnString)[0])
        
    def getWavelength(self):
        """Reads and returns the Mai Tai operating wavelength. the returned value may not match the commanded wavelength until the system has finished moving to the newly commanded wavelength."""
        waveLengthStr = self['READ:WAVelength?']
        return self.convertToFloat(waveLengthStr)
    
    def setWavelength(self, wl, block=False):
        """Sets the Mai Tai wavelength betweeen 690 and 1020 nm (actual wavelength range may depend on the Mai Tai model ordered).
        If block=True, do not return until the tuning is complete."""
        (minWaveLength,maxWaveLength) = self.getWavelengthRange()
        if (wl < minWaveLength) or (wl > maxWaveLength):
            raise Exception("Specified wavelength of %s nm is outside the supported range by the Mai Tai : %s < wavelength < %s" % (wl,minWaveLength,maxWaveLength)  )
        else:
            self['WAVelength'] = int(wl)
            if block:
                while True:
                    if self.getWavelength() == wl:
                        break
                    time.sleep(0.1)

    def getWavelengthRange(self):
        minWl = self['WAVelength:MIN?']
        maxWl = self['WAVelength:MAX?']
        return self.convertToFloat(minWl), self.convertToFloat(maxWl)
    
    def getRelativeHumidity(self):
        """Reads and returns the relative humidity (in percent) of the Mai Tai Ti:sapphire laser cavity. Humidity should always be below 10 %."""
        relHumidity = self['READ:HUM?']
        return self.convertToFloat(relHumidity)
    
    def isLaserOn(self):
        """Returns wheter laser is on."""
        status = int(self['*STB?'])  #Returns the product status byte.
        return self.is_set(status,0)
    
    def getPower(self):
        """Reads and returns Mai Tai output power"""
        outputPower = self['READ:POWer?']
        return self.convertToFloat(outputPower)
    
    def getPumpPower(self):
        """Reads and returns laser output power of the pump laser"""
        pumpOutputPower = self['READ:PLASer:POWer?']
        return self.convertToFloat(pumpOutputPower)
    
    def getLastCommandedPumpLaserPower(self):
        """ returns the last commanded pump laser power in Watts."""
        return self.convertToFloat(self['PLASer:POWer?'])
    
    def setPumpLaserPower(self, ppower):
        """ set the pump laser power """
        self['PLASer:POWer'] = float(ppower)
    
    def getShutter(self):
        """Return True if the shutter is open."""
        return bool(int(self['SHUTter?']))
    
    def setShutter(self, val):
        """Open (True) or close (False) the shutter"""
        while self.getShutter() != val:
            self['SHUTter'] = (1 if val else 0)
        if val:
            print('Shutter OPEN')
        else:
            print('Shutter CLOSED')
        
    def getPumpMode(self):
        """ returns pump mode of the laser """
        crypticMode = self['MODE?']
        return self.modeNames[crypticMode]
    
    def setPumpMode(self, mode):
        """ sets the pump mode of the laser """
        oldMode = self.getPumpMode()
        for k in self.modeNames :
            if mode == self.modeNames[k] :
                self['MODE'] = k
        newMode = self.getPumpMode()
        print('changedMode : ', oldMode, newMode)
        
    def getSystemIdentification(self):
        """Return a system identification string that contains 4 fields separated by commas."""
        return self['*IDN?']
    
    def checkPulsing(self):
        """Return True if the laser is pulsing."""
        status = int(self['*STB?'])  #Returns the product status byte.
        return self.is_set(status,1)
    
    def getHistoryBuffer(self):
        """ returns the content of the history buffer for the status and error codes """
        history = self['READ:AHISTory?']
        lhist = [int(k) for k in history.split()]
        if lhist[0] in StatusErrorCodes:
            return StatusErrorCodes[lhist[0]]
        else:
            return ("Unknown status/error code %s" % lhist[0])
   
    def getHistoryBufferPumpLaser(self):
        """ returns the content of the history buffer for the status and error codes of the pump laser operation """
        historyPL = self['PLASer:AHISTory?']
        lhistPL = [int(k) for k in historyPL.split()]
        if lhistPL[0] in StatusErrorCodesPumpLaser:
            return StatusErrorCodesPumpLaser[lhistPL[0]]
        else:
            return ("Unknown Pump Laser status/error code %s" % lhistPL[0])
    
    def getP2Status(self):
        """ returns P2 pump optimization status. The values returned are servos active (TRUE) or inactive(FALSE). """
        p2Status = int(self['READ:PDITher?'])
        if p2Status == 443: # P2 switch = Autoseek: if output power > ~ 150 mW, servo is active
            return True
        elif p2Status == 441: # P2 switch = off: servo always inactive
            return False
        elif p2Status == 442: # P2 switch = Autoseek: if output power < ~130 mW, servo is inactive
            return False
        else:
            return "Unknown status"
    
    def setP2Status(self, enable):
        """ Enable (1) or disable (0) the 'dither for power'. This  loop  dithers  mirror  P """
        self['CONTrol:PDITher'] = int(enable)
    
    def is_set(self,x, n):
        """ checks whether n^th bit is set"""
        return (x & 2**n != 0)

    def turnLaserOn(self):
        
        while True:
            warmedUP = self.convertToFloat(self['READ:PCTWarmedup?'])
            if warmedUP == 100.:
                break
            else:
                print('System warming up. Currently at %f ' % warmedUP)
                time.sleep(self.waitTime)

        self.write('ON\r')
        time.sleep(self.waitTime)
        print('LASER IS ON')
        
    def turnLaserOff(self):
        if self.getShutter():
            self.setShutter(False)
        self.write('OFF\r')
        time.sleep(self.waitTime)
        print('LASER IS OFF')
    
    def __getitem__(self, arg):  ## request a single value from the laser
        #print("write", arg
        self.write("%s\r" % arg)
        ret = self.readPacket()
        #print("   return:", ret
        return ret
        
    def __setitem__(self, arg, val):  ## set a single value on the laser
        #print("write", arg, val
        self.write("%s %s\r" % (arg,str(val)))
        #ret = self.readPacket()
        #print("   return:", ret
        #return ret

    def clearBuffer(self):
        d = self.read()
        time.sleep(0.1)
        d += self.read()
        if len(d) > 0:
            print("Mai Tai: Warning: tossed data ", repr(d))
        return d
    
    def readPacket(self, expect=0, timeout=10, block=True):
        ## Read until a CRLF is encountered (or timeout).
        ## If expect is >0, then try to get a packet of that length, ignoring CRLF within that data
        ## if block is False, then return immediately if no data is available.
        start = time.time()
        s = ''
        errors = []
        packets = []
        while True:
            n = self.serial.inWaiting()
            s += self.read(n)
            #print("read:", repr(s)
            if not block and len(s) == 0:
                return
            
            while len(s) > 0:  ## pull packets out of s one at a time
                if '\n' in s[expect:]:
                    i = expect + s[expect:].index('\n')
                    packets.append(s[:i])
                    expect = 0
                    s = s[i+2:]
                else:
                    break
                
            if len(s) == 0:
                if len(packets) == 1:
                    if 'Error' in packets[0]:
                        raise Exception(packets[0])
                    return packets[0]   ## success
                if len(packets) > 1:
                    raise Exception("Too many packets read.", packets)
            
            time.sleep(0.01)
            if time.time() - start > timeout:
                raise TimeoutError("Timeout while waiting for response. (Data so far: %s)" % (repr(s)))
      
        
if __name__ == '__main__':
    maiTai = MaiTai(port=2) 
    #maiTai.setWavelength(910)
    #print('current wavelength : ', maiTai.getWavelength()
    #maiTai.setWavelength(880)
    #print('current wavelength : ', maiTai.getWavelength()
    
    print('relative Humidity : ', maiTai.getRelativeHumidity())
    print('current wavelength : ', maiTai.getWavelength())
    
    print('output power : ', maiTai.getPower())
    print('pump power : ', maiTai.getPumpPower())
    
    print('shutter open? : ', maiTai.getShutter())
    
    print('check status : ', maiTai.checkStatus())
    
    print('turning laser on : ', maiTai.turnLaserOn())
    print('done')
    print('check status : ', maiTai.checkStatus())
    print('opening shutter : ', maiTai.setShutter(True))
    print('done')
    print('check status : ', maiTai.checkStatus())
    n=0
    while n < 10:
        print('relative Humidity : ', maiTai.getRelativeHumidity())
        print('output power : ', maiTai.getPower())
        print('pump power : ', maiTai.getPumpPower())
        time.sleep(1)
        n+=1
    
    print('closing shutter : ', maiTai.setShutter(False))
    print('done')
    print('turning laser off : ', maiTai.turnLaserOff())
    print('done')
            
