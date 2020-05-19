#! /usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Plugin to generate Daikin AC IR commands as done by the ARC480A44
#
# This module without the work/code from:
#      Scott Kyle https://gist.github.com/appden/42d5272bf128125b019c45bc2ed3311f
#      mat_fr     https://www.instructables.com/id/Reverse-engineering-of-an-Air-Conditioning-control/
#
# Copyright (c) 2020 François Wautier
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

import struct
from hashlib import blake2b

try:
    from .hvaclib import HVAC
except:
    class HVAC(object):

        def available_functions(self):
            return {}

        def build_ircode(self):
            return self._build_ircode()

STARFRAME = [ 3500, 1750 ]
ENDFRAME = [435, 10000 ]
MARK = 435
SPACE0 = 435
SPACE1 = 1300

FBODY = b'\x88\x5b\xe4\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa3\x00\x10'


def bit_reverse(i, n=8):
    return int(format(i, '0%db' % n)[::-1], 2)




class Daikin(HVAC):
    """Generic Daikin HVAC object. It must have, at the very minimum
       "mode" and "temperature" capabilities"""

    def __init__(self):
        self.brand = "Daikin"
        self.model = "Generic"
        self.capabilities = {"mode": ["off", "cool", "fan", "dry"],
                             "temperature": [x for x in range(18,32)]
                             }
        #For functions that require their own frames
        self.xtra_capabilities = {}
        self.status = {"mode": "cool",
                       "temperature": 25}

        self.to_set = {}
        #Specify wether the bits order has to be swapped
        self.is_msb = False
        self.FBODY = b'\x88\x5b\xe4\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa3\x00\x10'


    def set_temp(self, temp):
        if temp < self.capabilities["temperature"][0]:
            temp = self.capabilities["temperature"][0]
        elif temp > self.capabilities["temperature"][-1]:
            temp = self.capabilities["temperature"][-1]
            temp = 27
        self.to_set["temperature"] = temp

    def code_temp(self):
        if "temperature" in self.to_set:
            temp = self.to_set["temperature"]
            if "mode" in self.to_set and self.to_set["mode"] == "fan":
                temp = 25
        else:
            temp = self.status["temperature"]
        mask = bytearray(b'\x00'*18)
        mask[6] = bit_reverse(temp*2)
        return mask, False

    def set_fan(self, mode):
        if "fan" not in self.capabilities:
            return
        if mode not in self.capabilities["fan"]:
            return
        self.to_set["fan"] = mode

    def code_fan(self):
        """ mode is one of auto, lowest, low, middle, high, highest
        """
        if "fan" in self.to_set:
            mode = self.to_set["fan"]
        else:
            if "fan" in self.capabilities:
                mode = self.status["fan"]
            else:
                mode = "auto"
        rank = ['lowest','low','middle','high','highest']
        if mode not in rank:
            mode="auto"   #Just in case
        mask = bytearray(b'\x00'*18)
        if mode == "auto":
            mask[8] = 0x05
        else:
            mask[8] = bit_reverse(48+(16*rank.index(mode)))
        return mask, False

    def set_swing(self, mode):
        if "swing" not in self.capabilities:
            return
        if mode not in self.capabilities["swing"]:
            return
        self.to_set["swing"] = mode

    def code_swing(self):
        if "swing" in self.to_set:
            mode = self.to_set["swing"]
        else:
            if "swing" in self.capabilities:
                mode = self.status["swing"]
            else:
                mode = False

        mask = bytearray(b'\x00'*18)
        if mode:
            mask[8] = 0xf0
        else:
            mask[8] = 0x00
        return mask, False

    def set_powerfull(self,mode=False):
        if "powerfull" not in self.capabilities:
            return
        if mode not in self.capabilities["powerfull"]:
            return
        self.to_set["powerfull"] = mode

    def code_powerfull(self):

        if "powerfull" in self.to_set:
            mode = self.to_set["powerfull"]
        else:
            if "powerfull" in self.capabilities:
                mode = self.status["powerfull"]
            else:
                mode = False

        mask = bytearray(b'\x00'*18)
        if mode==True:
            mask[13] = 0x80
        return mask, True

    def set_comfort(self,mode=False):
        if "comfort" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["comfort"]:
            return
        #This is a toggling value AFAIK
        if self.status["comfort"] != mode:
            self.to_set["comfort"] = mode

    def code_comfort(self):
        """Some Daikin AC seem to have such """
        return []


    def set_mode(self,mode):
        if mode not in self.capabilities["mode"]:
            mode = "cool"
        self.to_set["mode"] = mode
        if mode == "fan":
            self.to_set["temperature"] = 25

    def code_mode(self):
        if "mode" in self.to_set:
            mode = self.to_set["mode"]
        else:
            mode = self.status["mode"]

        mask = bytearray(b'\x00'*18)
        if mode == "off":
            mask[5] = 0x0c
            mask[16] = 0x02
        elif mode == "dry":
            mask[5] = 0x84
            mask[6] = 0x03
        elif mode == "fan":
            mask[5] = 0x86
        elif mode == "heat":
            mask[5] = 0x82
        elif mode == "auto":
            mask[5] = 0x80
        else:
            mask[5] = 0x8c
        return mask, True



    def build_code(self):
        frames = []
        packet = bytearray(self.FBODY)
        #Note that set mod must be last for it replaces values
        for f in [self.code_temp, self.code_fan, self.code_swing, self.code_powerfull, self.code_mode]:
            mask,replace = f()
            if replace:
                packet = bytearray([ y or x for x,y in zip(packet,mask)])
            else:
                packet = bytearray([x | y for x,y in zip(packet,mask)])
        frames += [packet]
        return frames

    def _build_ircode(self):
        frames = []
        frames += self.code_comfort()
        frames += self.build_code()
        idx = 0
        for x in frames:
            frames[idx] += self.crc(x)
            idx += 1
        return frames


    def crc(self,frame):
        crc=0
        for x in frame:
            #print("Adding 0x%02x as 0x%02x"%(x,bit_reverse(x)))
            crc += bit_reverse(x)
            #print("crc now 0x%02x"%crc)
        return bit_reverse(crc&0xff).to_bytes(1,'big')


class FTMPV2S(Daikin):

    def __init__(self):
        super().__init__()
        self.model = "FTM-PV2S"
        self.capabilities = {"mode": ["off", "cool", "fan", "dry"],
                             "temperature": [x for x in range(18,32)],
                             "fan": ["auto", "highest", "high", "middle", "low", "lowest"],
                             "swing": [False, True],
                             "powerfull": [False, True]
                             }
        self.status = {"mode": "cool",
                       "temperature": 25,
                       "fan": "auto",
                       "swing": False,
                       "powerfull": False}



class PluginObject(object):

    def __init__(self):
        self.brand = "Daikin"
        self.models = ["generic",  "FTMPV2S"]

    def factory(self, model):
        if model not in self.models:
            model = "generic"

        if model == "generic":
            return Daikin()
        elif model == "FTMPV2S":
            return FTMPV2S()



if __name__ == '__main__':

    import argparse
    import base64

    def to_lirc(frames):
        """Transform a list of frames into a LIRC compatible list of pulse timing pairs"""
        lircframe =  []
        for frame in frames:
            lircframe += STARFRAME
            for x in frame:
                idx = 0x80
                while idx:
                    lircframe.append(MARK)
                    if x & idx:
                        lircframe.append(SPACE1)
                    else:
                        lircframe.append(SPACE0)
                    idx >>= 1
            lircframe += ENDFRAME
        return lircframe

    def to_broadlink(pulses):
        array = bytearray()

        for pulse in pulses:
            pulse = round(pulse * 269 / 8192)  # 32.84ms units

            if pulse < 256:
                array += bytearray(struct.pack('>B', pulse))  # big endian (1-byte)
            else:
                array += bytearray([0x00])  # indicate next number is 2-bytes
                array += bytearray(struct.pack('>H', pulse))  # big endian (2-bytes)

        packet = bytearray([0x26, 0x00])  # 0x26 = IR, 0x00 = no repeats
        packet += bytearray(struct.pack('<H', len(array)))  # little endian byte count
        packet += array
        packet += bytearray([0x0d, 0x05])  # IR terminator

        # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
        remainder = (len(packet) + 4) % 16  # rm.send_data() adds 4-byte header (02 00 00 00)
        if remainder:
            packet += bytearray(16 - remainder)

        return packet


    parser = argparse.ArgumentParser(description="Decode LIRC IR code into frames.")
    # version="%prog " + __version__ + "/" + bl.__version__)
    parser.add_argument("-t", "--temp",  type=int, default=25,
                        help="Temperature (°C). (default 25).")
    parser.add_argument("-m", "--mode",   choices=['cool','dry','fan','off'] , default='cool',
                        help="Mode to set. (default 'cool').")
    parser.add_argument("-f", "--fan",   choices=['auto','highest','high','middle','low','lowest'] , default='auto',
                        help="Fan mode. (default 'auto').")
    parser.add_argument("-s", "--swing", action="store_true", default=False,
                        help="Set sawing")
    parser.add_argument("-p", "--powerfull", action="store_true", default=False,
                        help="Set powerfull")
    parser.add_argument("-l", "--lirc", action="store_true", default=False,
                        help="Output LIRC compatible timing")
    parser.add_argument("-b", "--broadlink", action="store_true", default=False,
                        help="Output Broadlink timing")
    parser.add_argument("-B", "--base64", action="store_true", default=False,
                        help="Output Broadlink timing in base64 encoded")

    try:
        opts = parser.parse_args()
    except Exception as e:
        parser.error("Error: " + str(e))

    device = FTMPV2S()
    frames = []
    device.set_temp(opts.temp)
    device.set_mode(opts.mode)
    device.set_fan(opts.fan)
    device.set_swing(opts.swing)
    device.set_powerfull(opts.powerfull)

    frames = device.build_ircode()

    if opts.lirc:
        lircf = to_lirc(frames)
        while lircf:
            print ("\t".join(["%d"%x for x in lircf[:6]]))
            lircf = lircf[6:]
    elif opts.broadlink or opts.base64:
        lircf = to_lirc(frames)
        bframe = to_broadlink([int(x) for x in lircf])
        if opts.base64:
            print("{}".format(str(base64.b64encode(bframe),'ascii')))
        else:
            print("{}".format(bframe))
    else:
        for f in frames:
            print( " ".join([hex(x) for x in f]))
