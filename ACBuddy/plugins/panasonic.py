#! /usr/bin/env python3
# Plugin to generate Panasonic AC IR commands
#
# This module without the work/code from:
#      Scott Kyle https://gist.github.com/appden/42d5272bf128125b019c45bc2ed3311f
#      mat_fr     https://www.instructables.com/id/Reverse-engineering-of-an-Air-Conditioning-control/
#      user two, mathieu, vincent
#                 https://www.analysir.com/blog/2014/12/27/reverse-engineering-panasonic-ac-infrared-protocol/
import struct

STARFRAME = [ 3500, 1750 ]
ENDFRAME = [435, 10000 ]
MARK = 435
SPACE0 = 435
SPACE1 = 1300

FHEADER = b'\x40\x04\x07\x20\x00'
F1BODY = b'\x00\x00'
F2COMMON = b'\x00\x00\x70\x07\x00\x00\x91\x00'
FODOUR = b'\x40\x04\x07\x20\x01\xd9\x4c'
FILLER = b'\x01'

def set_temp(temp):
    tempv = bin(temp-16)[2:][::-1]
    if len(tempv) == 1:
        tempv = tempv+'0'
    tempb = [z for z in '00000100']
    idx = 1
    for c in tempv:
        tempb[idx]=c
        idx += 1
    return int(''.join(tempb),2).to_bytes(1,'big')

def set_mode(mode):
    if mode == "off":
        return b'\x10'
    elif mode == "auto":
        return b'\x90'
    elif mode == "dry":
        return b'\x94'
    elif mode == "fan":
        return b'\x96'
    elif mode == "cool":
        return b'\x9c'
    else:
        #If we do not know.... auto mode
        return b'\x90'

def set_fan(mode):
    if mode == "auto":
        return b'\x05'
    elif mode == "high":
        return b'\x0e'
    elif mode == "medium":
        return b'\x0a'
    elif mode == "low":
        return b'\x0c'
    else:
        #If we do not know.... auto mode
        return b'\x05'


def set_swing(mode):
    if mode == "auto":
        return b'\xf0'
    elif mode == "auto high":
        return b'\x70'
    elif mode == "auto low":
        return b'\xb0'
    elif mode == "90":
        return b'\x80'
    elif mode == "60":
        return b'\x40'
    elif mode == "45":
        return b'\xc0'
    elif mode == "30":
        return b'\x20'
    else:
        #If we do not know.... auto mode
        return b'\xf0'

def set_nanoex(mode=False):
    if mode:
        return b'\x20'
    else:
        return b'\x00'

def bit_reverse(i, n=8):
    return int(format(i, '0%db' % n)[::-1], 2)

def crc(frame):
    crc=0
    for x in frame:
        #print("Adding 0x%02x as 0x%02x"%(x,bit_reverse(x)))
        crc += bit_reverse(x)
        #print("crc now 0x%02x"%crc)
    return bit_reverse(crc&0xff).to_bytes(1,'big')



def build_code(mode="auto", temp=25, fan="auto", swing="auto", nanoex=False, odourwash=False):
    frames = [FHEADER + F1BODY]
    if odourwash:
        frames += [FODOUR]
    else:
        f2 = FHEADER + set_mode(mode) + set_temp(temp) + FILLER
        f2 += (set_fan(fan)[0] + set_swing(swing)[0]).to_bytes(1,'big')
        f2 += F2COMMON
        f2 += set_nanoex(nanoex)
        frames += [f2]

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
    parser.add_argument("-m", "--mode",   choices=['auto','cool','dry','fan','off'] , default='auto',
                        help="Mode, one of 'off', 'auto', 'cool', 'dry' or 'fan'. (default 'auto').")
    parser.add_argument("-f", "--fan",   choices=['auto','high','middle','low'] , default='auto',
                        help="Fan, one of 'auto', 'high', 'middle' or 'low'. (default 'auto').")
    parser.add_argument("-s", "--swing",   choices=['auto','auto high','auto low', '90', '60', '45', '30'] , default='auto',
                        help="Swing, one of 'auto','auto high','auto low', '90', '60', '45', '30'. (default 'auto').")
    parser.add_argument("-n", "--nanoex", action="store_true", default=False,
                        help="nanoeX mode")
    parser.add_argument("-o", "--odour", action="store_true", default=False,
                        help="Odour Wash mode")
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
    if opts.odour:
        frames += build_code(odourwash=True)

    frames  += build_code(mode=opts.mode, temp=opts.temp, fan=opts.fan, swing=opts.swing, nanoex=opts.nanoex)

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
