import os
import tempfile
import shutil

from compositor import Font as CompositorFont
from extractor.formats.opentype import extractOpenTypeInfo

from xmlWriter import XMLWriter

from mojo.compile import executeCommand

sfnt2woff = os.path.join(os.path.dirname(__file__), "sfnt2woff")


class Info(object):

    def get(self, key, fallback=None):
        return self.__dict__.get(key, fallback)


class Font(CompositorFont):

    def loadInfo(self):
        self.info = Info()
        extractOpenTypeInfo(self.source, self)


class WoffMetaDataWriter(object):

    def __init__(self, metaDataPath, fontPath):
        self.writer = XMLWriter(metaDataPath, encoding="UTF-8")
        self.font = Font(fontPath)

        self.beginMetaData()

        self.uniqueId()
        self.vendor()
        self.credits()
        self.description()
        self.license()
        self.copyright()
        self.trademark()
        self.endMetaData()

        self.writer.close()

    def beginMetaData(self):
        self.writer.begintag("metadata")
        self.writer.newline()

    def uniqueId(self):
        url = self.font.info.get("openTypeNameManufacturerURL")
        if not url:
            return
        reverseUrl = reverseDomain(url)
        name = "%s%s" % (self.font.info.familyName, self.font.info.styleName)
        name = name.replace(" ", "")
        self.writer.simpletag("uniqueid", id="%s.%s" % (reverseUrl, name))
        self.writer.newline()

    def vendor(self):
        name = self.font.info.get("openTypeNameManufacturer")
        url = self.font.info.get("openTypeNameManufacturerURL")
        if not name or not url:
            return
        self.writer.simpletag("vendor", name=name, url=url)
        self.writer.newline()

    def credits(self):
        manufacturerName = self.font.info.get("openTypeNameManufacturer")
        manufacturerUrl = self.font.info.get("openTypeNameManufacturerURL")

        designerName = self.font.info.get("openTypeNameDesigner")
        designerUrl = self.font.info.get("openTypeNameDesignerURL")

        if not manufacturerName and not manufacturerUrl and not designerName and not designerUrl:
            return

        self.writer.begintag("credits")
        self.writer.newline()

        if manufacturerName and manufacturerUrl:
            manufacturerName = manufacturerName.encode("utf-8")
            self.writer.simpletag("credit", name=manufacturerName, url=manufacturerUrl, role="Foundry")
            self.writer.newline()
        if designerName and designerUrl:
            designerName = designerName.encode("utf-8")
            self.writer.simpletag("credit", name=designerName, url=designerUrl, role="Designer")
            self.writer.newline()

        self.writer.endtag("credits")
        self.writer.newline()

    def _addData(self, tag, infoAttr, extra=dict()):
        data = self.font.info.get(infoAttr)
        if not data:
            return
        data = data.encode("utf-8")
        self.writer.begintag(tag, **extra)
        self.writer.newline()
        self.writer.begintag("text", lang="en")
        self.writer.newline()
        self.writer.write(data)
        self.writer.endtag("text")
        self.writer.newline()
        self.writer.endtag(tag)
        self.writer.newline()

    def description(self):
        self._addData("description", "openTypeNameDescription")

    def license(self):
        extra = dict()
        licenseUrl = self.font.info.get("openTypeNameLicenseURL")
        if licenseUrl:
            extra["url"] = licenseUrl
        self._addData("license", "openTypeNameLicense", extra)

    def copyright(self):
        self._addData("copyright", "copyright")

    def trademark(self):
        self._addData("trademark", "trademark")

    def endMetaData(self):
        self.writer.endtag("metadata")
        self.writer.newline()


def reverseDomain(url):
    for r in ("http:", "www.", "/"):
        url = url.replace(r, "")
    url = url.split(".")
    url.reverse()
    return ".".join(url[-2:])


def generateWOFF(source, dest, metaData=None, version=None):
    cmds = [sfnt2woff]
    if version is not None:
        cmds.append("-v")
        cmds.append(version)
    if metaData is not None:
        cmds.append("-m")
        cmds.append(metaData)
    cmds.append(source)

    result = executeCommand(cmds)
    resultWoff = os.path.splitext(source)[0] + ".woff"
    shutil.move(resultWoff, dest)
    return result


def WOFFBuilder(sourcePath, destinationPath):
    fileName, ext = os.path.splitext(sourcePath)
    if ext.lower() not in [".otf", ".ttf"]:
        return

    xmlPath = tempfile.mkstemp(suffix=".xml")[1]

    WoffMetaDataWriter(xmlPath, sourcePath)

    result = generateWOFF(sourcePath, destinationPath, xmlPath, version="1.0")

    os.remove(xmlPath)
    return result


def WOFFBuilderFromFolder(sourceDir, destinationDir):
    for fileName in os.listdir(sourceDir):
        name, ext = os.path.splitext(fileName)
        path = os.path.join(sourceDir, fileName)
        destinationPath = os.path.join(destinationDir, name+".woff")
        WOFFBuilder(path, destinationPath)
