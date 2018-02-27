#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application looks for published services Avahi/Bonjour
# figures out the MAC address of the server and send events about
# newly discoverd services.
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

import argparse
import sys
import json
import os
import ssl
import logging,json
#import ipaddress
import asyncio as aio
import buddylib as bl
import socket
from functools import partial
from passlib.apps import custom_app_context as pwd_context
from hbmqtt.plugins.authentication import BaseAuthPlugin
from hbmqtt.broker import Broker
import pkg_resources

thislocation = os.path.split(os.path.abspath(__file__))[0]

SUBTYPE = "mqtt"
__version__ = "0.10"
CERTFILE = "autobuddy.crt"
mqtt_function = """
"""

mqtt_config = """
<buddyui version="0.1">
    <configuration  name="mqtt">
        <controlgroup type="listmaker"  name="credential" label="Credentials">
            <control name="user" label="User" type="text" length="32" />
            <control name="password" label="Password" type="text" length="32" />
        </controlgroup>
    </configuration>
</buddyui>
"""
mqtt_config_default = {"passwords": {}}
sharedfile="/tmp/zzmqttauthentication"

class BuddyAuthPlugin(BaseAuthPlugin):
    def __init__(self, context):
        super().__init__(context)

    async def authenticate(self, *args, **kwargs):
        authenticated = super().authenticate(*args, **kwargs) or False
        if authenticated:
            session = kwargs.get('session', None)
            if session.username:
                hash = get_passwords().get(session.username, None)
                if not hash:
                    authenticated = False
                    self.context.logger.debug("No hash found for user '%s'" % session.username)
                else:
                    authenticated = pwd_context.verify(session.password, hash)
            else:
                authenticated = False
        return authenticated

ep = pkg_resources.EntryPoint.parse('auth_buddy = MQTTBuddy:BuddyAuthPlugin')
# Create a fake distribution to insert into the global working_set
d = pkg_resources.Distribution(location=thislocation)

# Add the mapping to the fake EntryPoint
d._ep_map = {'hbmqtt.broker.plugins': {'auth_buddy': ep}}
ep.dist = d
# Add the fake distribution to the global working_set
pkg_resources.working_set.add(d, 'auth_buddy')

def get_passwords():
    return json.load(open(sharedfile,"r"))

def set_passwords():
    json.dump(mqtt_config_default["passwords"],open(sharedfile,"w"))


class MQTTBridge(bl.BuddyBridge):

    """
    This is the bridge application. It will check for the current list  of mqtt bulb.
    It will report any new bulb
    """

    def __init__(self, loop, future, config, log):
        super(MQTTBridge, self).__init__(loop, future, config, log)
        self.mqtt_service = None
        self.mqtt_broker = None
        self.mqtt_config = mqtt_config_default

    def process_command(self, msg):
        if msg["content"]["command"] == "update config":
            if msg["content"]["target"] == self.target:
                if "credential" in msg["content"]["value"]:
                    louser=[x for x in mqtt_config_default["passwords"].keys()]
                    for passwds in msg["content"]["value"]["credential"]:
                        try:
                            louser.remove(passwds["user"])
                        except:
                            pass
                        if passwds["password"]:
                            mqtt_config_default["passwords"][passwds["user"]] = pwd_context.hash(passwds["password"])
                    for u in louser:
                        print("remove {}".format(u))
                        del(mqtt_config_default["passwords"][u])

                self.sending({"subject": "control" + "." + self.subtype,
                              "content_type": "request",
                              "content": {"request": "save configuration",
                                          "target": self.type,
                                          #"token": self.target,
                                          "value": bl.encrypt(mqtt_config_default, self.config["buddykey"])}})

        # else:
            # for aconn in self.devices:
                # aconn.process(msg)

    def process_response(self, msg):
        if self.state == "init" and msg["content"]["response"] == "configuration" and msg["subject"] == self.target:
            # Getting the config
            newconfig = {}
            fromconfig = []
            if msg["content"]["configuration"]:
                try:
                    storedconfig = bl.decrypt(
                        msg["content"]["configuration"],
                        self.config["buddykey"])
                    if self.config["debug"]:
                        self.log.debug(
                            "The config stored is {}".format(storedconfig))
                except:
                    storedconfig = {}
                    savenew = True
                    # log
                    if self.log:
                        self.log.warning("Config is mangled")
                    else:
                        print("Config is mangled")

                for x in storedconfig:
                    self.mqtt_config[x] = storedconfig[x]

            self.config["database"] = msg["content"]["database"]
            if "configonly" in self.config and self.config["configonly"]:
                self.state = "wait config save"
            else:
                self.state = "active"
                self.build()
                self.sending({"subject": "control" + "." + self.target,
                              "content_type": "request",
                              "content": {"request": "functions",
                                          "target": self.type,
                                          "subtype": self.subtype,
                                          #"token": self.target,
                                          "value": {"configs": [mqtt_config,{"credential":[{"user":x, "password":""} for x in self.mqtt_config["passwords"].keys()]}]}}})
                self.sending({"subject": self.config["restricted"],
                              "content_type": "restricted event",
                              "content": {"event": "config updated",
                                          "target": self.target,
                                          "value": {"credential":[{"user":x, "password":""} for x in self.mqtt_config["passwords"].keys()]}}})

                #No need for events, we don't have any handler
                self.sending({"subject":"control","content": {"subject":self.type},"content_type":"mute events"})

        elif msg["content"]["response"] == "save configuration" and msg["subject"] == self.target:
            if self.state == "active" and msg["content"]["status"] != "done":
                # log
                if self.log:
                    self.log.warning("Warning: Configuration was not saved.")
                else:
                    print("Warning: Configuration was not saved.")
            elif self.state == "wait config save":
                if msg["content"]["status"] == "done":
                    raise bl.Exit(0, "Configuration was saved")
                else:
                    raise bl.Exit(2, "Error: Configuration was not saved")
            else:
                self.sending({"subject": "control" + "." + self.target,
                              "content_type": "request",
                              "content": {"request": "functions",
                                          "target": self.type,
                                          "subtype": self.subtype,
                                          #"token": self.target,
                                          "value": {"configs": [mqtt_config, {"credential":[{"user":x, "password":""} for x in self.mqtt_config["passwords"].keys()]}]}}})
                self.sending({"subject": self.config["restricted"],
                              "content_type": "restricted event",
                              "content": {"event": "config updated",
                                          "target": self.target,
                                          "value": {"credential":[{"user":x, "password":""} for x in self.mqtt_config["passwords"].keys()]}}})


        elif msg["content"]["response"] == "functions" and msg["subject"] == self.type+".functions":
            if msg["content"]["status"] != "done":
                if self.log:
                    self.log.warning("Warning: Something went wrong when registering with the server. We probably should stop.")
                else:
                    print("Warning: Something went wrong when registering with the server. We probably should stop.")
        else:
            if self.log:
                self.log.warning(
                    "Unknown response {} {} {}".format(msg["subject"],
                                                       msg["content_type"],
                                                       msg["content"]))
            else:
                print (
                    "Unknown response {} {} {}".format(msg["subject"],
                                                       msg["content_type"],
                                                       msg["content"]))

    def process_event(self, msg):
        # We can react to no event.
        # TODO
        return

    def build(self):
        set_passwords()
        self.sending({"subject": "control" + "." + self.target,
                      "content_type": "request",
                      "content": {"request": "functions",
                                  "target": self.type,
                                  "subtype": self.subtype,
                                  "value": {"functions": "", "configs": [mqtt_config, {"credential":[{"user":x, "password":""} for x in self.mqtt_config["passwords"].keys()]}]}}})
        #Starting MQTT
        broker_config= {"listeners":{"default": {"max-connections": 50000, "type": "tcp", "bind": "0.0.0.0:1883"}}}
        broker_config["timeout-disconnect-delay"] = 2
        broker_config["auth"] = {"plugins": ['auth_buddy'],
                                 "allow-anonymous": False}
        self.mqtt_broker = Broker(broker_config)
        self.mqtt_service = aio.ensure_future((self.mqtt_broker.start()))


    def send_service_status(self, servname):
        for knownserv, entity in  self.seen_service.items():
            if knownserv.endswith(servname):
                self.sending({"subject": self.target,
                            "content_type": "event",
                            "content": {"event": "service found",
                                        "target": self.target,
                                        "value": {"name":entity.name,"address":entity.address,
                                                  "port":entity.port,"properties":entity.decoded_properties,
                                                  "type":entity.type, "mac": entity.mac}}})




aboutstr = """<p>MQTTBuddy is an MQTT broker controlled by the AutoBuddy framework. It uses the MQTT broker from <a href="https://github.com/beerfactory/hbmqtt">hbmqtt</a></p>
<p class=\"bu-copyright\">&copy; 2017 Fran&ccedil;ois Wautier</p>
"""

iconstr = {}

cfgdefault = {
    "type": "service",
     "subtype": "mqtt",
     "host": "localhost",
     "port": 8745,
     "credential": "",
     "ssl": "",
     "restricted": "guibridge",
     "iface": ""}


def configure():
    parser = argparse.ArgumentParser(
        description="Track mqtt of people/pet/devices over the LAN.")
    # version="%prog " + __version__ + "/" + bl.__version__)
    parser.add_argument("-t", "--type", default=cfgdefault["type"],
                        help="The type of devices we handle. (default \"%s\")." % cfgdefault["type"])
    parser.add_argument("-s", "--subtype", default=cfgdefault["subtype"],
                        help="The specific subtype we manage. (default \"%s\")." % cfgdefault["subtype"])

    parser.add_argument("-a", "--host", default=cfgdefault["host"],
                        help="The host address of the server (default \"%s\")." % cfgdefault["host"])
    parser.add_argument("-p", "--port", type=int, default=cfgdefault["port"],
                        help="The port used by the server (default \"%s\")." % cfgdefault["port"])

    parser.add_argument("-c", "--config", default="/etc/autobuddy/mqtt.cfg", type=argparse.FileType('r'),
                        help="Config file to use (default \"/etc/autobuddy/mqtt.cfg\")")

    parser.add_argument("-i", "--iface", action="append", default=cfgdefault["iface"],
                        help="The interfaces to use (default all).")

    parser.add_argument("-V", "--credential", default=cfgdefault['credential'],
                        help="The credential used to verify authorization (default \"%s\")." % cfgdefault["credential"])
    parser.add_argument("-S", "--ssl", default="",
                        help="The directory where the file %s can be found." % (CERTFILE))
    parser.add_argument("-r", "--restricted", default=cfgdefault["restricted"],
                        help="Where to send \"restricted events\" (default \"%s\")." % cfgdefault["restricted"])
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="Log warning messages")

    parser.add_argument("-C", "--configonly", default="",
                        help="Exit after the the configuration has been saved")
    parser.add_argument("-d", "--debug", action="count", default=0,
                        help="Log debug information (default False)")

    try:
        opts = parser.parse_args()
    except Exception as e:
        parser.error("Error: " + str(e))

    if opts.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)7s: %(message)s',
            stream=sys.stderr,
        )
    elif opts.verbose:
        logging.basicConfig(
            level=logging.WARNING,
            format='%(levelname)7s: %(message)s',
            stream=sys.stderr,
        )
    else:
        logging.basicConfig(
            level=logging.CRITICAL,
            format='%(levelname)7s: %(message)s',
            stream=sys.stderr,
        )
    mqttlog = logging.getLogger('')
    mqttcfg = {"debug": opts.debug}
    try:
    # if True:
        try:
            cfgdata = json.load(opts.config)
            opts.config.close()
        except:
            cfgdata = {}
            mqttlog.warning("Config file could not be opened.")

        # Definition
        for attr in cfgdefault:
            if opts.__getattribute__(attr) != cfgdefault[attr]:
                mqttcfg[attr] = opts.__getattribute__(attr)
            elif attr in cfgdata:
                mqttcfg[attr] = cfgdata[attr]
            else:
                mqttcfg[attr] = opts.__getattribute__(attr)
            if opts.debug:
                mqttlog.debug("The %s is %s." % (attr,mqttcfg[attr]))


        if mqttcfg["ssl"] and not (os.path.isfile(mqttcfg["ssl"] + "/" + CERTFILE)):
            mqttlog.critical("Encryption: Could not find {} .".format(
                mqttcfg["ssl"] + "/" + CERTFILE))
            sys.exit()
        if opts.debug:
            if mqttcfg["ssl"]:
                mqttlog.debug(
                    "The ssl certificates can be found in %s" %
                    mqttcfg["ssl"])
            else:
                mqttlog.debug("The connection is not encrypted")

        if "buddykey" in cfgdata:
            mqttcfg["buddykey"] = cfgdata["buddykey"]

        # Save hings
        if opts.configonly:

            if "buddykey" not in mqttcfg:
                if opts.debug:
                    mqttlog.debug("Generating random key")
                mqttcfg["buddykey"] = bl.keygen()
            try:
                del(mqttcfg["debug"])
            except:
                pass
            with open(opts.configonly, "w") as cfile:
                json.dump(mqttcfg, cfile)
            os.chmod(opts.configonly, 384)  # 0600
            sys.exit()

    except Exception as e:
        mqttlog.error("Error: %r" % e)
        sys.exit(-2)

    return (mqttlog, mqttcfg)


if __name__ == "__main__":
    log, config = configure()
    log.info("Configured")
    loop = aio.get_event_loop()
    if config["debug"]:
        loop.set_debug(True)

    ## Let's find out what network and interface we have Linux
    #config["networks"] = {}
    #if config["lan"]:
        #p1 = subprocess.getoutput(
            #"ip route | sed '/via/d' | sed '/dev/!d' | sed '/src/!d'")
        #if config["debug"]:
            #log.debug("Received from the shell: {}".format(p1))
        #for aroute in p1.split("\n"):
            #allofit = [z for z in [y.strip()
                                   #for y in aroute.split(" ")] if z != ""]
            #netadd = ipaddress.IPv4Address(allofit[allofit.index("src") + 1])
            #network = ipaddress.IPv4Network(allofit[0])
            #dev = allofit[allofit.index("dev") + 1]
            #config["networks"][netadd] = [dev, network]

    if config["ssl"]:
        sslcontext = ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
                                                cafile=config["ssl"] + '/' + CERTFILE)

        sslcontext.check_hostname = False
    else:
        sslcontext = None
    connFuture = aio.Future()
    fac = loop.create_connection(
            partial(MQTTBridge,
                    loop,
                    connFuture,
                    config,
                    log),
            config["host"],
            config["port"],
            ssl=sslcontext)
    conn, bridgectl = loop.run_until_complete(fac)
    loop.call_soon(
        bridgectl.configrequest,
        {"about": {"MQTTBuddy": aboutstr},
         "display": iconstr})

    try:
        loop.run_until_complete(connFuture)
    except KeyboardInterrupt:
        print("\n", "Exiting at user's request")
    finally:
        conn.close()
        loop.run_until_complete(bridgectl.mqtt_broker.shutdown())
        os.remove(sharedfile)
        bridgectl.mqtt_service.cancel()
        loop.run_until_complete(aio.sleep(5))
        loop.close()
