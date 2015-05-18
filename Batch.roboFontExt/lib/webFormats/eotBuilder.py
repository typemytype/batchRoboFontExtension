import os
import tempfile

from fontTools.ttLib import TTFont

from mojo.compile import executeCommand

ttf2eot = os.path.join(os.path.dirname(__file__), "ttf2eot")

def generateEOT(source, dest):
    cmds = [ttf2eot]
    cmds.append("<")
    cmds.append(source)
    cmds.append(">")
    cmds.append(dest)

    result = executeCommand(cmds)
    return result

def _winStr(content):
    s = content.replace('\x00', "")
    s = "".join(s)
    s = str(unicode(s, "utf8"))
    s = s.strip()
    return s.encode("utf_16_be")

def _macStr(content):
    s = content.replace('\x00', "")
    s = "".join(s)
    s = s.strip()
    return unicode(s, "utf8").encode("latin1")

def _optimizeForEOT(sourcePath, destPath):
    source = TTFont(sourcePath)
    ## fix naming
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