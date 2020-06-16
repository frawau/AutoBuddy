#! /usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Plugin to generate LG AC IR commands as done by the AXB74515402
#
# Found the info about 4 bits somewhere on the  Internet...Can't find
# it again. Apologies for not being able to thanks that person.
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


STARFRAME = [ 3100, 9850 ]
ENDFRAME = [520, 12000 ]
MARK = 520
SPACE0 = 520
SPACE1 = 1530



def bit_reverse(i, n=8):
    return int(format(i, '0%db' % n)[::-1], 2)




class LG(HVAC):
    """Generic LG HVAC object. It must have, at the very minimum
       "mode" and "temperature" capabilities"""

    def __init__(self):
        super().__init__()
        self.brand = "LG"
        self.model = "Generic"
        self.capabilities = {"mode": ["off", "cool", "fan", "dry"],
                             "temperature": [x for x in range(18,30)]
                             }
        #For functions that require their own frames
        self.xtra_capabilities = {}
        self.status = {"mode": "off",
                       "temperature": 25}

        self.to_set = {}
        #Specify wether the bits order has to be swapped
        self.is_msb = False
        self.FBODY = b'\x88\x00\x00'


    def set_temperature(self, temp):
        if temp < self.capabilities["temperature"][0]:
            temp = self.capabilities["temperature"][0]
        elif temp > self.capabilities["temperature"][-1]:
            temp = self.capabilities["temperature"][-1]
        if temp != self.status["temperature"]:
            self.to_set["temperature"] = temp

    def code_temperature(self):
        if "temperature" in self.to_set:
            temp = self.to_set["temperature"]
        else:
            temp = self.status["temperature"]

        if "mode" in self.to_set:
            mode = self.to_set["mode"]
        else:
            mode = self.status["mode"]

        if mode == "fan":
            temp = 18
        elif mode == "auto":
            if "auto_bias" in self.status:
                try: #Getting ahead of oneself...
                    if "auto_bias" in self.to_set:
                        temp = 15 + self.capabilities["auto_bias"].index(self.to_set["auto_bias"])
                    else:
                        temp = 15 + self.capabilities["auto_bias"].index(self.status["auto_bias"])
                except:
                    temp = 17
            else:
                temp = 17
        elif mode == "dry":
                temp = 24
        mask = bytearray(b'\x00'*3)
        mask[2] = (temp-15)<<4
        return mask, False

    def set_auto_bias(self, mode):
        if "auto_bias" not in self.capabilities:
            return
        if mode not in self.capabilities["auto_bias"]:
            return
        if self.status["auto_bias"] != mode:
            self.to_set["auto_bias"] = mode

    def set_fan(self, mode):
        if "fan" not in self.capabilities:
            return
        if mode not in self.capabilities["fan"]:
            return
        if self.status["fan"] != mode:
            self.to_set["fan"] = mode

    def code_fan(self):
        """ mode is one of auto, lowest, low, middle, high, highest
        """
        if "fan" in self.to_set:
            fmode = self.to_set["fan"]
        else:
            if "fan" in self.capabilities:
                fmode = self.status["fan"]
            else:
                fmode = "auto"
        rank = {'lowest': 0x0,'low':0x09,'middle': 0x02,'high': 0x0a,'highest': 0x04, "auto": 0x05}

        if "mode" in self.to_set:
            mode = self.to_set["mode"]
        else:
            mode = self.status["mode"]

        if mode == "auto":
            fmode = "auto"
        if fmode not in rank:
            fmode="auto"   #Just in case
        mask = bytearray(b'\x00'*3)
        mask[2] = rank[fmode]
        return mask, False

    def set_swing(self, mode):
        if "swing" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["swing"]:
            return
        if self.status["swing"] != mode:
            self.to_set["swing"] = mode

    def code_swing(self):
        if "swing" in self.to_set:
            mode = self.to_set["swing"]

            if mode in ["swing","on"]:
                return bytearray(b'\x88\x13\x14')
            elif mode == "off":
                return bytearray(b'\x88\x13\x15')
            elif mode == "0":
                return bytearray(b'\x88\x13\x04')
            elif mode == "15":
                return bytearray(b'\x88\x13\x05')
            elif mode == "30":
                return bytearray(b'\x88\x13\x06')
            elif mode == "45":
                return bytearray(b'\x88\x13\x07')
            elif mode == "60":
                return bytearray(b'\x88\x13\x08')
            elif mode == "90":
                return bytearray(b'\x88\x13\x09')

        return bytearray()

    def set_hswing(self, mode):
        if "hswing" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["hswing"]:
            return
        if self.status["hswing"] != mode:
            self.to_set["hswing"] = mode

    def code_hswing(self):
        if "hswing" in self.to_set:
            mode = self.to_set["hswing"]

            if mode in ["swing","on"]:
                return bytearray(b'\x88\x13\x16')
            elif mode == "off":
                return bytearray(b'\x88\x13\x17')
            elif mode == "left":
                return bytearray(b'\x88\x13\x0b')
            elif mode == "centre left":
                return bytearray(b'\x88\x13\x0c')
            elif mode == "centre":
                return bytearray(b'\x88\x13\x0d')
            elif mode == "centre right":
                return bytearray(b'\x88\x13\x0e')
            elif mode == "right":
                return bytearray(b'\x88\x13\x0f')
            elif mode == "swing left":
                return bytearray(b'\x88\x13\x10')
            elif mode == "swing right":
                return bytearray(b'\x88\x13\x11')
        return bytearray()

    def set_powerfull(self,mode="off"):
        #print("\n\nLG set powerfull {}\n\n".format(mode))
        if "powerfull" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["powerfull"]:
            return
        if self.status["powerfull"] != mode:
            self.to_set["powerfull"] = mode

    def code_powerfull(self):

        if "powerfull" in self.to_set:
            mode = self.to_set["powerfull"]
            if mode == "on":
                return bytearray(b'\x88\x10\x08')
            #Off... send the "normal" code
            dosend = True
            for x in self.capabilities:
                if x in self.to_set:
                    dosend = False
                    break
            if dosend:
                otoset = self.to_set
                self.to_set = {"mode": self.status["mode"]}
                frame = self.build_code()
                self.to_set = otoset
                return frame
        return []

    def set_purifier(self,mode="off"):
        if "purifier" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["purifier"]:
            return
        #This is a toggling value AFAIK
        if self.status["purifier"] != mode:
            self.to_set["purifier"] = mode

    def code_purifier(self):
        """Some LG AC seem to have such """
        if self.to_set["purifier"] == "on":
            return bytearray(b'\x88\xc0\x00')
        else:
            return bytearray(b'\x88\xc0\x08')

    def set_economy(self, mode):
        if "economy" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["economy"]:
            return
        if self.status["economy"] != mode:
            self.to_set["economy"] = mode

    def code_economy(self):
        if "economy" in self.to_set:
            mode = self.to_set["economy"]

            if mode == "off":
                return bytearray(b'\x88\xc0\x7f')
            elif mode == "80":
                return bytearray(b'\x88\xc0\x7d')
            elif mode == "60":
                return bytearray(b'\x88\xc0\x7e')
            elif mode == "40":
                return bytearray(b'\x88\xc0\x80')

        return bytearray()

    def set_cleaning(self, mode):
        if "cleaning" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["cleaning"]:
            return
        if self.status["cleaning"] != mode:
            self.to_set["cleaning"] = mode

    def code_cleaning(self):
        if "cleaning" in self.to_set:
            mode = self.to_set["cleaning"]

            if mode == "off":
                return bytearray(b'\x88\xc0\x0b')
            elif mode == "on":
                return bytearray(b'\x88\xc0\x0c')

        return bytearray()

    def set_diagnostic(self):
        if "diagnostic" not in self.xtra_capabilities:
            return
        if mode not in self.xtra_capabilities["diagnostic"]:
            return
        if self.status["diagnostic"] != mode:
            self.to_set["diagnostic"] = mode

    def code_cleaning(self):
        if "diagnostic" in self.to_set:
            mode = self.to_set["diagnostic"]
            self.to_set["diagnostic"] = "off" #It is a request, not a toggle
            if mode == "on":
                return bytearray(b'\x88\xc0\xce')

    def set_mode(self,mode):
        if mode not in self.capabilities["mode"]:
            mode = "cool"
        if mode != self.status["mode"]:
             self.to_set["mode"] = mode

    def code_mode(self):
        if "mode" in self.to_set:
            mode = self.to_set["mode"]
        else:
            mode = self.status["mode"]

        mask = bytearray(b'\x88\x00\x00')
        if mode == "off":
            return bytearray(b'\x00\xc0\x05'), True
        if self.status["mode"] != "off":
            addit = 8
        else:
            addit = 0
        mask = bytearray(b'\x00\x00\x00')
        if mode == "auto":
            mask[1] = 3 + addit
        elif  mode == "cool":
            mask[1] = addit
        elif  mode == "dry":
            mask[1] = 1 + addit
        elif  mode == "fan":
            mask[1] = 2 + addit

        return mask, False



    def build_code(self):
        frames = []
        packet = bytearray(self.FBODY)
        #Note that set mod must be last for it replaces values
        if {'mode','temperature','fan'}.intersection(set(self.to_set.keys())):
            for f in [self.code_temperature, self.code_fan, self.code_mode]:
                mask,replace = f()
                if replace:
                    packet = bytearray([ y or x for x,y in zip(packet,mask)])
                else:
                    packet = bytearray([x | y for x,y in zip(packet,mask)])
            frames += [packet]
        if "mode" in self.to_set:
            mode = self.to_set["mode"]
        else:
            mode = self.status["mode"]
        if mode != "off":
            print("Mode is {} from {}".format(mode,self.to_set))
            for prop in self.xtra_capabilities:
                    #print("Looking at {} with {} and {}".format(prop,self.to_set,self.status))
                    if prop in self.to_set and self.to_set[prop] != self.status[prop]:
                        f = getattr(self,"code_"+prop,None)
                        if f:
                            frames.append(f())
        return frames

    def _build_ircode(self):
        frames = []
        frames += self.build_code()
        idx = 0
        for x in frames:
            frames[idx] += self.crc(x)
            idx += 1
        return frames


    def crc(self,frame):
        crc=0
        for x in frame:
            crc += (x&0xf0)>>4
            crc += (x&0x0f)
        return ((crc&0x0f)<<4).to_bytes(1,'big')

    def get_timing(self):
        #Well LG is different
        return {"start frame": STARFRAME,
                  "end frame": ENDFRAME,
                  "mark": MARK,
                  "space 0": SPACE0,
                  "space 1": SPACE1,
                  "drop_bits": 4}

class InverterV(LG):

    def __init__(self):
        super().__init__()
        self.model = "Inverter V"
        self.capabilities = {"mode": ["off", "auto", "cool", "fan", "dry"],
                             "temperature": [x for x in range(16,30)],
                             "auto_bias": [ "-2","-1","default", "+1", "+2"],
                             "fan": ["auto", "highest", "high", "middle", "low", "lowest"],
                             }
        self.xtra_capabilities = {
                             "swing": ["off", "swing", "90","0"],
                             "powerfull": ["off", "on"],
                             "cleaning":["off", "on"],
                             "economy":["off", "80", "60","40"],
                             }
        self.status = {"mode": "off",
                       "temperature": 25,
                       "fan": "auto",
                       "swing": "off",
                       "auto_bias": "default",
                       "powerfull": "off",
                       "cleaning": "off",
                       "economy": "off"}


class DualInverter(LG):

    def __init__(self):
        super().__init__()
        self.model = "Dual Imverter"
        self.capabilities = {"mode": ["off", "auto", "cool", "fan", "dry"],
                             "temperature": [x for x in range(16,30)],
                             "auto_bias": [ "-2","-1","default", "+1", "+2"],
                             "fan": ["auto", "highest", "high", "middle", "low", "lowest"],
                             }
        self.xtra_capabilities = {
                             "swing": ["off", "swing", "90","60","45","30","15","0"],
                             "hswing": ["off", "swing", "left","centre left","centre","centre right","right","swing left","swing right"],
                             "powerfull": ["off", "on"],
                             "purifier":["off", "on"],
                             "cleaning":["off", "on"],
                             "economy":["off", "80", "60","40"],
                             "diagnostic": ["off", "on"],
                             }
        self.status = {"mode": "off",
                       "temperature": 25,
                       "fan": "auto",
                       "swing": "off",
                       "auto_bias": "default",
                       "powerfull": "off",
                       "purifier": "off",
                       "cleaning": "off",
                       "economy": "off",
                       "diagnostic": "off"}


class PluginObject(object):

    def __init__(self):
        self.brand = "LG"
        self.models = ["generic", "Inverter V", "Dual Inverter"]

    def factory(self, model):
        if model not in self.models:
            model = "generic"

        if model == "generic":
            return LG()
        elif model == "Inverter V":
            return InverterV()
        elif model == "Dual Inverter":
            return DualInverter()



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
            lircframe = lircframe[:-8]   #LG uses 28 bits, remove the last 4
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
    parser.add_argument("-m", "--mode",   choices=['auto','cool','dry','fan','off'] , default='cool',
                        help="Mode to set. (default 'cool').")
    parser.add_argument("-f", "--fan",   choices=['auto','highest','high','middle','low','lowest'] , default='auto',
                        help="Fan mode. (default 'auto').")
    parser.add_argument("-s", "--swing",   choices=['off','swing','90','0'] , default='off',
                        help="Swing mode. (default 'off').")
    parser.add_argument("-e", "--economy",   choices=['off','80','60','40'] , default='off',
                        help="Economy mode. (default 'off').")
    parser.add_argument("-A", "--bias",   choices=['-2','-1','default','1','2'] , default='default',
                        help="Auto mode temperature bias. (default 'default').")
    parser.add_argument("-P", "--purifier", action="store_true", default=False,
                        help="Set plasma")
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

    device = InverterV()
    frames = []
    device.set_temperature(opts.temp)
    device.set_fan(opts.fan)
    device.set_swing(opts.swing)
    device.set_powerfull((opts.powerfull and "on") or "off")
    device.set_auto_bias(opts.bias)
    device.set_economy(opts.economy)
    device.set_purifier((opts.purifier and "on") or "off")
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
            print( " ".join([hex(x) for x in f]))
