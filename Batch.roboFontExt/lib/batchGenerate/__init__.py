from AppKit import *
import os

from vanilla import *

from lib.settings import doodleSupportedExportFileTypes

from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.roboFont import OpenFont

from tools import settingsIdentifier, Report, buildTree

class BatchGenerate(Group):

    generateSettings = ["Decompose", "Remove Overlap", "Autohint", "Release Mode"]

    def __init__(self, posSize, controller):
        super(BatchGenerate, self).__init__(posSize)
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
        for format in doodleSupportedExportFileTypes:
            checkbox = CheckBox((10, y, -10, 22), format.upper(), 
                                value=getExtensionDefault("%s.%s" % (settingsIdentifier, format), format != "pfa"),
                                callback=self.saveDefaults)
            setattr(self, format, checkbox)
            y += 30
        
        middle = 45
        self.suffixText = TextBox((10, y+2, middle, 22), "Suffix:", alignment="right")
        self.generateSuffix = EditText((middle+10, y, 100, 22), 
            getExtensionDefault("%s.generateSuffix" % settingsIdentifier, ""),
            callback=self.saveDefaults)

        self.generate = Button((-100, -30, -10, 22), "Generate", callback=self.generateCallback)

    def saveDefaults(self, sender):
        for setting in self.generateSettings:
            key = setting.replace(" ", "_").lower()
            value = getattr(self, key).get()
            setExtensionDefault("%s.%s" % (settingsIdentifier, key), value)

        for format in doodleSupportedExportFileTypes + ["generateSuffix"]:
            value = getattr(self, format).get()
            setExtensionDefault("%s.%s" % (settingsIdentifier, format), value)

    def run(self, destDir, progress, report=None):
        decompose = self.decompose.get()
        removeOverlap = self.remove_overlap.get()
        autohint = self.autohint.get()
        releaseMode = self.release_mode.get()
        suffix = self.generateSuffix.get()

        formats = [i for i in doodleSupportedExportFileTypes if getattr(self, i).get()]
        
        if report is None:
            report = Report()
        report.writeTitle("Batch Generate Files:")

        progress.update("Collecting Data...")
        
        paths = self.controller.get()

        fonts = []
        for path in paths:
            font = OpenFont(path, showUI=False)
            fonts.append(font)
        
        if decompose:
            report.writeTitle("Decompose:")
            progress.update("Decompose...")
            progress.setTickCount(len(fonts))
            for font in fonts:
                report.write("%s %s" % (font.info.familyName, font.info.styleName))
                progress.update()
                font.decompose()
            progress.setTickCount(None)
            report.newLine()
        
        if removeOverlap:
            report.writeTitle("Remove Overlap:")
            progress.update("Remove Overlap...")
            progress.setTickCount(len(fonts))
            for font in fonts:
                report.write("%s %s" % (font.info.familyName, font.info.styleName))
                progress.update()
                font.removeOverlap()
            progress.setTickCount(None)
            report.newLine()
        
        report.writeTitle("Generate:")
        exportPaths = []
        for font in fonts:
            for format in formats:
                familyName = font.info.familyName.replace(" ", "")
                styleName = font.info.styleName.replace(" ", "")
                fileName = "%s-%s%s.%s" % (familyName, styleName, suffix, format)
                progress.update("Generating ... %s" % fileName)
                if self.controller.exportInFolders():
                    fontDir = os.path.join(destDir, format) 
                else:
                    fontDir = destDir
                buildTree(fontDir)
                path = os.path.join(fontDir, fileName)
                report.write("%s %s to %s" % (font.info.familyName, font.info.styleName, path))
                result = font.generate(path, format, 
                              decompose=False, 
                              checkOutlines=False, 
                              autohint=autohint, 
                              releaseMode=releaseMode,
                              progressBar=progress,
                              glyphOrder=font.glyphOrder)
                report.write(result)
                exportPaths.append(path)
            font.close()
        reportPath = os.path.join(destDir, "Generate Report")
        report.save(reportPath)
        return exportPaths

    def _generate(self, destDir):
        if not destDir:
            return
        destDir = destDir[0]
        self.controller.runTask(self.run, destDir=destDir)

    def generateCallback(self, sender):
    	self.controller.showGetFolder(self._generate)
