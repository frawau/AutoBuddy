#! /usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Plugin to generate Panasonic AC IR commands
#
# This module without the work/code from:
#      Scott Kyle https://gist.github.com/appden/42d5272bf128125b019c45bc2ed3311f
#      mat_fr     https://www.instructables.com/id/Reverse-engineering-of-an-Air-Conditioning-control/
#      user two, mathieu, vincent
#                 https://www.analysir.com/blog/2014/12/27/reverse-engineering-panasonic-ac-infrared-protocol/
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

FHEADER = b'\x40\x04\x07\x20\x00'
F1BODY = b'\x00\x00'
F2COMMON1 = b'\x00\x00\x70\x07'
F2COMMON2 = b'\x00\x91\x00'
FODOUR = b'\x40\x04\x07\x20\x01\xd9\x4c'
FECON = b'\x40\x04\x07\x20\x01\xa1\xac'
FILLER = b'\x01'

def bit_reverse(i, n=8):
    return int(format(i, '0%db' % n)[::-1], 2)


class Panasonic(HVAC):
    """Generic Panasonic HVAC object. It must have, at the very minimum
       "mode" and "temperature" capabilities"""

    def __init__(self):
        super().__init__()
        self.brand = "Panasonic"
        self.model = "Generic"
        self.capabilities = {"mode": ["off", "auto", "cool", "fan", "dry"],
                             "temperature": [x for x in range(16,32)]
                             }
        #For functions that require their own frames
        self.xtra_capabilities = {}
        self.status = {"mode": "auto",
                       "temperature": 25}

        self.to_set = {}
        #Specify wether the bits order has to be swapped
        self.is_msb = False
        self.base_temp = 16
        self.functions = []

    def set_temperature(self, temp):
        if temp < self.capabilities["temperature"][0]:
            temp = self.capabilities["temperature"][0]
        elif temp > self.capabilities["temperature"][-1]:
            temp = self.capabilities["temperature"][-1]
            temp = 27
        self.to_set["temperature"] = temp

    def code_temperature(self):
        if "temperature" in self.to_set:
            temp = self.to_set["temperature"]
            if "mode" in self.to_set and self.to_set["mode"] == "fan":
                temp = 27
        else:
            temp = self.status["temperature"]
        t = 0x20+((temp-self.base_temp)<<1)
        return bit_reverse(t).to_bytes(1,'big')


    def set_mode(self,mode):
        if mode not in self.capabilities["mode"]:
            mode = "auto"
        self.to_set["mode"] = mode
        if mode == "fan":
            self.to_set["temperature"] = 27
        if mode == "off":
            self.to_set = {"mode": "off"}

    def code_mode(self):
        if "mode" in self.to_set:
            mode = self.to_set["mode"]
        else:
            mode = self.status["mode"]

        if mode == "off":
            return b'\x10'
        elif mode == "dry":
            return b'\x94'
        elif mode == "fan":
            return b'\x96'
        elif mode == "cool":
            return b'\x9c'
        elif mode == "heat":
            return b'\x92'
        else:
            #If we do not know, also auto mode
            return b'\x90'

    def set_fan(self, mode):
        if "fan" not in self.capabilities:
            return
        if mode not in self.capabilities["fan"]:
            return
        self.to_set["fan"] = mode

    def code_fan(self):
        if "fan" in self.to_set:
            mode = self.to_set["fan"]
        else:
            if "fan" in self.capabilities:
                mode = self.status["fan"]
            else:
                mode = None

        if mode == "auto":
            return b'\x05'
        elif mode == "highest":
            return b'\x0e'
        elif mode == "high":
            return b'\x06'
        elif mode == "medium":
            return b'\x0a'
        elif mode == "low":
            return b'\x02'
        elif mode == "lowest":
            return b'\x0c'
        else:
            #If we do not know.... 0
            return b'\x00'


    def set_swing(self, mode):
        if "swing" not in self.capabilities:
            return
        if mode not in self.capabilities["swing"]:
            if "auto" in self.capabilities["swing"] and "auto" in mode:
                self.to_set["swing"] = "auto"
            return
        self.to_set["swing"] = mode

    def code_swing(self):
        if "swing" in self.to_set:
            mode = self.to_set["swing"]
        else:
            if "swing" in self.capabilities:
                mode = self.status["swing"]
            else:
                mode = None

        if mode == "auto":
            return b'\xf0'
        elif mode == "auto high":
            return b'\x70'
        elif mode == "auto low":
            return b'\xb0'
        elif mode == "90":
            return b'\x80'
        elif mode == "60":
            return b'\x40'
        elif mode == "45":
            return b'\xc0'
        elif mode == "30":
            return b'\x20'
        elif mode == "15":
            return b'\xa0'
        else:
            #If we do not know....0
            return b'\x00'

    def set_profile(self, mode):
        if "profile" not in self.capabilities:
            return
        if mode not in self.capabilities["profile"]:
            return
        self.to_set["profile"] = mode

    def code_profile(self):
        if "profile" in self.to_set:
            mode = self.to_set["profile"]
        else:
            if "profile" in self.capabilities:
                mode = self.status["profile"]
            else:
                mode = None
        if mode == "normal":
            return b'\x08'
        elif mode == "boost":
            return b'\x88'
        elif mode == 'quiet':
            return b'\x0c'

        return b'\x00'

    def set_purifier(self,mode=False):
        if "purifier" not in self.capabilities:
            return
        if mode not in self.capabilities["purifier"]:
            return
        self.to_set["purifier"] = mode

    def code_purifier(self):

        if "purifier" in self.to_set:
            mode = self.to_set["purifier"]
        else:
            if "purifier" in self.capabilities:
                mode = self.status["purifier"]
            else:
                mode = None

        if mode == True: # int values could cause a problem....
            return b'\x20'
        else:
            return b'\x00'

    def set_odourwash(self,mode=False):
        if "odourwash" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["odourwash"]:
            return
        #This is a toggling value AFAIK
        if self.status["odourwash"] != mode:
            self.to_set["odourwash"] = mode

    def code_odourwash(self):
        frames = []
        if "odourwash" in self.to_set:
            frames += [FHEADER + F1BODY]
            frames += [FODOUR]
        return frames

    def set_economy(self,mode=False):
        if "economy" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["economy"]:
            return
        #This is a toggling value AFAIK
        if self.status["economy"] != mode:
            self.to_set["economy"] = mode

    def code_economy(self):
        frames = []
        if "economy" in self.to_set:
            frames += [FHEADER + F1BODY]
            frames += [FECON]
        return frames

    def crc(self,frame):
        crc=0
        for x in frame:
            #print("Adding 0x%02x as 0x%02x"%(x,bit_reverse(x)))
            crc += bit_reverse(x)
            #print("crc now 0x%02x"%crc)
        return bit_reverse(crc&0xff).to_bytes(1,'big')


    def build_code(self):
        if "mode" not in self.to_set and self.status["mode"] == "fan":
            self.to_set["temperature"] = 27
        frames = [FHEADER + F1BODY]
        f2 = FHEADER + self.code_mode() + self.code_temperature() + FILLER
        f2 += (self.code_fan()[0] + self.code_swing()[0]).to_bytes(1,'big')
        f2 += F2COMMON1
        f2 += self.code_profile()
        f2 += F2COMMON2
        f2 += self.code_purifier()
        frames += [f2]
        return frames

    def _build_ircode(self):
        frames = []
        frames += self.code_odourwash()
        frames += self.code_economy()
        frames += self.build_code()
        idx = 0
        for x in frames:
            frames[idx] += self.crc(x)
            idx += 1
        return frames



class PanaPX2T5(Panasonic):
    """PX2T5 amd similar Panasonic HVAC object."""

    def __init__(self):
        super().__init__()
        self.model = "PX2T5"
        self.capabilities = {"mode": ["off", "auto", "cool", "fan", "dry"],
                             "temperature": [x for x in range(16,32)],
                             "fan": ["auto", "highest", "medium", "lowest"],
                             "swing": ["auto", "auto high", "auto low", "90", "60", "45", "30"],
                             "purifier": [False,True],
                             }
        #For functions that require their own frames
        self.xtra_capabilities = {"economy": [False,True],
                                  "odourwash": [False, True]}
        self.status = {"mode": "auto",
                       "temperature": 25,
                       "fan": "auto",
                       "swing": "auto",
                        "purifier": False,
                        "economy": False,
                        "odourwash": False}


class PluginObject(object):

    def __init__(self):
        self.brand = "Panasonic"
        self.models = ["generic",  "PX2T5"]

    def factory(self, model):
        if model not in self.models:
            model = "generic"

        if model == "generic":
            return Panasonic()
        elif model == "PX2T5":
            return PanaPX2T5()




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
    parser.add_argument("-m", "--mode",   choices=['auto','cool','dry','fan','off'] , default='auto',
                        help="Mode, one of 'off', 'auto', 'cool', 'dry' or 'fan'. (default 'auto').")
    parser.add_argument("-f", "--fan",   choices=['auto','high','middle','low'] , default='auto',
                        help="Fan, one of 'auto', 'high', 'middle' or 'low'. (default 'auto').")
    parser.add_argument("-s", "--swing",   choices=['auto','auto high','auto low', '90', '60', '45', '30'] , default='auto',
                        help="Swing, one of 'auto','auto high','auto low', '90', '60', '45', '30'. (default 'auto').")
    parser.add_argument("-n", "--nanoex", action="store_true", default=False,
                        help="nanoeX mode")
    parser.add_argument("-o", "--odour", action="store_true", default=False,
                        help="Odour Wash mode")
    parser.add_argument("-e", "--economy", action="store_true", default=False,
                        help="Economy mode")
    parser.add_argument("-l", "--lirc", action="store_true", default=False,
                        help="Output LIRC compatible timing")
    parser.add_argument("-b", "--broadlink", action="store_true", default=False,
                        help="Output Broadlink timing")
    parser.add_argument("-B", "--base64", action="store_true", default=False,
                        help="Output Broadlink timing base64 encoded")

    try:
        opts = parser.parse_args()
    except Exception as e:
        parser.error("Error: " + str(e))

    device = PanaPX2T5()
    frames = []
    device.set_temperature(opts.temp)
    device.set_fan(opts.fan)
    device.set_swing(opts.swing)
    device.set_purifier(opts.nanoex)
    device.set_odourwash(opts.odour)
    device.set_economy(opts.economy)
    device.set_mode(opts.mode)

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
            print( " ".join(["%02x"%x for x in f]))
