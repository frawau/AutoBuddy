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

import aioblescan as able
from struct import unpack
from base64 import b64decode
from math import sqrt
from statistics import mean
import datetime as dt

SAMPLESIZE=200

#This class manages RuuviTag sensors
class RuuviTag(object):
    name="RuuviTag"
    measurements=["temperature","pressure","humidity","accelerometer"]
    is_running = False
    
    def __init__(self,parent,calibration,throttle):
        self.parent=parent
        self.calibration = calibration
        self.throttle = throttle
        self.calibrating = {}
        self.is_running=True
        self.next_run = {}       #mac keyed dictionaries

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
        url=able.EddyStone(packet)
        if url is None:
            url=packet.retrieve("Payload for mfg_specific_data")
            if url:
                val=url[0].val
                if val[0]==0x99 and val[1]==0x04 and val[2]==0x03:
                    #Looks just right
                    macaddr = packet.retrieve("peer")[0].val
                    if macaddr not in self.next_run:
                        self.next_run[macaddr]={}
                        for x in self.measurements:
                            self.next_run[macaddr][x]=thisrun
                    if macaddr not in self.calibration:
                        self.calibration[macaddr]={"cx":0,"cy":0,"cz":0}
                            
                    result["mac address"]=packet.retrieve("peer")[0].val
                    val=val[2:]
                    if thisrun >= self.next_run[macaddr]["humidity"]:
                        result["humidity"]=val[1]/2.0
                        hasinfo = True
                        if "humidity" in self.throttle:
                            self.next_run[macaddr]["humidity"]=thisrun+dt.timedelta(seconds=self.throttle["humidity"])
                    if thisrun >= self.next_run[macaddr]["temperature"]:
                        result["temperature"]=unpack(">b",int(val[2]).to_bytes(1,"big"))[0]
                        result["temperature"]+=val[3]/100.0
                        hasinfo = True
                        if "temperature" in self.throttle:
                            self.next_run[macaddr]["temperature"]=thisrun+dt.timedelta(seconds=self.throttle["temperature"])
                            
                    if thisrun >= self.next_run[macaddr]["pressure"]:
                        result["pressure"]=int.from_bytes(val[4:6],"big")+50000
                        hasinfo = True
                        if "pressure" in self.throttle:
                            self.next_run[macaddr]["pressure"]=thisrun+dt.timedelta(seconds=self.throttle["pressure"])
                    
                    dx=int.from_bytes(val[6:8],"big",signed=True) + self.calibration[macaddr]["cx"]
                    dy=int.from_bytes(val[8:10],"big",signed=True) + self.calibration[macaddr]["cy"]
                    dz=int.from_bytes(val[10:12],"big",signed=True) + self.calibration[macaddr]["cz"]
                    if thisrun >= self.next_run[macaddr]["accelerometer"]:
                        result["accelerometer"]={"x":dx,"y":dy,"z":dz,"vector":round(sqrt(dx**2 + dy**2 + dz**2),2)}
                        hasinfo = True
                        if "accelerometer" in self.throttle:
                            self.next_run[macaddr]["accelerometer"]=thisrun+dt.timedelta(seconds=self.throttle["accelerometer"])
                    
                    if macaddr in self.calibrating:
                        self.calibrating[macaddr][0].append(int.from_bytes(val[6:8],"big",signed=True) )
                        self.calibrating[macaddr][1].append(int.from_bytes(val[8:10],"big",signed=True) )
                        self.calibrating[macaddr][2].append(int.from_bytes(val[10:12],"big",signed=True))
                        if len(self.calibrating[macaddr][0]) >= SAMPLESIZE:
                            self.done_calibrate(macaddr)
                    result["voltage"]=int.from_bytes(val[12:14],"big")
                    if hasinfo:
                        return result
                    else:
                        return None
            
            else:
                return None
        rssi=packet.retrieve("rssi")
        if rssi:
            result["rssi"]=rssi[-1].val
        power=packet.retrieve("tx_power")
        if power:
            result["tx_power"]=power[-1].val
        try:
            if "//ruu.vi/" in url["url"]:
                #We got a live one
                macaddr=packet.retrieve("peer")[0].val
                result["mac address"]=macaddr
                url=url["url"].split("//ruu.vi/#")[-1] 
                if len(url)>8:
                    url=url[:-1]
                val=b64decode(url+ '=' * (4 - len(url) % 4),"#.")
                if val[0] in [2,4]:
                    if thisrun >= self.next_run[macaddr]["humidity"]:
                        result["humidity"]=val[1]/2.0
                        hasinfo = True
                        if "humidity" in self.throttle:
                            self.next_run[macaddr]["humidity"]=thisrun+dt.timedelta(seconds=self.throttle["humidity"])
                    if thisrun >= self.next_run[macaddr]["temperature"]:
                        result["temperature"]=unpack(">b",int(val[2]).to_bytes(1,"big"))[0] #Signed int...
                        hasinfo = True
                        if "temperature" in self.throttle:
                            self.next_run[macaddr]["temperature"]=thisrun+dt.timedelta(seconds=self.throttle["temperature"])
                    if thisrun >= self.next_run[macaddr]["pressure"]:
                        result["pressure"]=int.from_bytes(val[4:6],"big")+50000
                        hasinfo = True
                        if "pressure" in self.throttle:
                            self.next_run[macaddr]["pressure"]=thisrun+dt.timedelta(seconds=self.throttle["pressure"])
                    if hasinfo:
                        return result
                elif val[0] == 3:
                    if thisrun >= self.next_run[macaddr]["humidity"]:
                        result["humidity"]=val[1]/2.0
                        hasinfo = True
                        if "humidity" in self.throttle:
                            self.next_run[macaddr]["humidity"]=thisrun+dt.timedelta(seconds=self.throttle["humidity"])
                    
                    if thisrun >= self.next_run[macaddr]["temperature"]:
                        result["temperature"]=unpack(">b",int(val[2]).to_bytes(1,"big"))[0]
                        result["temperature"]+=val[3]/100.0
                        hasinfo = True
                        if "temperature" in self.throttle:
                            self.next_run[macaddr]["temperature"]=thisrun+dt.timedelta(seconds=self.throttle["temperature"])
                            
                    if thisrun >= self.next_run[macaddr]["pressure"]:
                        result["pressure"]=int.from_bytes(val[4:6],"big")+50000
                        hasinfo = True
                        if "pressure" in self.throttle:
                            self.next_run[macaddr]["pressure"]=thisrun+dt.timedelta(seconds=self.throttle["pressure"])
                    dx=int.from_bytes(val[6:8],"big",signed=True) + self.calibration[macaddr]["cx"]
                    dy=int.from_bytes(val[8:10],"big",signed=True) + self.calibration[macaddr]["cy"]
                    dz=int.from_bytes(val[10:12],"big",signed=True) + self.calibration[macaddr]["cz"]
                    if thisrun >= self.next_run[macaddr]["accelerometer"]:
                        result["accelerometer"]={"x":dx,"y":dy,"z":dz,"vector":round(sqrt(dx**2 + dy**2 + dz**2),2)}
                        hasinfo = True
                        if "accelerometer" in self.throttle:
                            self.next_run[macaddr]["accelerometer"]=thisrun+dt.timedelta(seconds=self.throttle["accelerometer"])
                    if macaddr in self.calibrating:
                        self.calibrating[macaddr][0].append(int.from_bytes(val[6:8],"big",signed=True) )
                        self.calibrating[macaddr][1].append(int.from_bytes(val[8:10],"big",signed=True) )
                        self.calibrating[macaddr][2].append(int.from_bytes(val[10:12],"big",signed=True))
                        if len(self.calibrating[macaddr][0]) >= SAMPLESIZE:
                            self.done_calibrate(macaddr)
                    result["voltage"]=int.from_bytes(val[12:14],"big")
                    if hasinfo:
                        return result
        except:
            return None
        return None
    
PluginObject=RuuviTag
