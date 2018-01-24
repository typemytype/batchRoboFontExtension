from fontTools.misc.py23 import *
from fontTools.misc.py23 import PY2

import os
import tempfile

from fontTools.ttLib import TTFont


ttf2eot = os.path.join(os.path.dirname(__file__), "ttf2eot")
os.chmod(ttf2eot, 0o0777)


def generateEOT(source, dest):
    # ttf2eot has this weird 'ttf2eot < source.ttf > out.eot' commandline input..
    cmd = "'%s' < '%s' > '%s'" % (ttf2eot, source, dest)
    os.system(cmd)


def _winStr(content):
    s = content.replace('\x00', "")
    s = "".join(s)
    if PY2:
        s = str(unicode(s, "utf8"))
    s = s.strip()
    return s.encode("utf_16_be")


def _macStr(content):
    s = content.replace('\x00', "")
    s = "".join(s)
    s = s.strip()
    if PY2:
        s = unicode(s, "utf8").encode("latin-1")
    return s


def _optimizeForEOT(sourcePath, destPath):
    source = TTFont(sourcePath)
    # fix naming
    nameTable = source["name"]
    familyName = nameTable.getName(1, 3, 1)
    styleName = nameTable.getName(2, 3, 1)
    if familyName:
        familyName = familyName.string
    else:
        familyName = "Untitled"
    if styleName:
        styleName = styleName.string
    else:
        styleName = "Regular"

    records = []
    for record in nameTable.names:
        # ignore preferred naming
        if record.nameID not in [16, 17]:
            if record.nameID == 4:
                s = "%s %s" % (familyName, styleName)
                if record.platformID == 3 and record.platEncID in (0, 1):
                    record.string = _winStr(s)
                else:
                    record.string = _macStr(s)
        records.append(record)

    nameTable.names = records

    # set embedding bit
    os2 = source["OS/2"]
    os2.fsType = 4
    source.save(destPath)
    source.close()


def EOTBuilder(sourcePath, destinationPath):
    tempTTF = tempfile.mkstemp(suffix=".ttf")[1]
    _optimizeForEOT(sourcePath, tempTTF)
    generateEOT(tempTTF, destinationPath)
    if os.path.exists(tempTTF):
        os.remove(tempTTF)
