#! /usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Plugin to generate Sharp AC IR commands as done by the CRMC-B028JBEZ
#
# This module  is in part based on the work/code from:
#      ToniA      https://github.com/adafruit/Raw-IR-decoder-for-Arduino/pull/3/commits/887ed4204711c0b911571f3090b7fd066e93f006
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

STARFRAME = [ 3800, 1900 ]
ENDFRAME = [435, 10000 ]
MARK = 435
SPACE0 = 435
SPACE1 = 1400


def bit_reverse(i, n=8):
    return int(format(i, '0%db' % n)[::-1], 2)




class Sharp(HVAC):
    """Generic Sharp HVAC object. It must have, at the very minimum
       "mode" and "temperature" capabilities"""

    def __init__(self):
        super().__init__()
        self.brand = "Sharp"
        self.model = "Generic"
        self.capabilities = {"mode": ["off", "auto", "cool", "dry"],
                             "temperature": [x for x in range(18,38)]
                             }
        #For functions that require their own frames
        self.xtra_capabilities = {}
        self.status = {"mode": "cool",
                       "temperature": 25}

        self.to_set = {}
        #Specify wether the bits order has to be swapped
        self.is_msb = True
        self.FBODY = b'\xaa\x5a\xcf\x10\x00\x00\x00\x00\x00\x80\x00\xe0'
        self.crc_special = 0x01



    def set_temperature(self, temp):
        if temp < self.capabilities["temperature"][0]:
            temp = self.capabilities["temperature"][0]
        elif temp > self.capabilities["temperature"][-1]:
            temp = self.capabilities["temperature"][-1]
        if self.status["temperature"] != temp:
            self.to_set["temperature"] = temp

    def code_temperature(self):
        if "temperature" in self.to_set:
            temp = self.to_set["temperature"]
            if "mode" in self.to_set and self.to_set["mode"] != "cool":
                temp = 17
            elif self.status["mode"] != "cool":
                temp = 17
            else:
                temp = self.status["temperature"]
        else:
            temp = self.status["temperature"]
        mask = bytearray(b'\x00'*len(self.FBODY))
        mask[6] = temp-17
        return mask, False

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
        if "mode" in self.to_set and self.to_set["mode"] == "dry":
            mode = "auto"
            self.to_set["fan"] = mode
        elif self.status["mode"] == "dry":
            mode = "auto"
            self.to_set["fan"] = mode
        else:
            if "fan" in self.to_set:
                mode = self.to_set["fan"]
            else:
                if "fan" in self.capabilities:
                    mode = self.status["fan"]
                else:
                    mode = None
        rank = ["auto",'low', 'lowest','middle','high','highest']
        mask = bytearray(b'\x00'*len(self.FBODY))
        if mode:
            fval = (rank.index(mode)+2)<<4
            mask[6] = fval
        return mask, False

    def set_swing(self, mode):
        if "swing" not in self.capabilities:
            return
        if mode not in self.capabilities["swing"]:
            return
        if self.status["swing"] != mode:
            self.to_set["swing"] = mode

    def code_swing(self):
        if "swing" in self.to_set:
            mode = self.to_set["swing"]
        else:
            if "swing" in self.capabilities:
                mode = self.status["swing"]
            else:
                mode = False

        rank = ["auto",'ceiling','90','60','45','30' 'swing']
        if mode not in rank:
            mode="auto"   #Just in case
        mask = bytearray(b'\x00'*len(self.FBODY))
        fval = (rank.index(mode)+8)
        mask[8] = fval
        return mask, False


    def set_powerfull(self,mode="off"):
        #print("\n\nSharp set powerfull {}\n\n".format(mode))
        if "powerfull" not in self.status:
            return

        if "powerfull" in self.capabilities:
            checkwith = self.capabilities
        elif "powerfull" in self.xtra_capabilities:
            checkwith = self.xtra_capabilities
        #print("Setting powerfull as {} from {}".format(mode,checkwith))
        if mode not in checkwith["powerfull"]:
            return
        if self.status["powerfull"] != mode:
            self.to_set["powerfull"] = mode

    def code_powerfull(self,toggle=False):
        b10code=0x00
        if toggle:
            if "powerfull" in self.to_set:
                b10code = 0x01

        mask = bytearray(b'\x00'*len(self.FBODY))
        mask[10] = b10code
        #Nothing to set... I know... it's the mode that will do this
        return mask, False

    def set_economy(self,mode="off"):
        if "economy" not in self.status:
            return

        if "exonomy" in self.capabilities:
            checkwith = self.capabilities
        elif "economy" in self.xtra_capabilities:
            checkwith = self.xtra_capabilities

        if mode not in checkwith["economy"]:
            return
        if self.status["economy"] != mode:
            self.to_set["economy"] = mode

    def code_economy(self, toggle=False):
        if not toggle:
            mode = self.status["economy"]
        elif "economy" in self.to_set:
            mode = self.to_set["economy"]
        else:
            if "economy" not in self.status:
                mode = "off"
            else:
                mode = self.status["economy"]

        mask = bytearray(b'\x00'*len(self.FBODY))
        if mode == "on":
            mask[11] |= 0x10
        return mask, False

    def set_purifier(self,mode="off"):
        if "purifier" not in self.capabilities:
            return
        if mode not in self.capabilities["purifier"]:
            return
        if self.status["purifier"] != mode:
            self.to_set["purifier"] = mode


    def code_purifier(self):

        mask = bytearray(b'\x00'*len(self.FBODY))

        return mask, False



    def set_mode(self,mode):
        if mode not in self.capabilities["mode"]:
            mode = "cool"
        if mode != self.status["mode"]:
            self.to_set["mode"] = mode

    def code_mode(self,option=None):
        if "mode" in self.to_set:
            mode = self.to_set["mode"]
        else:
            mode = self.status["mode"]

        mask = bytearray(b'\x00'*len(self.FBODY))
        if option is None or mode == "off":
            if mode != self.status["mode"]:
                if mode == "off":
                    b5val = 0x21
                    b6mode = self.status["mode"]
                elif self.status["mode"] == "off":
                    b5val = 0x11
                    b6mode = mode
                else:
                    b5val = 0x31
                    b6mode = mode
            else:
                b5val = 0x31
                b6mode = mode
        else:
            #Caller should not send option if off
            if option == "on":
                b5val = 0x61
            else:
                b5val = 0x71
            b6mode = mode
        mask[5] = b5val
        mask[6] = ["auto","heat","cool","dry"].index(b6mode)
        return mask, False



    def build_code(self, withmode=True):
        packet = bytearray(self.FBODY)
        #Note that set mod must be last for it replaces values
        if withmode:
            lof = [self.code_temperature, self.code_fan, self.code_swing, self.code_purifier, self.code_economy, self.code_mode]
        else:
            lof = [self.code_temperature, self.code_fan, self.code_swing, self.code_purifier, self.code_economy]
        for f in lof:
            mask,replace = f()
            if replace:
                packet = bytearray([ y or x for x,y in zip(packet,mask)])
            else:
                packet = bytearray([x | y for x,y in zip(packet,mask)])
        return packet

    def _build_ircode(self):
        frames = []
        normalframe=False
        for x in self.capabilities:
            if x in self.to_set:
                normalframe = True
                break
        if normalframe:
            frames += [self.build_code()]

        if ("mode" in self.to_set and (self.to_set["mode"] != "off") ) or \
            self.status["mode"] != "off":
            for prop in self.xtra_capabilities:
                #print("Looking at {} with {} and {}".format(prop,self.to_set,self.status))
                if prop in self.to_set and self.to_set[prop] != self.status[prop]:
                    f = getattr(self,"code_"+prop,None)
                    if f:
                        packet = self.build_code(withmode=False)
                        for mask,replace in [self.code_mode(option=self.to_set[prop]), f(toggle=True)]:
                            if replace:
                                packet = bytearray([ y or x for x,y in zip(packet,mask)])
                            else:
                                packet = bytearray([x | y for x,y in zip(packet,mask)])
                        frames.append(packet)
        else:
            #We are off, so xtra_capabilities should also be off
            for x in self.xtra_capabilities:
                selt.to_set[x] = "off"
        idx = 0
        for x in frames:
            frames[idx] += self.crc(x)
            idx += 1
        return frames

    def crc(self,frame):
        crc=0
        for x in frame:
            crc^=x
        crc ^= self.crc_special
        crc ^= (crc >>4)
        crc = (crc&0x0f)<<4
        crc += self.crc_special
        return crc.to_bytes(1,'big')

    def get_timing(self):
        #Well Sharp is different
        return {"start frame": STARFRAME,
                  "end frame": ENDFRAME,
                  "mark": MARK,
                  "space 0": SPACE0,
                  "space 1": SPACE1}


class JTech(Sharp):

    def __init__(self):
        super().__init__()
        self.model = "FTM-PV2S"
        self.capabilities = {"mode": ["off", "auto", "cool", "dry"],
                             "temperature": [x for x in range(14,30)],
                             "fan": ["auto", "highest", "middle", "low", "lowest"],
                             "swing": ["auto", "ceiling", "90","60","45","30","swing"],
                             "hswing": ["left", "middle","right","swing"],
                             "target":  ["off","close left","close middle","close right",
                                         "far left","far middle","far right"],
                             "purifier": ["off", "on"]
                             }
        self.xtra_capabilities = {"powerfull": ["off", "on"],
                                  "economy":["off","on"]}
        self.status = {"mode": "off",
                       "temperature": 25,
                       "fan": "auto",
                       "swing": "auto",
                       "hswing": "middle",
                       "target":"off",
                       "purifier": "off",
                       "economy": "off",
                       "powerfull": "off"}
        self.temperature_step = 0.5

    def code_purifier(self):

        mask = bytearray(b'\x00'*len(self.FBODY))

        if "purifier" in self.to_set:
            mode = self.to_set["purifier"]
        else:
            mode = self.status["purifier"]
        if mode == "on":
            mask[11] |= 0x04

        #Nothing to set... I know... it's the mode that will do this
        return mask, False

    def code_swing(self):
        """This one takes care of "swing", "horizontal swing" and "spot" (AKA target"""
        if ("target" in self.to_set and  self.to_set["target"] == "off") or self.status["target"] == "off":
            # OK, swing and horizontal swing are on
            if "swing" in self.to_set:
                smode = self.to_set["swing"]
            else:
                smode = self.status["swing"]
            if "hswing" in self.to_set:
                hsmode = self.to_set["hswing"]
            else:
                hsmode = self.status["hswing"]
            b8val = (["","middle","left","right"]+11*[""]+["swing"]).index(hsmode) << 4
            b8val += 8 + ["auto","ceiling","90","60","45","30","swing"].index(smode)
            b9val = 0x0
        else:
            #Target is on
            b9val = 0x01
            front, side = (("target" in self.to_set and  self.to_set["target"]) or self.status["target"]).split(" ")
            b8val = (["","middle","left","right"]).index(side) << 4
            if front == "close":
                b8val+=0xc
            else:
                b8val+=0x9

        mask = bytearray(b'\x00'*len(self.FBODY))
        mask[9] |= b9val
        mask[8] = b8val
        return mask, False

    def set_hswing(self, mode):
        if "hswing" not in self.capabilities:
            return
        if mode not in self.capabilities["hswing"]:
            return
        if self.status["hswing"] != mode:
            self.to_set["hswing"] = mode

    def code_hswing(self):
        """ Nothing to do. hNalded by code_swing"""
        return bytearray(b'\x00'*len(self.FBODY)), False

    def set_target(self, mode):
        if "target" not in self.capabilities:
            return
        if mode not in self.capabilities["target"]:
            return
        if self.status["target"] != mode:
            self.to_set["target"] = mode

    def code_target(self):
        """ Nothing to do. hNalded by code_swing"""
        return bytearray(b'\x00'*len(self.FBODY)), False

    def code_temperature(self):
        if "temperature" in self.to_set:
            temp = self.to_set["temperature"]
        else:
            temp = self.status["temperature"]
        if "mode" in self.to_set:
            if self.to_set["mode"] != "cool":
                temp = None
        elif self.status["mode"] != "cool":
            temp = None
        mask = bytearray(b'\x00'*len(self.FBODY))
        if temp:
            if (temp*10)%10:
                deci = True
                temp=int(temp)
            else:
                deci=False
            if temp<16:
                temp += 0x3e
                if deci:
                    temp += 0x20
            else:
                if not deci:
                    temp = 0xc0+(temp-15)
                else:
                    temp = 0x70+(temp-15)
            mask[4] = temp
        return mask, True


class PluginObject(object):

    def __init__(self):
        self.brand = "Sharp"
        self.models = ["generic",  "J-Tech"]

    def factory(self, model):
        if model not in self.models:
            model = "generic"

        if model == "generic":
            return Sharp()
        elif model == "J-Tech":
            return JTech()



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
    parser.add_argument("-m", "--mode",   choices=['auto','cool','dry','off'] , default='cool',
                        help="Mode to set. (default 'cool').")
    parser.add_argument("-f", "--fan",   choices=['auto','highest','high','middle','low','lowest'] , default='auto',
                        help="Fan mode. (default 'auto').")
    spotgroup = parser.add_mutually_exclusive_group()
    swinggroup = spotgroup.add_argument_group()
    swinggroup.add_argument("-s", "--swing", choices=['auto','ceiling',"90","60","45","30","swing"], default="auto",
                        help="Set swing")
    swinggroup.add_argument("-H", "--hswing", choices=['middle','left',"right","swing"], default="middle",
                        help="Set horizontal swing")
    spotgroup.add_argument("-S", "--spot", choices=['off','close left',"close middle","close right","far left","far middle","far right"], default="off",
                        help="Set spot")
    parser.add_argument("-p", "--powerfull", action="store_true", default=False,
                        help="Set super jet")
    parser.add_argument("-P", "--plasma", action="store_true", default=False,
                        help="Set Plasmacluster purifier")
    parser.add_argument("-e", "--economy", action="store_true", default=False,
                        help="Set economy mode")
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

    device = JTech()
    frames = []
    device.set_temperature(opts.temp)
    device.set_fan(opts.fan)
    device.set_swing(opts.swing)
    device.set_hswing(opts.hswing)
    device.set_target(opts.spot)
    device.set_purifier((opts.plasma and "on") or "off")
    device.set_powerfull((opts.powerfull and "on") or "off")
    device.set_economy((opts.economy and "on") or "off")
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
