#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application is simply a bridge application for Lifx bulbs.
# 
# Copyright (c) 2016 François Wautier
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

import argparse, os,sys,datetime
from ctypes import *

import alsaaudio
from pocketsphinx.pocketsphinx import *
from sphinxbase.sphinxbase import *


parser = argparse.ArgumentParser(description="Listen on the microphone and transcribe.")
#                            version="%prog " + __version__ + "/" + bl.__version__)
parser.add_argument("-m", "--model", default="/usr/share/pocketsphinx/model/en-us/en-us",
                help="Where to find pocketsphinx models. (default  \"/usr/share/pocketsphinx/model/en-us/en-us\").")
parser.add_argument("-c", "--corpus", default="/usr/share/pocketsphinx/model/en-us",
                help="Where to find the corpus files (autobuddy.ln and autobuddy.dic). (default  \"/usr/share/pocketsphinx/model/en-us\")." )
parser.add_argument("-d", "--device", default="default",
                help="ALSA device to use. (default  \"default\")." )
parser.add_argument("-t", "--toggle", default="listen_buddy",
                help="Phrase toggling recognition. (default  \"listen_buddy\")." )
parser.add_argument("-D", "--duration", type=int, default=10,
                help="How long to wait for phrase after recognition started. (default 10 secs).")
parser.add_argument("-l", "--longest", type=int, default=10,
                help="How long to wait vefore returning a guess. (default 10 secs).")

try:
    opts=parser.parse_args()
except Exception as e:
    parser.error("Error: "+str(e))
    sys.exit(-1)
  
#logfile=open("/tmp/voice.log","w")

#model_dir = "/usr/share/pocketsphinx/model/fr-fr/"
#hmm = os.path.join(model_dir, "fr-ptm")
#lm = os.path.join(model_dir, "fr-small.lm.bin")
#dic = os.path.join(model_dir, "fr.dict")

config = Decoder.default_config()
config.set_string('-hmm', opts.model)
config.set_string('-lm', os.path.join(opts.corpus,"autobuddy.lm"))
config.set_string('-dict', os.path.join(opts.corpus,"autobuddy.dic"))
config.set_string('-logfn', '/dev/null')
decoder = Decoder(config)
stream = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, 0, device=opts.device)
# Set attributes: Mono, 16000 Hz, 16 bit little endian samples
stream.setchannels(1)
stream.setrate(16000)
stream.setformat(alsaaudio.PCM_FORMAT_S16_LE)
stream.setperiodsize(1024)
in_speech_bf = True
decoder.start_utt()
cmd_mode=False
cmd_tstmp=datetime.datetime.now()
sentence_delay=cmd_tstmp+datetime.timedelta(seconds=opts.longest)
while True:
    l,buf = stream.read()
    if buf:
        isnow=datetime.datetime.now()
        decoder.process_raw(buf, False, False)
        if decoder.get_in_speech() != in_speech_bf or isnow>sentence_delay:
            in_speech_bf = decoder.get_in_speech()
            if not in_speech_bf or isnow>sentence_delay:
                decoder.end_utt()
                try:
                    if decoder.hyp().hypstr != '':
                        #logfile.write('Stream decoding result: {}'.format(decoder.hyp().hypstr))
                        if decoder.hyp().hypstr.upper()==opts.toggle.upper():
                            #print(decoder.hyp().hypstr)
                            cmd_mode=True
                            cmd_tstmp=datetime.datetime.now()+datetime.timedelta(seconds=opts.duration)
                        elif cmd_mode:
                            print(decoder.hyp().hypstr)
                            sys.stdout.flush()
                except AttributeError:
                    pass
                decoder.start_utt()
                sentence_delay=isnow+datetime.timedelta(seconds=opts.longest)
    else:
        break
    if cmd_mode and datetime.datetime.now()>cmd_tstmp:
        cmd_mode=False
        
decoder.end_utt()