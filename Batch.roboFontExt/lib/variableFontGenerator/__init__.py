import os

from vanilla import *

from designSpaceDocument.ufo import DesignSpaceProcessor

import fontCompiler.objects as compilerObjects
from fontCompiler.compiler import generateFont

from fontTools import varLib
from cu2qu.ufo import fonts_to_quadratic

from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator

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

    """
    Create a compatible glyphs
    based on a given list of segmentTypes.
    """

    def __init__(self, types):
        self.types = list(types)

    def addPoint(self, pt, segmentType=None, *args, **kwargs):
        self.contour.append((pt, segmentType, args, kwargs))

    def beginPath(self):
        self.contour = list()

    def endPath(self):
        # lets start
        newContour = []
        for i, ((x, y), segmentType, args, kwargs) in enumerate(self.contour):
            # if there is segmentType
            if segmentType is not None:
                # check with the given list of segmentTypes
                if segmentType != self.types[0]:
                    # its different
                    # get the previous point
                    (px, py), _, _, _ = self.contour[i - 1]
                    # calculate offcurve points
                    # on 1/3 of the line segment length
                    dx = x - px
                    dy = y - py

                    nx1 = px + dx * 0.333
                    ny1 = py + dy * 0.333

                    nx2 = px + dx * 0.666
                    ny2 = py + dy * 0.666
                    # add it to the new contour
                    newContour.append(((nx1, ny1), None, [], {}))
                    newContour.append(((nx2, ny2), None, [], {}))
                    segmentType = self.types[0]
                # remove the first given segmentType
                self.types.pop(0)
            # add the point
            newContour.append(((x, y), segmentType, args, kwargs))
        # set the contour
        self.contour = newContour

    def drawPoints(self, pointPen, roundCoordinates=1):
        """
        Draw into an other pointPen
        """
        pointPen.beginPath()
        for (x, y), segmentType, args, kwargs in self.contour:
            pointPen.addPoint((x, y), segmentType, *args, **kwargs)
        pointPen.endPath()


class DecomposePointPen(TransformPointPen):

    """
    A simple transform point pen able to decompose components
    in a given point pen.
    """

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

    """
    VarLib needs an argement mapping source UFOs to binary fonts.
    A simple dict which is callable with an source UFO path returning
    the binary font path.
    """

    def __call__(self, arg):
        return self.get(arg)


class BatchDesignSpaceProcessor(DesignSpaceProcessor):

    """
    A subclass of a DesignSpaceProcessor with support for variation fonts.
    """

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
        self.checkAxes()
        self.checkDefault()

    def generateUFO(self):
        # make sure it only generates all instances only once
        if not hasattr(self, "_didGenerate"):
            super(BatchDesignSpaceProcessor, self).generateUFO()
            self._didGenerate = True

    def masterUFOPaths(self):
        """
        Return the master ufo paths.
        """
        return [sourceDescriptor.path for sourceDescriptor in self.sources]

    def instancesUFOPaths(self):
        """
        Return the instances ufo paths.
        Its possible that those paths does not exists yet.
        call `.generateUFO()` to generate instances.
        """
        return [instanceDescriptor.path for instanceDescriptor in self.instances if instanceDescriptor.path is not None]

    def generateVariationFont(self, destPath, autohint=False, releaseMode=True, glyphOrder=None, report=None):
        """
        Generate a variation font based on a desingSpace.
        """
        if report is None:
            report = Report()
        self.generateReport = report
        self.compileSettingAutohint = autohint
        self.compileSettingReleaseMode = releaseMode
        self.compileGlyphOrder = glyphOrder

        self.loadFonts()
        self.loadLocations()

        self.makeMasterGlyphsCompatible()
        self.decomposedMixedGlyphs()
        self.makeMasterGlyphsQuadractic()
        self.makeMasterKerningCompatible()
        self._generateVariationFont(destPath)
        return report

    def loadLocations(self):
        """
        Store all locations similary as the `.fonts` dict.
        The sourceDescriptor name is the key.
        """
        self.locations = dict()
        for sourceDescriptor in self.sources:
            location = Location(sourceDescriptor.location)
            self.locations[sourceDescriptor.name] = location

    def makeMasterGlyphsCompatible(self):
        """
        Update all masters with missing glyphs.
        All Masters must have the same glyphs.
        """
        self.generateReport.writeTitle("Making master glyphs compatible", "'")
        # collect all possible glyph names
        glyphNames = []
        for master in self.fonts.values():
            glyphNames.extend(master.keys())
        glyphNames = set(glyphNames)
        # get the default master
        defaultMaster = self.fonts[self.default.name]
        # loop over all glyphName
        for glyphName in glyphNames:
            # first check if the default master has this glyph
            if glyphName not in defaultMaster:
                # the default does not have the glyph
                # build a repair mutator to generate a glyph
                glyphItems = []
                for sourceDescriptor in self.sources:
                    master = self.fonts[sourceDescriptor.name]
                    if glyphName in sourceDescriptor.mutedGlyphNames:
                        continue
                    if glyphName in master:
                        sourceGlyph = self.mathGlyphClass(master[glyphName])
                        sourceGlyphLocation = self.locations[sourceDescriptor.name]
                        glyphItems.append((sourceGlyphLocation, sourceGlyph))
                _, mutator = buildMutator(glyphItems)
                # use the repair mutator to generate an instance at the default location
                result = mutator.makeInstance(self.defaultLoc)
                # round if necessary
                if self.roundGeometry:
                    result.round()
                self.generateReport.write("Adding missing glyph '%s' in the default master '%s %s'" % (glyphName, defaultMaster.info.familyName, defaultMaster.info.styleName))
                # add the glyph to the default master
                defaultMaster.newGlyph(glyphName)
                glyph = defaultMaster[glyphName]
                result.extractGlyph(glyph)

            glyphs = []
            # fill all masters with missing glyphs
            # and collect all glyphs from all masters
            # to send them to optimize contour data
            for sourceDescriptor in self.sources:
                master = self.fonts[sourceDescriptor.name]
                if glyphName in master:
                    # found do nothing
                    glyphs.append(master[glyphName])
                else:
                    # get the mutator
                    mutator = self.getGlyphMutator(glyphName)
                    # get the location
                    location = self.locations[sourceDescriptor.name]
                    # generate an instance
                    result = mutator.makeInstance(location)
                    # round if necessary
                    if self.roundGeometry:
                        result.round()

                    self.generateReport.write("Adding missing glyph '%s' in master '%s %s'" % (glyphName, master.info.familyName, master.info.styleName))
                    # add the glyph to the master
                    master.newGlyph(glyphName)
                    glyph = master[glyphName]
                    result.extractGlyph(glyph)
                    glyphs.append(glyph)
            # optimize glyph contour data from all masters
            self.makeGlyphOutlinesCompatible(glyphs)
        self.generateReport.newLine()

    def makeGlyphOutlinesCompatible(self, glyphs):
        if len(glyphs) <= 1:
            return
        # map all segment type for the given glyphs by contour index
        glyphSegmentTypeMap = {}
        for glyph in glyphs:
            for i, contour in enumerate(glyph):
                types = [point.segmentType for point in contour if point.segmentType]
                if i not in glyphSegmentTypeMap:
                    glyphSegmentTypeMap[i] = list()
                glyphSegmentTypeMap[i].append((types, glyph))

        for contourIndex, contourTypes in glyphSegmentTypeMap.items():
            # collect all segment types for a single glyph
            pointTypes = None
            for types, glyph in contourTypes:
                if pointTypes is None:
                    pointTypes = list(types)
                else:
                    for i, t in enumerate(types):
                        if t in ("curve", "qcurve"):
                            pointTypes[i] = t

            master = glyph.getParent()
            # check if they are different
            for types, glyph in contourTypes:
                if types == pointTypes:
                    continue
                # add missing off curves
                self.generateReport.write("Adding missing offcurves in contour %s for glyph '%s' in master '%s %s'" % (contourIndex, glyph.name, master.info.familyName, master.info.styleName))
                contour = glyph[contourIndex]
                pen = CompatibleContourPointPen(pointTypes)
                contour.drawPoints(pen)
                contour.clear()
                pen.drawPoints(contour)

    def decomposedMixedGlyphs(self):
        """
        Decompose all glyphs which have both contour point data as components.
        """
        self.generateReport.writeTitle("Decompose Mixed Glyphs", "'")
        masters = self.fonts.values()
        for master in masters:
            for glyph in master:
                # check if the glyph has both contour point data as components
                if len(glyph) and len(glyph.components):
                    # found, loop over all components and decompose
                    for component in glyph.components:
                        # get the master font
                        base = master[component.baseGlyph]
                        # get the decompose pen
                        decomposePointPen = DecomposePointPen(master, glyph.getPointPen(), component.transformation)
                        # draw the base into the pen
                        for contour in base:
                            contour.drawPoints(decomposePointPen)
                        # draw the base components into the pen
                        for component in base.components:
                            component.drawPoints(decomposePointPen)
                    # remove all components
                    glyph.clearComponents()
                    self.generateReport.write("Decomposing glyph '%s' in master '%s %s'" % (glyph.name, master.info.familyName, master.info.styleName))
        self.generateReport.newLine()

    def makeMasterGlyphsQuadractic(self):
        """
        Optimize and convert all master ufo to quad curves.
        """
        masters = self.fonts.values()
        # use cu2qu to optimize all masters
        fonts_to_quadratic(masters)
        for master in masters:
            master.segmentType = "qcurve"

    def makeMasterKerningCompatible(self):
        """
        Optimize kerning data.
        All masters must have the same kering pairs.
        Build repair mutators for missing kering pairs
        and generate the kerning value within the design space.
        """
        self.generateReport.writeTitle("Making master kerning compatible", "'")
        # collect all kerning pairs
        allPairs = list()
        # collect all groups
        allGroups = dict()
        masters = self.fonts.values()
        for master in masters:
            allPairs.extend(master.kerning.keys())
            allGroups.update(master.groups)
        allPairs = set(allPairs)
        # loop over all pairs
        for pair in allPairs:
            # loop over all masters
            for sourceDescriptor in self.sources:
                master = self.fonts[sourceDescriptor.name]
                if pair not in master.kerning:
                    # build a repair mutator
                    kernItems = []
                    for kernSourceDescriptor in self.sources:
                        kernMaster = self.fonts[kernSourceDescriptor.name]
                        if pair in kernMaster.kerning:
                            sourceLocation = self.locations[kernSourceDescriptor.name]
                            sourceValue = kernMaster.kerning[pair]
                            kernItems.append((sourceLocation, sourceValue))
                    # get a repair mutotator
                    _, mutator = buildMutator(kernItems)
                    # get the location
                    location = self.locations[sourceDescriptor.name]
                    # generate an instance kern value for the given pair
                    result = mutator.makeInstance(location)
                    # set the kern value for the given pair
                    master.kerning[pair] = result
                    # check pairs on group kerning
                    first, second = pair
                    if first.startswith("@") and first not in master.groups:
                        # add a group
                        master.groups[first] = allGroups[first]
                    if second.startswith("@") and second not in master.groups:
                        # add a group
                        master.groups[second] = allGroups[second]
        self.generateReport.newLine()

    def _generateVariationFont(self, outPutPath):
        """
        Generate a variation font.
        """
        dirname = os.path.dirname(outPutPath)
        # fontCompiler settings
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
            glyphOrder=self.compileGlyphOrder,
            useMacRoman=False,
            fdk=CurrentFDK(),
            generateFeaturesWithFontTools=False,
        )

        self.generateReport.newLine()
        self.generateReport.writeTitle("Generate TTF", "'")
        self.generateReport.indent()
        # map all master ufo paths to generated binaries
        masterBinaryPaths = VarLibMasterFinder()
        for master in self.fonts.values():
            # get the output path
            outputPath = os.path.join(dirname, "temp_%s-%s.ttf" % (master.info.familyName, master.info.styleName))
            masterBinaryPaths[master.path] = outputPath
            # set the output path
            options["outputPath"] = outputPath
            try:
                # generate the font
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
        # optimize the design space for varlib
        designSpacePath = os.path.join(os.path.dirname(self.path), "temp_%s" % os.path.basename(self.path))
        self.write(designSpacePath)
        axisMap = {a.name: (a.tag, a.name) for a in self.axes}
        # let varLib build the variation font
        varFont, _, _ = varLib.build(designSpacePath, master_finder=masterBinaryPaths, axisMap=axisMap)
        # save the variation font
        varFont.save(outPutPath)
        # remove the temp design space file
        if os.path.exists(designSpacePath):
            os.remove(designSpacePath)
        # remove all temp binaries
        for tempPath in masterBinaryPaths.values():
            if os.path.exists(tempPath):
                os.remove(tempPath)
