from AppKit import NSSegmentStyleSmallSquare

import os
import tempfile
import shutil

from vanilla import *
from fontTools.ttLib import TTFont

from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.roboFont import OpenFont

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
        report = Report()
        tempDir = tempfile.mkdtemp()
        tempExportPaths = self._generateCallback(tempDir, progress, report)

        progress.update("Merging Tables...")
        report.writeTitle("Merging Tables:")

        paths = self.controller.get()
        tableNames = [item["tableName"] for item in self.tableList if item["add"]]

        for fontIndex, path in enumerate(paths):
            font = OpenFont(path, showUI=False)
            binarySourcepath = font.lib.get("com.typemytype.robofont.binarySource")
            tempExportPath = tempExportPaths[fontIndex]
            if binarySourcepath:
                binaryIsOpenType = os.path.splitext(binarySourcepath)[1].lower() in [".ttf", ".otf"]
                tempIsOpenType = os.path.splitext(tempExportPath)[1].lower() in [".ttf", ".otf"]
                if binaryIsOpenType and tempIsOpenType:
                    binarySource = TTFont(binarySourcepath)
                    tempFont = TTFont(tempExportPath)
                    fileName = os.path.basename(tempExportPath)
                    path = os.path.join(destDir, fileName)
                    report.write(path)
                    for table in tableNames:
                        if table in binarySource:
                            report.write("\tmerge %s table from %s" % (table, binarySourcepath))
                            tempFont[table] = binarySource[table]
                    tempFont.save(path)
                    tempFont.close()
                    binarySource.close()
            font.close()

        reportPath = os.path.join(destDir, "Binary Merge Report")
        report.save(reportPath)

        if os.path.exists(tempDir):
            shutil.rmtree(tempDir)

    def _generate(self, destDir):
        if not destDir:
            return
        destDir = destDir[0]
        self.controller.runTask(self.run, destDir=destDir)

    def generateCallback(self, sender):
        self.controller.showGetFolder(self._generate)
