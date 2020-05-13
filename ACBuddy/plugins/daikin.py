#! /usr/bin/env python3
# Plugin to generate Daikin AC IR commands
#
# This module without the work/code from:
#      Scott Kyle https://gist.github.com/appden/42d5272bf128125b019c45bc2ed3311f
#      mat_fr     https://www.instructables.com/id/Reverse-engineering-of-an-Air-Conditioning-control/
import struct

STARFRAME = [ 3500, 1750 ]
ENDFRAME = [435, 10000 ]
MARK = 435
SPACE0 = 435
SPACE1 = 1300

FBODY = b'\x88\x5b\xe4\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\xa3\x00\x10'


def bit_reverse(i, n=8):
    return int(format(i, '0%db' % n)[::-1], 2)


def crc(frame):
    crc=0
    for x in frame:
        #print("Adding 0x%02x as 0x%02x"%(x,bit_reverse(x)))
        crc += bit_reverse(x)
        #print("crc now 0x%02x"%crc)
    return bit_reverse(crc&0xff).to_bytes(1,'big')


def set_temp(temp):
    if temp<18:
        temp=18
    elif temp > 31:
        temp = 31
    mask = bytearray(b'\x00'*18)
    mask[6] = bit_reverse(0x24+(temp-18)*2)
    return mask, False

def set_fan(mode="auto"):
    """ mode is one of auto, lowest, low, middle, high, highest
    """
    rank = ['lowest','low','middle','high','highest']
    if mode not in rank:
        mode="auto"   #Just in case
    mask = bytearray(b'\x00'*18)
    if mode == "auto":
        mask[8] = 0x05
    else:
        mask[8] = bit_reverse(48+(16*rank.index(mode)))
    return mask, False


def set_swing(mode=True):
    mask = bytearray(b'\x00'*18)
    if mode:
        mask[8] = 0xf0
    else:
        mask[8] = 0x00
    return mask, False


def set_mode(mode):
    mask = bytearray(b'\x00'*18)
    if mode == "off":
        mask[5] = 0x0c
        mask[16] = 0x02
    elif mode == "dry":
        mask[5] = 0x84
        mask[6] = 0x03
    elif mode == "fan":
        mask[5] = 0x86
    else:
        mask[5] = 0x8c
    return mask, True


def build_code(mode="cool", temp=25, fan="auto", swing=False):
    frames = []
    packet = bytearray(FBODY)
    #Note that set mod must be last for it replaces values
    for f,v in [(set_temp,temp),(set_fan,fan),(set_swing,swing),(set_mode,mode)]:
        mask,replace = f(v)
        if replace:
            packet = bytearray([ y or x for x,y in zip(packet,mask)])
        else:
            packet = bytearray([x | y for x,y in zip(packet,mask)])
    frames += [packet]
    idx = 0
    for x in frames:
        frames[idx] += crc(x)
        idx += 1
    return frames


if __name__ == '__main__':

    import argparse
    import base64

    def to_lirc(frames):
        """Transform a list of frames into a LIRC compatible list of pulse timing pairs"""
        lircframe =  []
        for frame in frames:
            lircframe += STARFRAME
            for x in frame:
                idx = 0x80
                while idx:
                    lircframe.append(MARK)
                    if x & idx:
                        lircframe.append(SPACE1)
                    else:
                        lircframe.append(SPACE0)
                    idx >>= 1
            lircframe += ENDFRAME
        return lircframe

    def to_broadlink(pulses):
        array = bytearray()

        for pulse in pulses:
            pulse = round(pulse * 269 / 8192)  # 32.84ms units

            if pulse < 256:
                array += bytearray(struct.pack('>B', pulse))  # big endian (1-byte)
            else:
                array += bytearray([0x00])  # indicate next number is 2-bytes
                array += bytearray(struct.pack('>H', pulse))  # big endian (2-bytes)

        packet = bytearray([0x26, 0x00])  # 0x26 = IR, 0x00 = no repeats
        packet += bytearray(struct.pack('<H', len(array)))  # little endian byte count
        packet += array
        packet += bytearray([0x0d, 0x05])  # IR terminator

        # Add 0s to make ultimate packet size a multiple of 16 for 128-bit AES encryption.
        remainder = (len(packet) + 4) % 16  # rm.send_data() adds 4-byte header (02 00 00 00)
        if remainder:
            packet += bytearray(16 - remainder)

        return packet


    parser = argparse.ArgumentParser(description="Decode LIRC IR code into frames.")
    # version="%prog " + __version__ + "/" + bl.__version__)
    parser.add_argument("-t", "--temp",  type=int, default=25,
                        help="Temperature (°C). (default 25).")
    parser.add_argument("-m", "--mode",   choices=['cool','dry','fan','off'] , default='cool',
                        help="Mode to set. (default 'cool').")
    parser.add_argument("-f", "--fan",   choices=['auto','highest','high','middle','low','lowest'] , default='auto',
                        help="Fan mode. (default 'auto').")
    parser.add_argument("-s", "--swing",   choices=['on','off'] , default='auto',
                        help="Swing on or off. (default 'off').")
    parser.add_argument("-l", "--lirc", action="store_true", default=False,
                        help="Output LIRC compatible timing")
    parser.add_argument("-b", "--broadlink", action="store_true", default=False,
                        help="Output Broadlink timing")
    parser.add_argument("-B", "--base64", action="store_true", default=False,
                        help="Output Broadlink timing in base64 encoded")

    try:
        opts = parser.parse_args()
    except Exception as e:
        parser.error("Error: " + str(e))

    frames = []
    frames  += build_code(mode=opts.mode, temp=opts.temp, fan=opts.fan, swing=opts.swing=='on')

    if opts.lirc:
        lircf = to_lirc(frames)
        while lircf:
            print ("\t".join(["%d"%x for x in lircf[:6]]))
            lircf = lircf[6:]
    elif opts.broadlink or opts.base64:
        lircf = to_lirc(frames)
        bframe = to_broadlink([int(x) for x in lircf])
        if opts.base64:
            print("{}".format(str(base64.b64encode(bframe),'ascii')))
        else:
            print("{}".format(bframe))
    else:
        for f in frames:
            print( " ".join([hex(x) for x in f]))
