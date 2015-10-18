#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# This application is simply a bridge application for Lifx bulbs.
# 
# Copyright (c) 2015 François Wautier
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
import qpid.messaging as qm 
import json,sys,traceback,argparse,os

def iprint(*arg):
    """
        Just here to make it easy when changing to python 3
    """
    for x in arg:
        print >> sys.stderr, x,
    print      

config={}

default={"topic":"autobuddy","subject":["gui"]}
parser = argparse.ArgumentParser(description="Autobuddy Websocket bridge.")
#                            version="%prog " + __version__ + "/" + bl.__version__) 
parser.add_argument("-b", "--broker", default="",
                help="connect to specified BROKER")
parser.add_argument("-c", "--config", default="/etc/autobuddy/websocket.cfg", type=file,
                help="Config file to use (default \"/etc/autobuddy/websocket.cfg\")")
parser.add_argument("-d", "--debug", action="count", default=0,
                help="Log debug information (default False)")
parser.add_argument("-s", "--subject", nargs="+", default=default,
                help="List of subject content to echo to websocket. (default \"%s\""%" ".join(default["subject"]))
parser.add_argument("-t", "--topic", default=default,
                help="The AMQP-style topic we are listening to (default \"%s\")."%default["topic"])
    
try:
    opts=parser.parse_args()
except Exception as e:
    iprint("Error: ",e)
    parser.print_help()
    sys.exit(-2)

try:
    
    cfgdata = json.load(opts.config)
    config["debug"] = opts.debug
    if opts.broker:
        config["broker"] = opts.broker
    else:
        config["broker"] = ""
        if "user" in cfgdata["broker"] and cfgdata["broker"]["user"]:
            config["broker"] += cfgdata["broker"]["user"]+"/" + cfgdata["broker"]["password"] + "@"
        config["broker"] += cfgdata["broker"]["host"]
        
        if "port" in cfgdata["broker"] and cfgdata["broker"]["port"]:
            config["broker"] += ":"+ str(cfgdata["broker"]["port"])

    if opts.debug:
        iprint("The broker is",config["broker"]) 
        
    for cfg in default:
        if getattr(opts,cfg,False) and  getattr(opts,cfg) != default:
            config[cfg] = getattr(opts,cfg)
        elif cfg in cfgdata:
            config[cfg] = cfgdata[cfg]
        else:
            config[cfg] = default[cfg]
        if opts.debug:
            iprint("%s is %s"%(cfg,config[cfg]))      

except Exception as e:
    iprint("Error:",e)
    sys.exit(-2)
            

conn = qm.Connection(url=str(config["broker"]),protocol="ssl") 
conn.open()
ssn = conn.session() 
rcv = ssn.receiver(config["topic"]+"/#")

while True: 
    try:
        msg = rcv.fetch()
        passit=False
        for x in config["subject"]:
            if x in msg.subject:
                passit=True
                break
        if passit or msg.content_type == "event":
            wsmsg={"subject":msg.subject}
            wsmsg["content_type"]=msg.content_type
            try:
                wsmsg["content"]=json.loads(msg.content)
            except:
                wsmsg["content"]=msg.content
            json.dump(wsmsg,sys.stdout)
            print 
            sys.stdout.flush()
        ssn.acknowledge(msg) 
    except  KeyboardInterrupt:
        print >> sys.stderr, "Exiting at user's request"
        try:
            conn.close()
        except:
            pass
        sys.exit(0)
    except: 
        traceback.print_exc() 
        try:
            ssn.acknowledge(msg)
        except:
            pass
        try:
            conn.close()
        except:
            pass
        