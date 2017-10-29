#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Handking if HTU21D humidity and temperature sensor
#
# Copyright (c) 2017 François Wautier
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
##

from time import sleep
import datetime as dt
try:
    from .i2clib import i2c
except:
    from i2clib import i2c


SENSORS = {"temperature":"°C","humidity":"%"}
I2CBUS = 0

HTU21D_ADDR = 0x40
CMD_READ_TEMP_HOLD = 0xe3
CMD_READ_HUM_HOLD = 0xe5
CMD_READ_TEMP_NOHOLD = 0xf3
CMD_READ_HUM_NOHOLD = 0xf5
CMD_WRITE_USER_REG = 0xe6
CMD_READ_USER_REG = 0xe7
CMD_SOFT_RESET= 0xfe


#This class manages HTU21D sensors
class HTU21D(object):
    name="HTU21D"
    measurements=SENSORS

    def __init__(self,bus=I2CBUS):
        self.bus = bus
        self.throttle = {}
        self.calibration = None
        self.next_run = dict([(x,0) for x in SENSORS])
        now= dt.datetime.now()
        for meas in self.measurements:
            self.next_run[meas] = now
            self.throttle[meas] = 10
        self.is_running = False
        self.dev = None

    def SetUp(self):
        return []

    def TearDown(self):
        return []


    def done_calibrate(self,name=None):
        pass

    def do_calibrate(self, mac):
        pass


    def get_measurement(self,what):
        if what == "temperature":
            return round(self.read_temperature(),2)
        elif what == "humidity":
            return round(self.read_humidity(),2)
        return None

    # Ruuvi tag stuffs
    def Process(self,data=None,runtime=None):
        #Look for Ruuvi tag URL and decode it
        if runtime:
            thisrun = runtime
        else:
            thisrun=dt.datetime.now()
        hasinfo=False
        result={}
        self.dev = i2c(HTU21D_ADDR, self.bus) #HTU21D 0x40, bus 0
        self.dev.write(bytes([CMD_SOFT_RESET])) #soft reset
        sleep(.1)
        for meas in self.measurements:
            if thisrun >= self.next_run[meas]:
                result[meas] = self.get_measurement(meas)
                self.next_run[meas]=thisrun+dt.timedelta(seconds=self.throttle[meas])
                hasinfo = True
        self.dev.close()
        self.dev = None
        if hasinfo:
            return result
        else:
            return None

    def ctemp(self, sensorTemp):
        tSensorTemp = (sensorTemp & 0xFFFC) / 65536.0
        return -46.85 + (175.72 * tSensorTemp)

    def chumid(self, sensorHumid):
        tSensorHumid = (sensorHumid & 0xFFFC)/ 65536.0
        return -6.0 + (125.0 * tSensorHumid)

    def crc8check(self, value):
        # Ported from Sparkfun Arduino HTU21D Library: https://github.com/sparkfun/HTU21D_Breakout
        remainder = ( ( value[0] << 8 ) + value[1] ) << 8
        remainder |= value[2]

        # POLYNOMIAL = 0x0131 = x^8 + x^5 + x^4 + 1
        # divsor = 0x988000 is the 0x0131 polynomial shifted to farthest left of three bytes
        divsor = 0x988000

        for i in range(0, 16):
            if( remainder & 1 << (23 - i) ):
                remainder ^= divsor
            divsor = divsor >> 1

        if remainder == 0:
            return True
        else:
            return False

    def read_temperature(self):
        self.dev.write(bytes([CMD_READ_TEMP_NOHOLD])) #measure temp
        sleep(.1)
        temp = int.from_bytes(self.dev.read(2), byteorder="big", signed=False)
        return self.ctemp(temp)
        #data = self.dev.read(3)
        #buf = array.array('B', data)

        #if self.crc8check(buf):
            #temp = (buf[0] << 8 | buf [1]) & 0xFFFC
            #return self.ctemp(temp)
        #else:
            #return -255

    def read_humidity(self):
        self.dev.write(bytes([CMD_READ_HUM_NOHOLD])) #measure humidity
        sleep(.1)

        hum = int.from_bytes(self.dev.read(2), byteorder="big", signed=False)
        return self.ctemp(hum)
        #buf = self.dev.read_block_data(CMD_READ_HUM_NOHOLD,3)
        ##data = self.dev.read(3)
        ##buf = array.array('B', data)

        #if self.crc8check(buf):
            #humid = (buf[0] << 8 | buf [1]) & 0xFFFC
            #return self.chumid(humid)
        #else:
            #return -255

PluginObject=HTU21D

if __name__ == "__main__":
    myi2c = HTU21D(1)
    val=myi2c.Process()
    for x in SENSORS:
        print("{}: {}".format(x,val[x]))
