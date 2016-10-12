import os

from vanilla import *

from mojo.extensions import getExtensionDefault, setExtensionDefault

from batchTools import settingsIdentifier, ufoVersion, Report, BatchDesignSpaceDocumentReader


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

            desingSpace = BatchDesignSpaceDocumentReader(path, ufoVersion)
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
