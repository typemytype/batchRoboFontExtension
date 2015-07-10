from AppKit import *
import os

from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController
from defcon import Font as DefconFont

from lib.formatters import PathFormatter
from lib.tools.misc import walkDirectoryForFile

from lib.doodlePreferences import ExtensionPathWrapper

from mojo.UI import AccordionView
from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.roboFont import AllFonts

from webFormats import WebFormats
from batchGenerate import BatchGenerate
from binaryMerger import BinaryMerger

from batchTools import settingsIdentifier, updateWithDefaultValues, TaskRunner

defaultOptions = {
            "threaded": False,
            "exportInFolders": False,
        }


class Settings(BaseWindowController):

    identifier = "%s.%s" % (settingsIdentifier, "general")

    def __init__(self, parentWindow):

        data = getExtensionDefault(self.identifier, dict())
        updateWithDefaultValues(data, defaultOptions)

        width = 300
        height = 1000

        self.w = Sheet((width, height), parentWindow=parentWindow)

        y = 10
        self.w.threaded = CheckBox((10, y, -10, 22), "Threaded", value=data["threaded"])

        y += 30
        self.w.exportInFolders = CheckBox((10, y, -10, 22), "Export in Sub Folders", value=data["exportInFolders"])

        y += 35
        self.w.saveButton = Button((-100, y, -10, 20), "Save settings", callback=self.saveCallback, sizeStyle="small")
        self.w.setDefaultButton(self.w.saveButton)

        self.w.closeButton = Button((-190, y, -110, 20), "Cancel", callback=self.closeCallback, sizeStyle="small")
        self.w.closeButton.bind(".", ["command"])
        self.w.closeButton.bind(unichr(27), [])

        self.w.resetButton = Button((-280, y, -200, 20), "Reset", callback=self.resetCallback, sizeStyle="small")

        y += 30
        self.w.resize(width, y, False)

        self.w.open()

    def resetCallback(self, sender):
        self.w.threaded.set(defaultOptions["threaded"])
        self.w.exportInFolders.set(defaultOptions["exportInFolders"])

    def saveCallback(self, sender):
        data = {
            "threaded": self.w.threaded.get(),
            "exportInFolders": self.w.exportInFolders.get()
        }
        setExtensionDefault(self.identifier, data)
        self.closeCallback(sender)

    def closeCallback(self, sender):
        self.w.close()

genericListPboardType = "genericListPboardType"


class ToolBox(BaseWindowController):

    pathItemClass = ExtensionPathWrapper

    def __init__(self):
        h = 530
        self.w = Window((300, h), "Batch", minSize=(300, 400))

        toolbarItems = [
                        dict(itemIdentifier="open",
                            label="Open",
                            imageNamed="toolbarScriptOpen",
                            callback=self.toolbarOpen,
                        ),
                        dict(itemIdentifier="addOpenFonts",
                            label="Add Open Fonts",
                            imageNamed="toolbarScriptNew",
                            callback=self.toolbarAddOpenFonts,
                        ),
                        dict(itemIdentifier=NSToolbarFlexibleSpaceItemIdentifier),
                        dict(itemIdentifier="settings",
                            label="Settings",
                            imageNamed="prefToolbarMisc",
                            callback=self.toolbarSettings,
                        ),
                        ]

        self.w.addToolbar(toolbarIdentifier="ToolBoxToolbar", toolbarItems=toolbarItems, addStandardItems=False)

        y = 10

        columnDescriptions = [
                              dict(title="path", key="path", formatter=PathFormatter.alloc().init()),
                              ]

        self.paths = List((0, 0, -0, -0), [],
                            columnDescriptions=columnDescriptions,
                            showColumnTitles=False,
                            allowsMultipleSelection=False,
                            enableDelete=True,
                            dragSettings=dict(type=genericListPboardType, callback=self.dragCallback),
                            selfDropSettings=dict(type=genericListPboardType, operation=NSDragOperationMove, callback=self.selfDropCallback),
                            otherApplicationDropSettings=dict(type=NSFilenamesPboardType,
                                                              operation=NSDragOperationCopy,
                                                              callback=self.dropPathCallback),
                            )

        y += 200

        self.webFormats = WebFormats((0, 0, -0, -0), self)
        self.batchGenerate = BatchGenerate((0, 0, -0, -0), self)
        self.binaryMerger = BinaryMerger((0, 0, -0, -0), self, self.batchGenerate.run)

        descriptions = [
                            dict(label="Fonts", view=self.paths, minSize=50, size=200, canResize=True, collapsed=False),
                            dict(label="Web Fonts", view=self.webFormats, size=240, canResize=False, collapsed=False),
                            dict(label="Generate", view=self.batchGenerate, size=240, canResize=False, collapsed=False),
                            dict(label="Binary Merge", view=self.binaryMerger, size=240, canResize=False, collapsed=False),
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

    def runTask(self, callback, **kwargs):
        progress = self.startProgress("Preparing...")
        self.task = TaskRunner(callback, self.isThreaded(), progress, kwargs)

    # list

    def get(self):
        items = self.paths.get()
        paths = []
        for item in items:
            path = item.path()
            if os.path.splitext(path)[1] == ".ufo":
                f = DefconFont(path)
                if f.info.familyName and f.info.styleName:
                    paths.append(path)
                else:
                    message = "%s has not family name or style name" % path
                    print "*" * len(message)
                    print message
                    print "*" * len(message)
            elif os.path.isdir(path):
                _paths = walkDirectoryForFile(path, ext=".ttf")
                _paths += walkDirectoryForFile(path, ext=".otf")
                _paths += walkDirectoryForFile(path, ext=".ufo")
                paths.extend(_paths)
            else:
                paths.append(path)
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
        # only include UFOs
        paths = [path for path in paths if os.path.splitext(path)[-1].lower() in [".ttf", ".otf", ".ufo"] or os.path.isdir(path)]
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
        self.showGetFile(["ttf", "otf", "ufo", ""], self._toolbarOpen)

    def toolbarSettings(self, sender):
        Settings(self.w)

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
