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

class HVAC(object):


    def set_value(self, name, value):
        try:
            xx = getattr(self,"set_"+name)(value)
        except AttributeError:
            print("Setting {} on {} {} should not have appened.".format(name,selt.brand, self.model))

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
                newname += "%d"%v[0] +"|"+"%d"%v[-1]
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

        return lof
