#!/usr/bin/env python3
# -*- coding:utf-8 -*-
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
#
import optparse, sys, traceback,base64
import asyncio as aio
import datetime as dt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine, and_,ForeignKeyConstraint
from sqlalchemy.orm import sessionmaker,relationship,backref
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, VARCHAR
from uuid import uuid4
from random import randint

import json,functools
from Crypto.Cipher import  AES

__version__="0.10"   #Major change. Get rid of AMQP, use asyncio with python >=3.5

def encrypt (val,key):
    x=json.dumps(val)
    codec=AES.new(key)
    return base64.b64encode(codec.encrypt(x+(16-len(x)%16)*"\x00")).decode()


def decrypt(val,key):
    x=base64.b64decode(val.encode())
    codec=AES.new(key)
    x=codec.decrypt(x).decode().strip("\x00")
    return json.loads(x)


def keygen():
    from random import shuffle,randrange
    lolet=list("0123456789aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ`~!@#$%^&*()_+-|\[{]}?/.,<:;")
    for i in range(5):
        shuffle(lolet)
    lolet *= 1000
    for i in range(20):
        shuffle(lolet)
    startidx=randrange(len(lolet)-32)
    return "".join(lolet[startidx:startidx+32])

def genid():
    return str(uuid4())

def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]
    return memoizer


#Lifted from manual
class JSONEncodedDict(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

#Lifted from manual
class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()


class BEntity(object):
    """
    This object defines a number of behaviour common to all
    connected devices
    """

    def __init__(self,type=None):
        """
        Creating a Buddy entity is simply definig its type
        """
        self.type=type
        super().__init__()

    def of_interest(self,subject):
        """
        This method check whether a given address is
        of interest to the entity
        """
        #TODO  change to a regex... Now light.Home and light.Home Theatre  would both match on Home zone
        myinterest="%s.%s"%(self.type,self.name)
        split=subject.split(".")
        if split[0] == self.type and ( split[1] in ["*","#"] or split[1] == self.name):
            return True
        return False

    def process(self,msg):
        """
        generic processing
        """

        if self.of_interest(msg["subject"]):
            return self._process(msg)
        return None

    def set_process(self,func):
        self._process=func

    def _process(self,msg):
        """
        Needs to be overloaded. Actual processing
        returns None or a list of dictionary
        [{"subject":"subject.subject","data":<data to be sent>}]
        """
        raise NotImplementedError()


Base= declarative_base()

class Zone(Base,BEntity):
    """
    The automation system groups  entity by zone.Commands can be
    applied to the devices in the zone.

    Zone can contain sub-zone
    """

    __tablename__ = "zone"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    nickname =  Column(String(64))
    parent_id = Column(Integer, ForeignKey('zone.id'),nullable=True)

    sub_zone = relationship("Zone", backref = backref("parent",remote_side=[id]),
            cascade = "all,delete,delete-orphan")

    def __repr__(self):
        return  "Zone "+self.name



    def allNames(self):
        result=[self.name]
        for x in self.sub_zone:
            result += x.allNames()
        return result

    def allDevices(self):
        result=[]
        for device in self.devices:
            result.append(device)
        for x in self.sub_zone:
            result += x.allDevices()
        return result

    def toDict(self):
        resu={"name":self.name,"nickname": self.nickname, "devices":{},"sub_zone":[]}
        for adevice in self.devices:
            if adevice.type not in resu["devices"]:
                resu["devices"][adevice.type]=[]
            resu["devices"][adevice.type].append(
                {"name":adevice.name,"nickname":adevice.nickname,
                   "subtype":adevice.subtype})
        for szone in self.sub_zone:
            resu["sub_zone"].append(szone.toDict())
        return resu

    type="zone"

class BuddyFunction(Base):
    """
    Here we define the list of functions associated with a type/subtype pair
    """

    __tablename__ = "function"

    type = Column(String(16), primary_key=True)
    subtype = Column(String(16), primary_key=True)
    functions = Column(Text)


class BuddyDevice(Base,BEntity):
    """
        Buddy devices have a name, a type, possibly a location and a list of
        functions. The list of fuctions is a dictionary of dictionaries.
            The key is the name of the function e.g. Volume, Switch, Brightness,...
            The  sub-dictionaries' keys are "type' and 'value' and optionaly 'display'
            The optional 'display' is to indicate a prefered widget for the display of the control.
            It can be used by the GUI, if it make sense to it.
            The various types and their associated value are
                trigger: The name of the trigger. This triggers and action. The name
                        must make sense to the received entity
                switch: A list with the name of values. E.g.
                        { 'type':'switch','value': ["on","off"], 'display': 'toggle' }
                        { 'type':'switch', 'value': ["music","movie","concert"]
                    Only one value can be selected in a switch

                range : A dictionary with key a name and value doubles, or triples with the
                        start,end and optional increment of range. E.g.
                        { 'type':'range', 'value': {'volume':(0,100)}
                        { 'type':'range', 'value': {'red':(0,255,5),'green':(0,255), 'blue': (0,255)}
                        if the increment is not specified, its value is 1
                select : A list of values of which one or many can be selected. E.g.
                        { 'type':'select', ['action','horror','comedy']|

                set     : set a free form string value
    """
    __tablename__ = "device"
    id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True)
    nickname = Column(String(64))
    type = Column(String(16))
    subtype = Column(String(16))
    location_id = Column(Integer, ForeignKey('zone.id'),nullable=True)
    location = relationship("Zone", backref = backref("devices"))
    functions = relationship("BuddyFunction",
                            primaryjoin="and_(BuddyDevice.type==BuddyFunction.type, "
                                    "BuddyDevice.subtype==BuddyFunction.subtype)",
                            backref = backref("devices"))
    __table_args__ = (
        ForeignKeyConstraint(
            ['type', 'subtype'],
            ['function.type', 'function.subtype']
        ),)
    __mapper_args__ = {'polymorphic_on': type}


class light(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'light'}

class mediaplayer(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'mediaplayer'}

class video(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'video'}

class voice(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'voice'}

class aircon(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'aircon'}

class remotec(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'remotec'}

class fridge(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'fridge'}

class switch(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'switch'}

class drape(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'drape'}

class sensor(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'sensor'}



class BuddyProperty(Base):
    """
    Here we define a property/command  and its associated values. The entity  indicates the
    entity  targetted
    """

    __tablename__ = "property"

    id = Column(Integer, primary_key=True)
    entity = Column(String)
    name = Column(String(64))
    values = Column(String)


class Exit(Exception):
    """
    Exception used when Exit is needed
    """
    def __init__(self, value, msg):
        self.value = value
        self.msg = msg


class BuddyBridge(aio.Protocol):
    """
    This is a bridge application. It will check for the current list  of devices.
    It will report any new device
    """
    def __init__(self,loop,future,config,log):
        #Create a bridge. config MUST contain a type,subtype and credential keys
        super().__init__()
        self.config = config
        self.devices = []    # list of device known to the controller
        self.state = "init"
        self.pending = []     # list of emtities not know by the controller yet
        self.default = {}     # dictionary of command line option that should be persisted with their default value
        self.future=future
        self.loop=loop
        self.log=log
        self.partialdata=""
        self.tokens={}

    def configure(self):
        """
        This function MUST set at leat 3 key in the self.config dictionary
            server    The messaging server to connect to
                      Format should be <credentials>@<host>:<port>
            subject   The topic and subject we are listening to
        """
        raise NotImplementedError()


    def connection_made(self,transport):
        self.transport=transport
        self.sending({"subject":"control","content": {"credential":self.config["credential"],"subject":self.type},"content_type":"authenticate"})

    def data_received(self,data):
        if data:
            #All messages are dictionaries... so we can parse the JSON to seperate multiple objects
            mydata=self.partialdata+data.decode()
            self.partialdata=""
            lvl=0
            pdata=""
            for x in mydata:
                if x == "{":
                    lvl+=1
                elif x == "}":
                    lvl-=1
                pdata+=x
                if lvl==0:
                    msg=json.loads(pdata)
                    self.MsgProcess(msg)
                    pdata=""

            if pdata:
                if self.log:
                    self.log.warning ("Partially received")
                self.partialdata=pdata

    def connection_lost(self,error):
        if self.log:
            self.log.debug ("Connection to server lost")
        self.transport.close()
        if not self.future.done():
            self.future.set_result(True)
        super().connection_lost(error)


    def disconnect(self):
        self.transport.close()
        if not self.f.done():
            self.f.set_result(True)

    def configrequest(self,value=None):
        if value:
            self.sending({"subject":"control"+"."+self.type,
                        "content_type": "request",
                        "content":{"request":"configuration",
                                    #"token": self.target,
                                    "target":self.target,
                                    "value":value,
                                    "credential":self.config["credential"]}})
        else:
            self.sending({"subject":"control"+"."+self.type,
                        "content_type": "request",
                        "content":{"request":"configuration",
                                    #"token": self.target,
                                    "target":self.target,
                                    "credential":self.config["credential"]}})


    def MsgProcess(self,msg):
        try:
            if self.log:
                self.log.debug("Got %r" % msg)
            if msg["content_type"] == "command":
                self.process_command(msg)
            elif msg["content_type"] == "event":
                self.process_event(msg)
            elif msg["content_type"] == "request":
                self.process_request(msg)
            elif msg["content_type"] == "response" and msg["content"]["token"] in self.tokens :
                del(self.tokens[msg["content"]["token"]])
                self.process_response(msg)
            else:
                if self.log:
                    self.log.debug("other %r"%msg)

            if randint(1,200)==69: #from time to time
                #clean
                comp=dt.datetime.now()-dt.timedelta(minutes=1)
                lot=self.tokens.keys()
                for x in [y for y in lot]:
                    if self.tokens[x]<comp:
                        del(self.tokens[x])

        except Exit as e:
            raise e
        except Exception as e:
            if self.log:
                self.log.critical("Message problem for {}\n".format(msg),exc_info=(type(e), e, e.__traceback__))
            else:
                print("Warning: Message problem for {}:\n{}".format(msg,e.__traceback__))


    def process_command(self,msg):
        """
        By default, for a bridge,  commands are just forwarded to the devices
        """
        for aconn in self.devices:
            aconn.process(msg)

    def process_response(self,msg):
        raise NotImplementedError()

    def process_request(self,msg):
        """
        By default just do nothing
        """
        if self.log:
            self.log.debug("request {}".format(msg["content"]))

    def process_event(self,msg):
        """
        By default just do nothing
        """
        if self.log:
            self.log.debug("event {}".format(msg["content"]))

    def sending(self,msg):
        if msg["content_type"]=="request":
            if not ("token" in msg["content"] and msg["content"]["token"]):
                nt=genid()
                msg["content"]["token"]=nt
            self.tokens[msg["content"]["token"]]=dt.datetime.now()
        if self.log:
            self.log.debug("Sending {}".format(msg))
        jmsg = json.dumps(msg)
        self.transport.write(jmsg.encode())


    def build(self):
        raise NotImplementedError()

    @property
    def type(self):
        return self.config["type"]

    @property
    def subtype(self):
        return self.config["subtype"]

    @property
    def target(self):
        #When destined to me
        return self.type + "." + self.subtype

    # Manage devices

    def register(self,dev):
        self.devices.append(dev)

    def unregister(self,dev):
        try:
            self.devices.remove(dev)
        except:
            pass




def getSession(db):
    """
    db = postgresql://autobuddy:76Bon19@lima.fwconsult.com/autobuddy'
    """
    engine = create_engine(db)
    mysess=sessionmaker(bind=engine)()
    mysess.Engines=[engine]
    return mysess

def initialize(sess):
    Base.metadata.create_all(sess.Engines[0])
