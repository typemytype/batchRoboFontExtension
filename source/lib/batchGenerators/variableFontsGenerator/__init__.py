import os
import shutil

import defcon

from fontTools.cu2qu.ufo import fonts_to_quadratic
from fontTools import varLib
from fontTools.ttLib import TTFont

from fontPens.transformPointPen import TransformPointPen

from lib.tools.compileTools import CurrentFDK, CurrentFontCompilerTool
from mojo.UI import getDefault
from fontCompiler.compiler import generateFont, FontCompilerOptions

from ufo2fdk.kernFeatureWriter import side1Prefix, side2Prefix

from batchGenerators.batchTools import postProcessCollector, WOFF2Builder, buildTree, removeTree, BatchEditorOperator, Report


class GenerateVariableFont:

    def __init__(self, operator, destinationPath, autohint=False, fitToExtremes=False, releaseMode=True, glyphOrder=None, report=None, debug=False):
        # this must be an operator with no discrete axes.
        # split the designspace first first
        if report is None:
            report = Report()
        self.operator = operator
        self.destinationPath = destinationPath
        self.binaryFormat = os.path.splitext(self.destinationPath)[-1][1:].lower()
        self.autohint = autohint
        self.fitToExtremes = fitToExtremes
        self.releaseMode = releaseMode
        self.glyphOrder = glyphOrder
        self.report = report
        self.debug = debug
        self.build()

    def build(self):
        self.generatedFiles = set()

        self.operator.loadFonts(reload=True)
        self.applySkipExportGlyphs()
        self.makeSourceGlyphsCompatible()
        self.decomposedMixedGlyphs()
        self.makeSourceKerningCompatible()
        self.makeSourceOnDefaultLocation()
        self.makeLayerSource()
        self.makeSourcesAtAxesExtremes()
        if self.binaryFormat == "ttf":
            self.makeSourceGlyphsQuadractic()
        elif self.binaryFormat == "otf":
            self.makeSourceExportOptimizeCharstring()

        self.generate()

        if not self.debug:
            # remove generated files
            for path in self.generatedFiles:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)

    def applySkipExportGlyphs(self):
        for font in self.operator.fonts.values():
            skipExportGlyphs = set(font.lib.get("public.skipExportGlyphs", []))
            if skipExportGlyphs:
                # Decompose the listed glyphs everywhere they are used as components.
                for glyph in font:
                    for component in glyph.components:
                        if component.baseGlyph in skipExportGlyphs:
                            glyph.decomposeComponent(component)
                # Remove these glyphs before the compilation run.
                for glyphName in skipExportGlyphs:
                    if glyphName in font:
                        del font[glyphName]
                # Prune all groups of the listed glyphs.
                for key, value in list(font.groups.items()):
                    font.groups[key] = [glyphName for glyphName in value if glyphName not in skipExportGlyphs]
                # Prune all kerning pairs that contain any of the listed glyphs.
                for side1, side2 in list(font.kerning.keys()):
                    if side1 in skipExportGlyphs or side2 in skipExportGlyphs:
                        del font.kerning[side1, side2]

    def makeSourcesAtAxesExtremes(self):
        if self.fitToExtremes:
            self.report.writeTitle("Add sources at axes extremes", "'")
            extremeLocations = []
            for axis in self.operator.axes:
                location = dict()
                for otherAxis in self.operator.axes:
                    if otherAxis == axis:
                        continue
                    location[otherAxis.name] = otherAxis.default

                if hasattr(axis, "values"):
                    for value in axis.values:
                        extremeLocations.append(dict(**location, **{axis.name: value}))
                else:
                    extremeLocations.append(dict(**location, **{axis.name: axis.minimum}))
                    extremeLocations.append(dict(**location, **{axis.name: axis.maximum}))

            sourceLocations = [sourceDescriptor.location for sourceDescriptor in self.operator.sources]
            for extremeLocation in extremeLocations:
                if extremeLocation not in sourceLocations:

                    self.report.indent()
                    self.report.write("Adding source at location:")
                    self.report.indent()
                    self.report.writeDict(extremeLocation)
                    self.report.dedent()
                    font = self.operator.makeInstance(extremeLocation)
                    self.operator.addSourceDescriptor(
                        font=font,
                        name=f"source.{len(self.operator.sources) + 1}",
                        familyName=font.info.familyName,
                        styleName=font.info.styleName,
                        location=extremeLocation
                    )
                    self.report.dedent()
            self.report.newLine()

    def makeSourceGlyphsCompatible(self):
        """
        Update all sources with missing glyphs.
        All sources must have the same glyphs.
        """
        self.report.writeTitle("Making source glyphs compatible", "'")
        self.report.indent()
        # collect all possible glyph names
        glyphNames = set()
        for font in self.operator.fonts.values():
            glyphNames.update(font.keys())
        # get the default source
        defaultSource = self.operator.findDefaultFont()
        # loop over all glyphName
        for glyphName in glyphNames:
            # first check if the default source has this glyph
            if glyphName not in defaultSource:
                # the default does not have the glyph
                # build a repair glyph
                result = self.operator.makeOneGlyph(
                    glyphName=glyphName,
                    location=self.operator.newDefaultLocation(),
                    decomposeComponents=False,
                    useVarlib=False,
                    roundGeometry=self.operator.roundGeometry,
                    clip=False
                )
                self.report.write(f"Adding missing glyph '{glyphName}' in the default source '{defaultSource.info.familyName} {defaultSource.info.styleName}'")
                # add the glyph to the default source
                glyph = defaultSource.newGlyph(glyphName)
                result.extractGlyph(glyph, onlyGeometry=True)
                glyph.unicodes = list(result.unicodes)

            sourceGlyphs = []
            # fill all sources with missing glyphs
            # and collect all glyphs from all sources
            # to send them to optimize contour data
            for sourceDescriptor in self.operator.sources:
                sourceFont = self.operator.fonts[sourceDescriptor.name]
                if glyphName in sourceFont:
                    sourceGlyphs.append(sourceFont[glyphName])
                    continue
                # build a filler glyph
                result = self.operator.makeOneGlyph(
                    glyphName=glyphName,
                    location=sourceDescriptor.location,
                    decomposeComponents=False,
                    useVarlib=self.operator.useVarlib,
                    roundGeometry=self.operator.roundGeometry,
                    clip=False
                )
                self.report.write(f"Adding missing glyph '{glyphName}' in the source '{sourceFont.info.familyName} {sourceFont.info.styleName}'")
                # add the glyph to the source
                glyph = sourceFont.newGlyph(glyphName)
                result.extractGlyph(glyph, onlyGeometry=True)
                glyph.unicodes = list(result.unicodes)
                sourceGlyphs.append(glyph)
            # optimize glyph contour data from all source
            self.makeGlyphOutlinesCompatible(sourceGlyphs)

        if self.debug:
            for name, font in self.operator.fonts.items():
                tempPath = os.path.join(os.path.dirname(font.path), f"{name}_{os.path.basename(font.path)}")
                font.save(tempPath)

        # optimize glyph order if no glyph order is provided
        if self.glyphOrder is None:
            self.glyphOrder = defaultSource.lib.get("public.glyphOrder", [])
            for glyphName in sorted(glyphNames):
                if glyphName not in self.glyphOrder:
                    self.glyphOrder.append(glyphName)

        self.report.dedent()
        self.report.newLine()

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
                self.report.write(f"Adding missing offcurves in contour {contourIndex} for glyph '{glyph.name}' in source '{font.info.familyName} {font.info.styleName}'")
                contour = glyph[contourIndex]
                pen = CompatibleContourPointPen(pointTypes)
                contour.drawPoints(pen)
                contour.clear()
                pen.drawPoints(contour)

    def decomposedMixedGlyphs(self):
        """
        Decompose all glyphs which have both contour point data as components.
        """
        self.report.writeTitle("Decompose Mixed Glyphs", "'")
        self.report.indent()
        fontSources = self.operator.fonts.values()
        for fontSource in fontSources:
            for glyph in fontSource:
                # check if the glyph has both contour point data as components
                if len(glyph) and len(glyph.components):
                    # found, loop over all components and decompose
                    for component in glyph.components:
                        # get the source font
                        base = fontSource[component.baseGlyph]
                        # get the decompose pen
                        decomposePointPen = DecomposePointPen(glyph.layer, glyph.getPointPen(), component.transformation)
                        # draw the base into the pen
                        for contour in base:
                            contour.drawPoints(decomposePointPen)
                        # draw the base components into the pen
                        for component in base.components:
                            component.drawPoints(decomposePointPen)
                    # remove all components
                    glyph.clearComponents()
                    self.report.write(f"Decomposing glyph '{glyph.name}' in source '{fontSource.info.familyName} {fontSource.info.styleName}'")
        self.report.dedent()
        self.report.newLine()

    def makeSourceGlyphsQuadractic(self):
        """
        Optimize and convert all source ufo to quad curves.
        """
        # use cu2qu to optimize all sources
        fonts_to_quadratic(self.operator.fonts.values())

    def makeSourceExportOptimizeCharstring(self):
        for name, font in self.operator.fonts.items():
            font.lib["com.typemytype.robofont.optimizeCharstring"] = False

    def makeSourceKerningCompatible(self):
        """
        Optimize kerning data.
        All sources must have the same kering pairs.
        Build repair mutators for missing kering pairs
        and generate the kerning value within the design space.
        """
        self.report.writeTitle("Making source kerning compatible", "'")
        self.report.indent()
        # collect all kerning pairs
        allPairs = set()
        # collect all groups and all pairs
        allGroups = dict()
        sourceFonts = self.operator.fonts.values()
        for sourceFont in sourceFonts:
            allPairs.update(sourceFont.kerning.keys())
            allGroups.update(sourceFont.groups)
        # build a kerning mutator
        kerningMutator = self.operator.getKerningMutator()
        kerningCache = dict()
        # loop over all pairs
        for pair in allPairs:
            # loop over all sources
            for sourceDescriptor in self.operator.sources:
                sourceFont = self.operator.fonts[sourceDescriptor.name]
                missingPairs = []
                missingGroups = []
                if pair not in sourceFont.kerning:
                    missingPairs.append(pair)
                    kerningInstance = kerningCache.get(sourceDescriptor.name)
                    if kerningInstance is None:
                        kerningInstance = kerningMutator.makeInstance(sourceDescriptor.location)
                        kerningCache[sourceDescriptor.name] = kerningInstance
                    sourceFont.kerning[pair] = kerningInstance[pair]
                    # check pairs on group kerning
                    side1, side2 = pair
                    if side1.startswith(side1Prefix) and side1 not in sourceFont.groups:
                        # add a group
                        sourceFont.groups[side1] = allGroups[side1]
                        missingGroups.append(side1)
                    if side2.startswith(side2Prefix) and side2 not in sourceFont.groups:
                        # add a group
                        sourceFont.groups[side2] = allGroups[side2]
                        missingGroups.append(side2)
                if missingPairs:
                    self.report.write(f"Adding missing kerning pairs in {sourceFont.info.familyName} {sourceFont.info.styleName}: {', '.join(['(%s, %s)' % (s1, s2) for s1, s2 in missingPairs])}")
                if missingGroups:
                    self.report.write(f"Adding missing kerning groups in {sourceFont.info.familyName} {sourceFont.info.styleName}: {', '.join(missingGroups)}")
        self.report.dedent()
        self.report.newLine()

    def makeSourceOnDefaultLocation(self):
        """
        create default location
        which is on the crossing of all axis
        """
        defaultLocation = self.operator.newDefaultLocation(bend=True)
        # compare default location with locations all of sources
        for sourceDescriptor in self.operator.sources:
            if defaultLocation == sourceDescriptor.location:
                # found the default location
                # do nothing
                return
        self.report.writeTitle("Setting a source on the default", "'")
        self.report.indent()
        # there is no source at the default location
        # change the defaults of each axis so it fits with a given source
        for axis in self.operator.axes:
            axis.default = axis.map_backward(defaultLocation[axis.name])
        self.report.writeDict(defaultLocation)
        self.report.dedent()
        self.report.newLine()

    def makeLayerSource(self):
        """
        If there is a layer name in a source description add it as seperate source in the source description.
        """
        for sourceDescriptor in self.operator.sources:
            if sourceDescriptor.layerName is not None:
                layerName = sourceDescriptor.layerName

                layeredUFOPath = sourceDescriptor.path

                path, ext = os.path.splitext(layeredUFOPath)

                sourceDescriptor.path = os.path.join(os.path.dirname(self.destinationPath), f"{path}-{layerName}{ext}")
                sourceDescriptor.styleName = f"{sourceDescriptor.styleName} {layerName}"
                sourceDescriptor.filename = None
                sourceDescriptor.layerName = None

                layeredSource = self.operator._instantiateFont(layeredUFOPath)
                layeredSource.layers.defaultLayer = layeredSource.layers[layerName]
                layeredSource.save(sourceDescriptor.path)

                self.operator.fonts[sourceDescriptor.name] = layeredSource
                self.generatedFiles.add(sourceDescriptor.path)

    def generate(self):
        dirname = os.path.dirname(self.destinationPath)

        # fontCompiler settings
        options = FontCompilerOptions()
        options.fdk = CurrentFDK()
        options.fontCompilerTool = CurrentFontCompilerTool()
        options.saveFDKPartsNextToUFO = self.debug
        options.shouldDecomposeWithCheckOutlines = False
        options.generateCheckComponentMatrix = True
        options.format = self.binaryFormat
        options.decompose = False
        options.checkOutlines = False
        options.autohint = self.autohint
        options.releaseMode = self.releaseMode
        options.turnOnSubroutinization = False
        options.glyphOrder = self.glyphOrder
        options.useMacRoman = False
        # the generate features with fontTools flag is a users decision and should be extracted from the lib
        # options.generateFeaturesWithFontTools = True

        self.report.newLine()
        self.report.writeTitle(f"Generate {self.binaryFormat.upper()}", "'")
        self.report.indent()

        for sourceCount, sourceDescriptor in enumerate(self.operator.sources):
            source = self.operator.fonts[sourceDescriptor.name]
            # get the output path
            familyName = sourceDescriptor.familyName
            if not familyName:
                familyName = source.info.familyName
            styleName = sourceDescriptor.styleName
            if not styleName:
                styleName = source.info.styleName
            outputPath = os.path.join(dirname, f"temp_{sourceCount}_{familyName}-{styleName}.{self.binaryFormat}")
            self.generatedFiles.add(outputPath)
            # set the output path
            options.outputPath = outputPath
            options.layerName = None
            if sourceDescriptor.layerName:
                options.layerName = sourceDescriptor.layerName
            # generate the font
            try:
                result = generateFont(source, options=options)
                sourceDescriptor.font = TTFont(outputPath)
                if sourceDescriptor.layerName:
                    # https://github.com/googlefonts/ufo2ft/blob/150c2d6a00da9d5854173c8457a553ce03b89cf7/Lib/ufo2ft/_compilers/interpolatableTTFCompiler.py#L58-L66
                    if "post" in sourceDescriptor.font:
                        sourceDescriptor.font["post"].underlinePosition = -0x8000
                        sourceDescriptor.font["post"].underlineThickness = -0x8000

                if self.debug:
                    tempSavePath = os.path.join(dirname, f"temp_{sourceCount}_{familyName}-{styleName}.ufo")
                    source.save(tempSavePath)
                    if source.layers.defaultLayer.name != sourceDescriptor.layerName:
                        tempFont = defcon.Font(tempSavePath)
                        tempFont.layers.defaultLayer = tempFont.layers[sourceDescriptor.layerName]
                        tempFont.save()
            except Exception as e:
                import traceback
                tracebackResult = traceback.format_exc()
                result = f"Faild to generate: {e}:\n{tracebackResult}"
                print(tracebackResult)
                self.report.newLine()
                self.report.write(f"Generate failed {familyName}-{styleName}")
                self.report.indent()
                self.report.write(tracebackResult)
                self.report.dedent()

            self.report.newLine()
            self.report.write(f"Generate {familyName}-{styleName}")
            self.report.write(result)
        self.report.dedent()

        # optimize the design space for varlib
        designSpacePath = os.path.join(dirname, f"{self.destinationPath}.designspace")
        self.operator.write(designSpacePath)
        self.generatedFiles.add(designSpacePath)

        try:
            # let varLib build the variation font
            varFont, _, _ = varLib.build(self.operator.doc)
            # save the variation font
            varFont.save(self.destinationPath)
        except Exception:
            import traceback
            result = traceback.format_exc()
            print(result)


def build(root, generateOptions, settings, progress, report):

    binaryFormats = []
    if generateOptions.get("variableFontGenerate_OTF"):
        binaryFormats.append(("otf", postProcessCollector()))
    if generateOptions.get("variableFontGenerate_OTFWOFF2"):
        binaryFormats.append(("otf-woff2", postProcessCollector(WOFF2Builder)))
    if generateOptions.get("variableFontGenerate_TTF"):
        binaryFormats.append(("ttf", postProcessCollector()))
    if generateOptions.get("variableFontGenerate_TTFWOFF2"):
        binaryFormats.append(("ttf-woff2", postProcessCollector(WOFF2Builder)))

    if not binaryFormats:
        return

    variableFontsRoot = os.path.join(root, "Variable")
    removeTree(variableFontsRoot)

    for sourceDesignspace in generateOptions["sourceDesignspaces"]:
        if isinstance(sourceDesignspace, str):
            operator = BatchEditorOperator(sourceDesignspace)
        else:
            operator = sourceDesignspace
            operator.doc = operator.doc.deepcopyExceptFonts()
            # copy all sources
            for key, font in list(operator.fonts.items()):
                operator.fonts[key] = font.copy()

        # loop over all interpolable operators based on the given variable fonts
        for name, interpolableOperator in operator.getInterpolableUFOOperators(useVariableFonts=True):
            for binaryFormat, postProcessCallback in binaryFormats:
                binaryExtention = binaryFormat.split("-")[0]

                suffix = settings["variableFontsSuffix"]
                fileName = f"{name}{suffix}.{binaryExtention}"
                tempFileName = f"temp_{fileName}"

                if settings["batchSettingExportInSubFolders"]:
                    fontDir = os.path.join(variableFontsRoot, binaryFormat)
                else:
                    fontDir = variableFontsRoot

                buildTree(fontDir)

                GenerateVariableFont(
                    operator=interpolableOperator,
                    destinationPath=os.path.join(fontDir, tempFileName),
                    autohint=settings["variableFontsAutohint"],
                    fitToExtremes=settings["variableFontsInterpolateToFitAxesExtremes"],
                    releaseMode=False,
                    glyphOrder=None,
                    report=report,
                    debug=settings["batchSettingExportDebug"]
                )

                sourcePath = os.path.join(fontDir, tempFileName)
                destinationPath = os.path.join(fontDir, fileName)
                sourcePath, destinationPath = postProcessCallback(
                    sourcePath,
                    destinationPath
                )
                if os.path.exists(sourcePath) and sourcePath != destinationPath:
                    shutil.copyfile(sourcePath, destinationPath)
                    os.remove(sourcePath)


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
