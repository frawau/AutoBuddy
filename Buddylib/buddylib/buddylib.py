#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Copyright (c) 2021 François Wautier
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
import asyncio as aio
import datetime as dt
import argparse, base64, colorsys, json, logging, math, os, random, string, ssl, sys

from . import buddyxml as xml

from collections import defaultdict
import irgen
from copy import copy
from Crypto.Cipher import AES
from random import randint
from uuid import uuid4

__version__ = (
    "0.90"  # Major change. Remove SQLAlchemy,  make this library actually useful
)

# Logging setup is done via line parameters
_log = logging.getLogger(__name__)

# A few Exception
class BuddyConfigOnly(Exception):
    """Exception raised during Buddy partner creation if it was a configuration only run"""

    pass


# A few useful functions


def encrypt(val, key):
    x = json.dumps(val)
    if isinstance(key, str):
        key = key.encode()
    codec = AES.new(key, AES.MODE_ECB)
    return base64.b64encode(
        codec.encrypt((x + (16 - len(x) % 16) * "\x00").encode())
    ).decode()


def decrypt(val, key):
    x = base64.b64decode(val)
    if isinstance(key, str):
        key = key.encode()
    codec = AES.new(key, AES.MODE_ECB)
    x = codec.decrypt(x).decode().strip("\x00")
    return json.loads(x)


def keygen():
    from random import shuffle, randrange

    lolet = list(
        "0123456789aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ`~!@#$%^&*()_+-|\[{]}?/.,<:;"
    )
    for i in range(5):
        shuffle(lolet)
    lolet *= 1000
    for i in range(20):
        shuffle(lolet)
    startidx = randrange(len(lolet) - 32)
    return "".join(lolet[startidx : startidx + 32])


def genid():
    return str(uuid4())


def animname():
    res = ""
    for x in range(4):
        res += random.choice(string.ascii_letters)
    return res


def canon_value(value):
    """
    Value received from the app can be complex. When a "choice" is used,  the value will contain a
    bu-cvalue (buddy choice value). This clean this up. If a value is only a bu-cvalue, the value is set
   as the value, if the dictionay contains more than 1 value, the key "bu-cvalue"" is changed to "selection"
    """
    if isinstance(value, dict):
        if "bu-cvalue" in value:
            if len(value) == 1:
                return value["bu-cvalue"]
            else:
                newval = {"selection": value["bu-cvalue"]}
                for x in value:
                    if x != "bu-cvalue":
                        newval[x] = canon_value(value[x])
                return newval
        else:
            newval = {}
            for x in value:
                if x != "bu-cvalue":
                    newval[x] = canon_value(value[x])
            return newval

    elif isinstance(value, list):
        newval = []
        for x in value:
            newval.append(canon_value(x))
        return newval
    else:
        return value


# Some constants
KEYFLIST = [
    "@keyframes",
    "@-webkit-keyframes",
    "@-moz-keyframes",
]  # @-o-keyframes (Still valid?)

CERTFILE = "autobuddy.crt"


def convert_K_to_RGB(colour_temperature, brightness=100):
    """
    Converts from K to RGB, algorithm courtesy of
    http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
    Taken from petrklus on github
    """

    def b_adjust(x):
        return int(round((x * (90 + brightness / 10)) / 100))

    # range check
    if colour_temperature < 1000:
        colour_temperature = 1000
    elif colour_temperature > 40000:
        colour_temperature = 40000

    tmp_internal = colour_temperature / 100.0

    # red
    if tmp_internal <= 66:
        red = 255
    else:
        tmp_red = 329.698727446 * math.pow(tmp_internal - 60, -0.1332047592)
        if tmp_red < 0:
            red = 0
        elif tmp_red > 255:
            red = 255
        else:
            red = int(tmp_red + 0.5)

    # green
    if tmp_internal <= 66:
        tmp_green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661
        if tmp_green < 0:
            green = 0
        elif tmp_green > 255:
            green = 255
        else:
            green = int(tmp_green + 0.5)
    else:
        tmp_green = 288.1221695283 * math.pow(tmp_internal - 60, -0.0755148492)
        if tmp_green < 0:
            green = 0
        elif tmp_green > 255:
            green = 255
        else:
            green = int(tmp_green + 0.5)

    # blue
    if tmp_internal >= 66:
        blue = 255
    elif tmp_internal <= 19:
        blue = 0
    else:
        tmp_blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
        if tmp_blue < 0:
            blue = 0
        elif tmp_blue > 255:
            blue = 255
        else:
            blue = int(tmp_blue + 0.5)
    return (b_adjust(red), b_adjust(green), b_adjust(blue))


# Now the classes


class BEntity(object):
    """
    This object defines a number of behaviour common to all
    connected devices
    """

    def __init__(self, type=None):
        """
        Creating a Buddy entity is simply definig its type
        """
        self.type = type
        super().__init__()

    def of_interest(self, subject):
        """
        This method check whether a given address is
        of interest to the entity
        """
        # TODO  change to a regex... Now light.Home and light.Home Theatre  would both match on Home zone
        try:
            split = subject.split(".")
            if split[0] == self.type and (
                split[1] in ["*", "#"] or split[1] == self.name
            ):
                return True
        except:
            pass
        return False

    async def _process_command(self, subject, msg):
        """
        generic processing
        """

        if self.of_interest(subject):
            return await self.process_command(msg)
        await aio.sleep(0)
        return None

    async def _process_response(self, subject, msg):
        """
        generic processing
        """

        if self.of_interest(subject):
            return await self.process_response(msg)
        await aio.sleep(0)
        return None

    async def process_command(self, msg):
        """
        Needs to be overloaded. Actual processing
        returns None or a list of dictionary
        [{"subject":"subject.subject","data":<data to be sent>}]
        """
        raise NotImplementedError()

    async def process_rerponse(self, msg):
        """
        Needs to be overloaded. Actual processing
        returns None or a list of dictionary
        [{"subject":"subject.subject","data":<data to be sent>}]
        """
        raise NotImplementedError()


class Zone(BEntity):
    """
    The automation system groups  entity by zone.Commands can be
    applied to the devices in the zone.

    Zone s a table createw with
        CREATE TABLE public.zone (
            id integer NOT NULL,
            name character varying,
            nickname character varying(64),
            parent_id integer
        );

        ALTER TABLE public.zone OWNER TO <username>;

        CREATE SEQUENCE public.zone_id_seq
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER TABLE public.zone_id_seq OWNER TO <uername>;

        ALTER SEQUENCE public.zone_id_seq OWNED BY public.zone.id;
        ALTER TABLE ONLY public.zone ALTER COLUMN id SET DEFAULT nextval('public.zone_id_seq'::regclass);
        ALTER TABLE ONLY public.zone
            ADD CONSTRAINT zone_name_key UNIQUE (name);
        ALTER TABLE ONLY public.zone
            ADD CONSTRAINT zone_pkey PRIMARY KEY (id);
        ALTER TABLE ONLY public.zone
            ADD CONSTRAINT zone_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.zone(id);

        GRANT SELECT ON TABLE public.zone TO <username>;

    This shoud have been created during initial configurationn
    Zone can contain sub-zone
    """

    def __init__(self, oid, name, nickname):

        super().__init__(type="zone")
        self.id = oid
        self.name = name
        self.nickname = nickname
        self.parent = None
        self.sub_zone = []
        self.devices = []

    def __repr__(self):
        return "Zone " + self.name

    def set_parent(self, parent):
        self.parent = parent

    def add_sub_zone(self, zone):
        for z in self.sub_zone:
            if z.id == zone.id:
                # Alreaay a sub zone
                return
        self.sub_zone.append(zone)
        zone.set_parent(self)

    def all_names(self):
        result = [self.name]
        for x in self.sub_zone:
            result += x.allNames()
        return result

    def add_device(self, device):
        self.devices.append(device)
        device.set_location(self.name, self.nickname)

    def all_devices(self):
        result = []
        for device in self.devices:
            result.append(device)
        for x in self.sub_zone:
            result += x.allDevices()
        return result

    def to_dict(self):
        resu = {
            "name": self.name,
            "nickname": self.nickname,
            "devices": {},
            "sub_zone": [],
        }
        for adevice in self.devices:
            if adevice.type not in resu["devices"]:
                resu["devices"][adevice.type] = []
            resu["devices"][adevice.type].append(
                {
                    "name": adevice.name,
                    "nickname": adevice.nickname,
                    "subtype": adevice.subtype,
                }
            )
        for szone in self.sub_zone:
            resu["sub_zone"].append(szone.toDict())
        return resu

    @classmethod
    def from_list(self, zlist):
        """
            Take a list of dictionaries defining classes, each dictionary should be
                {'id": <id>, 'name": "a name", "nickname": "a nickname", "parent_id": id or None}
            It returns a dictionary, the keys are zone id's and the value is a zone completely structured.


        """
        allzones = {}
        allzonesids = {}
        ptoset = defaultdict(list)
        for az in zlist:
            nzone = Zone(az["id"], az["name"], az["nickname"])
            allzones[az["name"]] = nzone
            allzonesids[az["id"]] = nzone
            if az["parent_id"] in allzonesids:
                allzonesids[az["parent_id"]].add_sub_zone(nzone)
            else:
                ptoset[az["parent_id"]].append(nzone)
            if nzone.id in ptoset:
                for sz in ptoset[nzone.id]:
                    nzone.add_sub_zone(sz)
                del ptoset[nzone.id]
        return allzones


class BuddyFunction:
    """
    Here we define the list of functions associated with a type/subtype pair.
    Functions are defined by an XML document.

    Table is build with

        CREATE TABLE public.function (
            type character varying(16) NOT NULL,
            subtype character varying(16) NOT NULL,
            functions text
        );

        ALTER TABLE public.function OWNER TO <username>;

        ALTER TABLE ONLY public.function
            ADD CONSTRAINT function_pkey PRIMARY KEY (type, subtype);



    """

    def __init__(self, dtype, dsubtype, functions):
        self.type = dtype
        self.subtype = dsubtype
        self.functions = functions

    @classmethod
    def from_list(self, fl):
        allf = defaultdict(dict)
        for af in fl:
            allf[af["type"]][af["subtype"]] = BuddyFunction(
                af["type"], af["subtype"], af["functions"]
            )
        return allf


class BuddyDevice(BEntity):
    """
        Buddy devices have a name, a type, possibly a location and a list of
        functions. The list of functions is an XML document.

        CREATE TABLE public.device (
            id integer NOT NULL,
            name character varying(256),
            nickname character varying(64),
            type character varying(16),
            subtype character varying(16),
            location_id integer
        );


        ALTER TABLE public.device OWNER TO <username>;

        CREATE SEQUENCE public.device_id_seq
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;


        ALTER TABLE public.device_id_seq OWNER TO <username>;

        ALTER SEQUENCE public.device_id_seq OWNED BY public.device.id;

        ALTER TABLE ONLY public.device ALTER COLUMN id SET DEFAULT nextval('public.device_id_seq'::regclass);

        ALTER TABLE ONLY public.device
            ADD CONSTRAINT device_name_key UNIQUE (name);

        ALTER TABLE ONLY public.device
            ADD CONSTRAINT device_pkey PRIMARY KEY (id);

        ALTER TABLE ONLY public.device
            ADD CONSTRAINT device_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.zone(id);

        ALTER TABLE ONLY public.device
            ADD CONSTRAINT device_type_fkey FOREIGN KEY (type, subtype) REFERENCES public.function(type, subtype);

        We are making a number of assumptions regarding the devices.

        Every device has a controller. The controller is usually a bridge, but it can be the device itself.
        The controller is the one communication with the AutoBuddy bus. As such it should manage a sending message
        queue. The device can enqueue message with the enqueue coroutine. The controller shall send the message
        shortly afterward

    """

    def __init__(self, name, nickname, type, subtype, did=None):
        super().__init__(type)
        self.id = did
        self.name = name
        self.nickname = nickname
        self.subtype = subtype
        self.location = [None, None]
        self.controller = None
        self._present = False
        self._send_presence = True
        self._icon_colour = "#FF1070"  # A default value for the icon colour

    def set_location(self, name, nickname):
        """
        Set the device location
        """
        self.location = [name, nickname]

    async def process_command(self, msg):
        """
        Needs to be overloaded. Actual processing
        returns None or a list of dictionary
        [{"subject":"subject.subject","data":<data to be sent>}]

        Some processing is common to all device

        """

        _log.debug(
            f"Calling process_command on {self.nickname} {self.present} with {msg}"
        )
        try:
            if "realtime mode" in msg and msg["realtime mode"]:
                rt = True
            else:
                rt = False
            cmd = msg["command"].replace(" ", "_")
            _log.debug(
                f"Calling handle_command_{cmd} with {msg['value']} for {self.nickname}"
            )
            res = getattr(self, f"handle_command_{cmd}")(msg["value"], rt)
            if aio.iscoroutine(res):
                return await res
            else:
                await aio.sleep(0)
                return res
        except Exception as e:
            _log.warning(
                f"Device {self.name} (aka {self.nickname}) cannot handle command from message {cmd}"
            )
            _log.debug(f"Exception was {e}")
            _log.exception(e)

    async def process_response(self, msg):
        """
        Needs to be overloaded. Actual processing
        returns None or a list of dictionary
        [{"subject":"subject.subject","data":<data to be sent>}]

        Some processing is common to all device

        """

        _log.debug(
            f"Calling process_response on {self.nickname} {self.present} with {msg}"
        )
        try:
            resp = msg["response"].replace(" ", "_")
            res = getattr(self, f"handle_response_{resp}")(msg)
            if aio.iscoroutine(res):
                return await res
            else:
                await aio.sleep(0)
                return res
        except Exception as e:
            _log.warning(
                f"Device {self.name} (aka {self.nickname}) cannot handle response from message {resp}"
            )
            _log.debug(f"Exception was {e}")

    async def handle_command_deletion(self, value, rt):
        """
        Deletion is common for all devices
        """
        await self.controller.enqueue(
            {
                "subject": "control" + "." + self.type,
                "content_type": "request",
                "content": {
                    "request": "deletion",
                    "target": self.type,
                    "value": self.name,
                },
            }
        )

    async def handle_response_deletion(self, msg):
        if msg["status"] == "done":
            await self.controller.enqueue(
                {
                    "subject": self.type,
                    "content_type": "event",
                    "content": {
                        "event": "deletion",
                        "target": self.type + "." + self.name,
                        "value": self.name,
                    },
                }
            )
            self.controller.unregister(self)
            self.last_rites()

    async def handle_command_status(self, value, rt):
        """
        Status information is common for all devices
        """
        try:
            await self.send_status()
        except Exception as e:
            self.present = False
            await aio.sleep(0)

    async def handle_command_nickname(self, value, rt):
        await self.controller.enqueue(
            {
                "subject": "control" + "." + self.controller.type,
                "content_type": "request",
                "content": {
                    "request": "nickname",
                    "target": self.controller.type + "." + self.name,
                    "value": {"name": self.name, "nickname": value},
                },
            }
        )

    async def handle_response_nickname(self, msg):
        if msg["status"] == "done":
            _log.debug(f"Nickname response {msg}")
            self.nickname = msg["value"]
            await self.controller.enqueue(
                {
                    "subject": self.controller.type,
                    "content_type": "event",
                    "content": {
                        "event": "nickname",
                        "target": self.controller.type + "." + self.name,
                        "value": self.nickname,
                    },
                }
            )
        else:
            await aio.sleep(0)

    async def send_status(self):
        raise NotImplementedError

    async def send_status_delayed(self, delay=0.5):
        """
        When sending a status not directly in response to an event, command,
        it is better to use this to avoid possible race conditions
        """
        await aio.sleep(delay)
        await self.send_status()

    async def start(self):
        pass

    @property
    def present(self):
        return self._present

    @present.setter
    def present(self, value):
        if self._present != value or self._send_presence:
            self._present = value
            self._send_presence = False
            if self.icon_colour():
                iconsts = {
                    "bu-fill": self.icon_colour(),
                    "bu-not-present": {"opacity": (not self._present and 1) or 0},
                }
            else:
                iconsts = {
                    "bu-not-present": {"opacity": (not self._present and 1) or 0}
                }
            aio.create_task(
                self.controller.enqueue(
                    {
                        "subject": self.controller.type,
                        "content_type": "event",
                        "content": {
                            "event": "presence",
                            "target": self.controller.type + "." + self.name,
                            "value": (self._present and "online") or "offline",
                            "icon status": iconsts,
                        },
                    }
                )
            )

    def icon_colour(self, force=False):
        """
        We have expectation on how elements of the icon are named
        Here we set the main colour for the icon in CSS format

        by default, just return the default colour

        """
        return self._icon_colour

    def last_rites(self):
        """
        Things to do when we go away for good (e.g. kill running tasks)
        """
        pass

    def update(self, val):
        """
        Updating the current object with the values passed in val, a dictionary
        """
        for k, v in val.items():
            setattr(self, k, v)

    def xml_names(self, gen_xml=False):
        """
        This method return a name reflecting the parameters of a function. It is expected that
        function with the same name and the same range/values will return the same name.

        The value returned shall be a dictionary: the key, the function/command name, the value
        depending on parameter xml:
              if xml == True   a string, the unique name
              if xml == False a 2-uple: ( the unique name, XML text)

        If the unique name is None, it means the command is available for all devices. If there is a
        onlyif it can be predicate to the state. E.g. onlyif="power::on"
        """
        return {}  # Nothing here

    @classmethod
    def from_list(cls, dl):
        """
        Here we expect the inheriting class to have a signature of the form
             name, nickname, did=None, other keywords arguments.

        The inheriting class must set type and subtype of the device
        """
        alldevs = []
        for ad in dl:
            _log.debug(f"Building from {ad},  class {ad.__class__}")
            if "id" not in ad:
                ad["id"] = None
            adev = cls(ad["name"], ad["nickname"], did=ad["id"])
            if "location" in ad:
                adev.set_location(*ad["location"])
            alldevs.append(adev)
        return alldevs


class onoff(BuddyDevice):
    """
    Simple device with on/off  function. Need to be subclassed instead of BuddyDevice
    """

    def __init__(self, name, nickname, type, subtype, did=None):
        super().__init__(name, nickname, type, subtype, did)
        self._power = "off"  # Current power state
        self.rt_duration = (
            "never"  # supports duration or not one of "yes", "no", "only" or "never"
        )

    @property
    def power(self):
        return self._power

    @power.setter
    def power(self, value):
        if value in [True, False]:
            self._power = "on" if value else "off"
        elif value == 0:
            self._power = "off"
        elif isinstance(value, str) and value.lower() in ["on", "off"]:
            self._power = value.lower()
        elif value == 1:
            self._power = "on"
        else:
            raise Exception(f"{value} is not a correct value for power")

    async def handle_command_power(self, value, rt):
        """
        The simplest of light can be turned on and off
        """
        if not self.present:
            await aio.sleep(0)  # Must await something
            return None
        try:
            iconsts = {"bu-fill": self.icon_colour(force=value["power"])}
            if self.power != value["power"]:
                if "duration" in value and value["duration"]:
                    prefix = animname()
                    startcss = self.icon_colour()["fill"]
                    endcss = self.icon_colour(force=value["power"])["fill"]
                    anim = ""
                    pref = ""
                    for kf in KEYFLIST:
                        anim += (
                            pref
                            + kf
                            + " "
                            + prefix
                            + self.name
                            + " {  from { fill: "
                            + startcss
                            + " }  to { fill: "
                            + endcss
                            + " }}"
                        )
                        pref = "\n"
                    alen = int(value["duration"] or 0)
                    anim += (
                        "\n.run-animation-"
                        + self.name
                        + " { animation-name: "
                        + prefix
                        + self.name
                        + "; animation-duration: %ds" % alen
                        + "; animation-iteration-count: 1; }"
                    )
                    if alen:
                        iconsts["animation"] = anim
                        self.heartbeat_delay(alen)
            msg = {
                "subject": self.controller.type,
                "content_type": "event",
                "content": {
                    "event": "power",
                    "target": self.controller.type + "." + self.name,
                    "icon status": iconsts,
                    "value": value,
                },
            }
            await self.pre_local_command_power(value, rt, msg=msg)
        except Exception as e:
            _log.warning(
                f"Could not set power for {self.name} (aka {self.nickname}): {e}"
            )
            await aio.sleep(0)

    async def pre_local_command_power(self, value, rt, msg=None):
        """
        The onoff object is a bit particular. In some cases, it might not be controlling the icon
        state. In that case, this method can be overloaded to remove the "icon status" from the message
        passed. By default, it just passes it along
        """
        await self.local_command_power(value, rt, msg=msg)

    async def local_command_power(self, value, rt, msg=None):
        """
        Generic command. local_command_power needs to be overloaded to
        perform actual power
        """
        raise NotImplementedError

    def xml_names(self, gen_xml=False):
        """
        Here for power. We expect the realtime factor to be consistent through all
        supported devices. We expect the 'duration' parameter to be handled correctly
        by the Buddypartner
        """
        # All lights support power the same way
        resu = super().xml_names(gen_xml)
        if gen_xml:
            pg = xml.xml_group("power", label="Power", realtime="yes")
            pe = xml.xml_switch("power", realtime="yes")
            pg.add_member(pe)
            if self.rt_duration in ["only", "no", "yes"]:
                pe = xml.xml_spinner(
                    "duration",
                    start=0,
                    end=600,
                    increment=1,
                    postfix="secs",
                    realtime=self.rt_duration,
                )
                pg.add_member(pe)
            resu["power"] = [None, pg.render()]
        else:
            resu["power"] = None
        return resu


class light(onoff):
    """
    Defines a simple light bulb. Just can power on/off
    """

    icon = """
        <svg class="bu-device-icon" width="60" height="60" viewBox="0 0 1792 1792" xmlns="http://www.w3.org/2000/svg">
            <path class="bu-shape" d="M1120 576q0 13-9.5
            22.5t-22.5 9.5-22.5-9.5-9.5-22.5q0-46-54-71t-106-25q-13 0-22.5-9.5t-9.5-22.5 9.5-22.5
            22.5-9.5q50 0 99.5 16t87 54 37.5 90zm160 0q0-72-34.5-134t-90-101.5-123-62-136.5-22.5-136.5 22.5-123 62-90
            101.5-34.5 134q0 101 68 180 10 11 30.5 33t30.5 33q128 153 141 298h228q13-145 141-298 10-11 30.5-33t30.5-33q68-79
            68-180zM1400 576q0 155-103 268-45 49-74.5 87t-59.5 95.5-34 107.5q47 28 47 82 0 37-25 64 25 27 25 64 0 52-45
            81 13 23 13 47 0 46-31.5 71t-77.5 25q-20 44-60 70t-87 26-87-26-60-70q-46 0-77.5-25t-31.5-71q0-24 13-47-45-29-45-81
            0-37 25-64-25-27-25-64 0-54 47-82-4-50-34-107.5t-59.5-95.5-74.5-87q-103-113-103-268 0-99 44.5-184.5t117-142
            164-89 186.5-32.5 186.5 32.5 164 89 117 142 44.5 184.5z"/>
            <path class="bu-fill" d="M1120 576q0 13-9.5 22.5t-22.5 9.5-22.5-9.5-9.5-22.5q0-46-54-71t-106-25q-13
                0-22.5-9.5t-9.5-22.5 9.5-22.5 22.5-9.5q50 0 99.5 16t87 54 37.5 90zm160
                0q0-72-34.5-134t-90-101.5-123-62-136.5-22.5-136.5 22.5-123 62-90
                101.5-34.5 134q0 101 68 180 10 11 30.5 33t30.5 33q128 153 141 298h228q13-145 141-298 10-11 30.5-33t30.5-33q68-79
                68-180z" fill="transparent"/>
            <path class="bu-not-present" fill="#a94442"
                d="M1440 893q0-161-87-295l-754 753q137 89 297 89 111 0 211.5-43.5t173.5-116.5 116-174.5
                43-212.5zm-999 299l755-754q-135-91-300-91-148
                0-273 73t-198 199-73 274q0 162 89 299zm1223-299q0 157-61 300t-163.5 246-245 164-298.5
                61-298.5-61-245-164-163.5-246-61-300 61-299.5 163.5-245.5 245-164 298.5-61 298.5 61
                245 164 163.5 245.5 61 299.5z"/>
        </svg>
        """

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "light", subtype, did)
        self._temperature = 6500  # Default temperature, can be set by
        self._temperature_range = [6500, 6500, 0]  # min, max, step
        self._brightness = 100  # Default, 100%
        self._brightness_range = [100, 100, 0]  # Default, 100%
        self._mode = "white"  # One of 'white', 'colour'
        self._colour = {"hue": 0, "saturation": 100, "value": 100}
        self._colour_range = False  # True if handles colours. False if not
        self.rt_duration = (
            "no"  # supports duration or not one of "yes", "no", "only" or "never"
        )

    @property
    def temperature(self):
        """
        Overload if needed
        """
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        if value < self._temperature_range[0]:
            value = self._temperature_range[0]
        if value > self._temperature_range[1]:
            value = self._temperature_range[1]
        if self._temperature_range[2]:
            self._temperature = (
                round(value / self._temperature_range[2]) * self._temperature_range[2]
            )
        else:
            self._temperature = int(value)

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        if value < self._brightness_range[0]:
            value = self._brightness_range[0]
        if value > self._brightness_range[1]:
            value = self._brightness_range[1]
        if self._brightness_range[2]:
            self._brightness = (
                round(value / self._brightness_range[2]) * self._brightness_range[2]
            )
        else:
            self._brightness = int(value)

    @property
    def colour(self):
        if self._mode == "white":
            return {"temperature": self._temperature, "brightness": self._brightness}
        else:
            return self._colour

    @colour.setter
    def colour(self, value):
        if "brightness" in value:
            if "temperature" in value:
                self.temperature = value["temperature"]
            self.brightness = value["brightness"]
            self._mode = "white"
        elif "temperature" in value:
            self.temperature = value["temperature"]
            self._mode = "white"
        elif "hue" in value:
            self._colour = value
            self._mode = "colour"
        elif "red" in value:
            self._colour = {
                x: y
                for (x, y) in zip(
                    ["hue", "saturation", "value"],
                    [
                        round(s * t)
                        for s, t in zip(
                            [359, 100, 100],
                            colorsys.rgb_to_hsv(
                                value["red"] / 255,
                                value["green"] / 255,
                                value["blue"] / 255,
                            ),
                        )
                    ],
                )
            }
            self._mode = "colour"

    @property
    def rgbcolour(self):
        if self.mode == "colour":
            return {
                x: y
                for (x, y) in zip(
                    ["red", "green", "blue"],
                    [
                        round(s * 255)
                        for s in colorsys.hsv_to_rgb(
                            self.colour["hue"] / 359,
                            self.colour["saturation"] / 100,
                            self.colour["value"] / 100,
                        )
                    ],
                )
            }
        else:
            return {
                x: y
                for (x, y) in zip(
                    ["red", "green", "blue"],
                    convert_K_to_RGB(self._temperature, self._brightness),
                )
            }

    async def handle_command_white(self, value, rt):
        if not self.present:
            await aio.sleep(0)  # Must await something
            return None
        try:
            if self.power == "on":
                endcss = self.icon_colour(value)
                iconsts = {"bu-fill": endcss}
                endcss = endcss["fill"]
                if "duration" in value and value["duration"]:
                    prefix = animname()
                    startcss = self.icon_colour()["fill"]
                    anim = ""
                    for kf in KEYFLIST:
                        anim += (
                            kf
                            + " "
                            + prefix
                            + self.name
                            + " {  from { fill: "
                            + startcss
                            + " }  to { fill: "
                            + endcss
                            + " }}"
                        )

                    alen = int(value["duration"] or 0)
                    anim += (
                        "\n.run-animation-"
                        + self.name
                        + " { animation-name: "
                        + prefix
                        + self.name
                        + "; animation-duration: %ds" % alen
                        + "; animation-iteration-count: 1; }"
                    )
                    if alen:
                        iconsts["animation"] = anim
                        self.heartbeat_delay(alen)
                        if self.conn.hbtimer < alen:
                            self.conn.hbtimer = alen + 5
            else:
                iconsts = {"bu-fill": self.icon_colour(value)}

            msg = {
                "subject": self.controller.type,
                "content_type": "event",
                "content": {
                    "event": "white",
                    "target": self.controller.type + "." + self.name,
                    "icon status": iconsts,
                    "value": value,
                },
            }
            await self.local_command_white(value, rt, msg=msg)

        except Exception as e:
            _log.warning(
                f"Could not set white for {self.name} (aka {self.nickname}): {e}"
            )
            _log.exception(e)
            await aio.sleep(0)

    async def local_command_white(self, value, rt, msg=None):
        """
        Must be overloaded to execute the command on the actual bulb
        message to enqueue upon successful completion of command

        Must update self._temperature and/orr self._brightness

        """
        raise NotImplementedError

    def handle_command_brightness(self, value, rt):
        """
        For those who cannot read
        """
        return self.handle_command_white(value, rt)

    async def handle_command_colour(self, value, rt):
        if not self.present:
            await aio.sleep(0)  # Must await something
            return None
        try:
            if self._power == "on":
                endcss = self.icon_colour(value)
                iconsts = {"bu-fill": endcss}
                endcss = endcss["fill"]
                if "duration" in value and value["duration"]:
                    prefix = animname()
                    startcss = self.icon_colour()["fill"]
                    anim = ""
                    for kf in KEYFLIST:
                        anim += (
                            kf
                            + " "
                            + prefix
                            + self.name
                            + " {  from { fill: "
                            + startcss
                            + " }  to { fill: "
                            + endcss
                            + " }}"
                        )

                    alen = int(value["duration"] or 0)
                    anim += (
                        "\n.run-animation-"
                        + self.name
                        + " { animation-name: "
                        + prefix
                        + self.name
                        + "; animation-duration: %ds" % alen
                        + "; animation-iteration-count: 1; }"
                    )
                    if alen:
                        iconsts["animation"] = anim
                        if self.conn.hbtimer < alen:
                            self.conn.hbtimer = alen + 5
            else:
                iconsts = {"bu-fill": self.icon_colour()}

            msg = {
                "subject": self.controller.type,
                "content_type": "event",
                "content": {
                    "event": "colour",
                    "target": self.controller.type + "." + self.name,
                    "icon status": iconsts,
                    "value": value,
                },
            }

            await self.local_command_colour(value, rt, msg=msg)
        except Exception as e:
            _log.warning(
                f"Could not set colour for {self.name} (aka {self.nickname}): {e}"
            )
            await aio.sleep(0)

    async def local_command_colour(self, value, msg=None):
        """
        Must be overloaded to execute the power command on the actual bulb
        message to enqueue upon successful completion of command

        Must update self._currrent_colour with HSV values
        """
        raise NotImplementedError

    def icon_colour(self, force=False):
        """
        Here force should take a colour dictionary (hue, saturation, value) value
        or "off" or "on"

        We have expectation on how elements of the icon are named
        Here we set the main colour for the icon in CSS format
        """
        try:
            # _log.debug(f"Icon colour with forcr {force} and colour {self.colour} ")
            if force:
                if force == "on":
                    colour = self.colour
                else:
                    colour = force
            else:
                colour = self.colour
            if "hue" in colour and "brightness" in colour:
                colour["value"] = colour["brightness"]

            if force and force == "off":
                iconsts = "transparent"
            elif force or self._power != "off":
                if "hue" in colour:
                    iconsts = "#%02x%02x%02x" % tuple(
                        map(
                            lambda x: int((x * 255) + 0.5),
                            colorsys.hsv_to_rgb(
                                colour["hue"] / 359.0,
                                colour["saturation"] / 100.0,
                                colour["value"] / 100.0,
                            ),
                        )
                    )
                elif "red" in colour:
                    iconsts = "#%02x%02x%02x" % (
                        colour["red"],
                        colour["green"],
                        colour["blue"],
                    )
                else:
                    if "brightness" in colour:
                        iconsts = "#%02x%02x%02x" % convert_K_to_RGB(
                            colour["temperature"], colour["brightness"]
                        )
                    else:
                        iconsts = "#%02x%02x%02x" % convert_K_to_RGB(
                            colour["temperature"]
                        )
            else:
                iconsts = "transparent"
        except Exception as e:
            _log.debug(f"Problem in icon_colour with {force}: {e}")
            _log.exception(e)
            if self.power != "off":
                iconsts = "#%02x%02x%02x" % convert_K_to_RGB(
                    self._temperature, self._brightness
                )
            else:
                iconsts = "transparent"

        return {"fill": iconsts}

    async def send_status(self):
        """
        Send the current light status
        """
        if not self.present:
            await aio.sleep(0)
            return
        try:
            val = {"power": {"power": self.power}}
            if self._colour_range:
                val["colour"] = self._colour
            white = {}
            if self._brightness_range[2]:
                white["brightness"] = self.brightness
            if self._temperature_range[2]:
                white["temperature"] = self._temperature
            if white:
                val["white"] = white
            content = {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": {
                    "bu-fill": self.icon_colour(),
                    "bu-not-present": {"opacity": 0},
                },
                "value": val,
            }
            for x in self.xml_names().values():
                if x is not None:
                    content["value"][x] = "yes"
            await self.controller.enqueue(
                {
                    "subject": self.controller.type,
                    "content_type": "event",
                    "content": content,
                }
            )
        except Exception as e:
            _log.warning(f"Ooops could not send status {e}")
            await aio.sleep(0)

    def heartbeat_delay(self, delay):
        """
        Some devices may have a heartbeat process. The heartbeat process
        my interfere with other tasks (e.g. icon animations). Here we provide a way to make
        sure the heartbeat won't occur before a certain time

        delay is the needed duration before a hb occurs

        Need to be overloaded.
        """
        pass

    def xml_names(self, gen_xml=False):
        """
        Here for lights. We expect the realtime factor to be consistent through all
        supported devices. We expect the 'duration' parameter to be handled correctly
        by the Buddypartner
        """
        resu = super().xml_names(gen_xml)
        # Now the white command
        if (
            self._temperature_range
            and self._temperature_range[0] != self._temperature_range[1]
        ):
            uname = (
                xml.XMLONLYLBL
                + f"white_{self._temperature_range[0]}_{self._temperature_range[1]}_{self._temperature_range[2]}"
            )
            if gen_xml:
                pg = xml.xml_group(
                    "white", label="White", realtime="yes", onlyif=uname + "::yes"
                )
                pe = xml.xml_slider(
                    "temperature",
                    label="Kelvin ",
                    start=self._temperature_range[0],
                    end=self._temperature_range[1],
                    increment=self._temperature_range[2],
                    realtime="yes",
                )
                pg.add_member(pe)
                if (
                    self._brightness_range
                    and self._brightness_range[0] != self._brightness_range[1]
                ):
                    pe = xml.xml_slider(
                        "brightness",
                        label="Brightness ",
                        start=self._brightness_range[0],
                        end=self._brightness_range[1],
                        increment=self._brightness_range[2],
                        realtime="yes",
                    )
                    pg.add_member(pe)
                if self.rt_duration:
                    pe = xml.xml_spinner(
                        "duration",
                        start=0,
                        end=600,
                        increment=1,
                        postfix="secs",
                        onlyif=xml.XMLONLYLBL + "duration::yes",
                        realtime=self.rt_duration,
                    )
                    pg.add_member(pe)
                resu["white"] = [uname, pg.render()]
            else:
                resu["white"] = uname
        elif (
            self._brightness_range
            and self._brightness_range[0] != self._brightness_range[1]
        ):
            uname = xml.XMLONLYLBL + "white_bright"
            if gen_xml:
                pg = xml.xml_group(
                    "white", label="White", realtime="yes", onlyif=uname + "::yes"
                )
                pe = xml.xml_slider(
                    "brightness",
                    label="Brightness ",
                    start=self._brightness_range[0],
                    end=self._brightness_range[1],
                    increment=self._brightness_range[2],
                    realtime="yes",
                )
                pg.add_member(pe)
                if self.rt_duration:
                    pe = xml.xml_spinner(
                        "duration",
                        start=0,
                        end=600,
                        increment=1,
                        postfix="secs",
                        onlyif=xml.XMLONLYLBL + "duration::yes",
                        realtime=self.rt_duration,
                    )
                    pg.add_member(pe)
                resu["white"] = [uname, pg.render()]
            else:
                resu["white"] = uname

        # Now colours
        if self._colour_range:
            uname = xml.XMLONLYLBL + "colours"
            if gen_xml:
                pg = xml.xml_group(
                    "colour", label="Colour", realtime="yes", onlyif=uname + "::yes"
                )
                pe = xml.xml_colour(realtime="yes")
                pg.add_member(pe)
                if self.rt_duration:
                    pe = xml.xml_spinner(
                        "duration",
                        start=0,
                        end=600,
                        increment=1,
                        postfix="secs",
                        onlyif=xml.XMLONLYLBL + "duration::yes",
                        realtime=self.rt_duration,
                    )
                    pg.add_member(pe)
                resu["colour"] = [uname, pg.render()]
            else:
                resu["colour"] = uname
        return resu


class mediaplayer(onoff):
    """
    Handlin of media playes
    """

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "mediaplaer", subtype, did)
        self._power = "off"  # Current power state
        self._music = True  # By default has everything
        self._video = True  # By default has everything

    def icon_colour(self, force=False):
        """
        To force can be set to a CSS colour
        """
        if force:
            return {"fill": force}
        if self.power == "on":
            return {"fill": self._icon_colour}
        return {"fill": "transparent"}

    def xml_names(self, gen_xml=False):
        """
        Here for media playes. We expect the realtime factor to be consistent through all
        supported devices. We expect the 'duration' parameter to be handled correctly
        by the Buddypartner
        """
        result = {}
        if gen_xml:
            pg = xml.xml_mediaplayer(
                "remote", label="Remote Control", realtime="only", onlyif="power::on"
            )
            result["remote"] = [
                None,
                pg.render(),
            ]  # Here onlyif is not a function/command discriminator
            # but a state conddition... hence None for unique name
        else:
            result["remote"] = None

        # playalbum
        if gen_xml:
            pg = xml.xml_group(
                "playalbum",
                label="Play Album",
                gtype="grouplist",
                realtime="yes",
                onlyif="power::on",
            )
            pe = xml.xml_entry("name", label="Title", length=64, default="random")
            pg.add_member(pe)
            pe = xml.xml_spinner(
                "offset",
                label="Offset",
                start=1,
                end=10,
                increment=1,
                postfix=" albums",
            )
            pg.add_member(pe)
            pe = xml.xml_switch("repeat", label="Repeat", default="off")
            pg.add_member(pe)
            result["playalbum"] = [None, pg.render()]
        else:
            result["playalbum"] = None
        # playmusic
        if gen_xml:
            pg = xml.xml_group(
                "playmusic",
                label="Play Music",
                gtype="grouplist",
                realtime="yes",
                onlyif="power::on",
            )
            pe = xml.xml_choice("type", ["albun", "song"], label="What")
            pg.add_member(pe)
            pe = xml.xml_entry("genre", label="Genre", length=64)
            pg.add_member(pe)
            pe = xml.xml_spinner(
                "length", label="Nb of items", start=1, end=20, increment=1, default=5
            )
            pg.add_member(pe)
            pe = xml.xml_switch("repeat", label="Repeat", default="off")
            pg.add_member(pe)
            result["playmusic"] = [None, pg.render()]
        else:
            result["playmusic"] = None
        # playsong
        if gen_xml:
            pg = xml.xml_group(
                "playsong",
                label="Play Song",
                gtype="grouplist",
                realtime="yes",
                onlyif="power::on",
            )
            pe = xml.xml_entry("name", label="Title", length=64)
            pg.add_member(pe)
            pe = xml.xml_spinner("offset", label="Offset", start=1, end=20, increment=1)
            pg.add_member(pe)
            pe = xml.xml_switch("repeat", label="Repeat", default="off")
            pg.add_member(pe)
            result["playsong"] = [None, pg.render()]
        else:
            result["playsong"] = None
        # playmvideo
        if gen_xml:
            pg = xml.xml_group(
                "playmvideo",
                label="Play Music Video",
                gtype="grouplist",
                realtime="yes",
                onlyif="power::on",
            )
            pe = xml.xml_entry("name", label="Title", length=64)
            pg.add_member(pe)
            pe = xml.xml_spinner("offset", label="Offset", start=1, end=20, increment=1)
            pg.add_member(pe)
            pe = xml.xml_switch("repeat", label="Repeat", default="off")
            pg.add_member(pe)
            result["playmvideo"] = [None, pg.render()]
        else:
            result["playmvideo"] = None
        # playmovie
        if gen_xml:
            pg = xml.xml_group(
                "playmvideo",
                label="Play Music Video",
                gtype="grouplist",
                realtime="yes",
                onlyif="power::on",
            )
            pe = xml.xml_entry("name", label="Title", length=64)
            pg.add_member(pe)
            pe = xml.xml_spinner("offset", label="Offset", start=1, end=20, increment=1)
            pg.add_member(pe)
            result["playmovie"] = [None, pg.render()]
        else:
            result["playmovie"] = None
        # All media playes support power the same way
        if gen_xml:
            pg = xml.xml_group("power", label="Power", realtime="yes")
            pe = xml.xml_switch("power", realtime="yes")
            pg.add_member(pe)
            result["power"] = [None, pg.render()]
        else:
            result["power"] = None

        return result


class video(BuddyDevice):
    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "video", subtype, did)


class voice(BuddyDevice):
    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "voice", subtype, did)

    def xml_names(self, gen_xml=False):
        """
        Here for voice, it is only about showing the utterances detected.
        """
        result = {}
        if gen_xml:
            pe = xml.xml_switch(
                "viewspeech", label="View Recognizzed Utterances", realtime="only"
            )
            result["viewspeech"] = [None, pe.render()]
        else:
            result["viewspeech"] = None
        return result


class hvac(BuddyDevice):
    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "hvac", subtype, did)


class remotec(BuddyDevice):
    """
    A remotec is a remote control device. It is mostly used by agent proxying other devices,
    e.g. AC, curtains, TV etc. The list depends on the available proxy buddies.
    A remotec device can support various  "protocols", ir, rf, zb, zw, ...

    """
    icon = """
<svg version="1.1" class="bu-device-icon" width="60" height="60" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 viewBox="0 0 58.14 58.14" >
<g>
	<path class="bu-pad" style="fill:black;" d="M13.759,38.588c0.344,0.321,0.886,0.304,1.207-0.04l0.368-0.393
		c0.321-0.344,0.303-0.887-0.041-1.208l-1.144-1.069c-0.345-0.322-0.887-0.303-1.208,0.041l-0.368,0.394
		c-0.321,0.344-0.304,0.885,0.041,1.207C12.614,37.52,13.759,38.588,13.759,38.588z M13.009,36.718l0.368-0.394
		c0.098-0.104,0.261-0.109,0.365-0.012l1.145,1.07c0.104,0.097,0.11,0.261,0.013,0.364l-0.368,0.395
		c-0.097,0.104-0.261,0.108-0.364,0.011l-1.145-1.069C12.917,36.985,12.912,36.821,13.009,36.718z M17.428,42.018
		c0.344,0.321,0.886,0.304,1.208-0.041l0.368-0.393c0.32-0.343,0.303-0.886-0.042-1.207l-1.145-1.07
		c-0.344-0.321-0.886-0.303-1.206,0.041l-0.368,0.394c-0.322,0.345-0.304,0.886,0.04,1.207L17.428,42.018z M16.678,40.148
		l0.368-0.395c0.097-0.104,0.261-0.109,0.364-0.012l1.146,1.07c0.104,0.097,0.109,0.262,0.013,0.364l-0.368,0.395
		c-0.097,0.104-0.261,0.108-0.365,0.012l-1.145-1.07C16.587,40.414,16.582,40.251,16.678,40.148z M21.487,42.735
		c-0.344-0.321-0.886-0.303-1.206,0.041l-0.368,0.394c-0.322,0.345-0.304,0.886,0.04,1.207l1.145,1.07
		c0.345,0.321,0.886,0.304,1.208-0.041l0.368-0.394c0.321-0.343,0.303-0.886-0.041-1.207C22.633,43.805,21.487,42.735,21.487,42.735
		z M22.239,44.606L21.871,45c-0.098,0.104-0.262,0.108-0.365,0.012l-1.145-1.07c-0.104-0.098-0.109-0.261-0.012-0.365l0.368-0.394
		c0.097-0.104,0.26-0.109,0.364-0.012l1.145,1.07C22.33,44.338,22.336,44.502,22.239,44.606z M10.857,41.693
		c0.344,0.321,0.886,0.304,1.207-0.041l0.368-0.393c0.321-0.344,0.304-0.886-0.041-1.208l-1.144-1.069
		c-0.345-0.322-0.887-0.303-1.208,0.041l-0.368,0.394c-0.321,0.344-0.303,0.885,0.041,1.207L10.857,41.693z M10.107,39.823
		l0.368-0.394c0.097-0.104,0.26-0.11,0.364-0.012l1.144,1.069c0.104,0.098,0.11,0.261,0.014,0.365l-0.368,0.394
		c-0.097,0.104-0.262,0.109-0.365,0.012l-1.145-1.069C10.015,40.09,10.01,39.927,10.107,39.823z M14.916,42.41
		c-0.344-0.321-0.886-0.302-1.206,0.041l-0.368,0.394c-0.322,0.345-0.304,0.886,0.04,1.208l1.145,1.069
		c0.345,0.322,0.886,0.305,1.208-0.04l0.368-0.395c0.321-0.343,0.303-0.885-0.041-1.207C16.062,43.48,14.916,42.41,14.916,42.41z
		 M15.668,44.281L15.3,44.675c-0.098,0.104-0.262,0.109-0.365,0.012l-1.146-1.07c-0.104-0.098-0.109-0.26-0.012-0.364l0.367-0.394
		c0.098-0.104,0.261-0.11,0.365-0.013l1.145,1.07C15.758,44.014,15.764,44.178,15.668,44.281z M18.585,45.84
		c-0.344-0.321-0.885-0.302-1.206,0.041l-0.368,0.394c-0.322,0.345-0.304,0.886,0.04,1.207l1.146,1.07
		c0.344,0.321,0.886,0.304,1.207-0.04l0.368-0.395c0.321-0.343,0.303-0.885-0.041-1.207C19.731,46.91,18.585,45.84,18.585,45.84z
		 M19.337,47.711l-0.368,0.394c-0.098,0.104-0.261,0.109-0.365,0.012l-1.146-1.07c-0.104-0.098-0.109-0.26-0.012-0.364l0.368-0.394
		c0.097-0.104,0.26-0.11,0.364-0.013l1.144,1.07C19.427,47.443,19.433,47.608,19.337,47.711z M8.345,42.087
		C8,41.765,7.458,41.783,7.137,42.127l-0.368,0.395c-0.321,0.344-0.303,0.885,0.042,1.207l1.144,1.069
		c0.345,0.321,0.886,0.304,1.207-0.04l0.368-0.394c0.322-0.345,0.304-0.887-0.04-1.208L8.345,42.087z M9.095,43.957l-0.368,0.394
		c-0.097,0.104-0.261,0.109-0.365,0.012l-1.145-1.069c-0.104-0.098-0.109-0.262-0.013-0.365l0.368-0.394
		c0.097-0.104,0.26-0.109,0.365-0.012l1.144,1.069C9.186,43.69,9.193,43.853,9.095,43.957z M12.013,45.516
		c-0.344-0.321-0.885-0.303-1.206,0.041l-0.368,0.394c-0.322,0.345-0.304,0.886,0.04,1.207l1.145,1.07
		c0.344,0.321,0.886,0.304,1.207-0.041l0.368-0.394c0.321-0.344,0.303-0.886-0.041-1.207L12.013,45.516z M12.765,47.386
		l-0.368,0.394c-0.098,0.104-0.261,0.109-0.365,0.012l-1.146-1.07c-0.104-0.097-0.109-0.26-0.012-0.364l0.368-0.394
		c0.097-0.104,0.26-0.109,0.364-0.012l1.144,1.069C12.856,47.118,12.862,47.282,12.765,47.386z M15.683,48.945
		c-0.344-0.321-0.886-0.303-1.207,0.04l-0.368,0.395c-0.321,0.345-0.304,0.886,0.04,1.207l1.146,1.07
		c0.344,0.321,0.886,0.304,1.208-0.041l0.368-0.394c0.32-0.344,0.302-0.886-0.042-1.207L15.683,48.945z M16.434,50.816l-0.368,0.394
		c-0.098,0.104-0.261,0.109-0.365,0.012l-1.145-1.07c-0.104-0.097-0.11-0.26-0.013-0.364l0.368-0.394
		c0.097-0.104,0.26-0.109,0.364-0.013l1.145,1.07C16.525,50.548,16.531,50.712,16.434,50.816z "/>
    <path class="bu-shell" style="fill:black" d="M27.084,20.485
		c-2.006-1.875-5.176-1.756-7.064,0.265L1.359,40.713c-1.89,2.021-1.795,5.192,0.211,7.067l9.658,9.028
		c2.007,1.875,5.177,1.756,7.066-0.267l18.66-19.963c1.889-2.021,1.794-5.191-0.213-7.066
		C36.741,29.512,27.084,20.485,27.084,20.485z M35.437,35.16l-18.66,19.964c-1.107,1.185-2.961,1.26-4.13,0.167l-9.658-9.028
          c-1.17-1.093-1.22-2.947-0.112-4.132l18.66-19.963c1.107-1.185,2.96-1.26,4.129-0.167l9.659,9.028 C36.494,32.122,36.545,33.976,35.437,35.16z" />
    <path class="bu-pluspad" style="fill:black;" d="M24.063,31.344
		c-0.625,0.668-0.589,1.72,0.079,2.344c0.667,0.624,1.719,0.589,2.344-0.079c0.624-0.668,0.588-1.72-0.08-2.344
		C25.739,30.641,24.687,30.676,24.063,31.344z M25.937,33.096c-0.342,0.366-0.917,0.386-1.283,0.044
		c-0.366-0.343-0.386-0.918-0.043-1.284c0.342-0.366,0.917-0.385,1.283-0.043C26.26,32.154,26.28,32.731,25.937,33.096z
		 M23.025,30.536c0.097,0.088,0.218,0.132,0.339,0.132c0.135,0,0.27-0.055,0.368-0.161c0.187-0.203,0.174-0.519-0.029-0.707
		l-3.007-2.767c-0.203-0.186-0.52-0.172-0.707,0.029c-0.187,0.203-0.174,0.52,0.029,0.707L23.025,30.536z M27.987,34.098
		c-0.203-0.185-0.52-0.172-0.707,0.029c-0.187,0.203-0.174,0.52,0.029,0.707l3.007,2.767c0.097,0.088,0.218,0.132,0.339,0.132
		c0.135,0,0.27-0.055,0.368-0.161c0.187-0.203,0.174-0.52-0.029-0.707L27.987,34.098z M27.791,30.673l2.767-3.007
		c0.187-0.203,0.174-0.519-0.029-0.707c-0.203-0.186-0.52-0.172-0.707,0.029l-2.767,3.007c-0.187,0.203-0.174,0.52,0.029,0.707
		c0.097,0.088,0.218,0.132,0.339,0.132C27.557,30.834,27.692,30.779,27.791,30.673z M22.756,34.279l-2.767,3.007
		c-0.186,0.203-0.174,0.52,0.029,0.707c0.097,0.088,0.218,0.132,0.339,0.132c0.135,0,0.27-0.055,0.368-0.161l2.767-3.007
          c0.187-0.203,0.174-0.52-0.029-0.707C23.259,34.065,22.945,34.078,22.756,34.279z" />
    <path class="bu-radar3" style="fill:transparent;" d="M27.493,0.003
		c-0.342-0.033-0.65,0.218-0.685,0.561c-0.02,0.194,0.053,0.384,0.195,0.518c0.101,0.094,0.227,0.151,0.365,0.166
		c7.444,0.738,14.276,3.837,19.757,8.96c4.84,4.523,8.222,10.304,9.781,16.716c0.028,0.119,0.091,0.226,0.181,0.31
		c0.153,0.144,0.368,0.2,0.574,0.15c0.119-0.029,0.226-0.091,0.309-0.181c0.144-0.154,0.201-0.369,0.15-0.574
          c-1.616-6.649-5.123-12.644-10.142-17.334C42.297,3.983,35.213,0.771,27.493,0.003z" />
    <path class="bu-radar2" style="fill:transparent;" d="M42.543,15.11
		c-3.871-3.618-8.663-6.01-13.859-6.915c-0.34-0.059-0.664,0.169-0.723,0.509c-0.037,0.208,0.033,0.419,0.188,0.564
		c0.089,0.083,0.199,0.138,0.318,0.159c4.957,0.863,9.529,3.146,13.222,6.597c3.429,3.204,5.921,7.268,7.208,11.752
		c0.031,0.109,0.092,0.207,0.174,0.284c0.16,0.149,0.39,0.204,0.598,0.144c0.109-0.03,0.208-0.09,0.286-0.174
		c0.151-0.162,0.205-0.386,0.145-0.599C48.749,22.729,46.135,18.468,42.543,15.11z " />
     <path class="bu-radar1" style="fill:transparent;" d="M36.503,21.572c-2.146-2.005-4.655-3.429-7.46-4.231
		c-0.161-0.046-0.33-0.026-0.476,0.056c-0.147,0.082-0.253,0.215-0.297,0.373c-0.066,0.227,0.001,0.468,0.174,0.63
		c0.071,0.066,0.159,0.116,0.253,0.143c2.614,0.748,4.953,2.074,6.952,3.943c1.582,1.479,2.851,3.211,3.769,5.149
		c0.033,0.071,0.08,0.135,0.138,0.189c0.188,0.176,0.461,0.219,0.692,0.108c0.071-0.032,0.136-0.079,0.191-0.139
           c0.176-0.189,0.219-0.461,0.107-0.694C39.562,25.021,38.201,23.16,36.503,21.572z" />
</g>
<g transform="translate(-4.6, -3.5)">
<g transform="scale(0.035,0.035)">
<path class="bu-not-present" fill="#a94442"
        d="M1440 893q0-161-87-295l-754 753q137 89 297 89 111 0 211.5-43.5t173.5-116.5 116-174.5 43-212.5zm-999 299l755-754q-135-91-300-91-148
            0-273 73t-198 199-73 274q0 162 89 299zm1223-299q0 157-61 300t-163.5 246-245 164-298.5 61-298.5-61-245-164-163.5-246-61-300 61-299.5
            163.5-245.5 245-164 298.5-61 298.5 61 245 164 163.5 245.5 61 299.5z"/>
</g>
</g>
</svg>
"""

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "remotec", subtype, did)
        self._proxies = {}  # Available proxy {"hvac": "Air Conditioner"}
        self.commands = ["send"]  # List of commands/protocols supported
        self.toggle = {"rc5": 0,"rc6": 0}

    async def handle_command_proxydevice(self, value, rt):
        """
        Remote control devices are often used to proxy commands to other devices.
        When a new device is created/detected the relevant buddy needs to be alerted
        """
        try:
            await self.controller.enqueue(
                {
                    "subject": value["device"] + ".proxy",
                    "content_type": "command",
                    "content": {
                        "command": "new proxy device",
                        "target": value["device"] + ".proxy",
                        "value": {
                            "name": value["name"],
                            "gateway": self.controller.type + "." + self.name,
                            "commands": self.commands,
                        },
                    },
                }
            )
        except Exception as e:
            _log.warning(f"Proxy agent could not be notified with {value}: Error {e}")
            await aio.sleep(0)

    async def handle_command_send(self, value, rt):
        """
        Most remote controls will send the commands they receive. The send over IR but it could also be
        zigbee or radio frequencies.

        """
        if not self.present:
            await aio.sleep(0)  # Must await something
            return None
        _log.debug(f"Sending code from {value}")
        iconsts = {
            "bu-radar1": {**{"opacity": "0.1"}, **self.icon_colour("send")},
            "bu-radar2": {**{"opacity": "0"}, **self.icon_colour("send")},
            "bu-radar3": {**{"opacity": "0"}, **self.icon_colour("send")},
            "multipart": True,
        }
        iconsts["animation"] = self.gen_anim("send")
        msg = {
            "subject": self.controller.type,
            "content_type": "event",
            "content": {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": iconsts,
                "value": {},
            },
        }
        await self.controller.enqueue(msg)
        msg = {
            "subject": value["sender"],
            "content_type": "event",
            "content": {
                "event": "code sent",
                "target": value["sender"],
                "icon status": iconsts,
                "value": {"sent": False,"sender": value["sender"], "command": value["command"]},
            },
        }
        await self.local_command_send(value, rt, msg)

    async def local_command_send(self, value, rt, msg):
        raise NotImplementedError

    async def handle_command_learn(self, value, rt):
        """
        Many remote controls can learn codes
        """
        if not self.present:
            await aio.sleep(0)  # Must await something
            return None

        iconsts = {
            "bu-radar1": {**{"opacity": "0"}, **self.icon_colour("learn")},
            "bu-radar2": {**{"opacity": "0"}, **self.icon_colour("learn")},
            "bu-radar3": {**{"opacity": "0.1"}, **self.icon_colour("learn")},
            "multipart": True,
        }
        iconsts["animation"] = self.gen_anim("learn")
        msg = {
            "subject": self.controller.type,
            "content_type": "event",
            "content": {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": iconsts,
                "value": {},
            },
        }
        await self.controller.enqueue(msg)
        msg = {
                "subject": value["sender"],
                "content_type": "command",
                "content": {
                    "command": "code learned",
                    "target": value["sender"],
                    "value": {
                        "code": False,
                        "sender": self.controller.type + "." + self.name,
                        "ctype": "ir",
                        "command": value["command"],
                    },
                },
            }
        await self.local_command_learn(value, rt, msg)

    async def local_command_learn(self, value, rt, msg):
        raise NotImplementedError

    async def handle_command_rflearn(self, value, rt):
        """
        Learning radio frequency xommands. Usually a 2 step process, lock the frequency
        then learn

        """
        if not self.present:
            await aio.sleep(0)  # Must await something
            return None
        iconsts = {
            "bu-radar1": {**{"opacity": "0.1"}, **self.icon_colour("lock")},
            "bu-radar2": {**{"opacity": "0"}, **self.icon_colour("lock")},
            "bu-radar3": {**{"opacity": "0"}, **self.icon_colour("lock")},
        }
        iconsts["animation"] = self.gen_anim("lock")
        iconsts["multipart"] = True

        self.controller.enqueue({
            "subject": self.controller.type,
            "content_type": "event",
            "content": {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": iconsts,
                "value": {},
            },
        })
        msg = {
                "subject": value["sender"],
                "content_type": "command",
                "content": {
                    "command": "code learned",
                    "target": value["sender"],
                    "value": {
                        "code": False,
                        "sender": self.controller.type + "." + self.name,
                        "ctype": "rf",
                        "command": value["command"],
                    },
                },
            }
        await self.local_command_rflearn(value, rt, msg)

    async def local_command_rflearn(self, value, msg):
        raise NotImplementedError

    async def handle_command_sendcode(self, value, rt):
        def clean_irgen(z):
            def sign(x):
                return int(x>0)
            if z[0] < 0:
                sidx = 1
            else:
                sidx = 0
            next = z[sidx]
            val = []
            for x in z[sidx+1:]:
                if sign(x) == sign(next):
                    next += x
                else:
                    val.append(next)
                    next = x
            val.append(next)
            return val
        try:
            ct = value["type"]
            val = {"sender": "Web", "command":"generic"}
            if ct != "raw":
                cv = [x.strip() for x in value["code"].split(",")]
                if len(cv) == 2:
                    dev = int(cv[0])
                    cmd = int(cv[1])
                    sdev = -1
                else:
                    dev = int(cv[0])
                    cmd = int(cv[2])
                    sdev = int(cv[1])
                toggle = 0
                if ct in self.toggle:
                    toggle = self.toggle[ct]
                    self.toggle[ct] = (self.toggle[ct] + 1 ) % 2
                val["code"] = [
                            abs(x)
                            for x in clean_irgen( [ y for  y in
                                    irgen.gen_raw_general(ct, dev, sdev, cmd, toggle=toggle) ]
                                )
                        ]
                val["timing"] = "pulses"
            else:
                val["code"]=value["code"]
                val["timing"] = "raw"

            await self.handle_command_send(val,True)
        except Exception as e:
            _log.debug(f"Could not send code: {e}")
            await self.controller.enqueue(
            {
                "subject": self.controller.type,
                "content_type": "event",
                "content": {
                    "event": "gui alert",
                    "target": self.controller.type + "." + self.name,
                    "value": f"Code {value['code'][:10]}... is not compatible with type {value['type']}",
                },
            }
        )



    def icon_colour(self, force=False):
        """
        Here force can be set to whatever is happening
        """
        if force == "send":
            return {"fill": "#3366ff"}
        elif force == "carrier":
            return {"fill": "#990099"}

        return {"fill": "#99cc00"}

    def gen_anim(self, state="send"):
        """Generate an animation for the given state
        """
        anim = ""
        cnt = "infinite"
        prefix = animname()
        if state == "send":
            cnt = "5"
            anim = ""
            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar1"
                    + " {  0% { opacity: 0.1;}  33%,100% { opacity: 1;}}"
                )

            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar2"
                    + " {  0%,33% { opacity: 0;}  100% { opacity: 1;}}"
                )

            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar3"
                    + " {  0%,66% { opacity: 0;}  100% { opacity: 1;}}"
                )

            for at in ["-bu-radar1", "-bu-radar2", "-bu-radar3"]:
                anim += (
                    "\n.run-animation-"
                    + self.name
                    + at
                    + " { animation-name: "
                    + prefix
                    + self.name
                    + at
                    + "; animation-duration: 1s; animation-iteration-count: %s; }" % cnt
                )

        elif state == "learn":
            anim = ""
            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar3"
                    + " {  0% { opacity: 0.1;}  33%,100% { opacity: 1;}}"
                )

            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar2"
                    + " {  0%,33% { opacity: 0;}  100% { opacity: 1;}}"
                )

            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar1"
                    + " {  0%,66% { opacity: 0;}  100% { opacity: 1;}}"
                )

            for at in ["-bu-radar1", "-bu-radar2", "-bu-radar3"]:
                anim += (
                    "\n.run-animation-"
                    + self.name
                    + at
                    + " { animation-name: "
                    + prefix
                    + self.name
                    + at
                    + "; animation-duration: 1s; animation-iteration-count: %s; }" % cnt
                )

        else:
            anim = ""
            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar1"
                    + " {  0% { opacity: 0;}  50%,100% { opacity: 1;}}"
                )

            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar2"
                    + " {  0% { opacity: 0;}  70%,100% { opacity: 1;}}"
                )

            for kf in KEYFLIST:
                anim += (
                    kf
                    + " "
                    + prefix
                    + self.name
                    + "-bu-radar3"
                    + " {  0% { opacity: 0;}  50%,100% { opacity: 1;}}"
                )

            for at in ["-bu-radar1", "-bu-radar2", "-bu-radar3"]:
                anim += (
                    "\n.run-animation-"
                    + self.name
                    + at
                    + " { animation-name: "
                    + prefix
                    + self.name
                    + at
                    + "; animation-duration: 1s; animation-iteration-count: %s; }" % cnt
                )

        return anim

    def xml_names(self, gen_xml=False):
        """
        Here for remote control. Highly dynamic.
        """
        result = {}
        if self._proxies:
            if gen_xml:
                pg = xml.xml_group(
                    "proxydevice",
                    label="Create a new device",
                    gtype="grouplist",
                    realtime="yes",
                )
                pe = xml.xml_entry("name", label="Name", length=64)
                pg.add_member(pe)
                pe = xml.xml_choice(
                    "device",
                    label="Device Type",
                    choices=[(x, y) for x, y in self._proxies.items()],
                )
                pg.add_member(pe)

                result["proxydevice"] = [
                    None,
                    pg.render(),
                ]  # Here onlyif is not a function/command discriminator
                # but a state conddition... hence None for unique name
            else:
                result["proxydevice"] = None
        #else:
        if "send" in self.commands or "sendrf" in self.commands:
            if gen_xml:
                pg = xml.xml_group(
                    "sendcode", label="Send Code", gtype="grouplist", realtime="yes",
                )
                codelist = [("raw","Raw (hex string)")]
                for x in irgen.gen_raw_protocols[::-1]:
                    if x.startswith("nec"):
                        codelist.append((x,x.upper()+" (dev, subdev, cmd)"))
                    else:
                        codelist.append((x,x.upper()+" (dev, cmd)"))
                pe = xml.xml_choice(
                    "type",
                    label="Code Type",
                    choices=codelist,
                )
                pg.add_member(pe)
                pe = xml.xml_entry("code", label="Code", length=1024)
                pg.add_member((pe))

                result["send"] = [
                    None,
                    pg.render(),
                ]
            else:
                result["send"] = None
        return result

    async def send_status(self):
        """
        Send the current switch status
        """
        if not self.present:
            content = {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": {
                    "bu-not-present": {"opacity": 1},
                },
                "value": {},
            }
            await self.controller.enqueue(
                {
                    "subject": self.controller.type,
                    "content_type": "event",
                    "content": content,
                }
            )
            return
        try:
            val = {}
            content = {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": {
                    "bu-fill": self.icon_colour(),
                    "bu-not-present": {"opacity": 0},
                },
                "value": val,
            }
            for x in self.xml_names().values():
                if x is not None:
                    content["value"][x] = "yes"
            await self.controller.enqueue(
                {
                    "subject": self.controller.type,
                    "content_type": "event",
                    "content": content,
                }
            )
        except Exception as e:
            _log.warning(f"Ooops could not send status {e}")
            await aio.sleep(0)


    def to_lirc(self, frames, timing):
        """Transform a list of frames (hex string)  into a LIRC compatible list of pulse timing pairs"""
        lircframe = []
        for frame in frames:
            lircframe += timing["start frame"]
            for x in [int(frame[i : i + 2], 16) for i in range(0, len(frame), 2)]:
                idx = 0x80
                while idx:
                    lircframe.append(timing["mark"])
                    if x & idx:
                        lircframe.append(timing["space 1"])
                    else:
                        lircframe.append(timing["space 0"])
                    idx >>= 1
            if "drop_bits" in timing:
                lircframe = lircframe[
                    : -2 * timing["drop_bits"]
                ]  # Each bit is a pulse and a space
            lircframe += timing["end frame"]
        return lircframe

class fridge(BuddyDevice):
    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "fridge", subtype, did)


class button(BuddyDevice):
    """
    Click, double cliclk and long click buttton.
    """

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "button", subtype, did)


class switch(BuddyDevice):
    """
    Simple on/off switch
    """

    icon = """
        <svg class="bu-device-icon" width="60" height="60" viewBox="0 0 537.63 537.63" xmlns="http://www.w3.org/2000/svg">
        <g>
            <circle class="bu-fill" cx="250" cy="144" r="127" stroke="none" fill="white" />
            <path class="bu-shape" d="M124.795,144.021c0-69.472,56.528-126.018,126.018-126.018s126.018,56.546,126.018,126.018
                c0,11.432-1.513,22.737-4.537,33.611l17.355,4.789c3.439-12.44,5.185-25.348,5.185-38.4C394.834,64.611,330.222,0,250.813,0
                S106.792,64.611,106.792,144.02c0,40.902,17.499,80.022,47.995,107.314l12.008-13.393
                C140.097,214.051,124.795,179.81,124.795,144.021z" />
            <rect class="bu-shape" x="230" y="122" width="42" height="160" fill="white" stroke="none"  />
            <rect class="bu-shape" x="284" y="212" width="42" height="62" fill="white" stroke="none"  />
            <path class="bu-shape bu-hand" d="M394.834,252.038c-0.001,0-0.001,0-0.002,0v-0.001c0-19.857-16.148-36.005-36.005-36.005
                c-7.41,0-14.302,2.25-20.032,6.101c-4.925-14.023-18.289-24.104-33.976-24.104c-6.556,0-12.701,1.769-18.001,4.841v-58.849
                c0-19.857-16.148-36.005-36.005-36.005c-19.857,0-36.005,16.148-36.005,36.005v144.926c-20.513,4.181-36.006,22.359-36.006,44.101
                c0,25.114,9.452,49.075,26.626,67.456c17.661,18.903,27.382,43.08,27.382,68.14v26.428c0,10.082,5.401,24.124,31.199,33.611
                c15.681,5.761,36.564,8.947,58.815,8.947c41.532,0,90.013-11.144,90.012-42.557v-47.167c0-12.476,1.603-25.69,4.879-40.38
                c8.695-39.155,13.124-79.355,13.124-119.483C430.839,268.186,414.691,252.038,394.834,252.038z M400.126,403.619
                c-3.565,15.986-5.293,30.46-5.293,44.286v47.167c0,13.538-32.297,24.556-72.01,24.556s-72.01-11.018-72.01-24.556v-26.428
                c0-29.633-11.45-58.203-32.243-80.454c-14.024-15.014-21.765-34.583-21.765-55.142c0-11.733,7.527-21.739,18.003-25.455v34.456
                h18.001V144.021c0-9.938,8.084-18.003,18.003-18.003c9.92,0,18.003,8.066,18.003,18.003v89.974c0,0.013-0.001,0.026-0.001,0.039
                h0.001v36.005h18.003v-36.024c0.011-9.929,8.089-17.984,18.002-17.984c9.92,0,18.003,8.066,18.003,18.003v17.964
                c0,0.013-0.001,0.026-0.001,0.039h0.001v18.002h18.001v-18.002h0.001c0-9.938,8.084-18.003,18.003-18.003
                c9.92,0,18.003,8.066,18.003,18.003v36.005h18.001V270.15c9.316,0.249,18.004,8.013,18.004,17.892
                C412.836,326.838,408.551,365.742,400.126,403.619z" fill="black" opacity="1" fill-rule="nonzero"/>
            <path class="bu-not-present" d="M268.5,270m-235,0a235,235 0 1,1 470,0a235,235 0 1,1 -470,0M90,447.63L447.63,90"
                stroke="#a94442" stroke-width="60" fill="none" opacity="1" />
        </g>
        </svg>
        """

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "switch", subtype, did)
        self._switch = "off"

    @property
    def switch(self):
        """
        Returns the swich position: on or off
        """
        return self._switch

    @switch.setter
    def switch(self, value):
        """
        Canonical setting
        """
        if value in [True, False]:
            self._switch = "on" if value else "off"
        elif value in [0, "0"]:
            self._switch = "off"
        elif isinstance(value, str) and value.lower() in ["on", "off"]:
            self._switch = value.lower()
        elif value in [1, "1"]:
            self._power = "on"
        else:
            raise Exception(f"{value} is not a correct value for switch")
        return self._switch

    async def handle_command_switch(self, value, rt):
        """
        Handling the relay
        """
        if not self.present:
            await aio.sleep(0)  # Must await something
            return None
        if self.switch != value["switch"].lower():
            msg = {
                "subject": self.controller.type + "." + self.name,
                "content_type": "event",
                "content": {
                    "event": "switch",
                    "target": self.controller.type + "." + self.name,
                    "icon status": {"bu-fill": self.icon_colour(force=value["switch"])},
                    "value": value,
                },
            }
            await self.local_command_switch(value, rt, msg=msg)
        else:
            await aio.sleep(0)

    async def local_command_switch(self, value, rt, msg=None):
        """
        In most cases, switches are passive devices, so just send the message
        """
        if msg:
            await self.controller.enqueue(msg)
        else:
            await aio.sleep(0)

    def icon_colour(self, force=False):
        """
        Here force can be set to on or off
        """
        if not force:
            force = self.switch
        if force == "on":
            return {"fill": self._icon_colour}
        else:
            return {"fill": "transparent"}

    def xml_names(self, gen_xml=False):
        """
        Here for relay  or switch
        """
        result = super().xml_names(gen_xml)
        if gen_xml:
            pg = xml.xml_group("switch", label="Switch", realtime="yes")
            pe = xml.xml_switch("switch", realtime="yes")
            pg.add_member(pe)
            result["switch"] = [None, pg.render()]
        else:
            result["switch"] = None
        return result


class relayswitch(switch, onoff):
    """
    Simple on/off switch with relay
    """

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, subtype, did)
        self._icon_follow_relay = True

    async def local_command_switch(self, value, rt, msg=None):
        """
        In most cases, switches are passive devices, so just send the message
        """
        if msg:
            if self._icon_follow_relay:
                try:
                    del msg["content"]["icon status"]
                except:
                    pass
            await self.controller.enqueue(msg)
        else:
            await aio.sleep(0)

    async def pre_local_command_power(self, value, rt, msg=None):
        if msg:
            if not self._icon_follow_relay:
                try:
                    del msg["content"]["icon status"]
                except:
                    pass
        await super().pre_local_command_power(value, rt, msg)

    def icon_colour(self, force=False):
        if not force:
            if self._icon_follow_relay:
                force = self.power
            else:
                force = self.switch
        if force == "on":
            return {"fill": self._icon_colour}
        else:
            return {"fill": "transparent"}

    async def send_status(self):
        """
        Send the current switch status
        """
        if not self.present:
            await aio.sleep(0)
            return
        try:
            val = {"power": {"power": self.power}}
            val["switch"] = {"switch": self.switch}
            content = {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": {
                    "bu-fill": self.icon_colour(),
                    "bu-not-present": {"opacity": 0},
                },
                "value": val,
            }
            for x in self.xml_names().values():
                if x is not None:
                    content["value"][x] = "yes"
            await self.controller.enqueue(
                {
                    "subject": self.controller.type,
                    "content_type": "event",
                    "content": content,
                }
            )
        except Exception as e:
            _log.warning(f"Ooops could not send status {e}")
            await aio.sleep(0)


#    def __init__(self, name, nickname, subtype, did=None):
#        super().__init__(name, nickname, "switch", subtype, did)


class drape(BuddyDevice):
    """
    Open, Stop, Close functions device

    These type of device can be proxied, so xml_names offers a set of usefull commands
    for those cases
    """

    icon = """
        <svg class="bu-device-icon" width="60" height="60" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg">
            <rect class="bu-rod" x="25" y="50" width="400px" height="25px" rx="5" ry="5" fill="black" />
            <rect class="bu-hook0" x="30" y="40" width="5px" height="45px" rx="5" ry="5" fill="black" />
            <rect class="bu-fill bu-panel0" x="25" y="85" width="15px" height="350px" rx="5" ry="5" fill="#4c0013" stroke="black" stroke-width="1px" stroke-opacity="0.5" />
            <rect class="bu-hook1" x="45" y="40" width="5px" height="45px" rx="5" ry="5" fill="black" />
            <rect class="bu-fill bu-panel1" x="40" y="85" width="15px" height="350px" rx="5" ry="5" fill="#4c0013" stroke="black" stroke-width="1px" stroke-opacity="0.5" />
            <rect class="bu-hook2" x="60" y="40" width="5px" height="45px" rx="5" ry="5" fill="black" />
            <rect class="bu-fill bu-panel2" x="55" y="85" width="15px" height="350px" rx="5" ry="5" fill="#4c0013" stroke="black" stroke-width="1px" stroke-opacity="0.5" />
            <rect class="bu-hook3" x="75" y="40" width="5px" height="45px" rx="5" ry="5" fill="black" />
            <rect class="bu-fill bu-panel3" x="70" y="85" width="15px" height="350px" rx="5" ry="5" fill="#4c0013" stroke="black" stroke-width="1px" stroke-opacity="0.5" />
            <rect class="bu-hook4" x="90" y="40" width="5px" height="45px" rx="5" ry="5" fill="black" />
            <rect class="bu-fill bu-panel4" x="85" y="85" width="15px" height="350px" rx="5" ry="5" fill="#4c0013" stroke="black" stroke-width="1px" stroke-opacity="0.5" />

            <g transform="scale(0.8,0.8)">
                <path class="bu-not-present" d="M268.5,270m-235,0a235,235 0 1,1 470,0a235,235 0 1,1 -470,0M90,447.63L447.63,90"
                    stroke="#a94442" stroke-width="60" fill="none" opacity="1" />
            </g>
        </svg>
        """

    # Here are the values for the icon animation,  order for closing. First is the hook second the panel
    icon_position = [(32, 0), (95, 65), (160, 130), (225, 195), (290, 260)]
    icon_panel_width = (15, 65)  # 65 is a delta, real is 15+65 = 80

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "drape", subtype, did)
        self._percent_close = -1
        self.commands = ["open", "close", "stop"]  # Also learn, learnrf, upload

    async def handle_command_action(self, value, rt):
        """
        This is the entry poin for open, close and stop
        """
        if value == "open":
            await self.handle_command_open(value, rt)
        elif value == "close":
            await self.handle_command_close(value, rt)
        elif value == "stop":
            await self.handle_command_stop(value, rt)
        else:
            _log.warning(f"Unknown action {value['action']} for drape")
            await aio.sleep(0)

    async def handle_command_open(self, value, rt):
        if self._percent_close > 0:
            iconsts = {"animation": self.gen_anim(self._percent_close, 0)}
            msg = {
                "subject": self.controller.type,
                "content_type": "event",
                "content": {
                    "event": "action",
                    "target": self.controller.type + "." + self.name,
                    "icon status": iconsts,
                    "value": "open",
                },
            }
            await self.local_command_open(value, rt, msg)
        else:
            await aio.sleep(0)

    async def local_command_open(self, value, rt, msg=None):
        raise NotImplementedError

    async def handle_command_close(self, value, rt):
        if self._percent_close < 100:
            iconsts = {"animation": self.gen_anim(self._percent_close, 100)}
            msg = {
                "subject": self.controller.type,
                "content_type": "event",
                "content": {
                    "event": "action",
                    "target": self.controller.type + "." + self.name,
                    "icon status": iconsts,
                    "value": "close",
                },
            }
            await self.local_command_close(value, rt, msg)
        else:
            await aio.sleep(0)

    async def local_command_close(self, value, rt, msg=None):
        raise NotImplementedError

    async def handle_command_stop(self, value, rt):
        """
        For a better handling of the icon position, overload or
        generate different animation in local_command_stop
        """
        if self._percent_close != 50:
            iconsts = {"animation": self.gen_anim(self._percent_close, 50)}
            msg = {
                "subject": self.controller.type,
                "content_type": "event",
                "content": {
                    "event": "action",
                    "target": self.controller.type + "." + self.name,
                    "icon status": iconsts,
                    "value": "close",
                },
            }
            await self.local_command_stop(value, rt, msg)
        else:
            await aio.sleep(0)

    async def local_command_stop(self, value, rt, msg=None):
        raise NotImplementedError

    def xml_names(self, gen_xml=False):
        """
        Here for remote control. Highly dynamic.
        """
        result = {}
        uname = None
        if "stop" in self.commands:
            uname = xml.XMLONLYLBL + "withstop"
            loc = ["open", "close", "stop"]
        else:
            uname = xml.XMLONLYLBL + "nostop"
            loc = ["open", "close"]

        if gen_xml:
            pg = xml.xml_group(
                "action",
                label="Operate",
                realtime="yes",
                onlyif=uname + "::yes",
                gtype="grouplist",
            )
            pe = xml.xml_choice("action", loc, realtime="yes")
            pg.add_member(pe)
            result["action"] = [uname, pg.render()]
        else:
            result["action"] = uname

        if "learn" in self.commands:
            uname = xml.XMLONLYLBL + "learn"
            if gen_xml:
                pg = xml.xml_group(
                    "learn",
                    label="Learn",
                    realtime="yes",
                    onlyif=uname + "::yes",
                    gtype="grouplist",
                )
                pe = xml.xml_choice("action", loc, realtime="yes")
                pg.add_member(pe)
                result["learn"] = [uname, pg.render()]
            else:
                result["learn"] = uname

        if "learnrf" in self.commands:
            uname = xml.XMLONLYLBL + "learnrf"
            if gen_xml:
                pg = xml.xml_group(
                    "learnrf",
                    label="Learn RF",
                    realtime="yes",
                    onlyif=uname + "::yes",
                    gtype="grouplist",
                )
                pe = xml.xml_choice("action", loc, realtime="yes")
                pg.add_member(pe)
                result["learnrf"] = [uname, pg.render()]
            else:
                result["learnrf"] = uname
        if "upload" in self.commands:
            uname = xml.XMLONLYLBL + "upload"
            if gen_xml:
                pg = xml.xml_group(
                    "upload",
                    label="Upload",
                    realtime="yes",
                    onlyif=uname + "::yes",
                    gtype="grouplist",
                )
                pe = xml.xml_choice("action")
                pg.add_member(pe)
                pe = xml.xml_choice(
                    "code type", ["Infrared", "RF/Zigbee/Z-Wave"], label="Code Type"
                )
                pg.add_member(pe)
                pe = xml.xml_entry("code", label="Code (Hexstring)")
                pg.add_member(pe)
                result["upload"] = [uname, pg.render()]
            else:
                result["upload"] = uname
        return result

    def gen_anim(self, fro=0, to=100):
        """Generate an icon animation for the given pos to the given.
            fro and to are in %
        """
        anim = ""
        prefix = animname()
        idx = 0
        for hook, panel in self.icon_position:
            hstart = int(round(hook * fro / 100.0))
            cstart = int(round(panel * fro / 100.0))
            wstart = self.icon_panel_width[0] + (
                round(self.icon_panel_width[1] * fro / 100.0)
            )
            hstop = int(round(hook * to / 100.0))
            cstop = int(round(panel * to / 100.0))
            wstop = self.icon_panel_width[0] + (
                round(self.icon_panel_width[1] * to / 100.0)
            )

            for kf in KEYFLIST:
                anim += (
                    f"{kf} {prefix}"
                    + self.name
                    + "hook"
                    + str(idx)
                    + " {  0%   {transform: translate("
                    + str(hstart)
                    + "px, 0); }"
                    + "   100%   {transform: translate("
                    + str(hstop)
                    + "px, 0); } } "
                )

            for kf in KEYFLIST:
                anim += (
                    f"{kf} {prefix}"
                    + self.name
                    + "panel"
                    + str(idx)
                    + " {  0%   {transform: translate("
                    + str(cstart)
                    + "px, 0); width: "
                    + str(wstart)
                    + "px; }"
                    + "   100%   {transform: translate("
                    + str(cstop)
                    + "px, 0); width: "
                    + str(wstop)
                    + "px; } } "
                )

            anim += (
                "\n#"
                + self.name
                + " .bu-hook"
                + str(idx)
                + " { animation: "
                + prefix
                + self.name
                + "hook"
                + str(idx)
                + " 8s"
                + "; animation-fill-mode: forwards; "
                + "  -webkit-animation: "
                + prefix
                + self.name
                + "hook"
                + str(idx)
                + " 8s"
                + "; -webkit-animation-fill-mode: forwards; } "
            )

            anim += (
                "\n#"
                + self.name
                + " .bu-panel"
                + str(idx)
                + " { animation: "
                + prefix
                + self.name
                + "panel"
                + str(idx)
                + " 8s"
                + "; animation-fill-mode: forwards; "
                + "  -webkit-animation: "
                + prefix
                + self.name
                + "panel"
                + str(idx)
                + " 8s"
                + "; -webkit-animation-fill-mode: forwards; } "
            )

            idx += 1

        return anim

    async def send_status(self):
        """
        Send the current drape status
        """
        if not self.present:
            await aio.sleep(0)
            return
        try:
            iconsts = {"animation": self.gen_anim(self._percent_close, self._percent_close)}
            iconsts["bu-not-present"] = {"opacity": 0}
            val = {"position": self._percent_close}
            content = {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": iconsts,
                "value": val,
            }
            for x in self.xml_names().values():
                if x is not None:
                    content["value"][x] = "yes"
            await self.controller.enqueue(
                {
                    "subject": self.controller.type,
                    "content_type": "event",
                    "content": content,
                }
            )
        except Exception as e:
            _log.warning(f"Ooops could not send status {e}")
            await aio.sleep(0)


class sensor(BuddyDevice):
    """
    Any kind of sensor. Data about the sensor's value should be in attributes starting with
    measurement_
    """

    def __init__(self, name, nickname, subtype, did=None):
        super().__init__(name, nickname, "sensor", subtype, did)

    async def send_status(self):
        try:
            val = {}
            # Look for all measurements and set their current value
            for meas in [a for a in dir(self) if a.startswith("measurement_")]:
                v = getattr(self, meas)
                if v is not None:
                    lbl = meas.replace("measurement_", "").replace("_", " ")
                    val[lbl] = v
            content = {
                "event": "status",
                "target": self.controller.type + "." + self.name,
                "icon status": {
                    "bu-fill": self.icon_colour(),
                    "bu-not-present": {"opacity": 0},
                },
                "value": val,
            }
            for x in self.xml_names().values():
                if x is not None:
                    content["value"][x] = "yes"
            await self.controller.enqueue(
                {
                    "subject": self.controller.type,
                    "content_type": "event",
                    "content": content,
                }
            )
        except Exception as e:
            _log.warning(f"Ooops could not send status {e}")
            await aio.sleep(0)


class BuddyProperty:
    """
    Here we define a property/command  and its associated values. The entity  indicates the
    entity  targeted

    CREATE TABLE public.property (
        id integer NOT NULL,
        entity character varying,
        name character varying(64),
        "values" character varying
    );


    ALTER TABLE public.property OWNER TO <username>;

    CREATE SEQUENCE public.property_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1;

    ALTER TABLE public.property_id_seq OWNER TO <username>;

    ALTER SEQUENCE public.property_id_seq OWNED BY public.property.id;

    ALTER TABLE ONLY public.property ALTER COLUMN id SET DEFAULT nextval('public.property_id_seq'::regclass);

    ALTER TABLE ONLY public.property
        ADD CONSTRAINT property_pkey PRIMARY KEY (id);

    """

    def __init__(self, oid, name, entity):

        self.type = "property"
        self.id = oid
        self.name = name
        self.entity = entity


class Exit(Exception):
    """
    Exception used when Exit is needed
    """

    def __init__(self, value, msg):
        self.value = value
        self.msg = msg


class BuddyBridge:
    """
    This is a bridge application. It will check for the current list  of devices.
    It will report any new device

    All Buddies do go through the following rocess
        - Initialize: Read the parameter from the command line and set things up.
            Create/Set the devices command. This is an XML desciption (generate by xml_names), attribute command_device
                         For each command defined here, the device should have a handle_command_<cmd> method (spaces replaced
                         by underbar) to actually handle it.
            Create/Set the buddy configuration. This is an XML description to set a number of values that are not specified on the command line.
                         The "update config" command is send when this must be updated. The attribute is config_buddy.
            Create/Set the buddy commands. This is a list of commands the buddy partner handles. For instance, pairing, provisioning, ...
                         The attribute is command_buddy. It is a dictionary. The key the command name, the value, a dictionary
                             module: Usually self.type
                             value: usually self.subtype
                             label: A string
                        The bridge must have a hendle_command_<cmd> to handle this

        - Start   start to communicate with the AutoBuddy controller and request info from controller
        - Configure  (in handle_response_configuration) Get needed info from ControlBuddy
        - Build  Instantiate and ready the devices.and send capabilities to controller
        - Run    Normat Processing

    """

    def __init__(self, dclass, defaults={}, descr="A Buddy Bridge"):
        """
        Create a bridge, dclass is the device class, default should contain all the parameters that can be configured from
        the command line. descr is the command line help message

        """
        # Create a bridge.
        self.dclass = dclass
        self.devices = []  # list of device known to the controller
        self.state = "init"
        self.pending = []  # list of emtities not know by the controller yet
        self.bridge_config = {}  # dictionary of option with their default value
        self.predef_command_buddy = [
            "update config"
        ]  # Command that should be handled by all partners
        self.buddy_config = (
            {}
        )  # A configuration retrieved from the Controller, and cannonized
        # can modify (Hence they have a XML definition)
        self.raw_buddy_config = (
            {}
        )  # A configuration retrieved from the Controller, these are the one the app
        # can modify (Hence they have a XML definition)
        self.pending_buddy_config = {}  # Pending save
        self.config_buddy = (
            []
        )  # list of XML entities defining the values stored in self.buddy_config
        self.config_name = "configuration"  # The name of the configurarion
        self.command_buddy = {}  # dictionary describing the bridge commands
        self.future = aio.Future()
        self.tokens = {}
        self.buddy_queue = (
            aio.Queue()
        )  # This queue used to communicate with the AutoBuddy bus
        self.reader = None
        self.writer = None
        self.buddy_read = None
        self.buddy_write = None
        self.noevent = False
        self.configure(defaults, descr)
        if self.future.done():
            raise BuddyConfigOnly

    def configure(self, defaults, descr):
        """
        First phase:

         Read  the line parameters and  prepare everything.

        This function MUST set at least 2 key in the self.bridge_config dictionary
            server    The messaging server to connect to
                      Format should be <credentials>@<host>:<port>
            subject   The topic and subject we are listening to

        This should be overloaded (with a stating super().configure camm) if you need
        to add module configuration options
        """
        # Now process the
        parser = self.lp_prepare(descr, default=defaults)
        self.lp_process(parser, defaults)

    def build_devices_commands(self):
        """
        Build commands for the devices. By default, just the default for the given device class
        This should be overloaded by the subclassing entity
        """
        mydev = self.dclass(
            "a", "b"
        )  # Only name and nickname are needed by higher level classes
        xx = mydev.xml_names(gen_xml=True)
        result = f"""
        <buddyui version="0.1">
            <command  name="{self.subtype}">
         """
        for xmlt in xx.values():
            result += xmlt[1] + "\n"
        result += """
            </command>
        </buddyui>
        """
        return result

    def build_buddy_commands(self):
        """
        Not doing anything by default.

        The commands are stored in the dictionary
            self.command_buddy

        The format is simple. the key is the command name, the value is a
        dictionary with
            "module":  usualy self.bridge_config["type"],
            "value": usually self.bridge_config["subtype"],
            "label": something like f"My command for {self.bridge_config["subtype"]"

        Should be overloaded if needed
        """
        pass

    def build_buddy_config(self):
        """
        Not doing anything by default
        """
        dosend = False
        result = f"""
        <buddyui version="0.1">
            <configuration  name="{self.subtype}">
         """
        for xmle in self.config_buddy:
            dosend = True
            result += xmle.render() + "\n"
        result += """
            </configuration>
        </buddyui>
        """
        if dosend:
            return result
        else:
            return ""

    async def start(self, value=None):
        """
        We start the client on the Buddy Bus. Authenticate and request
        the save configuration. If needs be, we can send extra info when asking for
        config, the value shall be a dictionary, the 2 keys known are 'about', for info to show in the
        about section of the GUI, and display, for the svg icon to use.
        """
        if self.bridge_config["ssl"]:
            sslcontext = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=self.bridge_config["ssl"] + "/" + CERTFILE,
            )
            sslcontext.check_hostname = False
        else:
            sslcontext = None
        self.reader, self.writer = await aio.open_connection(
            self.bridge_config["host"], self.bridge_config["port"], ssl=sslcontext
        )
        self.buddy_write = aio.create_task(self.write_task())
        self.buddy_read = aio.create_task(self.read_task())
        await self.enqueue(
            {
                "subject": "control",
                "content": {
                    "credential": self.bridge_config["credential"],
                    "subject": self.type,
                },
                "content_type": "authenticate",
            }
        )

        if value:
            if "config name" not in value:
                value["config name"] = self.config_name
            await self.enqueue(
                {
                    "subject": "control" + "." + self.type,
                    "content_type": "request",
                    "content": {
                        "request": "configuration",
                        "target": self.target,
                        "value": value,
                        # "credential": self.bridge_config["credential"],
                    },
                }
            )
        else:
            await self.enqueue(
                {
                    "subject": "control" + "." + self.type,
                    "content_type": "request",
                    "content": {
                        "request": "configuration",
                        "target": self.target,
                        # "credential": self.bridge_config["credential"],
                    },
                }
            )

    async def write_task(self):
        """
        Here we perform the actual sending
        """
        while True:
            try:
                msg = await self.buddy_queue.get()
                if self.future.done():
                    return
                self.writer.write(msg.encode())
                await self.writer.drain()
            except Exception as e:
                _log.debug(f"Got write exception: {e}")
                if not self.future.done():
                    self.last_rites()
                return

    async def read_task(self):
        """
        Here we perform the actual reading
        """
        partialdata = ""
        while True:
            try:
                data = await self.reader.read(2048)
                if data:
                    #_log.debug(f"\n\nGot {data}")
                    # All messages are dictionaries... so we can parse the JSON to seperate multiple objects
                    mydata = partialdata + data.decode()
                    partialdata = ""
                    lvl = 0
                    pdata = ""
                    for x in mydata:
                        if x == "{":
                            lvl += 1
                        elif x == "}":
                            lvl -= 1
                        pdata += x
                        if lvl == 0:
                            msg = json.loads(pdata)
                            aio.create_task(self.process_message(msg))
                            pdata = ""
                    if pdata:
                        if _log:
                            _log.warning("Partially received")
                        partialdata = pdata
                else:
                    _log.debug("Got empty data")
                    if not self.future.done():
                        self.last_rites()
                    return
            except aio.CancelledError:
                _log.debug("Read is being cancelled.")
            except Exception as e:
                _log.debug(f"Got reading exception {e}")
            if self.future.done():
                return

    async def process_message(self, msg):
        try:
            # _log.debug("Got %r" % msg)
            if (
                msg["content_type"] == "response"
                and msg["content"]["token"] in self.tokens
                and msg["content"]["response"]
                == self.tokens[msg["content"]["token"]][0]
            ):
                del self.tokens[msg["content"]["token"]]
                await self.process_response(msg["subject"], msg["content"])
            elif self.state != "init":
                if msg["content_type"] == "command":
                    await self.process_command(
                        msg["subject"], canon_value(msg["content"]), msg["content"]
                    )
                elif msg["content_type"] == "event":
                    await self.process_event(msg["subject"], msg["content"])
                elif msg["content_type"] == "request":
                    await self.process_request(msg["subject"], msg["content"])
                else:
                    _log.debug("other %r" % msg)
                    await aio.sleep(0)
            else:
                _log.debug(f"Got {msg} when not initialized")
                await aio.sleep(0)

            if randint(1, 200) == 69:  # from time to time
                # clean
                comp = dt.datetime.now() - dt.timedelta(minutes=1)
                for x in self.tokens.keys():
                    if self.tokens[x][1] < comp:
                        _log.warning(
                            f"Token {x} for {self.tokens[x][0]} was not answered."
                        )
                        del self.tokens[x]

        except Exit as e:
            raise e
        except Exception as e:
            _log.critical(
                "Message problem for {}\n".format(msg),
                exc_info=(type(e), e, e.__traceback__),
            )

    async def process_command(self, subject, msg, rawmsg):
        """
        By default, for a bridge,  commands are just forwarded to the devices
        """
        if msg["command"] in self.predef_command_buddy + list(
            self.command_buddy.keys()
        ):
            if subject == self.target:
                _log.debug(f"Got command {subject} {msg}")
                try:
                    cmd = msg["command"].replace(" ", "_")
                    if cmd == "update_config":
                        res = getattr(self, f"handle_command_{cmd}")(rawmsg)
                    else:
                        res = getattr(self, f"handle_command_{cmd}")(msg)
                    if aio.iscoroutine(res):
                        await res
                    else:
                        await aio.sleep(0)
                except Exception as e:
                    _log.warning(
                        f"Buddy {self.subtype} cannot handle command for {subject}: {cmd}"
                    )
                    _log.debug(f"Exception was {e}")
                    await aio.sleep(0)
            else:
                await aio.sleep(0)
        else:
            await aio.gather(
                *[adev._process_command(subject, msg) for adev in self.devices],
                return_exceptions=True,
            )

    async def process_response(self, subject, msg):

        _log.debug(f"Got response {subject} {msg}")
        try:
            cmd = msg["response"].replace(" ", "_")
            m = getattr(self, f"handle_response_{cmd}", None)
            if m:
                res = m(msg)
                if aio.iscoroutine(res):
                    return await res
                else:
                    await aio.sleep(0)
            else:
                await aio.gather(
                    *[adev._process_response(subject, msg) for adev in self.devices],
                    return_exceptions=True,
                )
        except Exception as e:
            _log.warning(
                f"Buddy {self.subtype} cannot handle response from message {cmd}"
            )
            _log.debug(f"Exception was {e}")
            _log.exception(e)
            await aio.sleep(0)

    async def process_request(self, subject, msg):
        """
        By default just do nothing
        """
        _log.debug(f"request {subject} {msg}")
        await aio.sleep(0)

    async def process_event(self, subject, msg):
        """
        By default just do nothing
        """
        #        if "target" in msg and self.subtype in msg["target"]:
        #            _log.debug(f"event {subject} {msg}")
        _log.debug(f"Got event {subject} {msg}")
        try:
            cmd = msg["event"].replace(" ", "_")
            m = getattr(self, f"handle_event_{cmd}", None)
            if m:
                res = m(msg)
                if aio.iscoroutine(res):
                    return await res
                else:
                    await aio.sleep(0)
            else:
                await aio.sleep(0)
        except Exception as e:
            _log.warning(
                f"Buddy {self.subtype} cannot handle response from message {cmd}"
            )
            _log.debug(f"Exception was {e}")
            _log.exception(e)
            await aio.sleep(0)

    async def handle_command_update_config(self, msg):
        # Command from GUI
        app_config = copy(
            self.raw_buddy_config
        )  # This is a configuration, shallow copies shall suffice
        for k, v in msg["value"].items():
            app_config[k] = v
        self.pending_buddy_config = app_config
        await self.enqueue(
            {
                "subject": "control" + "." + self.subtype,
                "content_type": "request",
                "content": {
                    "request": "save configuration",
                    "target": self.type,
                    "config name": self.config_name,
                    "value": encrypt(app_config, self.bridge_config["buddykey"]),
                },
            }
        )

    async def handle_response_save_configuration(self, msg):

        if self.state == "active" and msg["status"] != "done":
            # log
            _log.warning("Warning: Configuration was not saved.")
            self.pending_buddy_config = {}
            await aio.sleep(0)
        elif self.state == "wait config save":
            if msg["status"] != "done":
                _log.error("Error: Configuration was not saved")
            self.future.set(True)
            await aio.sleep(0)
        else:
            self.raw_buddy_config = self.pending_buddy_config
            self.buddy_config = canon_value(self.raw_buddy_config)
            self.pending_buddy_config = {}
            await self.enqueue(
                {
                    "subject": "control" + "." + self.target,
                    "content_type": "request",
                    "content": {
                        "request": "functions",
                        "target": self.type,
                        "subtype": self.subtype,
                        # "token": self.target,
                        "value": {
                            "configs": [
                                self.build_buddy_config(),
                                self.raw_buddy_config,
                            ]
                        },
                    },
                }
            )
            await self.enqueue(
                {
                    "subject": self.bridge_config["restricted"],
                    "content_type": "restricted event",
                    "content": {
                        "event": "config updated",
                        "target": self.target,
                        "value": self.raw_buddy_config,
                    },
                }
            )
        self.local_response_save_configuration(msg)

    async def handle_response_configuration(self, msg):
        try:
            storedconfig = decrypt(msg["configuration"], self.bridge_config["buddykey"])
            _log.debug(f"The config stored is {storedconfig}")
        except:
            storedconfig = {}
            if msg["configuration"]:
                _log.warning("Config is mangled")

        for x in storedconfig:
            self.raw_buddy_config[x] = storedconfig[x]
        self.buddy_config = canon_value(self.raw_buddy_config)
        if self.noevent:
            await self.enqueue(
                {
                    "subject": "control",
                    "content": {"subject": self.type},
                    "content_type": "mute events",
                }
            )
        self.state = "active"
        if msg["devices"]:
            self.build(json.loads(msg["devices"]))
        value = {}
        # Do we have fdevices' commands?
        devcmds = self.build_devices_commands()
        if devcmds:
            value["functions"] = devcmds
        if self.command_buddy:
            value["module commands"] = self.command_buddy
        if self.config_buddy:
            value["configs"] = [self.build_buddy_config(), self.raw_buddy_config]

        await self.enqueue(
            {
                "subject": "control" + "." + self.target,
                "content_type": "request",
                "content": {
                    "request": "functions",
                    "target": self.type,
                    "subtype": self.subtype,
                    # "token": self.target,
                    "value": value,
                },
            }
        )
        await self.enqueue(
            {
                "subject": self.bridge_config["restricted"],
                "content_type": "restricted event",
                "content": {
                    "event": "config updated",
                    "target": self.target,
                    "value": self.raw_buddy_config,
                },
            }
        )
        self.local_response_configuration(msg)

    async def handle_event_gui_refresh(self, msg):
        for dev in self.devices:
            await dev.send_status()


    def local_response_configuration(self, msg):
        """
        Overload to perform needed configurations updates
        """
        pass

    def local_response_save_configuration(self, msg):
        """
        Overload to perform needed configurations updates
        """
        pass

    async def handle_response_creation(self, msg):
        if msg["status"] == "done":
            bidx = 0
            thisdev = msg["value"]
            for b in self.pending:
                if b.name == thisdev["name"]:
                    b.update(thisdev)
                    self.devices.append(b)
                    self.pending = self.pending[:bidx] + self.pending[bidx + 1 :]
                    await self.enqueue(
                        {
                            "subject": self.type,
                            "content_type": "event",
                            "content": {
                                "event": "new device",
                                "target": self.type + "." + b.name,
                                "value": {
                                    "type": self.type,
                                    "subtype": self.subtype,
                                    "name": b.name,
                                    "nickname": b.nickname,
                                },
                            },
                        }
                    )
                    b.present = True
                    break
                bidx += 1
        else:
            thisdev = msg["value"]
            bidx = 0
            for b in self.pending:
                if b.name == thisdev:
                    self.pending = self.pending[:bidx] + self.pending[bidx + 1 :]
                    break
                bidx += 1
            await aio.sleep(0)

    async def handle_response_functions(self, msg):
        """
        No reason to fail
        """
        if msg["status"] == "failed":
            _log.debug("functions failed! What am I to do?")

    async def enqueue(self, msg):
        if msg["content_type"] == "request":
            if not ("token" in msg["content"] and msg["content"]["token"]):
                nt = genid()
                msg["content"]["token"] = nt
            self.tokens[msg["content"]["token"]] = (
                msg["content"]["request"],
                dt.datetime.now(),
            )
        _log.debug("Sending {}".format(msg))
        await self.buddy_queue.put(json.dumps(msg))

    def build(self, lodev):
        alldevs = self.dclass.from_list(lodev)
        for dev in alldevs:
            self.register(dev)
            dev.present = False

    @property
    def type(self):
        return self.bridge_config["type"]

    @property
    def subtype(self):
        return self.bridge_config["subtype"]

    @property
    def target(self):
        # When destined to me
        return self.type + "." + self.subtype

    # Manage devices

    def register(self, dev):
        dev.controller = self
        self.devices.append(dev)
        try:
            self.pending.remove(dev)
        except:
            pass

    def unregister(self, dev):
        try:
            self.devices.remove(dev)
        except:
            pass

    def last_rites(self):
        self.future.set_result(True)
        self.buddy_queue.put_nowait("Die")  # Sending anything would do here
        self.buddy_read.cancel()

    def lp_prepare(self, desc, parser=None, default={}):
        """This is the first one so no super()

        Whenever overloading this,  set your own dftls for those elements
        that need to be set and saved

        Set things in default to your own defaults (e.g. type and subtype

        """
        dflts = {
            "type": "generic",
            "subtype": "device",
            "host": "",
            "port": 8745,
            "credential": "",
            "ssl": "",
            "restricted": "guibridge",
        }
        for k, v in dflts.items():
            if k not in default:
                default[k] = v
        if parser is None:
            parser = argparse.ArgumentParser(description=desc)
        # version="%prog " + __version__ + "/" + bl.__version__)
        parser.add_argument(
            "-t",
            "--type",
            default=default["type"],
            help='The type we are listening to (default "%s").' % default["type"],
        )
        parser.add_argument(
            "-s",
            "--subtype",
            default=default["subtype"],
            help='The specific subtype we manage. (default  "%s").'
            % default["subtype"],
        )

        parser.add_argument(
            "-V",
            "--credential",
            default=default["credential"],
            help='The credential used to verify authorization (default "%s").'
            % default["credential"],
        )
        parser.add_argument(
            "-a",
            "--host",
            default=default["host"],
            help='The host address used by the server (default "%s").'
            % default["host"],
        )
        parser.add_argument(
            "-p",
            "--port",
            type=int,
            default=default["port"],
            help='The port used by the server (default "%s").' % default["port"],
        )
        parser.add_argument(
            "-c",
            "--config",
            type=argparse.FileType("r"),
            default=f"/etc/autobuddy/{default['type']}_config.cfg",
            help=f"Config file to use (default ''/etc/autobuddy/{default['type']}_config.cfg'')",
        )
        parser.add_argument(
            "-r",
            "--restricted",
            default=default["restricted"],
            help='Where to send "restricted events" (default "%s").'
            % default["restricted"],
        )
        parser.add_argument(
            "-S",
            "--ssl",
            default="",
            help="The directory where the file %s can be found." % (CERTFILE),
        )
        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            default=False,
            help="Log debug information (default False)",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            default=False,
            help="Log warning messages",
        )
        parser.add_argument(
            "-C",
            "--configonly",
            default="",
            help="Exit after the the configuration has been saved",
        )
        return parser

    def lp_process(self, parser, default):
        """
        Processing the line parameters.

        Only the parameters that appear in the default dictionary will be process here, plus debug, verbose and configonly.
        For others, use extra

        In most case there is no need to overload this
        """
        try:
            opts = parser.parse_args()
        except Exception as e:
            print("Error: ", e)
            parser.print_help()
            self.future.set_result(True)  # We are done
            return
        if opts.debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(levelname)7s: %(message)s",
                stream=sys.stderr,
            )
        elif opts.verbose:
            logging.basicConfig(
                level=logging.WARNING,
                format="%(levelname)7s: %(message)s",
                stream=sys.stderr,
            )
        else:
            logging.basicConfig(
                level=logging.CRITICAL,
                format="%(levelname)7s: %(message)s",
                stream=sys.stderr,
            )
        buddycfg = {}
        try:
            storedcfg = json.load(opts.config)
            opts.config.close()
        except:
            storedcfg = {}
            _log.warning("Config file could not be opened.")
        # Definition
        for attr in default:
            if getattr(opts, attr) != default[attr]:
                buddycfg[attr] = getattr(opts, attr)
            elif attr in storedcfg:
                buddycfg[attr] = storedcfg[attr]
            else:
                buddycfg[attr] = getattr(opts, attr)
            _log.debug("The %s is %s." % (attr, buddycfg[attr]))

        if buddycfg["ssl"] and not (os.path.isfile(buddycfg["ssl"] + "/" + CERTFILE)):
            _log.critical(
                "Encryption: Could not find {} .".format(
                    buddycfg["ssl"] + "/" + CERTFILE
                )
            )
            sys.exit()

        if buddycfg["ssl"]:
            _log.debug("The ssl certificates can be found in %s" % buddycfg["ssl"])
        else:
            _log.debug("The connection is not encrypted")

        if "buddykey" in storedcfg:
            buddycfg["buddykey"] = storedcfg["buddykey"]

        # Now extra
        try:
            self.lp_process_extra(opts, default, buddycfg)
        except Exception as e:
             _log.critical(e)
             sys.exit()

        if opts.configonly:
            if "buddykey" not in buddycfg:
                _log.debug("Generating random key")
                buddycfg["buddykey"] = keygen()

            with open(opts.configonly, "w") as cfile:
                json.dump(buddycfg, cfile)
            os.chmod(opts.configonly, 384)  # 0600
            self.future.set_result(True)  # We are done
        else:
            for k, v in buddycfg.items():
                self.bridge_config[k] = v

    def lp_process_extra(self, opts, default, cfg):
        """
        If some extra processing is needed one can use extra, a callable with signature
                def f(opts,default, currentcfg)
                    opts is the parsed parameters
                    default is the default values dictionary
                    cfg is the current state of the config

        It will be called before processing  of the "configonly" option""
        """

        pass

class BuddyService(BuddyBridge):
    """
    A service. No device associated
    """


    def __init__(self, defaults={}, descr="A Buddy Service"):
        """
        Create a bridge, dclass is the device class, default should contain all the parameters that can be configured from
        the command line. descr is the command line help message

        """
        super().__init__(None,defaults,descr)


    def build_devices_commands(self):
        return ""

    def build(self, lodev):
        pass
