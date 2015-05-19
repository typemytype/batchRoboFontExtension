import os
import tempfile
import shutil

from AppKit import *

import string
import re

from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController

from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

from compositor import Font as CompositorFont

from lib.settings import shouldAddPointsInSplineConversionLibKey
from lib.scripting.codeEditor import CodeEditor

from mojo.roboFont import OpenFont
from mojo.extensions import getExtensionDefault, setExtensionDefault

from woffBuilder import WOFFBuilder
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


def convertToTTF(otfPath, dest):
    temp = tempfile.mkstemp(suffix=".ttf")[1]
    tempDest = tempfile.mkstemp(suffix=".ttf")[1]

    defaultFontInfoAttributes = ["familyName", "styleName", "descender", "xHeight", "ascender", "capHeight", "unitsPerEm"]

    font = OpenFont(otfPath, showUI=False)
    font.lib[shouldAddPointsInSplineConversionLibKey] = 1

    for attr in font.info.asDict().keys():
        if attr not in defaultFontInfoAttributes:
            setattr(font.info, attr, None)

    font.generate(temp, "ttf", decompose=False, checkOutlines=False, autohint=False, releaseMode=True, glyphOrder=font.glyphOrder)
    font.close()

    sourceFont = TTFont(temp)
    sourceFontWithTables = TTFont(otfPath)

    for table in ["loca", "OS/2", "cmap", "name", "GSUB", "GPOS"]:
        if table in sourceFontWithTables:
            sourceFont[table] = sourceFontWithTables[table]
    fixMetrics(sourceFont)
    sourceFont.save(tempDest)

    sourceFont.close()
    del sourceFont
    sourceFontWithTables.close()
    del sourceFontWithTables

    autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
    TTFAutohint(tempDest, dest, autohintOptions)

    os.remove(temp)
    os.remove(tempDest)


def generateTTF(ufoPath, dest):
    tempDest = tempfile.mkstemp(suffix=".ttf")[1]

    font = OpenFont(ufoPath, showUI=False)
    font.lib[shouldAddPointsInSplineConversionLibKey] = 1

    font.generate(tempDest, "ttf", decompose=False, checkOutlines=True, autohint=False, releaseMode=True, glyphOrder=font.glyphOrder)
    font.close()

    autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
    TTFAutohint(tempDest, dest, autohintOptions)

    os.remove(tempDest)


def convertToWoff(ttfPath, dest):
    WOFFBuilder(ttfPath, dest)


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


class WebFormats(Group):

    webSettings = ["Save TTF", "Save Woff", "Save EOT", "Save SVG"]

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
            y += 30

        self.save_svg.enable(hasUfo2svg)

        middle = 45
        self.suffixText = TextBox((10, y+2, middle, 22), "Suffix:", alignment="right")
        self.webSuffix = EditText((middle+10, y, 100, 22),
            getExtensionDefault("%s.webSuffix" % settingsIdentifier, "_web"),
            callback=self.saveDefaults)

        self.preserveTTFhints = CheckBox((10, -25, -10, 18), "Preserve TTF hints",
            value=getExtensionDefault("%s.preserveTTFhints" % settingsIdentifier, False),
            sizeStyle="small")
        self.convert = Button((-100, -30, -10, 22), "Convert", callback=self.convertCallback)
        self.settings = ImageButton((-130, -28, 20, 20), bordered=False, imageNamed=NSImageNameSmartBadgeTemplate, callback=self.settingsCallback)

    def saveDefaults(self, sender):
        for setting in self.webSettings:
            key = setting.replace(" ", "_").lower()
            value = getattr(self, key).get()
            setExtensionDefault("%s.%s" % (settingsIdentifier, key), value)

        for key in ["webSuffix", "preserveTTFhints"]:
            value = getattr(self, key).get()
            setExtensionDefault("%s.%s" % (settingsIdentifier, key), value)

    # convert

    def _convertPath(self, path, destDir, saveTTF=True, saveWOFF=True, saveEOT=True, saveSVG=False, suffix="", report=None, preserveTTFhints=False):
        fileName = os.path.basename(path)
        fileName, ext = os.path.splitext(fileName)
        fileName += suffix

        tempTTF = tempfile.mkstemp(suffix=".ttf")[1]

        if ext == ".otf":
            convertToTTF(path, tempTTF)
        elif ext == ".ttf":
            shutil.copyfile(path, tempTTF)
            if not preserveTTFhints:
                tempDest = tempfile.mkstemp(suffix=".ttf")[1]
                autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
                TTFAutohint(tempTTF, tempDest, autohintOptions)
                os.remove(tempTTF)
                tempTTF = tempDest
        elif ext == ".ufo":
            generateTTF(path, tempTTF)

        font = CompositorFont(tempTTF)
        familyName = font.info.familyName
        styleName = font.info.styleName

        if self.controller.exportInFolders():
            fontDir = os.path.join(destDir, familyName.replace(" ", ""), styleName.replace(" ", ""))
        else:
            fontDir = destDir

        ttfPath = os.path.join(fontDir, fileName + ".ttf")
        woffPath = os.path.join(fontDir, fileName + ".woff")
        eotPath = os.path.join(fontDir, fileName + ".eot")
        svgPath = os.path.join(fontDir, fileName + ".svg")

        # convert to eot
        if saveEOT:
            buildTree(fontDir)
            convertToEot(tempTTF, eotPath)

        # convert to woff
        if saveWOFF:
            buildTree(fontDir)
            convertToWoff(tempTTF, woffPath)

        # save ttf
        if saveTTF:
            buildTree(fontDir)
            shutil.copyfile(tempTTF, ttfPath)

        # convert to svg
        if saveSVG:
            buildTree(fontDir)
            convertToSVG(tempTTF, svgPath)

        if os.path.exists(tempTTF):
            os.remove(tempTTF)

        self._writeHTMLPreview(report.html, report.css, fileName, familyName, styleName, saveTTF, saveWOFF, saveEOT, saveSVG)

    def _writeHTMLPreview(self, htmlWriter, cssWriter, fileName, familyName, styleName, saveTTF, saveWOFF, saveEOT, saveSVG):
        # css
        if self.controller.exportInFolders():
            cssFileName = "%s/%s/%s" % (familyName.replace(" ", ""), styleName.replace(" ", ""), fileName)
        else:
            cssFileName = fileName

        cssWriter.write("@font-face {")
        cssWriter.write("\tfont-family: '%s_%s';" % (familyName, styleName))

        cssSources = []
        if saveEOT:
            cssWriter.write("\tsrc:\turl('%s.eot');" % cssFileName)
            cssSources.append("\turl('%s.eot?#iefix') format('embedded-opentype')" % cssFileName)
        if saveWOFF:
            cssSources.append("\turl('%s.woff') format('woff')" % cssFileName)
        if saveTTF:
            cssSources.append("\turl('%s.ttf') format('truetype')" % cssFileName)
        if saveSVG:
            cssSources.append("\turl('%s.svg#svgFontName') format('svg')" % cssFileName)

        cssWriter.write("\tsrc:%s;" % (",\n\t".join(cssSources)))
        cssWriter.write("\tfont-weight: normal;")
        cssWriter.write("\tfont-style: normal;")
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

        report = Report()
        report.css = CSSWriter()
        report.html = HTMLWriter(cssFileName="font.css", style=getExtensionDefault("%s.globalCSSPreview" % settingsIdentifier, ""))

        report.writeTitle("Converted Files:")

        saveTTF = self.save_ttf.get()
        saveWOFF = self.save_woff.get()
        saveEOT = self.save_eot.get()
        saveSVG = self.save_svg.get()
        suffix = self.webSuffix.get()

        preserveTTFhints = self.preserveTTFhints.get()

        paths = self.controller.get()

        progress.setTickCount(len(paths))

        for path in paths:
            txt = os.path.basename(path)
            progress.update(txt)
            report.write(path)
            self._convertPath(path, destDir=destDir, saveTTF=saveTTF, saveWOFF=saveWOFF, saveEOT=saveEOT, saveSVG=saveSVG, suffix=suffix, report=report, preserveTTFhints=preserveTTFhints)

        report.newLine()
        report.writeTitle("TTFAutohint options:")
        autohintOptions = getExtensionDefault(settingsIdentifier, defaultOptions)
        report.writeDict(autohintOptions)

        reportPath = os.path.join(destDir, "WebFonts Report")
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
        self.controller.showGetFolder(self._convert)

    def settingsCallback(self, sender):
        TTHAutoHintSettings(self.controller.window())
