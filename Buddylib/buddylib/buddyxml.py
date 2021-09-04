#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application is simply a bridge application for flic buttons
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

# Some constants
XMLPREFIX = """
<buddyui version="0.1">
<command  name="{buddy}">
"""
XMLPOSTFIX = """
</command>
</buddyui>
"""

XMLONLYLBL = "buoicmd_"


XMLWHITE = [
    "slider",
    """
<controlgroup  type="list" name="white" label="White" rteffect="1">
    <control type="slider" name="value" label="Brightness" rteffect="1">
        <start>0</start>
        <end>100</end>
        <increment>1</increment>
    </control>
    <control type="slider" name="temperature" label="Kelvin" rteffect="1">
        <start>{start}</start>
        <end>{end}</end>
        <increment>{increment}</increment>
    </control>"""
    + """
    <control  type="spinner" name="duration" label="Duration" onlyif="{}duration::yes" >
        <start>0</start>
        <end>600</end>
        <increment>1</increment>
        <postfix>secs</postfix>
        <default>0</default>
    </control>
</controlgroup>
            """.format(
        XMLONLYLBL
    ),
]

XMLCOLOUR = """
    <controlgroup type="list" name="colour" label="Colour" widget="colourpicker" rteffect="{realtime}">
        <control type="slider" name="hue" label="Hue" rteffect="{realtime}">
            <start>0</start>
            <end>360</end>
            <increment>1</increment>
        </control>
        <control type="slider" name="saturation" label="Saturation" rteffect="1">
            <start>0</start>
            <end>100</end>
            <increment>1</increment>
        </control>
        <control type="slider" name="value" label="Brightness" rteffect="1">
            <start>0</start>
            <end>100</end>
            <increment>1</increment>
        </control>
    </controlgroup>"""


XMLGENSLIDER = """
<control type="slider" name="{name}" label="{label}" rteffect="{realtime}" {onlyif} >
    <start>{start}</start>
    <end>{end}</end>
    <increment>{increment}</increment>
</control>"""


XMLGENCHOICE = """
<controlgroup type="choice" name="{name}" label="{label}" {onlyif} >
    {choicelist}
</controlgroup>"""


XMLGENSWITCH = """
<control type="switch" name="{name}" label="{label}" rteffect="{realtime}" {onlyif} >
    <value label="{onlbl}">{onval}</value>
    <value label="{offlbl}">{offval}</value> {default}
</control>"""

XMLGENSPINNER = """
<control  type="spinner" name="{name}" label="{label}" rteffect="{realtime}" {onlyif} >
    <start>{start}</start>
    <end>{end}</end>
    <increment>{increment}</increment>
    <postfix>{postfix}</postfix>
    <default>{default}</default>
</control>"""

XMLDURATION = """
    <control type="spinner" name="duration" label="Duration" {onlyif} >
        <start>0</start>
        <end>600</end>
        <increment>1</increment>
        <postfix>secs</postfix>
        <default>0</default>
    </control>"""

#
# Here we define XML elements a few parameters are common to all elements
#      name: the name of the command. Used when sending a command on the AutoBuddy bus
#      label: The name to display. If not set name.title() will be used
#      readonly: one of yes  Can be used both realtime and when defining rules,
#                       no  can only be used when defining rules
#                       only can only be used in realtime, not defining rules
#      onlyif: define that the XML should only be rendered when some status meets a specific value.
#              If not empty, the format MUST be of the form (note the quotation marks)
#
#                      onlyif="<accessor>::<value>"
#              where <accessor> is of the form
#                      <key>[::<key]*
#
#              For instance
#                      onlyif="colour::hue::0"
#                 us equivalen to
#                      if status["colour"]["hue"] == 0


class xml_item:
    """
    Generic class
    """

    def __init__(self, name, label=None, realtime="yes", onlyif=""):
        self.name = name
        if label:
            self.label = label
        else:
            self.label = self.name.title()
        self.realtime = 1 if realtime == "yes" else 0 if realtime == "no" else -1
        if onlyif:
            self.onlyif = f'onlyif="{onlyif}"'
        else:
            self.onlyif = ""
        self.members = []


class xml_group(xml_item):
    """
    A group of elements
    """

    def __init__(self, name, label=None, realtime="yes", onlyif="", gtype="list"):
        super().__init__(name, label, realtime, onlyif)
        self.gtype = gtype

    def add_member(self, xe):
        self.members.append(xe)

    def render(self):
        vals = {
            "name": self.name,
            "label": self.label,
            "realtime": self.realtime,
            "onlyif": self.onlyif,
            "gtype": self.gtype,
        }

        txt = """<controlgroup  type="{gtype}" name="{name}" label="{label}" rteffect="{realtime}" {onlyif} >"""
        txt = txt.format(**vals)
        for elt in self.members:
            if isinstance(elt, str):
                txt += elt
            else:
                txt += elt.render()
        txt += "\n</controlgroup>"
        return txt


class xml_commands:
    """
    An XML document defining commands
    """

    def __init__(self, name):
        self.name = name
        self.members = []

    def add_member(self, xe):
        self.members.append(xe)

    def render(self):
        vals = {
            "buddy": self.name,
        }

        txt = XMLPREFIX.format(vals) + "\n"
        for elt in self.members:
            if isinstance(elt, str):
                txt += elt
            else:
                txt += elt.render()
        txt += XMLPOSTFIX
        return txt


class xml_slider(xml_item):
    def __init__(
        self, name, start=0, end=100, increment=10, label=None, realtime="no", onlyif=""
    ):
        super().__init__(name, label, realtime, onlyif)
        self.start = start
        self.end = end
        self.increment = increment

    def render(self):
        vals = {
            "name": self.name,
            "label": self.label,
            "realtime": self.realtime,
            "onlyif": self.onlyif,
            "start": self.start,
            "end": self.end,
            "increment": self.increment,
        }
        return XMLGENSLIDER.format(**vals)


class xml_choice(xml_item):
    def __init__(self, name, choices, label=None, realtime="no", onlyif=""):
        super().__init__(name, label, realtime, onlyif)
        self.choices = choices

    def render(self):
        vals = {
            "name": self.name,
            "label": self.label,
            "realtime": self.realtime,
            "onlyif": self.onlyif,
        }
        chstr = ""
        for x in self.choices:
            if isinstance(x, str):
                chstr += """<item label="{}" value="{}" />\n""".format(
                    str(x).title(), x
                )
            elif isinstance(x, list):
                chstr += """<item label="{}" value="{}" />\n""".format(
                    str(x[1]), str(x[0])
                )
            elif isinstance(x, tuple):
                chstr += """<item label="{}" value="{}" />\n""".format(
                    str(x[1]), str(x[0])
                )

        vals["choicelist"] = chstr
        return XMLGENCHOICE.format(**vals)


class xml_switch(xml_item):
    def __init__(
        self,
        name,
        on=["on", "On"],
        off="off",
        label=None,
        realtime="no",
        onlyif="",
        default="",
    ):
        """
        Here on and off are strings or 2-uples (list or tuple) [value, label]
        """
        super().__init__(name, label, realtime, onlyif)
        if isinstance(on, str):
            self.on = [on, on.title()]
        else:
            assert (isinstance(on, list) or isinstance(on, tuple)) and len(on) == 2
            self.on = on
        if isinstance(off, str):
            self.off = [off, off.title()]
        else:
            assert (isinstance(off, list) or isinstance(off, tuple)) and len(off) == 2
            self.off = off
        if default:
            self.default = f"\n<default>{default}</default>"
        else:
            self.default = ""

    def render(self):
        vals = {
            "name": self.name,
            "label": self.label,
            "realtime": self.realtime,
            "onlyif": self.onlyif,
            "onval": self.on[0],
            "onlbl": self.on[1],
            "offval": self.off[0],
            "offlbl": self.off[1],
            "default": self.default,
        }
        return XMLGENSWITCH.format(**vals)


class xml_spinner(xml_item):
    def __init__(
        self,
        name,
        start=0,
        end=100,
        increment=1,
        postfix="",
        default=None,
        label=None,
        realtime="no",
        onlyif="",
    ):
        super().__init__(name, label, realtime, onlyif)
        self.start = start
        self.end = end
        self.increment = increment
        self.postfix = postfix
        if default:
            self.default = default
        else:
            self.default = start

    def render(self):
        vals = {
            "name": self.name,
            "label": self.label,
            "realtime": self.realtime,
            "onlyif": self.onlyif,
            "start": self.start,
            "end": self.end,
            "increment": self.increment,
            "postfix": self.postfix,
            "default": self.default,
        }
        return XMLGENSPINNER.format(**vals)


class xml_colour(xml_item):
    def __init__(self, realtime="yes"):
        super().__init__("colour", "Colour", realtime)

    def render(self):
        vals = {
            "realtime": self.realtime,
        }
        return XMLCOLOUR.format(**vals)


class xml_entry(xml_item):
    def __init__(self, name, label=None, length=512, default=""):
        super().__init__(name, label)
        self.length = length
        if default:
            self.default = f'default="{default}"'
        else:
            self.default = ""

    def render(self):
        vals = {
            "name": self.name,
            "label": self.label,
            "length": self.length,
            "default": self.default,
        }
        return """\n<control type="text" name="{name}" label="{label}" length="{length}" {default} />""".format(
            **vals
        )


class xml_mediaplayer(xml_item):
    def render(self):
        vals = {
            "name": self.name,
            "label": self.label,
            "realtime": self.realtime,
            "onlyif": self.onlyif,
        }

        xml = """
        <controlgroup type="list" name="{name}" label="{label}" widget="remotecontrol" rteffect="{realtime}" {onlyif}>
            <control type="button" name="up" label="Up" rteffect="1" />
            <control type="button" name="left" label="Left" rteffect="1" />
            <control type="button" name="right" label="Right" rteffect="1" />
            <control type="button" name="down" label="Down" rteffect="1" />
            <control type="button" name="enter" label="OK" rteffect="1" />
            <control type="button" name="home" label="Home" rteffect="1" />
            <control type="button" name="back" label="Back" rteffect="1" />
            <control type="button" name="previous" label="Previous" rteffect="1" />
            <control type="button" name="backward" label="Backward" rteffect="1" />
            <control type="button" name="play" label="Play" rteffect="1" />
            <control type="button" name="forward" label="Forward" rteffect="1" />
            <control type="button" name="next" label="Next" rteffect="1" />
            <control type="button" name="isplaying" label="Is Playing" rteffect="1" />
        </controlgroup>"""
        return xml.format(**vals)


class xml_asis(xml_item):
    def __init__(self, name, val):
        super().__init__(name, None)
        self.value = val

    def render(self):
        return self.value
