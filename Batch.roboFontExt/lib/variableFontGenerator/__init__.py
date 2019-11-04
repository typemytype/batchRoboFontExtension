import os
import shutil

from vanilla import *

import defcon

from ufoProcessor import DesignSpaceProcessor
from ufoProcessor.emptyPen import checkGlyphIsEmpty

import fontCompiler.objects as compilerObjects
from fontCompiler.compiler import generateFont, FontCompilerOptions

from fontTools import varLib
from fontTools.varLib.featureVars import addFeatureVariations
from fontTools.varLib.models import normalizeLocation

from cu2qu.ufo import fonts_to_quadratic

from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator

from fontPens.transformPointPen import TransformPointPen

from ufo2fdk.kernFeatureWriter import side1Prefix, side2Prefix

from lib.tools.compileTools import CurrentFDK
from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.UI import getDefault

from batchTools import settingsIdentifier, ufoVersion, Report


class BatchVariableFontGenerate(Group):

    generateSettings = ["Interpolate to fit axes extremes", "Autohint"]

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
        fitToExtremes = self.interpolate_to_fit_axes_extremes.get()

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
            desingSpace.generateVariationFont(outputPath, autohint=autohint, releaseMode=True, fitToExtremes=fitToExtremes, report=report)
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
            if self.types:
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
            # identifiers are not needed here
            # but the could cause errors, so remove them
            kwargs["identifier"] = None
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

    def beginPath(self, identifier=None):
        super().beginPath()

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, **kwargs):
        kwargs["identifier"] = None
        super().addPoint(pt, segmentType=segmentType, smooth=smooth, name=name, **kwargs)

    def addComponent(self, glyphName, transformation, identifier=None):
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


class BatchLayer(compilerObjects.Layer):

    def _get_info(self):
        return self.font.info

    info = property(_get_info)

    def _get_kerning(self):
        return self.font.kerning

    kerning = property(_get_kerning)

    def _get_groups(self):
        return self.font.groups

    groups = property(_get_groups)

    def _get_path(self):
        return self.font.path

    path = property(_get_path)


class BatchDesignSpaceProcessor(DesignSpaceProcessor):

    """
    A subclass of a DesignSpaceProcessor with support for variation fonts.
    """

    fontClass = compilerObjects.Font
    layerClass = BatchLayer
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
        self.useVarlib = True
        self.read(path)

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

    def generateVariationFont(self, destPath, autohint=False, fitToExtremes=False, releaseMode=True, glyphOrder=None, report=None):
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
        self.loadMasters()

        self._generatedFiles = set()

        self.makeMasterGlyphsCompatible()
        self.decomposedMixedGlyphs()
        self.makeMasterGlyphsQuadractic()
        self.makeMasterKerningCompatible()
        self.makeMasterOnDefaultLocation()
        self.makeLayerMaster()
        try:
            self._generateVariationFont(destPath)
        except Exception:
            import traceback
            result = traceback.format_exc()
            print(result)
        finally:
            if not getDefault("Batch.Debug", False):
                # remove generated files
                for path in self._generatedFiles:
                    if os.path.exists(path):
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
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

    def loadMasters(self):
        """
        Store all masters, layers in a single dict.
        """
        self.masters = dict()
        for sourceDescriptor in self.sources:
            masterFont = self.fonts[sourceDescriptor.name]
            if sourceDescriptor.layerName is None:
                layer = masterFont.layers.defaultLayer
            else:
                layer = masterFont.layers[sourceDescriptor.layerName]
            if layer is not None:
                self.masters[sourceDescriptor.name] = layer

    def makeLayerMaster(self):
        """
        If there a layer name in a source description add it as seperate master in the source description.
        """
        for sourceDescriptor in self.sources:
            if sourceDescriptor.layerName is not None:
                path, ext = os.path.splitext(sourceDescriptor.path)
                sourceDescriptor.path = "%s-%s%s" % (path, sourceDescriptor.layerName, ext)
                sourceDescriptor.styleName = "%s %s" % (sourceDescriptor.styleName, sourceDescriptor.layerName)
                sourceDescriptor.filename = None
                sourceDescriptor.layerName = None
                if getDefault("Batch.Debug", False):
                    masterFont = self.fonts[sourceDescriptor.name]
                    layerPath = os.path.join(os.path.dirname(self.path), sourceDescriptor.path)
                    masterFont.save(layerPath)

    def makeMasterOnDefaultLocation(self):
        # create default location
        # which is on the crossing of all axis
        #defaultLocation = Location()
        defaultLocation = self.newDefaultLocation(bend=True)
        # compare default location with locations all of sources
        for sourceDescriptor in self.sources:
            if defaultLocation == sourceDescriptor.location:
                # found the default location
                # do nothing
                return
        self.generateReport.writeTitle("Setting a master on the default", "'")
        self.generateReport.indent()
        # there is no master at the default location
        # change the defaults of each axis so it fits with a given master
        neutralLocation = self.locations[self.default.name]
        for axis in self.axes:
            axis.default = neutralLocation[axis.name]
        self.generateReport.writeDict(neutralLocation)
        self.generateReport.dedent()
        self.generateReport.newLine()

    def makeMasterGlyphsCompatible(self):
        """
        Update all masters with missing glyphs.
        All Masters must have the same glyphs.
        """
        self.generateReport.writeTitle("Making master glyphs compatible", "'")
        self.generateReport.indent()
        # collect all possible glyph names
        glyphNames = []
        for master in self.masters.values():
            glyphNames.extend(master.keys())
        glyphNames = set(glyphNames)
        # get the default master
        defaultMaster = self.masters[self.default.name]
        # loop over all glyphName
        for glyphName in glyphNames:
            # first check if the default master has this glyph
            if glyphName not in defaultMaster:
                # the default does not have the glyph
                # build a repair mutator to generate a glyph.
                glyphItems = []
                for sourceDescriptor in self.sources:
                    master = self.masters[sourceDescriptor.name]
                    if glyphName in sourceDescriptor.mutedGlyphNames:
                        continue
                    if glyphName in master:
                        sourceGlyph = self.mathGlyphClass(master[glyphName])
                        sourceGlyphLocation = self.locations[sourceDescriptor.name]
                        glyphItems.append((sourceGlyphLocation, sourceGlyph))
                # Note: this needs to be a mutatormath mutator, not a varlib.model.
                # A varlib model can't work without in the missing default.
                # Filling in the default is a bit of a hack: it will make the font work,
                # but it is a bit of a guess.
                _, mutator = buildMutator(glyphItems)
                # use the repair mutator to generate an instance at the default location
                result = mutator.makeInstance(Location(self.newDefaultLocation()))
                # round if necessary
                if self.roundGeometry:
                    result.round()
                self.generateReport.write("Adding missing glyph '%s' in the default master '%s %s (%s)'" % (glyphName, defaultMaster.font.info.familyName, defaultMaster.font.info.styleName, defaultMaster.name))
                # add the glyph to the default master
                defaultMaster.newGlyph(glyphName)
                glyph = defaultMaster[glyphName]
                result.extractGlyph(glyph, onlyGeometry=True)

            glyphs = []
            # fill all masters with missing glyphs
            # and collect all glyphs from all masters
            # to send them to optimize contour data
            for sourceDescriptor in self.sources:
                master = self.masters[sourceDescriptor.name]
                hasGlyph = False
                if glyphName in master:
                    # Glyph is present in the master.
                    # This checks for points, components and so on.
                    if not checkGlyphIsEmpty(master[glyphName], allowWhiteSpace=True):
                        glyphs.append(master[glyphName])
                        hasGlyph = True
                if not hasGlyph:
                    # Get the varlibmodel to generate a filler glyph.
                    # These is probably a support with just a few glyphs.
                    try:
                        self.useVarlib = True
                        mutator = self.getGlyphMutator(glyphName)
                        if mutator is None:
                            self.useVarlib = False
                            mutator = self.getGlyphMutator(glyphName)
                            self.useVarlib = True
                        # generate an instance
                        result = mutator.makeInstance(Location(sourceDescriptor.location))
                    except Exception as e:
                        print("Problem in %s" % glyphName)
                        print("\n".join(self.problems))
                        raise e
                    # round if necessary
                    if self.roundGeometry:
                        result.round()
                    self.generateReport.write("Adding missing glyph '%s' in master '%s %s (%s)'" % (glyphName, master.font.info.familyName, master.font.info.styleName, master.name))
                    # add the glyph to the master
                    master.newGlyph(glyphName)
                    result.extractGlyph(master[glyphName], onlyGeometry=True)
                    glyphs.append(master[glyphName])
            # optimize glyph contour data from all masters
            self.makeGlyphOutlinesCompatible(glyphs)
        if getDefault("Batch.Debug", False):
            for k, m in self.masters.items():
                tempPath = os.path.join(os.path.dirname(m.font.path), "%s_%s" % (k, os.path.basename(m.font.path)))
                m.font.save(tempPath)

        if self.compileGlyphOrder is None:
            self.compileGlyphOrder = defaultMaster.font.lib.get("public.glyphOrder", [])
            for glyphName in sorted(glyphNames):
                if glyphName not in self.compileGlyphOrder:
                    self.compileGlyphOrder.append(glyphName)

        self.generateReport.dedent()
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

            font = glyph.font
            # check if they are different
            for types, glyph in contourTypes:
                if types == pointTypes:
                    continue
                # add missing off curves
                self.generateReport.write("Adding missing offcurves in contour %s for glyph '%s' in master '%s %s'" % (contourIndex, glyph.name, font.info.familyName, font.info.styleName))
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
        self.generateReport.indent()
        masters = self.masters.values()
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
                    self.generateReport.write("Decomposing glyph '%s' in master '%s %s (%s)'" % (glyph.name, master.font.info.familyName, master.font.info.styleName, master.name))
        self.generateReport.dedent()
        self.generateReport.newLine()

    def makeMasterGlyphsQuadractic(self):
        """
        Optimize and convert all master ufo to quad curves.
        """
        masters = self.masters.values()
        # use cu2qu to optimize all masters
        fonts_to_quadratic(masters)
        for master in masters:
            master.font.segmentType = "qcurve"

    def makeMasterKerningCompatible(self):
        """
        Optimize kerning data.
        All masters must have the same kering pairs.
        Build repair mutators for missing kering pairs
        and generate the kerning value within the design space.
        """
        self.generateReport.writeTitle("Making master kerning compatible", "'")
        self.generateReport.indent()
        # collect all kerning pairs
        allPairs = list()
        # collect all groups and all pairs
        allGroups = dict()
        masters = self.fonts.values()
        for master in masters:
            allPairs.extend(master.kerning.keys())
            allGroups.update(master.groups)
        allPairs = set(allPairs)
        # build a kerning mutator
        kerningItems = []
        for sourceDescriptor in self.sources:
            # ignore muted kerning sources
            if sourceDescriptor.muteKerning:
                continue
            master = self.fonts[sourceDescriptor.name]
            location = self.locations[sourceDescriptor.name]
            kerningItems.append((location, self.mathKerningClass(master.kerning, master.groups)))
        _, kerningMutator = buildMutator(kerningItems)
        kerningCache = dict()
        # loop over all pairs
        for pair in allPairs:
            # loop over all masters
            for sourceDescriptor in self.sources:
                font = self.fonts[sourceDescriptor.name]
                missingPairs = []
                missingGroups = []
                if pair not in font.kerning:
                    missingPairs.append(pair)
                    kerningInstance = kerningCache.get(sourceDescriptor.name)
                    if kerningInstance is None:
                        location = self.locations[sourceDescriptor.name]
                        kerningInstance = kerningMutator.makeInstance(Location(location))
                    master.kerning[pair] = kerningInstance[pair]
                    # check pairs on group kerning
                    side1, side2 = pair
                    if side1.startswith(side1Prefix) and side1 not in master.groups:
                        # add a group
                        master.groups[side1] = allGroups[side1]
                        missingGroups.append(side1)
                    if side2.startswith(side2Prefix) and side2 not in master.groups:
                        # add a group
                        master.groups[side2] = allGroups[side2]
                        missingGroups.append(side2)
                if missingPairs:
                    self.generateReport.write("Adding missing kerning pairs in %s %s: %s" % (font.info.familyName, font.info.styleName, ", ".join(["(%s, %s)" % (s1, s2) for s1, s2 in missingPairs])))
                if missingGroups:
                    self.generateReport.write("Adding missing kerning groups in %s %s: %s" % (font.info.familyName, font.info.styleName, ", ".join(missingGroups)))
        self.generateReport.dedent()
        self.generateReport.newLine()

    def _generateVariationFont(self, outPutPath):
        """
        Generate a variation font.
        """
        dirname = os.path.dirname(outPutPath)
        # fontCompiler settings
        options = FontCompilerOptions()
        options.saveFDKPartsNextToUFO = getDefault("saveFDKPartsNextToUFO")
        options.shouldDecomposeWithCheckOutlines = False
        options.generateCheckComponentMatrix = True
        options.defaultDrawingSegmentType = "qcurve"
        options.format = "ttf"
        options.decompose = False
        options.checkOutlines = False
        options.autohint = self.compileSettingAutohint
        options.releaseMode = self.compileSettingReleaseMode
        options.glyphOrder = self.compileGlyphOrder
        options.useMacRoman = False
        options.fdk = CurrentFDK()
        options.generateFeaturesWithFontTools = False

        self.generateReport.newLine()
        self.generateReport.writeTitle("Generate TTF", "'")
        self.generateReport.indent()
        # map all master ufo paths to generated binaries
        masterBinaryPaths = VarLibMasterFinder()
        masterCount = 0
        for sourceDescriptor in self.sources:
            master = self.masters[sourceDescriptor.name]
            # get the output path
            outputPath = os.path.join(dirname, "temp_%02d_%s-%s-%s.ttf" % (masterCount, master.font.info.familyName, master.font.info.styleName, master.name))
            masterBinaryPaths[sourceDescriptor.path] = outputPath
            self._generatedFiles.add(outputPath)
            masterCount += 1
            # set the output path
            options.outputPath = outputPath
            options.layerName = master.name
            try:
                # generate the font
                result = generateFont(master.font, options=options)
                if getDefault("Batch.Debug", False):
                    tempSavePath = os.path.join(dirname, "temp_%s-%s-%s.ufo" % (master.font.info.familyName, master.font.info.styleName, master.name))
                    font = master.font
                    font.save(tempSavePath)
                    if font.layers.defaultLayer.name != master.name:
                        tempFont = defcon.Font(tempSavePath)
                        tempFont.layers.defaultLayer = tempFont.layers[master.name]
                        tempFont.save()
            except Exception:
                import traceback
                result = traceback.format_exc()
                print(result)
            self.generateReport.newLine()
            self.generateReport.write("Generate %s %s (%s)" % (master.font.info.familyName, master.font.info.styleName, master.name))
            self.generateReport.indent()
            self.generateReport.write(result)
            self.generateReport.dedent()
        self.generateReport.dedent()
        # optimize the design space for varlib
        designSpacePath = os.path.join(os.path.dirname(self.path), "temp_%s" % os.path.basename(self.path))
        self.write(designSpacePath)
        self._generatedFiles.add(designSpacePath)
        try:
            # let varLib build the variation font
            varFont, _, _ = varLib.build(designSpacePath, master_finder=masterBinaryPaths)
            # save the variation font
            varFont.save(outPutPath)
        except Exception:
            if getDefault("Batch.Debug", False):
                print("masterBinaryPaths:", masterBinaryPaths)
            import traceback
            result = traceback.format_exc()
            print(result)
