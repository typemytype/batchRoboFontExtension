import AppKit
import os

from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController
from defcon import Font as DefconFont

from lib.formatters import PathFormatter
from lib.tools.misc import walkDirectoryForFile
from lib.settings import doodleSupportedExportFileTypes

from mojo.UI import AccordionView, getDefault, setDefault
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
from mojo.roboFont import AllFonts

from webFormats import WebFormats
from batchGenerate import BatchGenerate
from binaryMerger import BinaryMerger
from variableFontGenerator import BatchVariableFontGenerate, BatchDesignSpaceProcessor

from batchTools import settingsIdentifier, ufoVersion, updateWithDefaultValues, TaskRunner

defaultOptions = {
    "threaded": False,
    "exportInFolders": False,
    "keepFileNames": False,
}


class Settings(BaseWindowController):

    identifier = "%s.%s" % (settingsIdentifier, "general")

    def __init__(self, parentWindow):

        data = getExtensionDefault(self.identifier, dict())
        updateWithDefaultValues(data, defaultOptions)
        data["debug"] = getDefault("Batch.Debug", False)

        width = 380
        height = 1000

        self.w = Sheet((width, height), parentWindow=parentWindow)

        y = 10
        self.w.threaded = CheckBox((10, y, -10, 22), "Threaded", value=data["threaded"])

        y += 30
        self.w.exportInFolders = CheckBox((10, y, -10, 22), "Export in Sub Folders", value=data["exportInFolders"])

        y += 30
        self.w.keepFileNames = CheckBox((10, y, -10, 22), "Keep file names (otherwise use familyName-styleName)", value=data["keepFileNames"])

        y += 30
        self.w.debug = CheckBox((10, y, -10, 22), "Debug", value=data["debug"])

        y += 35
        self.w.saveButton = Button((-100, y, -10, 20), "Save settings", callback=self.saveCallback, sizeStyle="small")
        self.w.setDefaultButton(self.w.saveButton)

        self.w.closeButton = Button((-190, y, -110, 20), "Cancel", callback=self.closeCallback, sizeStyle="small")
        self.w.closeButton.bind(".", ["command"])
        self.w.closeButton.bind(chr(27), [])

        self.w.resetButton = Button((-280, y, -200, 20), "Reset", callback=self.resetCallback, sizeStyle="small")

        y += 30
        self.w.resize(width, y, False)

        self.w.open()

    def resetCallback(self, sender):
        self.w.threaded.set(defaultOptions["threaded"])
        self.w.exportInFolders.set(defaultOptions["exportInFolders"])
        self.w.keepFileNames.set(defaultOptions["keepFileNames"])
        self.w.debug.set(False)

    def saveCallback(self, sender):
        data = {
            "threaded": self.w.threaded.get(),
            "exportInFolders": self.w.exportInFolders.get(),
            "keepFileNames": self.w.keepFileNames.get()
        }
        setExtensionDefault(self.identifier, data)
        setDefault("Batch.Debug", self.w.debug.get())
        self.closeCallback(sender)

    def closeCallback(self, sender):
        self.w.close()


genericListPboardType = "genericListPboardType"


class BatchPathWrapper(AppKit.NSObject):

    def __new__(cls, *arg, **kwargs):
        return cls.alloc().init()

    def __init__(self, path):
        self._path = path

    def path(self):
        return self._path


class ToolBox(BaseWindowController):

    pathItemClass = BatchPathWrapper

    supportedFontFileFormats = [".%s" % ext.lower() for ext in doodleSupportedExportFileTypes + ["ufo", "woff", "pfb", "ttx", "designspace"]]

    def __init__(self):
        h = 530
        self.w = Window((300, h), "Batch", minSize=(300, 400))

        toolbarItems = [
            dict(
                itemIdentifier="open",
                label="Open",
                imageNamed="toolbarScriptOpen",
                callback=self.toolbarOpen,
            ),
            dict(
                itemIdentifier="addOpenFonts",
                label="Add Open Fonts",
                imageNamed="toolbarScriptNew",
                callback=self.toolbarAddOpenFonts,
            ),
            dict(itemIdentifier=AppKit.NSToolbarFlexibleSpaceItemIdentifier),

            dict(
                itemIdentifier="Help",
                label="Help",
                imageNamed="toolbarDefaultPythonAppUnknow",
                callback=self.toolbarHelp,
            ),
            dict(
                itemIdentifier="settings",
                label="Settings",
                imageNamed="prefToolbarMisc",
                callback=self.toolbarSettings,
            ),
        ]

        self.w.addToolbar(toolbarIdentifier="ToolBoxToolbar", toolbarItems=toolbarItems, addStandardItems=False)
        # some older RF have older vanilla with no support for toolbarStyle
        if hasattr(self.w, "setToolbarStyle"):
            self.w.setToolbarStyle("preference")

        y = 10

        columnDescriptions = [
            dict(title="path", key="path", formatter=PathFormatter.alloc().init()),
        ]

        self.paths = List((0, 0, -0, -0), [],
            columnDescriptions=columnDescriptions,
            showColumnTitles=False,
            allowsMultipleSelection=True,
            enableDelete=True,
            dragSettings=dict(type=genericListPboardType, callback=self.dragCallback),
            selfDropSettings=dict(type=genericListPboardType, operation=AppKit.NSDragOperationMove, callback=self.selfDropCallback),
            selfApplicationDropSettings=dict(
                type=AppKit.NSFilenamesPboardType,
                operation=AppKit.NSDragOperationCopy,
                callback=self.dropPathCallback),
            otherApplicationDropSettings=dict(
                type=AppKit.NSFilenamesPboardType,
                operation=AppKit.NSDragOperationCopy,
                callback=self.dropPathCallback),
        )

        y += 200

        self.webFormats = WebFormats((0, 0, -0, -0), self)
        self.batchGenerate = BatchGenerate((0, 0, -0, -0), self)
        self.binaryMerger = BinaryMerger((0, 0, -0, -0), self, self.batchGenerate.run)
        self.batchVariableFontGenerate = BatchVariableFontGenerate((0, 0, -0, -0), self)

        descriptions = [
            dict(label="Fonts", view=self.paths, minSize=50, size=200, canResize=True, collapsed=False),
            dict(label="Web Fonts", view=self.webFormats, size=self.webFormats.height, canResize=False, collapsed=False),
            dict(label="Batch Generate", view=self.batchGenerate, size=self.batchGenerate.height, canResize=False, collapsed=False),
            dict(label="Variable Fonts", view=self.batchVariableFontGenerate, size=self.batchVariableFontGenerate.height, canResize=False, collapsed=False),
            dict(label="Binary Merge", view=self.binaryMerger, size=240, canResize=self.binaryMerger.height, collapsed=False),
        ]

        self.w.accordionView = AccordionView((0, 0, -0, -0), descriptions)

        self.setUpBaseWindowBehavior()
        self.w.open()

    def window(self):
        return self.w

    def _getDefaultValue(self, identifier, key):
        data = getExtensionDefault(identifier, dict())
        return data.get(key, defaultOptions[key])

    def isThreaded(self):
        return self._getDefaultValue("%s.general" % settingsIdentifier, "threaded")

    def exportInFolders(self):
        return self._getDefaultValue("%s.general" % settingsIdentifier, "exportInFolders")

    def keepFileNames(self):
        return self._getDefaultValue("%s.general" % settingsIdentifier, "keepFileNames")

    def runTask(self, callback, **kwargs):
        progress = self.startProgress("Preparing...")
        self.task = TaskRunner(callback, self.isThreaded(), progress, kwargs)

    def hasSourceFonts(self, messageText, informativeText, supportedExtensions=None, flattenDesignSpace=True):
        if not self.get(supportedExtensions=supportedExtensions, flattenDesignSpace=flattenDesignSpace):
            self.showMessage(messageText, informativeText)
            return False
        return True

    # list

    def get(self, supportedExtensions=None, flattenDesignSpace=True):
        items = self.paths.get()
        paths = []
        for item in items:
            path = item.path()
            ext = os.path.splitext(path)[1].lower()
            if ext == ".ufo":
                f = DefconFont(path)
                if f.info.familyName and f.info.styleName:
                    paths.append(path)
                else:
                    message = "%s has no family name or style name" % path
                    print("*" * len(message))
                    print(message)
                    print("*" * len(message))
            elif os.path.isdir(path):
                for ext in self.supportedFontFileFormats:
                    paths.extend(walkDirectoryForFile(path, ext=ext))
            elif flattenDesignSpace and ext == ".designspace":
                if not hasattr(item, "designSpaceDocument"):
                    item.designSpaceDocument = BatchDesignSpaceProcessor(path, ufoVersion)
                item.designSpaceDocument.generateUFO()
                paths.extend([path for path in item.designSpaceDocument.masterUFOPaths()])
                paths.extend([path for path in item.designSpaceDocument.instancesUFOPaths()])
            else:
                paths.append(path)
        if supportedExtensions is not None:
            supportedExtensions = [".%s" % e for e in supportedExtensions]
            paths = [p for p in paths if os.path.splitext(p)[1] in supportedExtensions]
        return paths

    def _wrapItem(self, path):
        return self.pathItemClass(path)

    def _wrapItems(self, paths):
        return [self._wrapItem(path) for path in paths]

    def dropPathCallback(self, sender, dropInfo):
        isProposal = dropInfo["isProposal"]
        # get a list of existing paths
        existingPaths = [item.path() for item in sender.get()]
        # filter the existing paths out of the proposed paths
        paths = dropInfo["data"]
        paths = [path for path in paths if path not in existingPaths]
        # only include supported formats and folders
        paths = [path for path in paths if os.path.splitext(path)[-1].lower() in self.supportedFontFileFormats or os.path.isdir(path)]
        # no paths, return False
        if not paths:
            return False
        # if it isn't a proposal, store.
        if not isProposal:
            items = sender.get() + self._wrapItems(paths)
            sender.set(items)
        return True

    def dragCallback(self, sender, indexes):
        return indexes

    def selfDropCallback(self, sender, dropInfo):
        isProposal = dropInfo["isProposal"]

        if not isProposal:
            indexes = [int(i) for i in sorted(dropInfo["data"])]
            indexes.sort()
            rowIndex = dropInfo["rowIndex"]

            items = sender.get()

            toMove = [items[index] for index in indexes]

            for index in reversed(indexes):
                del items[index]

            rowIndex -= len([index for index in indexes if index < rowIndex])
            for font in toMove:
                items.insert(rowIndex, font)
                rowIndex += 1
            sender.set(items)
        return True

    # toolbar

    def _toolbarOpen(self, paths):
        existingPaths = [item.path() for item in self.paths.get()]
        paths = [path for path in paths if path not in existingPaths]
        items = self.paths.get() + self._wrapItems(paths)
        self.paths.set(items)

    def toolbarOpen(self, sender):
        # remove the .
        fileFormats = [ext[1:] for ext in self.supportedFontFileFormats]
        # add support for folders
        fileFormats.append("")
        self.showGetFile(fileFormats, self._toolbarOpen, allowsMultipleSelection=True)

    def toolbarAddOpenFonts(self, sender):
        fonts = AllFonts()
        existingPaths = [item.path() for item in self.paths.get()]
        paths = []
        unSaved = []
        for font in fonts:
            if font.path in existingPaths:
                continue
            if font.path:
                paths.append(font.path)
            else:
                unSaved.append("%s %s" % (font.info.familyName, font.info.styleName))
        if unSaved:
            self.showMessage("Cannot import unsaved fonts.", "\n".join(unSaved))
        items = self._wrapItems(paths)
        items = self.paths.get() + self._wrapItems(paths)
        self.paths.set(items)

    def toolbarSettings(self, sender):
        Settings(self.w)

    def toolbarHelp(self, sender):
        ExtensionBundle("Batch").openHelp()
