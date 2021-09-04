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

from .buddylib import BuddyBridge, _log
from . import buddyxml as xml
import asyncio as aio
import datetime as dt
import json
import logging
from hbmqtt.client import MQTTClient, ClientException

logging.getLogger("hbmqtt").setLevel(logging.WARNING)


class BuddyDeviceMQTT:
    async def _process_mqtt(self, event, payload):
        try:
            self.present = True
            res = getattr(self, f"handle_mqtt_{event}")(payload)
            if aio.iscoroutine(res):
                await res
            else:
                await aio.sleep(0)
        except Exception as e:
            _log.debug(f"Device {self.nickname} cannot handle MQTT event {event}: {e}")
            _log.exception(e)
            await aio.sleep(0)


class BuddyMQTT(BuddyBridge):
    """
    A bridge with a MQTT connection.

    The application must overload process_mqtt, a coroutine to preocess incoming messages from MQTT

    Any message to be sent to MQTT should be put to self.mqtt_wqueue


    """

    def __init__(self, dclass, defaults={}, descr="A Buddy Bridge"):
        super().__init__(dclass, defaults, descr)
        self.mqtt_topics = []
        self.mqtt_task = {}
        self.msg_tasks = []
        self.mqtt_client = None
        self.mqtt_rqueue = aio.Queue()
        self.mqtt_wqueue = aio.Queue()
        self.msg_lock = aio.Lock()
        self.buddy_config["mqtt"] = {}
        for k, v in zip(
            [
                "mqtt host",
                "mqtt port",
                "mqtt user",
                "mqtt password",
                "mqtt namespace",
                "mqtt qos",
            ],
            ["localhost", "1883", "", "", "", "1"],
        ):
            if k not in self.buddy_config:
                self.buddy_config["mqtt"][k] = v

    def configure(self, defaults, descr):
        super().configure(defaults, descr)
        cg = xml.xml_group("mqtt", label="MQTT Config")
        ce = xml.xml_entry("mqtt host", label="MQTT Host", default="localhost")
        cg.add_member(ce)
        ce = xml.xml_entry("mqtt port", label="MQTT Port", length=5, default="1883")
        cg.add_member(ce)
        ce = xml.xml_entry("mqtt user", label="MQTT User", length=32, default="")
        cg.add_member(ce)
        ce = xml.xml_entry("mqtt password", label="MQTT Pasword", length=32, default="")
        cg.add_member(ce)
        ce = xml.xml_entry("mqtt namespace", label="Name Space", length=32, default="")
        cg.add_member(ce)
        # ce = xml.xml_entry("topics", label="Topics (Comma separated)",  length=256,  default="")
        # cg.add_member(ce)
        ce = xml.xml_choice(
            "mqtt qos", choices=[[1, "QoS 1"], [2, "QoS 2"], [0, "QoS 0"]], label="QoS"
        )
        cg.add_member(ce)
        self.config_buddy.append(cg)

    async def mqtt_reader(self):
        mqttconfig = {
            "keep_alive": 10,
            "ping_delay": 5,
            "default_qos": 1,
            "default_retain": False,
            "auto_reconnect": False,
            "reconnect_max_interval": 5,
            "reconnect_retries": 10,
        }

        mqtt_client = MQTTClient(config=mqttconfig)
        connected = False
        while not connected:
            try:
                sbc = self.buddy_config["mqtt"]
                _log.debug(
                    f"MQTT connecting with mqtt://{sbc['mqtt user']}:{sbc['mqtt password']}@{sbc['mqtt host']}:{sbc['mqtt port']}/"
                )
                if "mqtt user" in sbc and sbc["mqtt user"]:
                    await mqtt_client.connect(
                        f"mqtt://{sbc['mqtt user']}:{sbc['mqtt password']}@{sbc['mqtt host']}:{sbc['mqtt port']}/"
                    )
                else:
                    await mqtt_client.connect(
                        f"mqtt://{sbc['mqtt host']}:{sbc['mqtt port']}/"
                    )
                    _log.debug(
                        f"Subscribing to {[(sbc['mqtt namespace'] + x, int(sbc['mqtt qos'])) for x in self.mqtt_topics]}"
                    )
                await mqtt_client.subscribe(
                    [
                        (sbc["mqtt namespace"] + x, int(sbc["mqtt qos"]))
                        for x in self.mqtt_topics
                    ]
                )
                connected = True
            except aio.CancelledError:
                return
            except Exception as e:
                _log.warning(f"MQTT could not connect to broker.{e}")
                await aio.sleep(10)
                connected = False
                continue
            self.mqtt_client = mqtt_client
            await self.mqtt_connection()
            try:
                while True:
                    # try:
                    message = await self.mqtt_client.deliver_message()
                    message = message.publish_packet
                    # except aio.TimeoutError:
                    # continue
                    topic = message.variable_header.topic_name
                    try:
                        payload = json.loads(message.payload.data)
                    except:
                        payload = message.payload.data.decode()
                    await self.mqtt_rqueue.put((topic, payload))
            except ClientException as ce:
                _log.debug("MQTT Client exception: %s\n\n" % ce)
                try:
                    await self.mqtt_client.disconnect()
                except:
                    pass
                connected = False
            except Exception as ce:
                _log.debug("MQTT Other exception: %s\n\n" % ce)
                if self.future.done():
                    return
                connected = False
            await aio.sleep(2)  # Just a wait a little

    async def mqtt_connection(self):
        """
        Overload to do things once the MQTT ibus is connected
        """
        await aio.sleep(0)

    async def mqtt_process(self):
        while True:
            try:
                topic, payload = await self.mqtt_rqueue.get()
                if self.future.done():
                    return
                async with self.msg_lock:
                    self.msg_tasks.append(
                        (
                            aio.create_task(self.process_mqtt(topic, payload)),
                            dt.datetime.now(),
                        )
                    )
            except aio.CancelledError:
                _log.debug("MQTT process is being cancelled.")
                return

    async def mqtt_writer(self):
        while True:
            try:
                topic, payload = await self.mqtt_wqueue.get()
                if isinstance(payload, str):
                    payload = payload.encode()
                elif not isinstance(payload, bytes):
                    payload = json.dumps(payload).encode()
                topic = self.buddy_config["mqtt"]["mqtt namespace"] + topic
                _log.debug(f"AB MQTT write {topic} with {payload} on {self.mqtt_client}")
                if self.mqtt_client:
                    try:
                        await self.mqtt_client.publish(
                            topic, payload, qos=int(self.buddy_config["mqtt"]["mqtt qos"])
                        )
                    except aio.CancelledError:
                        raise
                    except Exception as e:
                        _log.debug(f"Publish Exception {e}")
                if self.future.done():
                    return
            except aio.CancelledError:
                _log.debug("MQTT writer is being cancelled.")
                return

    async def process_mqtt(self, topic, payload):
        topic = topic.replace(self.buddy_config["mqtt"]["mqtt namespace"], "")
        #        _log.debug(f"Processing MQTT message for {topic} with {payload} ")
        if not await self.global_process_mqtt(topic, payload):
            lod, event = self.topic_to_devices(topic)
            # Pass it on to devices. We expect the device to have _process_mqtt coroutine
            if lod and self.devices:
                await aio.gather(
                    *[
                        adev._process_mqtt(event, payload)
                        for adev in self.devices
                        if adev.name in lod
                    ],
                    return_exceptions=True,
                )

    async def cleaner(self):
        """
        This task cleans up the msg_tasks list now and then
        """
        while True:
            try:
                await aio.sleep(15)
                rtask = []
                idx = 0
                for task, tstmp in self.msg_tasks:
                    if task.done():
                        rtask.append(idx)
                    else:
                        if tstmp < dt.datetime.now() - dt.timedelta(seconds=120):
                            _log.warning(
                                "Task has been running for more tha 120 secs. Cancelling"
                            )
                            task.cancel()
                            rtask.append(idx)
                        elif tstmp < dt.datetime.now() - dt.timedelta(seconds=30):
                            _log.warning("Task has been running for more tha 30 secs.")
                    idx += 1
                rtask = rtask[::-1]  # reverse and remove
                # _log.debug(f"Cleaning ({len(rtask)}) {rtask}")
                async with self.msg_lock:
                    for idx in rtask:
                        self.msg_tasks = self.msg_tasks[:idx] + self.msg_tasks[idx + 1 :]
            except aio.CancelledError:
                _log.debug("MQTT clean is being cancelled.")
                return

    def local_response_configuration(self, msg):
        """
        Overload to perform needed configurations updates
        """
        self.mqtt_task["mqtt write"] = aio.create_task(self.mqtt_writer())
        self.mqtt_task["mqtt process"] = aio.create_task(self.mqtt_process())
        self.mqtt_task["mqtt read"] = aio.create_task(self.mqtt_reader())
        self.mqtt_task["mqtt clean"] = aio.create_task(self.cleaner())

    def last_rites(self):
        super().last_rites()
        if self.mqtt_client:
            sbc = self.buddy_config["mqtt"]
            aio.create_task(
                self.mqtt_client.unsubscribe(
                    [sbc["mqtt namespace"] + x for x in self.mqtt_topics]
                )
            )
        if self.mqtt_client:
            aio.create_task(self.mqtt_client.disconnect())
        for t in self.mqtt_task.values():
            try:
                t.cancel()
            except:
                pass

    async def global_process_mqtt(self, topic, payload):
        """
        Treat mqtt messages that should not be passed on to devices
        Return True if the message was processed False if it is for devices
        """
        await aio.sleep(0)
        return False

    def topic_to_devices(self, topic):
        """
        Given a topic, returns a 2-uple
            - list of names of devices targeted
            - event
        """
        raise NotImplementedError
