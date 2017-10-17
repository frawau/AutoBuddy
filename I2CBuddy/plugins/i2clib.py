#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# Library used to deal with I2C entities. Mostly sensors
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
# Portions of this code are
# Copyright (c) 2016 Adafruit Industries
# Author: Tony DiCola
#
# Portions of this code are
# Copyright (c) Anavi Technology
#           http://www.anavi.technology



import time, io, fcntl
from ctypes import *
from sys import byteorder

# I2C C API constants (from linux kernel headers)
I2C_M_TEN             = 0x0010  # this is a ten bit chip address
I2C_M_RD              = 0x0001  # read data, from slave to master
I2C_M_STOP            = 0x8000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_NOSTART         = 0x4000  # if I2C_FUNC_NOSTART
I2C_M_REV_DIR_ADDR    = 0x2000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_IGNORE_NAK      = 0x1000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_NO_RD_ACK       = 0x0800  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_RECV_LEN        = 0x0400  # length will be first received byte

I2C_SLAVE             = 0x0703  # Use this slave address
I2C_SLAVE_FORCE       = 0x0706  # Use this slave address, even if
                                # is already in use by a driver!
I2C_TENBIT            = 0x0704  # 0 for 7 bit addrs, != 0 for 10 bit
I2C_FUNCS             = 0x0705  # Get the adapter functionality mask
I2C_RDWR              = 0x0707  # Combined R/W transfer (one STOP only)
I2C_PEC               = 0x0708  # != 0 to use PEC with SMBus
I2C_SMBUS             = 0x0720  # SMBus transfer


# ctypes versions of I2C structs defined by kernel.
class i2c_msg(Structure):
    _fields_ = [
        ('addr',  c_uint16),
        ('flags', c_uint16),
        ('len',   c_uint16),
        ('buf',   POINTER(c_uint8))
    ]

class i2c_rdwr_ioctl_data(Structure):
    _fields_ = [
        ('msgs',  POINTER(i2c_msg)),
        ('nmsgs', c_uint32)
    ]


def make_i2c_rdwr_data(messages):
    """Utility function to create and return an i2c_rdwr_ioctl_data structure
    populated with a list of specified I2C messages.  The messages parameter
    should be a list of tuples which represent the individual I2C messages to
    send in this transaction.  Tuples should contain 4 elements: address value,
    flags value, buffer length, ctypes c_uint8 pointer to buffer.
    """
    # Create message array and populate with provided data.
    msg_data_type = i2c_msg*len(messages)
    msg_data = msg_data_type()
    for i, m in enumerate(messages):
        msg_data[i].addr  = m[0] & 0x7F
        msg_data[i].flags = m[1]
        msg_data[i].len   = m[2]
        msg_data[i].buf   = m[3]
    # Now build the data structure.
    data = i2c_rdwr_ioctl_data()
    data.msgs  = msg_data
    data.nmsgs = len(messages)
    return data

class i2c(object):
    def __init__(self, device, bus):
        self.fd = io.open("/dev/i2c-"+str(bus), "r+b", buffering=0)
        # set device address
        fcntl.ioctl(self.fd, I2C_SLAVE, device)
        self.device = device

    def __enter__(self):
        """Context manager enter function."""
        # Just return this object so it can be used in a with statement
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit function, ensures resources are cleaned up."""
        self.close()
        return False  # Don't suppress exceptions.

    def __del__(self):
        """Clean up any resources used by instance."""
        self.close()

    def close(self):
        self.fd.close()

    def write(self, data):
        """Write data to the I2C device. data must be bytes or bytesarray
        """
        self.fd.write(data)

    def read(self, nb):
        """Read nb bytes from i2c device
        """
        return self.fd.read(nb)

    def read_byte(self, cmd):
        """Read a byte (1 bytes) from the specified cmd register of the device.
        """
        # Build ctypes values to marshall between ioctl and Python.
        reg = c_uint8(cmd)
        result = c_uint8()
        # Build ioctl request.
        request = make_i2c_rdwr_data([
            (self.device, 0, 1, pointer(reg)),             # Write cmd register.
            (self.device, I2C_M_RD, 1, cast(pointer(result), POINTER(c_uint8)))   # Read word (2 bytes).
        ])
        # Make ioctl call and return result data.
        fcntl.ioctl(self.fd, I2C_RDWR, request)
        return bytearray([result.value])

    def read_word(self, cmd):
        """Read a word (2 bytes) from the specified cmd register of the device.
        Return as bytearray, following for the processor endianess
        """
        # Build ctypes values to marshall between ioctl and Python.
        reg = c_uint8(cmd)
        result = c_uint16()
        # Build ioctl request.
        request = make_i2c_rdwr_data([
            (self.device, 0, 1, pointer(reg)),             # Write cmd register.
            (self.device, I2C_M_RD, 2, cast(pointer(result), POINTER(c_uint8)))   # Read word (2 bytes).
        ])
        # Make ioctl call and return result data.
        fcntl.ioctl(self.fd, I2C_RDWR, request)
        return bytearray(result.value.to_bytes(2,byteorder))

    def read_block_data(self, cmd, length=32):
        """Perform a read from the specified cmd register of device.  Length number
        of bytes (default of 32) will be read and returned as a bytearray.
        """
        # Build ctypes values to marshall between ioctl and Python.
        reg = c_uint8(cmd)
        result = create_string_buffer(length) #From ctypes
        # Build ioctl request.
        request = make_i2c_rdwr_data([
            (self.device, 0, 1, pointer(reg)),             # Write cmd register.
            (self.device, I2C_M_RD, length, cast(result, POINTER(c_uint8)))   # Read data.
        ])
        # Make ioctl call and return result data.
        fcntl.ioctl(self.fd, I2C_RDWR, request)
        return bytearray(result.raw)  # Use .raw instead of .value which will stop at a null byte!


    #Reading signed and unsigned integer values
    def readS16BE(self, cmd):
        return int.from_bytes(self.read_word(cmd), byteorder='big', signed=True)
    def readU16BE(self, cmd):
        return int.from_bytes(self.read_word(cmd), byteorder='big', signed=False)
    def readS16LE(self, cmd):
        return int.from_bytes(self.read_word(cmd), byteorder='little', signed=True)
    def readU16LE(self, cmd):
        return int.from_bytes(self.read_word(cmd), byteorder='little', signed=False)

    def readU8(self,cmd):
        return int.from_bytes(self.read_byte(cmd), byteorder='little', signed=False)
    def readS8(self,cmd):
        return int.from_bytes(self.read_byte(cmd), byteorder='little', signed=True)

    def write_byte_data(self, cmd, val):
        """Write a byte of data to the specified cmd register of the device.
        """
        # Construct a string of data to send with the command register and byte value.
        data = bytearray(2)
        data[0] = cmd & 0xFF
        data[1] = val & 0xFF
        self.write(data)

    def write_word_data(self, cmd, val):
        """Write a word (2 bytes) of data to the specified cmd register of the
        device.
        """
        # Send the data to the device.
        self.write_block_data(cmd,val.to_bytes(2,byteorder))

    def write_block_data(self, cmd, vals):
        """Write a block of data to the specified cmd register of the device.
        The amount of data to write should be the first byte inside the vals
        string/bytearray and that count of bytes of data to write should follow
        it.
        """
        # Just use the I2C block data write to write the provided values and
        # their length as the first byte.
        data = bytearray(len(vals)+1)
        data[0] = len(vals) & 0xFF
        data[1:] = vals[0:]
        self.write_i2c_block_data(cmd, data)

    def write_i2c_block_data(self, cmd, vals):
        """Write a buffer of data to the specified cmd register of the device.
        """
        # Construct a string of data to send, including room for the command register.
        data = bytearray(len(vals)+1)
        data[0] = cmd & 0xFF  # Command register at the start.
        data[1:] = vals[0:]   # Copy in the block data (ugly but necessary to ensure
                              # the entire write happens in one transaction).
        # Send the data to the device.
        self.write(data)
