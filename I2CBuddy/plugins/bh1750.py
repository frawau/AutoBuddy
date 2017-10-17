#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Handling of BH1750 sensor. Mesures luminosity.
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

ADDR=0x23

POWER_DOWN = 0x00 # No active state
POWER_ON   = 0x01 # Power on
RESET      = 0x07 # Reset data register value

# Start measurement at 4lx resolution. Time typically 16ms.
CONTINUOUS_LOW_RES_MODE = 0x13
# Start measurement at 1lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_1 = 0x10
# Start measurement at 0.5lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_2 = 0x11
# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_1 = 0x20
# Start measurement at 0.5lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_2 = 0x21
# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_LOW_RES_MODE = 0x23

SENSORS = ["luminosity"]
I2CBUS = 0

#This class manages BH1750 sensors
class BH1750(object):
    name="BH1750"
    measurements=SENSORS

    def __init__(self,bus=I2CBUS):
        self.bus = bus
        self.calibration = None
        self.throttle={}
        self.next_run = dict([(x,0) for x in SENSORS])
        now= dt.datetime.now()
        for meas in self.measurements:
            self.next_run[meas] = now
            self.throttle[meas] = 60
        self.is_running = False


    def SetUp(self):
        return []

    def TearDown(self):
        return []


    def done_calibrate(self,name=None):
        pass

    def do_calibrate(self, mac):
        pass


    def get_measurement(self,what):
        if what == "luminosity":
            return round(self.read_luminosity(),2)
        return None

    # Plugin processing stuffs
    def Process(self,data=None,runtime=None):
        #Look for Ruuvi tag URL and decode it
        if runtime:
            thisrun = runtime
        else:
            thisrun=dt.datetime.now()
        hasinfo=False
        result={}
        self.dev = i2c(ADDR, self.bus)
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

    def read_luminosity(self):
        return self.dev.readU16BE(CONTINUOUS_HIGH_RES_MODE_1)/1.2
        #return  int.from_bytes(self.dev.read(2),byteorder="little",signed=False)


PluginObject=BH1750

if __name__ == "__main__":
    myi2c = BH1750(1)
    val=myi2c.Process()
    for x in SENSORS:
        print("{}: {}".format(x,val[x]))
