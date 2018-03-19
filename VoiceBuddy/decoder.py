#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application recognize speech.
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

import argparse
import sys
import speech_recognition as sr
import datetime
import os


PSSENSIBILITY = 1.0
TRIGLANG = "en-US"
ENERGYTRESH = 1000

parser = argparse.ArgumentParser(
    description="Listen on the microphone and send.")
# version="%prog " + __version__ + "/" + bl.__version__)
parser.add_argument(
    "-M", "--mic", default="default",
                help="ALSA device to use. (default  \"default\").")
parser.add_argument(
    "-s", "--decoder", choices=["simplesphinx", 'sphinx', 'google', 'wit.ai', "houndify", "ibm", "bing"], default="simplesphinx",
                help="What decoder to use. (default sphinx).")
parser.add_argument(
    "-k", "--apikey", default="",
                help="API Key to use when decoding.")
parser.add_argument(
    "-i", "--apiid", default="",
                help="API ID to use when decoding.")
parser.add_argument(
    "-D", "--duration", type=int, default=5,
                help="How long to wait for phrase after recognition started. (default 5 secs).")
parser.add_argument(
    "-t", "--trigger", default="listen buddy",
                help="Phrase triggering recognition. (default  \"listen buddy\").")
parser.add_argument(
    "-T", "--timer", type=int, default=20,
                help="Time frame (in secs) for decoding after trigger. (default 20 secs).")
parser.add_argument(
    "-l", "--language", default="en-US",
                help="language used. (default  \"en-US\").")
parser.add_argument(
    "-m", "--model", default="",
                help="Where to find pocketsphinx models. (default  \"\").")
parser.add_argument(
    "-c", "--corpus", default="",
                help="Where to find the corpus files (autobuddy.lm and autobuddy.dic). (default  \"\").")
parser.add_argument(
    "-d", "--debug", action="count", default=0,
                help="Log debug information (default False)")

try:
    opts = parser.parse_args()
except Exception as e:
    parser.error("Error: " + str(e))
    sys.exit(-1)

if opts.decoder != "sphinx":
    if opts.corpus:
        sr.default_language_model_file = os.path.join(opts.corpus, "autobuddy.lm")
        sr.default_phoneme_dictionary_file = os.path.join(opts.corpus, "autobuddy.dic")

        if opts.model:
            sr.default_acoustic_parameters_directory = opts.model
        else:
            parser.error("Error: When specifying \"corpus\" you must also specify \"model\"")
            sys.exit(-1)


if opts.debug:
    dfile=open("/tmp/decoder.log","w")
    dfile.write("Config is {}\n".format(opts))

mode="keyword"
timer=datetime.datetime.now()
r = sr.Recognizer()
r.energy_threshold = ENERGYTRESH
m = None
for i, microphone_name in enumerate(sr.Microphone.list_microphone_names()):
    if microphone_name ==  opts.mic:
        m = sr.Microphone(device_index=i)
        break
if not m:
    raise Exception("Could not find microphone %s"%opts.mic)
with m as source:
    r.adjust_for_ambient_noise(source)
    while True:
        #try:
        audio = r.listen(source,phrase_time_limit=opts.duration)
        if datetime.datetime.now() > timer:
            mode="keyword"
        if opts.debug:
            dfile.write("Got audio whilst in %s mode\n"%mode)
        if  mode == "keyword":
            config = {}
            if opts.corpus:
                par_language=(opts.model,
                              os.path.join(opts.corpus, "autobuddy.lm"),
                              os.path.join(opts.corpus, "autobuddy.dic"))
            else:
                par_language=TRIGLANG
            try:
                line = r.recognize_sphinx(audio, language=par_language)
            except:
                line=""
            if opts.debug:
                dfile.write("Received keyword  {}\n".format(line))
            linebits = [x.lower() for x in line.split(" ") if x != ""]
            if linebits == [x.lower() for x in opts.trigger.split(" ") if x != ""]:
                mode = "command"
                print(line.lower())
                sys.stdout.flush()
                timer=datetime.datetime.now()+datetime.timedelta(seconds=opts.timer)
        else:
            line=""
            try:
                if opts.decoder == "google":
                    if opts.apikey:
                        line = r.recognize_google_cloud(audio, credentials_json= opts.apikey, language=opts.language)
                    else:
                        line = r.recognize_google(audio, language=opts.language)
                elif opts.decoder == "sphinx":
                    line = r.recognize_sphinx(audio, language=opts.language)
                elif opts.decoder == "wit.ai" and opts.apikey:
                    line = r.recognize_wit(audio, key=opts.apikey)
                elif opts.decoder == "houndify" and opts.apikey and opts.apiid:
                    line = r.recognize_houndify(audio, opts.apiid, opts.apikey)
                elif opts.decoder == "bing" and opts.apikey:
                    line = r.recognize_bing(audio, key=opts.apikey, language=opts.language)
                elif opts.decoder == "ibm" and opts.apikey and opts.apiid:
                    line = r.recognize_ibm(audio, username=opts.apikey, password=opts.apiid, language=opts.language)
                else:
                    config = {}
                    if opts.corpus:
                        par_language=(opts.model,
                                      os.path.join(opts.corpus, "autobuddy.lm"),
                                      os.path.join(opts.corpus, "autobuddy.dic"))
                    else:
                        par_language=opts.language

                    line = r.recognize_sphinx(audio, language=par_language)
            except:
                if opts.debug:
                    dfile.write("Evil man!\n")
                line=""

            if line:
                if opts.debug:
                    dfile.write("Received command \n")
                print(line.lower())
                sys.stdout.flush()
        #except Exception as e:
            #pass


