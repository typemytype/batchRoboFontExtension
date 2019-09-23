from AppKit import NSSegmentStyleSmallSquare

import os
import tempfile
import shutil

from vanilla import *
from fontTools.ttLib import TTFont

from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.roboFont import RFont
from mojo.UI import getDefault

from batchTools import settingsIdentifier, Report


class BinaryMerger(Group):

    defaultTableNames = [dict(add=False, tableName=t) for t in
                    ["head", "hhea", "maxp", "OS/2", "hmtx", "LTSH", "VDMX",
                    "hdmx", "cmap", "fpgm", "prep", "cvt ", "loca", "CFF ", "glyf",
                    "GPOS", "GSUB",
                    "kern", "name", "post", "gasp", "PCLT"]]

    binaryMergerIdentifierKey = "%s.%s" % (settingsIdentifier, "binaryMergerTables")

    def __init__(self, posSize, controller, generateCallback):

        super(BinaryMerger, self).__init__(posSize)

        self.controller = controller
        self._generateCallback = generateCallback

        tableNames = getExtensionDefault(self.binaryMergerIdentifierKey, self.defaultTableNames)

        columnDescriptions = [
            dict(title="", key="add", width=20, cell=CheckBoxListCell()),
            dict(title="Table Name", key="tableName", editable=True)
            ]

        self.tableList = List((0, 0, -0, -40), tableNames,
                    columnDescriptions=columnDescriptions,
                    editCallback=self.tableListEditCallback,
                    )

        segmentDescriptions = [dict(title="+"), dict(title="-")]
        self.addDel = SegmentedButton((12, -28, 60, 20), segmentDescriptions, selectionStyle="momentary", callback=self.addDelCallback)
        self.addDel.getNSSegmentedButton().setSegmentStyle_(NSSegmentStyleSmallSquare)

        self.generate = Button((-150, -30, -10, 22), "Generate & Merge", callback=self.generateCallback)
        self.height = 240

    def updateDefaults(self):
        tables = list(self.tableList)
        setExtensionDefault(self.binaryMergerIdentifierKey, tables)

    def tableListEditCallback(self, sender):
        self.updateDefaults()

    def addCallback(self):
        self.tableList.append(dict(add=False, tableName="----"))

    def delCallback(self):
        sel = self.tableList.getSelection()
        for i in reversed(sel):
            del self.tableList[i]

    def addDelCallback(self, sender):
        i = sender.get()
        if i == 0:
            self.addCallback()
        else:
            self.delCallback()
        self.updateDefaults()

    def run(self, destDir, progress):
        paths = self.controller.get(["ufo"])

        report = Report()

        tempDir = os.path.join(destDir, "temp")
        if not os.path.exists(tempDir):
            os.makedirs(tempDir)
        tempExportPaths = self._generateCallback(tempDir, progress, report)

        progress.update("Merging Tables...")
        report.writeTitle("Merged Fonts:")
        report.newLine()

        tableNames = [item["tableName"] for item in self.tableList if item["add"]]

        for fontIndex, path in enumerate(paths):
            font = RFont(path, document=False, showInterface=False)
            binarySourcepath = font.lib.get("com.typemytype.robofont.binarySource")
            tempExportPath = tempExportPaths[fontIndex]
            if binarySourcepath:
                binaryIs
                Type = os.path.splitext(binarySourcepath)[1].lower() in [".ttf", ".otf"]
                tempIsOpenType = os.path.splitext(tempExportPath)[1].lower() in [".ttf", ".otf"]
                if binaryIsOpenType and tempIsOpenType:
                    if os.path.exists(binarySourcepath) and os.path.exists(tempExportPath):
                        binarySource = TTFont(binarySourcepath)
                        tempFont = TTFont(tempExportPath)
                        fileName = os.path.basename(tempExportPath)
                        if not self.controller.keepFileNames():
                            fileName = "%s-%s%s" % (font.info.familyName, font.info.styleName, os.path.splitext(tempExportPath)[1])
                        path = os.path.join(destDir, fileName)
                        report.writeTitle(os.path.basename(path), "'")
                        report.write("source: %s" % tempExportPath)
                        report.write("binary source: %s" % binarySourcepath)
                        report.newLine()
                        report.indent()
                        for table in tableNames:
                            if table in binarySource:
                                report.write("merge %s table" % table)
                                tempFont[table] = binarySource[table]
                        report.write("save to %s" % path)
                        tempFont.save(path)
                        report.dedent()
                        report.newLine()
                        tempFont.close()
                        binarySource.close()
            if not font.hasInterface():
                font.close()

        reportPath = os.path.join(destDir, "Binary Merge Report.txt")
        report.save(reportPath)

        if not getDefault("Batch.Debug", False):
            if os.path.exists(tempDir):
                shutil.rmtree(tempDir)

    def _generate(self, destDir):
        if not destDir:
            return
        destDir = destDir[0]
        self.controller.runTask(self.run, destDir=destDir)

    def generateCallback(self, sender):
        if not self.controller.hasSourceFonts("No Fonts to Merge.", "Add Open, drop or add Open Fonts fonts to batch them.", supportedExtensions=["ufo"]):
            return
        self.controller.showGetFolder(self._generate)
