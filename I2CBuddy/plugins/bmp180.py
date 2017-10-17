#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Handling of BMP180 sensor. Mesures pressure and temperature.
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


SENSORS = ["temperature", "pressure"]
I2CBUS = 0
# BMP085 default address.
BMP085_I2CADDR           = 0x77

# Operating Modes
BMP085_ULTRALOWPOWER     = 0
BMP085_STANDARD          = 1
BMP085_HIGHRES           = 2
BMP085_ULTRAHIGHRES      = 3

# BMP085 Registers
BMP085_CAL_AC1           = 0xAA  # R   Calibration data (16 bits)
BMP085_CAL_AC2           = 0xAC  # R   Calibration data (16 bits)
BMP085_CAL_AC3           = 0xAE  # R   Calibration data (16 bits)
BMP085_CAL_AC4           = 0xB0  # R   Calibration data (16 bits)
BMP085_CAL_AC5           = 0xB2  # R   Calibration data (16 bits)
BMP085_CAL_AC6           = 0xB4  # R   Calibration data (16 bits)
BMP085_CAL_B1            = 0xB6  # R   Calibration data (16 bits)
BMP085_CAL_B2            = 0xB8  # R   Calibration data (16 bits)
BMP085_CAL_MB            = 0xBA  # R   Calibration data (16 bits)
BMP085_CAL_MC            = 0xBC  # R   Calibration data (16 bits)
BMP085_CAL_MD            = 0xBE  # R   Calibration data (16 bits)
BMP085_CONTROL           = 0xF4
BMP085_TEMPDATA          = 0xF6
BMP085_PRESSUREDATA      = 0xF6

# Commands
BMP085_READTEMPCMD       = 0x2E
BMP085_READPRESSURECMD   = 0x34
#This class manages BMP180 sensors
class BMP180(object):
    name="BMP180"
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
        self.mode = BMP085_ULTRAHIGHRES
        self.sealevel_pa = 101325.0
        self.altitude_m = 0.0

    def SetUp(self):
        return []

    def TearDown(self):
        return []


    def done_calibrate(self,name=None):
        pass

    def do_calibrate(self, data):
        """Correct the value for either altitude or sea level pressure to calculate the other
        """
        try:
            if "altitude" in data:
                self.altitude_m = data["altitude"]
            if "sealevel" in data:
                self.sealevel_pa = data["sealevel"]
        except:
            pass



    def get_measurement(self,what):
        if what == "temperature":
            return round(self.read_temperature(),2)
        if what == "pressure":
            return round(self.read_pressure(),2)
        if what == "altitude":
            return round(self.read_altitude(),2)
        if what == "sealevel":
            return round(self.read_sealevel_pressure(),2)
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
        self.dev = i2c(BMP085_I2CADDR, self.bus)
        self._load_calibration()
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


    def _load_calibration(self):
        self.cal_AC1 = self.dev.readS16BE(BMP085_CAL_AC1)   # INT16
        self.cal_AC2 = self.dev.readS16BE(BMP085_CAL_AC2)   # INT16
        self.cal_AC3 = self.dev.readS16BE(BMP085_CAL_AC3)   # INT16
        self.cal_AC4 = self.dev.readU16BE(BMP085_CAL_AC4)   # UINT16
        self.cal_AC5 = self.dev.readU16BE(BMP085_CAL_AC5)   # UINT16
        self.cal_AC6 = self.dev.readU16BE(BMP085_CAL_AC6)   # UINT16
        self.cal_B1 = self.dev.readS16BE(BMP085_CAL_B1)     # INT16
        self.cal_B2 = self.dev.readS16BE(BMP085_CAL_B2)     # INT16
        self.cal_MB = self.dev.readS16BE(BMP085_CAL_MB)     # INT16
        self.cal_MC = self.dev.readS16BE(BMP085_CAL_MC)     # INT16
        self.cal_MD = self.dev.readS16BE(BMP085_CAL_MD)     # INT16

    def read_raw_temp(self):
        """Reads the raw (uncompensated) temperature from the sensor."""
        self.dev.write_byte_data(BMP085_CONTROL, BMP085_READTEMPCMD)
        sleep(0.005)  # Wait 5ms
        raw = self.dev.readU16BE(BMP085_TEMPDATA)
        #print('Raw temp 0x{0:X} ({1})'.format(raw & 0xFFFF, raw))
        return raw

    def read_raw_pressure(self):
        """Reads the raw (uncompensated) pressure level from the sensor."""
        self.dev.write_byte_data(BMP085_CONTROL, BMP085_READPRESSURECMD + (self.mode << 6))
        if self.mode == BMP085_ULTRALOWPOWER:
            sleep(0.005)
        elif self.mode == BMP085_HIGHRES:
            sleep(0.014)
        elif self.mode == BMP085_ULTRAHIGHRES:
            sleep(0.026)
        else:
            sleep(0.008)
        #raw = int.from_bytes(self.dev.read_block_data(BMP085_PRESSUREDATA,3),byteorder="big",signed=False) >> (8 - self.mode)
        msb = self.dev.readU8(BMP085_PRESSUREDATA)
        lsb = self.dev.readU8(BMP085_PRESSUREDATA+1)
        xlsb = self.dev.readU8(BMP085_PRESSUREDATA+2)
        raw = ((msb << 16) + (lsb << 8) + xlsb) >> (8 - self.mode)
        #print('Raw pressure 0x{0:04X} ({1})'.format(raw & 0xFFFF, raw))
        return raw

    def read_temperature(self):
        """Gets the compensated temperature in degrees celsius."""
        UT = self.read_raw_temp()
        # Datasheet value for debugging:
        #UT = 27898
        # Calculations below are taken straight from section 3.5 of the datasheet.
        X1 = ((UT - self.cal_AC6) * self.cal_AC5) >> 15
        X2 = (self.cal_MC << 11) // (X1 + self.cal_MD)
        B5 = X1 + X2
        temp = ((B5 + 8) >> 4) / 10.0
        #print('Calibrated temperature {0} C'.format(temp))
        return temp

    def read_pressure(self):
        """Gets the compensated pressure in Pascals."""
        UT = self.read_raw_temp()
        UP = self.read_raw_pressure()
        # Datasheet values for debugging:
        #UT = 27898
        #UP = 23843
        # Calculations below are taken straight from section 3.5 of the datasheet.
        # Calculate true temperature coefficient B5.
        X1 = ((UT - self.cal_AC6) * self.cal_AC5) >> 15
        X2 = (self.cal_MC << 11) // (X1 + self.cal_MD)
        B5 = X1 + X2
        # Pressure Calculations
        B6 = B5 - 4000
        X1 = (self.cal_B2 * (B6 * B6) >> 12) >> 11
        X2 = (self.cal_AC2 * B6) >> 11
        X3 = X1 + X2
        B3 = (((self.cal_AC1 * 4 + X3) << self.mode) + 2) // 4
        X1 = (self.cal_AC3 * B6) >> 13
        X2 = (self.cal_B1 * ((B6 * B6) >> 12)) >> 16
        X3 = ((X1 + X2) + 2) >> 2
        B4 = (self.cal_AC4 * (X3 + 32768)) >> 15
        B7 = (UP - B3) * (50000 >> self.mode)
        if B7 < 0x80000000:
            p = (B7 * 2) // B4
        else:
            p = (B7 // B4) * 2
        X1 = (p >> 8) * (p >> 8)
        X1 = (X1 * 3038) >> 16
        X2 = (-7357 * p) >> 16
        p = p + ((X1 + X2 + 3791) >> 4)
        #print('Pressure {0} Pa'.format(p))
        return p

    def read_altitude(self):
        """Calculates the altitude in meters."""
        # Calculation taken straight from section 3.6 of the datasheet.
        pressure = float(self.read_pressure())
        altitude = 44330.0 * (1.0 - pow(pressure / self.sealevel_pa, (1.0/5.255)))
        #print('Altitude {0} m'.format(altitude))
        return altitude

    def read_sealevel_pressure(self):
        """Calculates the pressure at sealevel when given a known altitude in
        meters. Returns a value in Pascals."""
        pressure = float(self.read_pressure())
        p0 = pressure / pow(1.0 - self.altitude_m/44330.0, 5.255)
        #print('Sealevel pressure {0} Pa'.format(p0))
        return p0


PluginObject=BMP180

if __name__ == "__main__":
    myi2c = BMP180(1)
    val=myi2c.Process()
    for x in SENSORS:
        print("{}: {}".format(x,val[x]))
