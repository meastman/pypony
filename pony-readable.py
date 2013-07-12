#!/usr/bin/env python
import base64
import getopt
import os
import random
import re
import string
import sys
import bz2

TEMPLATE = """\
          ******************
        *************************
     *********xx*******************
    **********xxxxx***xxxxxx********
    *********xxxxxx***xxxxxxxx********
   ***********xxxxx***xxxxxxxxxx********
  *xxxxxxxxxx****xx***xxxxxxxxxxx********
  *xxxxxxxxxxxxxx****xxxxxxxxxxxxx*******
 *xxxxxxx**xxxxxx****xxxxxxxxxxxxxx*******
 *xxxxxx****xxxxx*****xxxxxxxxxxxxxx******
 *xxxxxxx**xxxxx**xx**xxxxxxxxxxxxxx*******
 *xxxxxxxxxxxx**xxxx**xxxxxxxxxxxxxx*******
****xxxxxxxxx**xxxxx*xxxxxxxxxxxxxxxx******
*xxx*****xxx**xxxxxxxxxxxxxxxxxxxxxxx*******         *****
*xxxxxxx****xxxxxxxxxxxxxxxxxxxx*********************xxxxx** ******
*xxxxxxxxxxx*****xxxxxxxxx*******xxxxxxx**xxxxxxxxx**xxxxxxxxx*******
 *xxxxxxx***  *xx**********xxxxxxxxxxxxxx**xxxxxxxxxx**xxxxxxxx*******
    *****      *xxxxxxxxxxxxxxxxxxxxxxxxxx**xxxxxxxxxx**xxxxxxxxx******
             **xxxxxxxxxxxxxxxxxxxxxxxxxxxx**xxxxxxxx**xxxxxxxxx*******
             *xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx*********xxxxxxxxxxxx*****
             *xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx*****xxxxxxxxxxxxxx*****
             *xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx**xxxxxxxxxxxxxxxx*****
             *xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx**xxxxxxxxxxxxxxxx******
             *xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx**xxxxxxxxxxxxxxxxx**  *
             *xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx**xxxxxxxxxxxxxxxxx***
             *xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx**xxxxxxxxxxxxxxxxxx***
            *xxxxxxxxxxxxxxxxxxxxxxxxxxxx****xxxxxxxxxxxxxxxxxxxx***
            *xxxxxxxxxxxxxxxxxxxxxxxxxxx*xxxxxxx**xxxxxxxxxxxxxxxx***
           *xxxxxxxxxxxxxxxxxxxxxxxxxxxx*xxxxxx** **xxxxxxxxxxxxxxx***
           *xxxxxxxxxxxxxxxxxxxxxxxxxxxx*xxxxxx*    *xxxxxxxxxxxxxx****
          *xxxxxxxxxxxxxxxxxxxxxxxxxxxx*xxxxxx*      *xxxxxxxxxxxxx****
         *xxxxxxxxxxxxxx*xxxxxxxxxxxxxx*xxxxx*        *xxxxxxxxxxxx***
         *xxxxxxxxxxxxx* *xxxxxxxxxxxx*xxxxx*         *xxxxxxxxxxxx***
        *xxxxxxxxxxxx**  *xxxxxxxxxxxx*xxxxx*         *xxxxxxxxxxxx***
       *xxxxxxxxxxx**    *xxxxxxxxxxx*xxxx**          *xxxxxxxxxxx***
       ************     *xxxxxxxxxxx******            *xxxxxxxxxxx***
         *******       *xxxxxxxxxxxx*                 *xxxxxxxxxxx**
                       ***xxxxxxxxx**                 ************
                        ************                       ***
                          *****

"""

TEMPLATE_CHARS = TEMPLATE.count('x')
TEMPLATE_BYTES = (TEMPLATE_CHARS // 4) * 3


def _encode_chunk(inchunk):
    echunk = list(base64.b64encode(inchunk).rstrip('='))
    if len(echunk) < TEMPLATE_CHARS:
        charset = string.letters + string.digits + '+/'
        echunk.append('=')
        while len(echunk) < TEMPLATE_CHARS:
            echunk.append(random.choice(charset))
    return re.sub('x', lambda m: echunk.pop(0), TEMPLATE)


def encode(instream, outstream):
    buf = ''
    compressor = bz2.BZ2Compressor(9)
    while True:
        rawdata = instream.read(1024)
        if rawdata:
            buf += compressor.compress(rawdata)
        else:
            buf += compressor.flush()
        while len(buf) >= TEMPLATE_BYTES:
            outstream.write(_encode_chunk(buf[:TEMPLATE_BYTES]))
            buf = buf[TEMPLATE_BYTES:]
        if not rawdata:
            break

    if buf:
        outstream.write(_encode_chunk(buf))


def decode(instream, outstream):
    decompressor = bz2.BZ2Decompressor()
    buf = ''
    for data in instream:
        if '**' not in data:
            continue
        buf += re.sub('[^a-zA-Z0-9+/=]', '', data).split('=')[0]
        eaten = (len(buf) // 4) * 4
        if eaten:
            bytes = base64.b64decode(buf[:eaten])
            outstream.write(decompressor.decompress(bytes))
            buf = buf[eaten:]
        if '=' in data:
            break
    if buf:
        buf += '=' * (3 - ((len(buf) - 1) % 4))
        bytes = base64.b64decode(buf)
        outstream.write(decompressor.decompress(bytes))


def show_usage(stream):
    progname = os.path.basename(sys.argv[0])
    print >>stream, 'Usage: %s (--usage | --encode | --decode)' % progname
    print >>stream


def main():
    shortargs = 'huedp'
    longargs = ('help', 'usage', 'encode', 'decode', 'python')

    try:
        getopt_func = getopt.gnu_getopt
    except AttributeError:
        getopt_func = getopt.getopt
    try:
        opts, args = getopt_func(sys.argv[1:], shortargs, longargs)
    except getopt.GetoptError, error:
        print >>sys.stderr, 'Error: ' + str(error)
        show_usage(sys.stderr)
        sys.exit(1)

    action = None
    actionopt = None
    pythonize = False
    for opt, value in opts:
        if opt in ('-h', '--help', '-u', '--usage'):
            show_usage(sys.stdout)
            sys.exit(0)
        elif opt in ('-e', '--encode'):
            if action is None:
                action = 'encode'
                actionopt = opt
            else:
                print >>sys.stderr, 'Error: %s cannot be combined with %s' % \
                    (opt, actionopt)
                show_usage(sys.stderr)
                sys.exit(1)
        elif opt in ('-d', '--decode'):
            if action is None:
                action = 'decode'
                actionopt = opt
            else:
                print >>sys.stderr, 'Error: %s cannot be combined with %s' % \
                    (opt, actionopt)
                show_usage(sys.stderr)
                sys.exit(1)
        elif opt in ('-p', '--python'):
            pythonize = True
        else:
            print >>sys.stderr, 'Error: unrecognized option %s' % opt
            show_usage(sys.stderr)
            sys.exit(1)

    if args:
        print >>sys.stderr, 'Error: unrecognized option "%s"' % args[0]
        show_usage(sys.stderr)
        sys.exit(1)

    if action is None:
        print >>sys.stderr, 'Error: no action was specified'
        show_usage(sys.stderr)
        sys.exit(1)
    elif action == 'encode':
        if pythonize:
            print '#!/usr/bin/env python'
            print '"""'
        encode(sys.stdin, sys.stdout)
        if pythonize:
            print '"""'
            print "import re,bz2;t=re.sub('[^a-zA-Z0-9+/=]','',__doc__).split('=')[0]"
            print "t+='='*(3-((len(t)-1)%4));exec bz2.decompress(t.decode('base64'))"
    elif action == 'decode':
        decode(sys.stdin, sys.stdout)
    else:
        print >>sys.stderr, 'BUG: did not recognize action %s' % action
        sys.exit(1)

if __name__ == '__main__':
    main()
