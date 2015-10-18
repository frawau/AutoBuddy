#!/usr/bin/env python
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
import optparse, sys, traceback
import qpid.messaging as qm
from qpid.log import enable, DEBUG, WARN
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine, and_,ForeignKeyConstraint
from sqlalchemy.orm import sessionmaker,relationship,backref
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, VARCHAR
from uuid import uuid4

import json,functools
from Crypto.Cipher import  AES

__version__="0.1"

def encrypt (val,key):
    x=json.dumps(val)
    codec=AES.new(key)
    return codec.encrypt(x+(16-len(x)%16)*"\x00").encode("base64")


def decrypt(val,key):
    x=val.decode("base64")
    codec=AES.new(key)
    x=codec.decrypt(x).strip("\x00")
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


def iprint(*arg):
    """
        Just here to make it easy when changing to python 3
    """
    for x in arg:
        print x,
    print      

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
        

class AMQPEntity(object):
    """
    This object defines a number beaviour common to all
    connected devices
    """

    def __init__(self,topic=None,subject=None):
        """
        Creating a AMQP entity is simply definig its topic and subject
        """
        self.topic=topic
        self.subject=subject
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
        
        if self.of_interest(msg.subject):
            return self._process(msg)
        return None
    
    def set_process(self,func):
        self._process=func
    
    def _process(self,msg):
        """
        Needs to be overloaded. Actual processing
        returns None or a list of dictionary
        [{"address":"topic/subject.subject","data":<data to be sent>}] or 
        [{"subject":"subject.subject","data":<data to be sent>}]
        """
        raise NotImplementedError()
        

Base= declarative_base()

class Zone(Base,AMQPEntity):
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
    
    
class BuddyDevice(Base,AMQPEntity):
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
    __mapper_args__ = {'polymorphic_identity': 'av'}

class television(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'tv'}
    
class voice(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'voice'}

class thermostat(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'ac'}
    
class remotec(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'rc'}
    
class fridge(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'fridge'}
    
class switch(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'switch'}
    
class drape(BuddyDevice):
    __mapper_args__ = {'polymorphic_identity': 'flic'}
    


class BuddyProperty(Base):
    """
    Here we define a property/command  and its associated values. The entity  indicates the 
    entity  targetted
    """
    
    __tablename__ = "property"
    
    id = Column(Integer, primary_key=True)
    entity = Column(String)
    name = Column(String(16))
    values = Column(String)


class Exit(Exception):
    """
    Exception used when Exit is needed
    """
    def __init__(self, value, msg):
        self.value = value
        self.msg=msg

class BuddyBridge(object):
    """
    This is a bridge application. It will check for the current list  of devices.
    It will report any new device
    """
    def __init__(self,name):
        self.name = name
        self.Receiver = None
        self.config = {"debug": False}
        self.devices = []    # list of device known to the controller
        self.state = "init"
        self.pending = []     # list of emtities not know by the controller yet
        self.default = {}     # dictionary of command line option that should be persisted with their default value

    def configure(self):
        """
        This function MUST set at leat 3 key in the self.config dictionary
            broker    The messaging server to connect to
                      For mat should be <usnername>/<password>@<host>:<port>
            address   The topic and subject we are listening to
                      format is <topic>/<subject>
        """
        raise NotImplementedError()

        
    def connect(self):
        self.Connection = qm.Connection(url=str(self.config["broker"]),
                  protocol='ssl')
        self.Connection.open()
        self.Session = self.Connection.session()
        self.Receiver = self.Session.receiver(self.config["address"]+".#", capacity=10)
        #self.Sender = self.Session.sender(self.config["address"])
    
    def disconnect(self):
        self.Connection.close()
    
    def configrequest(self,value=None):
        if value:
            self.sending({"subject":"control"+"."+self.name,
                        "content_type": "request",
                        "content":{"request":"configuration",
                                    "token": self.mysubject,
                                    "target":self.subject,
                                    "value":value}})
        else:
            self.sending({"subject":"control"+"."+self.name,
                        "content_type": "request",
                        "content":{"request":"configuration",
                                    "token": self.mysubject,
                                    "target":self.subject}})
        
    def receiving(self):
        try:
            while True:
                msg = self.Receiver.fetch(0)
                if msg:
                    msg.content=json.loads(msg.content)
                    self.MsgProcess(msg)
        except:
            self.Session.acknowledge()
            msg = self.Receiver.fetch(self.config["hb"])
            if msg:
                msg.content=json.loads(msg.content)
                self.MsgProcess(msg)
            
    def MsgProcess(self,msg):
        try:
            if self.config["debug"]:
                iprint("Got",msg.subject ,msg.content_type ,msg.content)
            if msg.content_type == "command":
                for aconn in self.devices:
                    aconn.process(msg)
            elif msg.content_type == "response" and msg.content["token"] == self.mysubject :
                self.process_response(msg)
            elif msg.content_type == "event":
                self.process_event(msg)
            else:
                iprint("other",msg.subject ,msg.content_type ,msg.content) 
            
        except Exit as e:
            raise e
        except:
            print "Fucking msg problem"
            traceback.print_exc(file=sys.stdout)
            
    def process_command(self,msg):
        """
        By default, for a bridge,  commands are just forwarded to the devices
        """
        for aconn in self.devices:
            aconn.process(msg)
            
    def process_response(self,msg):
        raise NotImplementedError()
                
    
    def process_event(self,msg):
        """
        By default just do nothing
        """
        if self.config["debug"]:
            iprint("event",msg.content["value"])
    
    def sending(self,msg):
        if self.config["debug"]:
            iprint("Sending",msg["subject"],msg["content_type"])
            #iprint("Sending",msg["subject"],msg["content_type"],msg["content"])
        qmsg = qm.Message(subject=msg["subject"],
                            content_type=msg["content_type"],
                            content=json.dumps(msg["content"]))
        snd = self.Session.sender(self.config["address"].split("/")[0]+"/"+msg["subject"]) 
        snd.send(qmsg,sync=False) 
        snd.close() 
        #self.Sender.send(qmsg,sync=False)
 
    def build(self):
        raise NotImplementedError()
                
    def _topic(self):
        return self.config["address"].split("/")[0]
    
    def _subject(self):
        return self.config["address"].split("/")[1] 

    def _mysubject(self):
        #When destined to me
        return self.subject + "." + self.name
    
    
    topic=property(_topic)
    subject=property(_subject)
    mysubject=property(_mysubject)



def getSession(db):
    """
    db = postgresql://autobuddy:76Bon19@lima.fwconsult.com/autobuddy')
    """
    engine = create_engine(db)
    mysess=sessionmaker(bind=engine)()
    mysess.Engines=[engine]
    return mysess

def initialize(sess):
    Base.metadata.create_all(sess.Engines[0])