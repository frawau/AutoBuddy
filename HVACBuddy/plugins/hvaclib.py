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

from hashlib import blake2b

#90% of hvac remotes use this timing
STARFRAME = [ 3500, 1750 ]
ENDFRAME = [435, 10000 ]
MARK = 435
SPACE0 = 435
SPACE1 = 1300

def bit_reverse(i, n=8):
    return int(format(i, '0%db' % n)[::-1], 2)


class HVAC(object):

    def __init__(self):
        self.brand = "Generic"
        self.model = "Generic"
        self.capabilities = {"mode": ["off", "auto", "cool", "fan", "dry"],
                             "temperature": [x for x in range(18,30)]
                             }
        #For functions that require their own frames
        self.xtra_capabilities = {}
        self.status = {"mode": "auto",
                       "temperature": 25}
        self.temperature_step = 1.0

        self.to_set = {}
        #Specify wether the bits order has to be swapped
        self.is_msb = False
        #Names of 'functions' used by this object
        self.functions = []

    def get_timing(self):
        return {"start frame": STARFRAME,
                  "end frame": ENDFRAME,
                  "mark": MARK,
                  "space 0": SPACE0,
                  "space 1": SPACE1}

    def set_value(self, name, value):
        xx = getattr(self,"set_"+name)(value)

    def available_functions(self):
        """Here we generate a number of names that can bew used to
              1- Generate XML for commands
              2- Setup status to only show the needed XML generated functions

        The names are always prefixed by 'buf-' for Buddy Function
        """
        lof = {}
        for x, v in self.capabilities.items():
            newname="buf-"+x+"-"
            if x == "temperature":
                #Special hare, we got a range
                newname += "%d"%v[0] +"|"+"%d"%v[-1]+"__"+"%d"%(self.temperature_step*10)
                lof[newname] = None
            else:
                lov = [str(y) for y in v]
                lov.sort()
                #Hopefully 4 bytes will be enough
                h = blake2b(digest_size=4)
                h.update(bytes(" ".join(lov),"utf-8"))
                newname += h.hexdigest()
                if newname not in lof:
                    lof[newname] = v
        for x, v in self.xtra_capabilities.items():
            newname="buf-"+x+"-"
            lov = [str(y) for y in v]
            lov.sort()
            #Hopefully 4 bytes will be enough
            h = blake2b(digest_size=4)
            h.update(bytes(" ".join(lov),"utf-8"))
            newname += h.hexdigest()
            if newname not in lof:
                lof[newname] = v
        self.functions = lof.keys()
        return lof

    def update_status(self):
        #print("From {}".format(self.status))
        #print("With {}".format(self.to_set))
        for x,y in self.to_set.items():
            self.status[x] = y
        #print("To {}".format(self.status))
        self.to_set = {}

    def build_ircode(self):
        frames = self._build_ircode()
        if self.is_msb:
            newframes = []
            for f in frames:
                newframes.append(bytearray([bit_reverse(x) for x in f]))
            frames = newframes
        #print("Frame with msb {} are:".format(self.is_msb))
        #for f in frames:
            #print(["0x%02x"%x for x in f])
        return frames
