#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application listen for events and process them according
# to a set of rules. Commands and/or state changes may ensue.
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

from aioblescan.plugins import RuuviWeather
from struct import unpack
from base64 import b64decode
from math import sqrt
from statistics import mean
import datetime as dt

SAMPLESIZE=200
#Key is measurement, value is 2-uple, unit symbol, lambda expression to transform to that unit from raw data if needed
SENSORS = {"temperature": ("°C", None),"pressure": ("hPa", lambda x: x/100.0),"humidity": ("%",None),"accelerometer": ("mɡ",lambda x: x["vector"]),"battery": ("V",lambda x: x/1000.0)}


#This class manages RuuviTag sensors
class RuuviTag(object):
    name="RuuviTag"
    measurements=SENSORS
    is_running = False

    def __init__(self,parent,calibration,throttle):
        self.parent=parent
        self.calibration = calibration
        self.throttle = throttle
        self.calibrating = {}
        self.is_running=True
        self.next_run = {}       #mac keyed dictionaries
        self.avgbat = {};

    def __call__(self,parent,calibration,throttle):
        #Needed when a plugin is disabled then enabled.
        self.calibration = calibration
        self.throttle = throttle
        return self

    def SetUp(self):
        """HCI commands to send when starting the probe. Here it is adv so nothing to do"""
        return []

    def TearDown(self):
        """HCI commands to send when closing probe"""
        return []


    def done_calibrate(self,mac):
        cx=0-round(mean(self.calibrating[mac][0]))
        cy=0-round(mean(self.calibrating[mac][1]))
        cz=0-round(mean(self.calibrating[mac][2]))
        self.calibration[mac]={"cx":cx,"cy":cy,"cz":cz}
        self.parent.update_calibrate(self.name,self.calibration)
        del(self.calibrating[mac])

    def do_calibrate(self, mac):
        self.calibrating[mac]=[[],[],[]]

    # Ruuvi tag stuffs
    def Process(self,packet):
        #Look for Ruuvi tag URL and decode it
        thisrun=dt.datetime.now()
        hasinfo=False
        result={}
        rawresult=RuuviWeather().decode(packet)
        if rawresult:

            macaddr = rawresult["mac address"]
            if macaddr not in self.next_run:
                self.next_run[macaddr]={}
                for x in self.measurements:
                    self.next_run[macaddr][x]=thisrun
            if macaddr not in self.calibration:
                self.calibration[macaddr]={"cx":0,"cy":0,"cz":0}

            result["mac address"]=rawresult["mac address"]
            if thisrun >= self.next_run[macaddr]["humidity"]:
                result["humidity"]=rawresult["humidity"]
                hasinfo = True
                if "humidity" in self.throttle:
                    self.next_run[macaddr]["humidity"]=thisrun+dt.timedelta(seconds=self.throttle["humidity"])
            if thisrun >= self.next_run[macaddr]["temperature"]:
                result["temperature"]=rawresult["temperature"]
                hasinfo = True
                if "temperature" in self.throttle:
                    self.next_run[macaddr]["temperature"]=thisrun+dt.timedelta(seconds=self.throttle["temperature"])

            if thisrun >= self.next_run[macaddr]["pressure"]:
                result["pressure"]=rawresult["pressure"]
                hasinfo = True
                if "pressure" in self.throttle:
                    self.next_run[macaddr]["pressure"]=thisrun+dt.timedelta(seconds=self.throttle["pressure"])

            dx, dy, dz, vector = rawresult["accelerometer"]
            if thisrun >= self.next_run[macaddr]["accelerometer"]:
                result["accelerometer"]={"x":dx,"y":dy,"z":dz,"vector":round(vector,2)}
                hasinfo = True
                if "accelerometer" in self.throttle:
                    self.next_run[macaddr]["accelerometer"]=thisrun+dt.timedelta(seconds=self.throttle["accelerometer"])

            if macaddr in self.calibrating:
                self.calibrating[macaddr][0].append(dx)
                self.calibrating[macaddr][1].append(dy)
                self.calibrating[macaddr][2].append(dz)
                if len(self.calibrating[macaddr][0]) >= SAMPLESIZE:
                    self.done_calibrate(macaddr)
            if macaddr not in self.avgbat:
                self.avgbat[macaddr] = None
            if self.avgbat[macaddr]  is None:
                self.avgbat[macaddr] = rawresult["voltage"]
            else:
                self.avgbat[macaddr]  = (self.avgbat[macaddr]  + rawresult["voltage"])/2
            if thisrun >= self.next_run[macaddr]["battery"]:
                result["battery"]=self.avgbat[macaddr]
                self.avgbat[macaddr] = None #reset
                hasinfo = True
                if "battery" in self.throttle:
                    self.next_run[macaddr]["battery"]=thisrun+dt.timedelta(seconds=self.throttle["battery"])

            if hasinfo:
                return result
        return None

PluginObject=RuuviTag
