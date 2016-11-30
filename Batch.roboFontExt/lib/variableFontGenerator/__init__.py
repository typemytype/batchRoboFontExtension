import os

from vanilla import *

from designSpaceDocument.ufo import DesignSpaceProcessor

import fontCompiler.objects as compilerObjects
from fontCompiler.compiler import generateFont

from fontTools import varLib
from cu2qu.ufo import fonts_to_quadratic

from mutatorMath.objects.location import Location

from robofab.pens.adapterPens import TransformPointPen

from lib.tools.compileTools import CurrentFDK
from mojo.extensions import getExtensionDefault, setExtensionDefault

from batchTools import settingsIdentifier, ufoVersion, Report


class BatchVariableFontGenerate(Group):

    generateSettings = ["Autohint", "Release Mode"]

    def __init__(self, posSize, controller):
        super(BatchVariableFontGenerate, self).__init__(posSize)
        self.controller = controller

        y = 10
        for setting in self.generateSettings:
            key = setting.replace(" ", "_").lower()
            checkbox = CheckBox((10, y, -10, 22), setting,
                                value=getExtensionDefault("%s.%s" % (settingsIdentifier, key), True),
                                sizeStyle="small",
                                callback=self.saveDefaults)
            setattr(self, key, checkbox)
            y += 25
        y += 10
        self.generate = Button((-100, -30, -10, 22), "Generate", callback=self.generateCallback)
        self.height = y

    def saveDefaults(self, sender):
        for setting in self.generateSettings:
            key = setting.replace(" ", "_").lower()
            value = getattr(self, key).get()
            setExtensionDefault("%s.%s" % (settingsIdentifier, key), value)

    def run(self, destDir, progress, report=None):
        paths = self.controller.get(supportedExtensions=["designspace"], flattenDesignSpace=False)

        autohint = self.autohint.get()
        releaseMode = self.release_mode.get()

        if report is None:
            report = Report()

        report.writeTitle("Batch Generated Variable Fonts:")
        report.newLine()

        for path in paths:
            fileName = os.path.basename(path)
            outputPath = os.path.join(destDir, "%s.ttf" % os.path.splitext(fileName)[0])
            report.write("source: %s" % path)
            report.write("path: %s" % outputPath)
            report.indent()

            progress.update("Generating design space ... %s" % fileName)

            desingSpace = BatchDesignSpaceProcessor(path, ufoVersion)
            desingSpace.generateVariationFont(outputPath, autohint=autohint, releaseMode=releaseMode, report=report)
            report.dedent()

        reportPath = os.path.join(destDir, "Batch Generated Variable Fonts Report.txt")
        report.save(reportPath)

    def _generate(self, destDir):
        if not destDir:
            return
        destDir = destDir[0]
        self.controller.runTask(self.run, destDir=destDir)

    def generateCallback(self, sender):
        if not self.controller.hasSourceFonts("No Design Space to Generate.", "Drop or add desing space files to generate from.", supportedExtensions=["designspace"], flattenDesignSpace=False):
            return
        self.controller.showGetFolder(self._generate)


# ===========
# = helpers =
# ===========

class CompatibleContourPointPen(object):

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


class DecomposePointPen(TransformPointPen):

    def __init__(self, glyphSet, outPen, transformation):
        TransformPointPen.__init__(self, outPen, transformation)
        self.glyphSet = glyphSet

    def addComponent(self, glyphName, transformation):
        try:
            glyph = self.glyphSet[glyphName]
        except KeyError:
            pass
        else:
            transfromPointPen = TransformPointPen(self, transformation)
            # ignore anchors
            for contour in glyph:
                contour.drawPoints(transfromPointPen)
            for component in glyph.components:
                component.drawPoints(transfromPointPen)


class VarLibMasterFinder(dict):

    def __call__(self, arg):
        return self.get(arg)


class BatchDesignSpaceProcessor(DesignSpaceProcessor):

    fontClass = compilerObjects.Font
    glyphClass = compilerObjects.Glyph
    libClass = compilerObjects.Lib
    glyphContourClass = compilerObjects.Contour
    glyphPointClass = compilerObjects.Point
    glyphComponentClass = compilerObjects.Component
    glyphAnchorClass = compilerObjects.Anchor
    kerningClass = compilerObjects.Kerning
    groupsClass = compilerObjects.Groups
    infoClass = compilerObjects.Info
    featuresClass = compilerObjects.Features

    def __init__(self, path, ufoVersion=2):
        super(BatchDesignSpaceProcessor, self).__init__(ufoVersion=ufoVersion)
        self.read(path)

    def generateUFO(self):
        if not hasattr(self, "_didGenerate"):
            self._didGenerate = True
            super(BatchDesignSpaceProcessor, self).generateUFO()

    def masterUFOPaths(self):
        return [sourceDescriptor.path for sourceDescriptor in self.sources]

    def instancesUFOPaths(self):
        return [instanceDescriptor.path for instanceDescriptor in self.instances if instanceDescriptor.path is not None]

    def generateVariationFont(self, destPath, autohint=False, releaseMode=True, report=None):
        if report is None:
            report = Report()
        self.generateReport = report
        self.compileSettingAutohint = autohint
        self.compileSettingReleaseMode = releaseMode

        self.loadFonts()
        self.loadLocations()

        self.makeMasterGlyphsCompatible()
        self.decomposedMixedGlyphs()
        self.makeMasterGlyphsQuadractic()
        self.makeMasterKerningCompatible()
        self._generateVariationFont(destPath)
        return report

    def loadLocations(self):
        self.locations = dict()
        for sourceDescriptor in self.sources:
            location = Location(sourceDescriptor.location)
            self.locations[sourceDescriptor.name] = location

    def makeMasterGlyphsCompatible(self):
        self.generateReport.writeTitle("Making master compatible", "'")

        glyphNames = []
        for master in self.fonts.values():
            glyphNames.extend(master.keys())
        glyphNames = set(glyphNames)

        for glyphName in glyphNames:
            glyphs = []
            for sourceDescriptor in self.sources:
                master = self.fonts[sourceDescriptor.name]
                if glyphName in master:
                    glyphs.append(master[glyphName])
                else:
                    mutator = self.getGlyphMutator(glyphName)
                    location = self.locations[sourceDescriptor.name]
                    result = mutator.makeInstance(location)
                    if self.roundGeometry:
                        result.round()

                    self.generateReport.write("Adding missing glyph '%s' in master '%s %s'" % (glyphName, master.info.familyName, master.info.styleName))
                    master.newGlyph(glyphName)
                    glyph = master[glyphName]
                    result.extractGlyph(glyph)
                    glyphs.append(glyph)

            self.makeGlyphOutlinesCompatible(glyphs)
        self.generateReport.newLine()

    def makeGlyphOutlinesCompatible(self, glyphs):
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
                pen = CompatibleContourPointPen(pointTypes)
                contour.drawPoints(pen)
                contour.clear()
                pen.drawPoints(contour)

    def decomposedMixedGlyphs(self):
        masters = self.fonts.values()
        for master in masters:
            for glyph in master:
                if len(glyph) and len(glyph.components):
                    for component in glyph.components:
                        base = master[component.baseGlyph]
                        decomposePointPen = DecomposePointPen(master, glyph.getPointPen(), component.transformation)
                        for contour in base:
                            contour.drawPoints(decomposePointPen)
                        for component in base.components:
                            component.drawPoints(decomposePointPen)
                    glyph.clearComponents()

    def makeMasterGlyphsQuadractic(self):
        masters = self.fonts.values()
        fonts_to_quadratic(masters)
        for master in masters:
            master.segmentType = "qcurve"

    def makeMasterKerningCompatible(self):
        allPairs = list()
        allGroups = dict()
        masters = self.fonts.values()
        for master in masters:
            allPairs.extend(master.kerning.keys())
            allGroups.update(master.groups)
        allPairs = set(allPairs)
        for master in masters:
            for pair in allPairs:
                if pair not in master.kerning:
                    master.kerning[pair] = 0
                    first, second = pair
                    if first.startswith("@") and first not in master.groups:
                        master.groups[first] = allGroups[first]
                    if second.startswith("@") and second not in master.groups:
                        master.groups[second] = allGroups[second]

    def _generateVariationFont(self, outPutPath):
        dirname = os.path.dirname(outPutPath)

        options = dict(
            saveFDKPartsNextToUFO=True,
            shouldDecomposeWithCheckOutlines=False,
            fontGenerateCheckComponentMatrix=True,
            defaultDrawingSegmentType="qcurve",
            format="ttf",
            decompose=False,
            checkOutlines=False,
            autohint=self.compileSettingAutohint,
            releaseMode=self.compileSettingReleaseMode,
            glyphOrder=None,
            useMacRoman=False,
            fdk=CurrentFDK(),
            generateFeaturesWithFontTools=False,
        )

        self.generateReport.newLine()
        self.generateReport.writeTitle("Generate TTF", "'")
        self.generateReport.indent()

        masterBinaryPaths = VarLibMasterFinder()
        for master in self.fonts.values():
            outputPath = os.path.join(dirname, "temp_%s-%s.ttf" % (master.info.familyName, master.info.styleName))
            masterBinaryPaths[master.path] = outputPath
            options["outputPath"] = outputPath
            try:
                result = generateFont(master, **options)
            except:
                import traceback
                result = traceback.format_exc()
                print result
            self.generateReport.newLine()
            self.generateReport.write("Generate %s %s" % (master.info.familyName, master.info.styleName))
            self.generateReport.indent()
            self.generateReport.write(result)
            self.generateReport.dedent()
        self.generateReport.dedent()
        # let varLib do the work
        varFont, _, _ = varLib.build(self.path, masterBinaryPaths)
        varFont.save(outPutPath)

        for tempPath in masterBinaryPaths.values():
           if os.path.exists(tempPath):
               os.remove(tempPath)

if __name__ is "__main__":

    path = u"/Users/frederik/Downloads/adobe-variable-font-prototype-master/RomanMasters/AdobeVFPrototype_rebuilt.designspace"
    outputPath = u"/Users/frederik/Downloads/adobe-variable-font-prototype-master/test/Adobe VF Prototype_super_test.ttf"
    document = BatchDesignSpaceProcessor(path)
    result = document.generateVariationFont(outputPath, autohint=False, releaseMode=False, report=None)
    print result.get()
