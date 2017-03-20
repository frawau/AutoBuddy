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
#
#A simple AutoBuddy event generating script to be used with apcupsd
# Can be used as both powerout and mainsback scripts
import socket, ssl, json,sys

buhost="<AUTOBUDDYHOST/>"
buport=<AUTOBUDDYPORT/>
credential="<AUTOBUDDYCREDENTIAL/>"
upsname="myups"

if sys.argv[0].strip().split("/")[-1] == "powerout":
    mval="grid power off"
elif sys.argv[0].strip().split("/")[-1] == "mainsback":
    mval="grid power on"
else:
    mval=sys.argv[0].strip().split("/")[-1]

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ssl_sock = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1)
    ssl_sock.connect((buhost, buport))

    content = {'credential':credential, 'subject':'ups'}
    msg = {'subject':'control','content_type':'authenticate','content':content}
    ssl_sock.send(json.dumps(msg).encode())

    content = {'event':'grid power', 'value':mval,'target':'ups.'+upsname}
    msg = {'subject': 'ups', 'content_type':'event', 'content':content}
    ssl_sock.send(json.dumps(msg).encode())
except:
    pass
finally:
    sys.exit(0)
