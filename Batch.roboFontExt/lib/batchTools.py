from AppKit import NSObject, NSThread

import shutil
import os
import re

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from fontTools.ttLib.tables._f_v_a_r import Axis, NamedInstance
from fontTools.ttLib.tables._g_v_a_r import GlyphVariation

try:
    from cu2qu.ufo import fonts_to_quadratic
except:
    print "Install cu2qu to have support for .designSpace files."

from fontCompiler.compiler import generateFont
import fontCompiler.objects as compilerObjects
from fontCompiler.settings import shouldAddPointsInSplineConversionLibKey

from mutatorMath.ufo.document import DesignSpaceDocumentReader
from mutatorMath.objects.mutator import buildMutator

from fontMath.mathGlyph import MathGlyph


settingsIdentifier = "com.typemytype.toolbox"

ufoVersion = 2


class Report(object):

    INDENT = "    "

    def __init__(self):
        self._data = []
        self._indent = 0

    def indent(self, value=None):
        if value is None:
            self._indent += 1
        else:
            self._indent = value

    def dedent(self):
        self._indent -= 1
        if self._indent < 0:
            self._indent = 0

    def write(self, value):
        indent = self.INDENT * self._indent
        value = value.replace("\n", "\n%s" % indent)
        self._data.append("%s%s" % (indent, value))

    def writeTitle(self, value, underline="*"):
        self.write(value)
        self.write(underline * len(value))

    def writeItems(self, items):
        for i in items:
            if i:
                self.write(i)

    def newLine(self):
        self._data.append("")

    def writeDict(self, d):
        maxLength = 0
        for key in d:
            l = len(key)
            if l > maxLength:
                maxLength = l

        for key in sorted(d):
            value = d[key]
            t = "%s = %s" % (key.ljust(maxLength), value)
            self.write(t)

    def writeList(self, l):
        for i in l:
            self.write(str(i))

    def save(self, path):
        f = file(path, "w")
        f.write(self.get())
        f.close()

    def get(self):
        return "\n".join(self._data)


def updateWithDefaultValues(data, defaults):
    for key, value in defaults.items():
        if key in data:
            continue
        data[key] = value


def buildTree(path):
    if not os.path.exists(path):
        os.makedirs(path)


class TaskRunner(NSObject):

    def __new__(cls, *args, **kwargs):
        return cls.alloc().init()

    def __init__(self, callback, threaded, progress, kwargs=dict()):
        self._callback = callback
        self._kwargs = kwargs
        self._progress = progress

        if threaded:
            self._thread = NSThread.alloc().initWithTarget_selector_object_(self, "runTask:", None)
            self._thread.start()
        else:
            self.runTask_(None)

    def runTask_(self, sender):
        try:
            self._callback(progress=self._progress, **self._kwargs)
        except:
            import traceback
            errorMessage = [
                "*" * 30,
                traceback.format_exc(),
                "*" * 30
            ]
            print "\n".join(errorMessage)
        self._progress.close()


# mutator design space support

class MathFont(compilerObjects.Font):

    def _dummyMath(self, other):
        return self

    __add__ = _dummyMath
    __sub__ = _dummyMath
    __mul__ = _dummyMath
    __rmul__ = _dummyMath
    __truediv__ = _dummyMath
    __rdiv__ = _dummyMath
    __rtruediv__ = _dummyMath


def normelizePositionValues(minValue, value, maxValue):
    diff = maxValue - minValue
    value = (value - minValue) / float(diff)
    return 0, value, 1


class CompatibleContourPen(object):

    def __init__(self, types):
        self.types = list(types)

    def addPoint(self, pt, segmentType=None, *args, **kwargs):
        self.contour.append((pt, segmentType, args, kwargs))

    def beginPath(self):
        self.contour = list()

    def endPath(self):
        newContour = []
        for i, ((x, y), segmentType, args, kwargs) in enumerate(self.contour):
            if segmentType is not None:
                if segmentType != self.types[0]:
                    (px, py), _, _, _ = self.contour[i - 1]

                    dx = x - px
                    dy = y - py

                    nx1 = px + dx * 0.333
                    ny1 = py + dy * 0.333

                    nx2 = px + dx * 0.666
                    ny2 = py + dy * 0.666

                    newContour.append(((nx1, ny1), None, [], {}))
                    newContour.append(((nx2, ny2), None, [], {}))
                    segmentType = self.types[0]

                self.types.pop(0)

            newContour.append(((x, y), segmentType, args, kwargs))
        self.contour = newContour

    def drawPoints(self, pointPen, roundCoordinates=1):
        pointPen.beginPath()
        for (x, y), segmentType, args, kwargs in self.contour:
            pointPen.addPoint((x, y), segmentType, *args, **kwargs)
        pointPen.endPath()


# tag builder

vowelRE = re.compile("[aeiouAEIOU]")

fillChar = "*"

predefined = {
    "italic": "ital",
    "optical": "opsz",
    "opticalSize": "opsz",
    "slant": "slnt",
    "width": "wdth",
    "Width": "wdth",
    "weight": "wght",
    "Weight": "wght",
}


def tagBuilder(value, maxCount=4):
    inputValue = value
    if value not in predefined:
        # replace all vowels
        value = vowelRE.sub("", value)
        if len(value) > maxCount:
            # remove duplicates
            result = []
            for char in value:
                if char not in result:
                    result.append(char)
            value = "".join(result)
        # limit the value to the given count
        value = value[:maxCount]
        # replace spaces
        value = value.replace(" ", fillChar)
        # the value is smaller then the max count
        # fill it with splaceholder char
        if len(value) < maxCount:
            value += (maxCount - len(value)) * fillChar
        # if there are still not unique add numbers
        i = 1
        while value in predefined.values():
            n = str(i)
            value = value[:-len(n)] + n
            i += 1
        predefined[inputValue] = value
    return predefined[inputValue]


class BathDesignSpaceDocumentReader(DesignSpaceDocumentReader):

    _fontClass = MathFont
    _glyphClass = compilerObjects.Glyph
    _libClass = compilerObjects.Lib
    _glyphContourClass = compilerObjects.Contour
    _glyphPointClass = compilerObjects.Point
    _glyphComponentClass = compilerObjects.Component
    _glyphAnchorClass = compilerObjects.Anchor
    _kerningClass = compilerObjects.Kerning
    _groupsClass = compilerObjects.Groups
    _infoClass = compilerObjects.Info
    _featuresClass = compilerObjects.Features

    binaryDirName = "ttf"

    def process(self):
        if hasattr(self, "isProcessed"):
            return
        super(self.__class__, self).process()
        self.isProcessed = True

    def generateVariationFont(self, destPath, autohint=True, releaseMode=True, report=None):
        if report is None:
            report = Report()
        self.generateReport = report
        self.compileSettingAutohint = autohint
        self.compileSettingReleaseMode = releaseMode
        mutatorItems = []
        for key, (font, location) in self.sources.items():
            mutatorItems.append((location, font))
        _, mutator = buildMutator(mutatorItems, warpDict=self.warpDict)
        self.mutator = mutator
        self.makeMasterGlyphsCompatible()
        self.process()
        self.makeMasterGlyphsQuadractic()
        self._generateVariationFont(destPath)

    def makeMasterGlyphsQuadractic(self):
        fonts_to_quadratic(self.getMasters())
        for master in self.getMasters():
            master.segmentType = "qcurve"

    def getNeutral(self):
        return self.mutator.getNeutral()

    def getMasters(self):
        return [font for _, (font, _) in self.sources.items()]

    def getInstances(self):
        return [instance.font for _, instance in self.instances.items()]

    def getAxisNames(self):
        return self.mutator.getAxisNames()

    def _buildMinMaxValuesForAxes(self):
        self._axesValues = dict()
        for _, (font, location) in self.sources.items():
            for axis, value in location.items():
                if axis not in self._axesValues:
                    self._axesValues[axis] = list()
                self._axesValues[axis].append(value)

    def _getValueForAxis(self, axisName, func):
        if not hasattr(self, "self._axesValues"):
            self._buildMinMaxValuesForAxes()
        return func(self._axesValues[axisName])

    def getMaxValueForAxis(self, axisName):
        return self._getValueForAxis(axisName, max)

    def getMinValueForAxis(self, axisName):
        return self._getValueForAxis(axisName, min)

    def makeMasterGlyphsCompatible(self):
        self.generateReport.writeTile("Making master compatible", "'")
        masters = self.getMasters()
        glyphNames = []
        for master in masters:
            glyphNames.extend(master.keys())
        glyphNames = set(glyphNames)

        for glyphName in glyphNames:
            glyphs = []
            for master in masters:
                if glyphName in master:
                    glyphs.append(master[glyphName])
                else:
                    mutatorItems = []
                    instanceLocation = None
                    for key, (font, location) in self.sources.items():
                        if glyphName in font:
                            mutatorItems.append((location, MathGlyph(font[glyphName])))
                        if master == font:
                            instanceLocation = location
                    bias, mutator = buildMutator(mutatorItems, warpDict=self.warpDict)
                    result = mutator.makeInstance(instanceLocation)
                    if self.roundGeometry:
                        result.round()

                    self.generateReport.write("Adding missing glyph '%s' in master '%s %s'" % (glyphName, master.info.familyName, master.info.styleName))
                    master.newGlyph(glyphName)
                    glyph = master[glyphName]
                    result.extractGlyph(glyph)

                    glyphs.append(glyph)

            self._compatiblizeGlyphs(glyphs)
        self.generateReport.newLine()

    def _compatiblizeGlyphs(self, glyphs):
        if len(glyphs) <= 1:
            return

        glyphTypeMap = {}
        for glyph in glyphs:
            for i, contour in enumerate(glyph):
                types = [point.segmentType for point in contour if point.segmentType]
                if i not in glyphTypeMap:
                    glyphTypeMap[i] = list()
                glyphTypeMap[i].append((types, glyph))

        for contourIndex, contourTypes in glyphTypeMap.items():
            pointTypes = None
            for types, glyph in contourTypes:
                if pointTypes is None:
                    pointTypes = list(types)
                else:
                    for i, t in enumerate(types):
                        if t in ("curve", "qcurve"):
                            pointTypes[i] = t

            master = glyph.getParent()
            for types, glyph in contourTypes:
                if types == pointTypes:
                    continue

                self.generateReport.write("Adding missing offcurves in contour %s for glyph '%s' in master '%s %s'" % (contourIndex, glyph.name, master.info.familyName, master.info.styleName))
                contour = glyph[contourIndex]
                pen = CompatibleContourPen(pointTypes)
                contour.drawPoints(pen)
                contour.clear()
                pen.drawPoints(contour)

    def _generateVariationFont(self, outPutPath):
        neutral = self.getNeutral()
        dirName = os.path.dirname(outPutPath)
        baseName = os.path.basename(outPutPath)
        tempOutPutPath = os.path.join(dirName, "temp_%s" % baseName)
        if os.path.exists(tempOutPutPath):
            os.remove(tempOutPutPath)
        options = dict(
            saveFDKPartsNextToUFO=True,
            shouldDecomposeWithCheckOutlines=False,
            fontGenerateCheckComponentMatrix=True,
            defaultDrawingSegmentType="qcurve",
            outputPath=tempOutPutPath,
            format="ttf",
            decompose=False,
            checkOutlines=False,
            autohint=self.compileSettingAutohint,
            releaseMode=self.compileSettingReleaseMode,
            glyphOrder=None,
            useMacRoman=False,
        )
        neutral.lib[shouldAddPointsInSplineConversionLibKey] = False
        try:
            result = generateFont(neutral, **options)
        except:
            import traceback
            result = traceback.format_exc()
            print result
        self.generateReport.newLine()
        self.generateReport.writeTitle("Generate TTF", "'")
        self.generateReport.newLine()
        self.generateReport.indent()
        self.generateReport.write(result)
        self.generateReport.dedent()

        self.binaryFont = TTFont(tempOutPutPath)

        self.axisNameIDMap = dict()

        self.variation_name()
        self.variation_fvar()
        self.variation_gvar()

        self.binaryFont.save(outPutPath)

        if os.path.exists(tempOutPutPath):
            os.remove(tempOutPutPath)

    def variation_name(self):
        self.generateReport.writeTitle("Build axis names", "'")
        name = self.binaryFont["name"]

        bias = self.mutator.getBias()
        for axisName in bias:
            nameID = 1 + max([n.nameID for n in name.names] + [256])
            self.axisNameIDMap[axisName] = nameID

            nameRecord = NameRecord()
            nameRecord.nameID = nameID
            nameRecord.string = axisName
            nameRecord.platformID, nameRecord.platEncID, nameRecord.langID = (1, 0, 0)
            name.names.append(nameRecord)

            nameRecord = NameRecord()
            nameRecord.nameID = nameID
            nameRecord.string = unicode(axisName)
            nameRecord.platformID, nameRecord.platEncID, nameRecord.langID = (3, 1, 1033)
            name.names.append(nameRecord)

        for instanceName, instance in self.instances.items():
            nameID = 1 + max([n.nameID for n in name.names] + [256])
            self.axisNameIDMap[instanceName] = nameID

            nameRecord = NameRecord()
            nameRecord.nameID = nameID
            nameRecord.string = instance.font.info.styleName
            nameRecord.platformID, nameRecord.platEncID, nameRecord.langID = (1, 0, 0)
            name.names.append(nameRecord)

            nameRecord = NameRecord()
            nameRecord.nameID = nameID
            nameRecord.string = unicode(instance.font.info.styleName)
            nameRecord.platformID, nameRecord.platEncID, nameRecord.langID = (3, 1, 1033)
            name.names.append(nameRecord)

    def variation_fvar(self):
        # fvar
        self.generateReport.writeTitle("Build fvar table", "'")
        self.generateReport.indent()
        fvar = newTable("fvar")
        self.binaryFont["fvar"] = fvar
        axes = []
        for axisName in self.getAxisNames():
            axis = Axis()
            axis.axisTag = tagBuilder(axisName)
            axis.nameID = self.axisNameIDMap[axisName]
            axis.minValue = 0
            axis.defaultValue = 0
            axis.maxValue = 1
            axes.append(axis)
        fvar.axes = axes

        instances = []
        for instanceName, instance in self.instances.items():
            namedInstance = NamedInstance()
            namedInstance.subfamilyNameID = self.axisNameIDMap[instanceName]

            positions = dict()
            for axisName in self.getAxisNames():
                axisTagName = tagBuilder(axisName)
                _, value, _ = normelizePositionValues(
                    self.getMinValueForAxis(axisName),
                    instance.locationObject[axisTagName],
                    self.getMaxValueForAxis(axisName))

                if value < 0 or value > 1:
                    self.generateReport.write("Instance '%s' is an extrapolation for axis '%s'" % (instance.font.info.styleName, axisName))

                positions[axisName] = value
            namedInstance.coordinates = positions
            instances.append(namedInstance)
        fvar.instances = instances
        self.generateReport.dedent()

    def _variationGlyph(self, glyph, location, other=None):
        numPointsInGlyph = 0
        for contour in glyph:
            numPointsInGlyph += len(contour)
        if other is None:
            coords = [None] * numPointsInGlyph
        else:
            coords = []
            for ci, contour in enumerate(glyph):
                points = other[ci]
                for pi, point in enumerate(contour):
                    op = points[pi]
                    dx = point.x - op.x
                    dy = point.y - op.y
                    coords.append((dx, dy))
        left = None
        right = None
        if other:
            left = (glyph.leftMargin - other.leftMargin, 0)
            right = (glyph.width - other.width, 0)
        coords.extend([left, right, None, None])  # spacing deltas: left right top bottom
        positions = dict()
        for axisName in self.getAxisNames():
            axisTagName = tagBuilder(axisName)
            positions[axisTagName] = normelizePositionValues(
                self.getMinValueForAxis(axisName),
                location[axisName],
                self.getMaxValueForAxis(axisName))
        return GlyphVariation(positions, coords)

    def variation_gvar(self):
        # gvar
        self.generateReport.writeTitle("Build gvar table", "'")
        self.generateReport.indent()
        gvar = newTable("gvar")
        self.binaryFont["gvar"] = gvar

        neutral = self.getNeutral()

        gvar.variations = dict()
        gvar.version = 1
        gvar.reserved = 0

        for glyphName in neutral.keys():
            variations = []
            for _, (font, location) in self.sources.items():
                if font == neutral:
                    var = self._variationGlyph(neutral[glyphName], location)
                else:
                    varGlyph = font[glyphName]
                    var = self._variationGlyph(varGlyph, location, neutral[glyphName])
                variations.append(var)

            gvar.variations[glyphName] = variations
        self.generateReport.dedent()
