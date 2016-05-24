import os
import tempfile
import shutil

from AppKit import *

import string
import re
import time

from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController

from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

from compositor import Font as CompositorFont

from lib.settings import shouldAddPointsInSplineConversionLibKey
from lib.scripting.codeEditor import CodeEditor

from mojo.roboFont import OpenFont
from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.compile import autohint as OTFAutohint

from woffBuilder import WOFFBuilder
from woff2Builder import WOFF2Builder
from eotBuilder import EOTBuilder
from svgBuilder import SVGBuilder
from autohint import TTFAutohint, defaultOptions, TTFAutoHintGroup
from htmlWriter import HTMLWriter, CSSWriter

from batchTools import Report, settingsIdentifier, buildTree

hasUfo2svg = True

try:
    import ufo2svg
except:
    hasUfo2svg = False


def getFontBounds(font):
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    for g in gs.keys():
        gs[g].draw(pen)
    return pen.bounds


def fixMetrics(font):
    minx, miny, maxx, maxy = getFontBounds(font)
    font["OS/2"].usWinDescent = abs(miny)
    font["OS/2"].usWinAscent = abs(maxy)
    font["hhea"].descent = miny
    font["hhea"].ascent = maxy

defaultFontInfoAttributes = ["familyName", "styleName", "descender", "xHeight", "ascender", "capHeight", "unitsPerEm"]


def convertToTTF(otfPath, dest, report):
    temp = tempfile.mkstemp(suffix=".ttf")[1]
    tempDest = tempfile.mkstemp(suffix=".ttf")[1]

    font = OpenFont(otfPath, showUI=False)
    font.lib[shouldAddPointsInSplineConversionLibKey] = 1
    font.kerning.clear()

    for attr in font.info.asDict().keys():
        if attr not in defaultFontInfoAttributes:
            setattr(font.info, attr, None)

    result = font.generate(temp, "ttf", decompose=False, checkOutlines=False, autohint=False, releaseMode=True, glyphOrder=font.glyphOrder)
    font.close()
    report.write(result)

    sourceFont = TTFont(temp)
    sourceFontWithTables = TTFont(otfPath)

    for table in ["loca", "OS/2", "cmap", "name", "GSUB", "GPOS", "GDEF", "kern"]:
        if table in sourceFontWithTables:
            sourceFont[table] = sourceFontWithTables[table]
    fixMetrics(sourceFont)
    sourceFont.save(tempDest)

    sourceFont.close()
    del sourceFont
    sourceFontWithTables.close()
    del sourceFontWithTables

    autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
    result = TTFAutohint(tempDest, dest, autohintOptions)
    report.writeItems(result)

    os.remove(temp)
    os.remove(tempDest)


def convertToOTF(ttfPath, dest, report):
    temp = tempfile.mkstemp(suffix=".otf")[1]

    font = OpenFont(ttfPath, showUI=False)
    font.kerning.clear()
    for attr in font.info.asDict().keys():
        if attr not in defaultFontInfoAttributes:
            setattr(font.info, attr, None)

    result = font.generate(temp, "otf", decompose=False, checkOutlines=False, autohint=False, releaseMode=True, glyphOrder=font.glyphOrder)
    font.close()
    report.write(result)

    sourceFont = TTFont(temp)
    sourceFontWithTables = TTFont(ttfPath)
    for table in ["loca", "OS/2", "cmap", "name", "GSUB", "GPOS", "GDEF", "kern"]:
        if table in sourceFontWithTables:
            sourceFont[table] = sourceFontWithTables[table]

    sourceFont.save(dest)

    result = OTFAutohint(dest)
    report.writeItems(result)

    os.remove(temp)


def generateTTF(ufoPath, dest, report):
    tempDest = tempfile.mkstemp(suffix=".ttf")[1]

    font = OpenFont(ufoPath, showUI=False)
    font.lib[shouldAddPointsInSplineConversionLibKey] = 1

    result = font.generate(tempDest, "ttf", decompose=False, checkOutlines=True, autohint=False, releaseMode=True, glyphOrder=font.glyphOrder)
    font.close()
    report.write(result)

    autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
    result = TTFAutohint(tempDest, dest, autohintOptions)
    report.writeItems(result)

    os.remove(tempDest)


def generateOTF(ufoPath, dest, report):
    font = OpenFont(ufoPath, showUI=False)

    result = font.generate(dest, "otf", decompose=False, checkOutlines=True, autohint=False, releaseMode=True, glyphOrder=font.glyphOrder)
    font.close()
    report.write(result)

    result = OTFAutohint(dest)
    report.writeItems(result)


def convertToWoff(ttfPath, dest):
    WOFFBuilder(ttfPath, dest)


def convertToWoff2(ttfPath, dest):
    WOFF2Builder(ttfPath, dest)


def convertToEot(ttfPath, dest):
    EOTBuilder(ttfPath, dest)


def convertToSVG(ttfPath, dest):
    SVGBuilder(ttfPath, dest)


htmlPreviewDefault = string.ascii_letters + string.digits


class TTHAutoHintSettings(BaseWindowController):

    identifier = "%s.%s" % (settingsIdentifier, "autohintSettings")

    def __init__(self, parentWindow):

        data = getExtensionDefault(self.identifier, dict())
        self.w = Sheet((470, 580), parentWindow=parentWindow)

        self.w.tabs = Tabs((10, 10, -10, -40), ["TTF AutoHint", "HTML Preview"])
        self.w.tabs[0].settings = self.settings = TTFAutoHintGroup((0, 0, -0, -0))
        self.settings.set(data)

        y = 10
        self.w.tabs[1].htmlText = TextBox((10, y, 100, 22), "HTML preview:")
        y += 30
        self.w.tabs[1].html = self.html = CodeEditor((10, y, -10, 250), getExtensionDefault("%s.htmlPreview" % settingsIdentifier, htmlPreviewDefault), lexer="html", showlineNumbers=False)
        y += 260
        self.w.tabs[1].globalCssText = TextBox((10, y, 100, 22), "CSS Style:")
        y += 30
        self.w.tabs[1].globalCss = self.globalCss = CodeEditor((10, y, -10, -10), getExtensionDefault("%s.globalCSSPreview" % settingsIdentifier, ""), lexer="css", showlineNumbers=False)

        self.w.saveButton = Button((-100, -30, -10, 20), "Save settings", callback=self.saveCallback, sizeStyle="small")
        self.w.setDefaultButton(self.w.saveButton)

        self.w.closeButton = Button((-190, -30, -110, 20), "Cancel", callback=self.closeCallback, sizeStyle="small")
        self.w.closeButton.bind(".", ["command"])
        self.w.closeButton.bind(unichr(27), [])

        self.w.resetButton = Button((-280, -30, -200, 20), "Reset", callback=self.resetCallback, sizeStyle="small")
        self.w.open()

    def resetCallback(self, sender):
        if self.w.tabs.get() == 0:
            self.settings.set(None)
        else:
            setExtensionDefault("%s.htmlPreview" % settingsIdentifier, htmlPreviewDefault)
            self.html.set(htmlPreviewDefault)
            setExtensionDefault("%s.globalCSSPreview" % settingsIdentifier, "")
            self.globalCss.set("")

    def saveCallback(self, sender):
        data = self.settings.get()
        setExtensionDefault(self.identifier, data)
        setExtensionDefault("%s.htmlPreview" % settingsIdentifier, self.html.get())
        setExtensionDefault("%s.globalCSSPreview" % settingsIdentifier, self.globalCss.get())
        self.closeCallback(sender)

    def closeCallback(self, sender):
        self.w.close()

_percentageRe = re.compile("%(?!\((familyName|styleName)\)s)")


class BatchRadioGroup(RadioGroup):

    def __init__(self, posSize, titles, value=0, isVertical=True, callback=None, sizeStyle='regular'):
        super(BatchRadioGroup, self).__init__(posSize, titles, isVertical=isVertical, callback=callback, sizeStyle=sizeStyle)
        self.set(value)


WOFF_OTF_FORMAT = 0
WOFF_TTF_FORMAT = 1


class WebFormats(Group):

    webSettings = ["Save OTF", "Save TTF", "Save Woff", "Save Woff2", "Save EOT", "Save SVG"]

    def __init__(self, posSize, controller):
        super(WebFormats, self).__init__(posSize)
        self.controller = controller

        y = 10
        for setting in self.webSettings:
            key = setting.replace(" ", "_").lower()
            checkBox = CheckBox((10, y, -10, 22), setting,
                                value=getExtensionDefault("%s.%s" % (settingsIdentifier, key), True),
                                callback=self.saveDefaults)
            setattr(self, key, checkBox)
            if "Woff" in setting:
                formatOption = BatchRadioGroup((120, y, 85, 22),
                                            ["OTF", "TTF"],
                                            value=getExtensionDefault("%s.format_%s" % (settingsIdentifier, key), True),
                                            callback=self.saveDefaults,
                                            isVertical=False,
                                            sizeStyle="mini")
                setattr(self, "%s_format" % key, formatOption)
            y += 30

        self.save_svg.enable(hasUfo2svg)
        y += 5
        self.preserveTTFhints = CheckBox((10, y, -10, 18), "Preserve TTF hints",
            value=getExtensionDefault("%s.preserveTTFhints" % settingsIdentifier, False),
            sizeStyle="small")
        y += 30

        middle = 45
        self.suffixText = TextBox((10, y + 2, middle, 22), "Suffix:", alignment="right")
        self.webSuffix = EditText((middle + 10, y, 100, 22),
            getExtensionDefault("%s.webSuffix" % settingsIdentifier, "_web"),
            callback=self.saveDefaults)
        y += 30

        self.convert = Button((-100, -30, -10, 22), "Generate", callback=self.convertCallback)
        self.settings = ImageButton((-130, -28, 20, 20), bordered=False, imageNamed=NSImageNameSmartBadgeTemplate, callback=self.settingsCallback)

        self.height = y

    def saveDefaults(self, sender):
        for setting in self.webSettings:
            key = setting.replace(" ", "_").lower()
            value = getattr(self, key).get()
            setExtensionDefault("%s.%s" % (settingsIdentifier, key), value)
            if "Woff" in setting:
                value = getattr(self, "%s_format" % key).get()
                setExtensionDefault("%s.format_%s" % (settingsIdentifier, key), value)

        for key in ["webSuffix", "preserveTTFhints"]:
            value = getattr(self, key).get()
            setExtensionDefault("%s.%s" % (settingsIdentifier, key), value)

    # convert

    def _getTempTTF(self, path, report=None, preserveTTFhints=False):
        if not hasattr(self, "_tempTTFPath"):
            _, ext = os.path.splitext(path)
            ext = ext.lower()
            self._tempTTFPath = tempfile.mkstemp(suffix=".ttf")[1]
            if ext == ".otf":
                report.write("Source is binary a OTF file. Convert to TTF.")
                report.indent()
                convertToTTF(path, self._tempTTFPath, report)
                report.dedent()
            elif ext == ".ttf":
                report.write("Source is binary a TTF file.")
                shutil.copyfile(path, self._tempTTFPath)
                if not preserveTTFhints:
                    report.write("Auto hint the existing TTF file.")
                    report.indent()
                    tempDest = tempfile.mkstemp(suffix=".ttf")[1]
                    autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
                    result = TTFAutohint(self._tempTTFPath, tempDest, autohintOptions)
                    report.writeItems(result)
                    os.remove(self._tempTTFPath)
                    self._tempTTFPath = tempDest
                    report.dedent()
            else:
                if ext == ".ufo":
                    report.write("Source is a UFO file. Generate TTF.")
                else:
                    report.write("Source is a %s file. Import the file. Generate TTF." % (ext[1:]))
                report.indent()
                generateTTF(path, self._tempTTFPath, report)
                report.dedent()
        return self._tempTTFPath

    def _getTempOTF(self, path, report=None, preserveTTFhints=False):
        if not hasattr(self, "_tempOTFPath"):
            _, ext = os.path.splitext(path)
            ext = ext.lower()
            self._tempOTFPath = tempfile.mkstemp(suffix=".otf")[1]
            if ext == ".otf":
                report.write("Source is binary a OTF file.")
                shutil.copyfile(path, self._tempOTFPath)
                if not preserveTTFhints:
                    report.write("Auto hint the existing OTF file.")
                    report.indent()
                    result = OTFAutohint(self._tempOTFPath)
                    report.writeItems(result)
                    report.dedent()
            elif ext == ".ttf":
                report.write("Source is binary a TTF file. Convert to OTF.")
                report.indent()
                convertToOTF(path, self._tempOTFPath, report)
                report.dedent()
            else:
                if ext == ".ufo":
                    report.write("Source is a UFO file. Generate OTF.")
                else:
                    report.write("Source is a %s file. Import the file. Generate OTF." % (ext[1:]))
                report.indent()
                generateOTF(path, self._tempOTFPath, report)
                report.dedent()
        return self._tempOTFPath

    def _removeTempFiles(self):
        if hasattr(self, "_tempTTFPath"):
            if os.path.exists(self._tempTTFPath):
                os.remove(self._tempTTFPath)
                del self._tempTTFPath
        if hasattr(self, "_tempOTFPath"):
            if os.path.exists(self._tempOTFPath):
                os.remove(self._tempOTFPath)
                del self._tempOTFPath

    def _convertPath(self, path, destDir, saveOTF=True, saveTTF=True, saveWOFF=True, saveWOFFFormat=WOFF_TTF_FORMAT, saveWOFF2=True, saveWOFF2Format=WOFF_TTF_FORMAT, saveEOT=True, saveSVG=False, suffix="", report=None, preserveTTFhints=False):
        fileName = os.path.basename(path)
        fileName, ext = os.path.splitext(fileName)
        ext = ext.lower()

        if ext in [".ttf", ".otf"]:
            font = CompositorFont(path)
        else:
            font = OpenFont(path, showUI=False)

        familyName = font.info.familyName
        styleName = font.info.styleName

        if not self.controller.keepFileNames():
            fileName = "%s-%s" % (familyName, styleName)
        fileName += suffix
        fileName = fileName.replace(" ", "_")

        if self.controller.exportInFolders():
            fontDir = os.path.join(destDir, familyName.replace(" ", ""), styleName.replace(" ", ""))
        else:
            fontDir = destDir

        otfPath = os.path.join(fontDir, fileName + ".otf")
        ttfPath = os.path.join(fontDir, fileName + ".ttf")
        woffPath = os.path.join(fontDir, fileName + ".woff")
        woff2Path = os.path.join(fontDir, fileName + ".woff2")
        eotPath = os.path.join(fontDir, fileName + ".eot")
        svgPath = os.path.join(fontDir, fileName + ".svg")

        # save otf
        if saveOTF:
            report.writeTitle("Build OTF", "'")
            report.indent()
            report.write("path: %s" % otfPath)
            buildTree(fontDir)
            temp = self._getTempOTF(path, report=report, preserveTTFhints=preserveTTFhints)
            shutil.copyfile(temp, otfPath)
            report.dedent()
            report.newLine()

        # save ttf
        if saveTTF:
            report.writeTitle("Build TTF", "'")
            report.indent()
            report.write("path: %s" % ttfPath)
            buildTree(fontDir)
            temp = self._getTempTTF(path, report=report, preserveTTFhints=preserveTTFhints)
            shutil.copyfile(temp, ttfPath)
            report.dedent()
            report.newLine()

        # convert to woff
        if saveWOFF:
            if saveWOFFFormat == WOFF_TTF_FORMAT:
                func = self._getTempTTF
                reportFormat = "TTF"
            elif saveWOFFFormat == WOFF_OTF_FORMAT:
                func = self._getTempOTF
                reportFormat = "OTF"
            report.writeTitle("Build WOFF (%s)" % reportFormat, "'")
            report.indent()
            report.write("path: %s" % woffPath)
            buildTree(fontDir)
            temp = func(path, report=report, preserveTTFhints=preserveTTFhints)
            convertToWoff(temp, woffPath)
            report.dedent()
            report.newLine()

        # convert to woff2
        if saveWOFF2:
            if saveWOFFFormat == WOFF_TTF_FORMAT:
                func = self._getTempTTF
                reportFormat = "TTF"
            elif saveWOFFFormat == WOFF_OTF_FORMAT:
                func = self._getTempOTF
                reportFormat = "OTF"
            report.writeTitle("Build WOFF2 (%s)" % reportFormat, "'")
            report.indent()
            report.write("path: %s" % woff2Path)
            buildTree(fontDir)
            temp = func(path, report=report, preserveTTFhints=preserveTTFhints)
            convertToWoff2(temp, woff2Path)
            report.dedent()
            report.newLine()

        # convert to eot
        if saveEOT:
            report.writeTitle("Build EOT", "'")
            report.indent()
            report.write("path: %s" % eotPath)
            buildTree(fontDir)
            temp = self._getTempTTF(path, report=report, preserveTTFhints=preserveTTFhints)
            convertToEot(temp, eotPath)
            report.dedent()
            report.newLine()

        # convert to svg
        if saveSVG:
            report.writeTitle("Build SVG", "'")
            report.indent()
            report.write("path: %s" % svgPath)
            buildTree(fontDir)
            convertToSVG(path, svgPath)
            report.dedent()
            report.newLine()

        self._removeTempFiles()

        self._writeHTMLPreview(report.html, report.css, fileName, familyName, styleName, saveTTF, saveWOFF, saveWOFF2, saveEOT, saveSVG)

    def _writeHTMLPreview(self, htmlWriter, cssWriter, fileName, familyName, styleName, saveTTF, saveWOFF, saveWOFF2, saveEOT, saveSVG):
        # css
        if self.controller.exportInFolders():
            cssFileName = "%s/%s/%s" % (familyName.replace(" ", ""), styleName.replace(" ", ""), fileName)
        else:
            cssFileName = fileName

        cssWriter.write("@font-face {")
        cssWriter.indent()
        cssWriter.write("font-family: '%s_%s';" % (familyName, styleName))

        cssSources = []
        if saveEOT:
            cssWriter.write("src:    url('%s.eot');" % cssFileName)
            cssSources.append("url('%s.eot?#iefix') format('embedded-opentype')" % cssFileName)
        if saveWOFF:
            cssSources.append("url('%s.woff') format('woff')" % cssFileName)
        if saveWOFF2:
            cssSources.append("url('%s.woff2') format('woff2')" % cssFileName)
        if saveTTF:
            cssSources.append("url('%s.ttf') format('truetype')" % cssFileName)
        if saveSVG:
            cssSources.append("url('%s.svg#svgFontName') format('svg')" % cssFileName)

        cssWriter.write("src:    %s;" % (",\n        ".join(cssSources)))
        cssWriter.write("font-weight: normal;")
        cssWriter.write("font-style: normal;")
        cssWriter.dedent()
        cssWriter.write("}")
        cssWriter.newLine()

        # html
        htmlWriter.write("<div style='font-family: \"%s_%s\", \"AdobeBlank\";'>" % (familyName, styleName))
        html = getExtensionDefault("%s.htmlPreview" % settingsIdentifier, htmlPreviewDefault)
        html = _percentageRe.sub("&#37;", html)
        html = html % dict(familyName=familyName, styleName=styleName)
        htmlWriter.write(html.encode("ascii", 'xmlcharrefreplace'))
        htmlWriter.write("</div>")

    def run(self, destDir, progress):
        progress.update("Converting...")

        paths = self.controller.get()

        report = Report()
        report.css = CSSWriter()
        report.html = HTMLWriter(cssFileName="font.css", style=getExtensionDefault("%s.globalCSSPreview" % settingsIdentifier, ""))

        report.writeTitle("Web Fonts:")
        report.newLine()

        saveOTF = self.save_otf.get()
        saveTTF = self.save_ttf.get()
        saveWOFF = self.save_woff.get()
        saveWOFFFormat = self.save_woff_format.get()
        saveWOFF2 = self.save_woff2.get()
        saveWOFF2Format = self.save_woff2_format.get()
        saveEOT = self.save_eot.get()
        saveSVG = self.save_svg.get()
        suffix = self.webSuffix.get()
        suffix = time.strftime(suffix)

        preserveTTFhints = self.preserveTTFhints.get()

        progress.setTickCount(len(paths))

        for path in paths:
            txt = os.path.basename(path)
            progress.update(txt)
            report.writeTitle(os.path.basename(path), "-")
            report.write("source: %s" % path)
            report.newLine()
            try:
                self._convertPath(path, destDir=destDir, saveOTF=saveOTF, saveTTF=saveTTF, saveWOFF=saveWOFF, saveWOFFFormat=saveWOFFFormat, saveWOFF2=saveWOFF2, saveWOFF2Format=saveWOFF2Format, saveEOT=saveEOT, saveSVG=saveSVG, suffix=suffix, report=report, preserveTTFhints=preserveTTFhints)
            except:
                import traceback
                message = traceback.format_exc()
                report.write("Failed:")
                report.write(message)
                report.indent(0)
            report.newLine()

        report.newLine()
        report.writeTitle("TTFAutohint options:")
        autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
        report.writeDict(autohintOptions)

        reportPath = os.path.join(destDir, "WebFonts Report.txt")
        report.save(reportPath)

        cssPath = os.path.join(destDir, "font.css")
        report.css.save(cssPath)

        htmlPath = os.path.join(destDir, "preview.html")
        report.html.save(htmlPath)

    def _convert(self, destDir):
        if not destDir:
            return
        destDir = destDir[0]
        self.controller.runTask(self.run, destDir=destDir)

    def convertCallback(self, sender):
        if not self.controller.hasSourceFonts("No Fonts to Generate.", "Add Open, drop or add Open Fonts fonts to batch them."):
            return
        self.controller.showGetFolder(self._convert)

    def settingsCallback(self, sender):
        TTHAutoHintSettings(self.controller.window())


if __name__ == "__main__":

    class TestWindow:

        def __init__(self):
            self.w = Window((400, 400))
            self.w.wf = WebFormats((0, 0, -10, -10), self)
            self.w.open()

    TestWindow()
