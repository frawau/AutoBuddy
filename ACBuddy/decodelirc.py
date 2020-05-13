#!/usr/bin/env python3
#
SHORT     = 440
LONG      = 1280
MARGIN    = 150
INTRO     = 3500
INTRO2    = 1750
SEPARATOR = 9880
ENDIAN = 'big'
curpair=[]


def decode(v1,v2):

    if abs(v1 - INTRO) < MARGIN and abs(v2 - INTRO2) < MARGIN:
        return 'start frame'
    if (abs(v1 - SHORT) < MARGIN and abs(v2 - SHORT) < MARGIN):
        return '0'
    if abs(v1 - SHORT) < MARGIN and abs(v2 - LONG) < MARGIN:
        return '1'
    if abs(v1 - SHORT) < MARGIN and abs(v2 - SEPARATOR) < MARGIN:
        return 'end frame'
    return None

def toframe(astr,curframe=False):
    global curpair

    newframes = []

    alist = [x for x in astr.split(' ') if x]
    if curframe == False and len(alist) != 6:
        return [],curframe

    for val in alist:
        logging.debug("Looking at %s"%val)
        try:
            ival = int(val,10)
            curpair.append(ival)
            logging.debug("Decoding {}".format(curpair))
            if len(curpair)==2:
                dval = decode(*curpair)
                logging.debug("\tGot {}".format(dval))
                curpair = []
                if dval == 'end frame' or dval is None:
                    if curframe != False and len(curframe):
                        newframes.append(int(curframe,2).to_bytes(len(curframe)//8,ENDIAN))
                    curframe = False
                elif dval == 'start frame':
                    curframe=''
                elif isinstance(curframe,str):
                    curframe += dval
        except ValueError:
            if curframe and len(curframe):
                newframes.append(int(curframe,2).to_bytes(len(curframe)//8,ENDIAN))
            curframe=False
            curpair = []
            logging.debug("Oops, ValueError")
            break
    return newframes,curframe

if __name__ == '__main__':
    import sys
    import argparse
    import binascii
    import json
    import logging

    parser = argparse.ArgumentParser(description="Decode LIRC IR code into frames.")
    # version="%prog " + __version__ + "/" + bl.__version__)
    parser.add_argument("-i", "--filein",  type=argparse.FileType('r'), default=sys.stdin,
                        help="The file to read from. (default \"stdin\").")
    parser.add_argument("-o", "--fileout",   type=argparse.FileType('w'), default=sys.stdout,
                        help="The file to write to. (default \"stdout\").")
    parser.add_argument("-j", "--json", action="count", default=0,
                        help="Output json (default False)")
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
    curframe = False
    loframes=[]
    newf = []
    pref =""

    try:
        for line in opts.filein:
            newf, curframe = toframe(line, curframe)
            if newf:
                loframes += newf
            if curframe ==  False and loframes:
                if opts.json:
                    json.dump(loframes,opts.fileout)
                else:
                    for aframe in loframes:
                        opts.fileout.write(pref+"frame: ")
                        opts.fileout.write(binascii.hexlify(bytearray(aframe)).decode('ascii'))
                        pref="\n"
                loframes = []
    except:
        pass

    if curframe and len(curframe):
        try:
            loframes.append(int(curframe,2).to_bytes(len(curframe)//8,ENDIAN))
        except Exception as e:
            print("Weird....with {}: {}".format(curframe,e))
        curframe = False
    if curframe ==  False and loframes:
        if opts.json:
            json.dump(loframes,opts.fileout)
        else:
            for aframe in loframes:
                opts.fileout.write(pref+"frame: ")
                opts.fileout.write(binascii.hexlify(bytearray(aframe)).decode('ascii'))
                pref="\n"
        loframes = []
    if not opts.json:
        opts.fileout.write(pref)


