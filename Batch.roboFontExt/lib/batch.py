import importlib
import batchSettings
importlib.reload(batchSettings)
import batchGenerators.batchTools
importlib.reload(batchGenerators.batchTools)

import batchGenerators
importlib.reload(batchGenerators)
import batchGenerators.desktopFontsGenerator
importlib.reload(batchGenerators.desktopFontsGenerator)
import batchGenerators.webFontsGenerator
importlib.reload(batchGenerators.webFontsGenerator)
import batchGenerators.variableFontsGenerator
importlib.reload(batchGenerators.variableFontsGenerator)

import os
import AppKit
import ezui
import defcon

from mojo.roboFont import OpenFont
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
from lib.tools.misc import walkDirectoryForFile

from batchSettings import BatchSettingsController

from batchGenerators import desktopFontsGenerator, webFontsGenerator, variableFontsGenerator
from batchGenerators.batchTools import Report, BatchEditorOperator


generators = [
    desktopFontsGenerator,
    webFontsGenerator,
    variableFontsGenerator
]


def buildIdentifierKey(identifier, item):
    return f"{identifier}Generate_{item.replace(' ', '')}"


def buildFormatCheckBoxes(items, identifier, prefix=""):
    result = []
    for item in items:
        result.append(f"{prefix} [ ] {item}                 @{buildIdentifierKey(identifier, item)}")
    return "\n".join(result)


def tableAddPathItems(table, paths):
    if paths:
        existingSources = [item["source"] for item in table.getItems()]
        items = []
        for path in paths:
            if path not in existingSources:
                items.append(table.makeItem(
                    source=path,
                ))
        table.appendItems(items)


class BatchController(ezui.WindowController):

    desktopFontsFormats = [
        "OTF",
        "TTF",
    ]
    webFontsFormats = [
        "OTF",
        "OTF Woff 2",
        "TTF",
        "TTF Woff 2",
        "SVG",
    ]
    variableFontsFormats = [
        "OTF",
        "OTF Woff 2",
        "TTF",
        "TTF Woff 2",
    ]

    supportedFileTypes = ["ufo", "designspace", "otf", "ttf", "woff", "ttx"]

    def build(self, sources=[]):
        content = f"""

#= ScrollingVerticalStack
|---|                                              @sources
(+-)                                               @sourcesAddRemoveButton

* HorizontalStack
> * Box @desktopFontsBox
>> !§ Desktop Fonts:
{ buildFormatCheckBoxes(self.desktopFontsFormats, "desktopFont", ">>") }

> * Box @webFontsBox
>> !§ Web Fonts:
{ buildFormatCheckBoxes(self.webFontsFormats, "webFont", ">>") }

> * Box @variableFontsBox
>> !§ Variable Fonts:
{ buildFormatCheckBoxes(self.variableFontsFormats, "variableFont", ">>") }

=---=

(?)                                               @help
(*)                                               @settings
( Generate )                                      @generate
"""
        descriptionData = dict(
            sources=dict(
                height=200,
                columnDescriptions=[dict(identifier="source", title="Sources", cellClassArguments=dict(truncationMode="head"))],
                showColumnTitles=True,
                items=[dict(source=source) for source in sources],
                dropSettings=dict(
                    pasteboardTypes=["fileURL"],
                    dropCandidateCallback=self.sourcesDropCandidateCallback,
                    performDropCallback=self.sourcesPerformDropCallback
                )
            ),
            sourcesAddOpenUFO=dict(
                width="fill",
                alignment="left",
                gravity="leading",
            ),
            help=dict(
                gravity="leading",
            ),
        )
        self.w = ezui.EZWindow(
            title="Batch",
            content=content,
            descriptionData=descriptionData,
            size="auto",
            controller=self,
        )

    def started(self):
        items = getExtensionDefault("com.typemytype.batch", dict())
        for identifier in ("sources", "help"):
            if identifier in items:
                del items[identifier]

        self.w.setItemValues(items)
        self.w.open()

    def destroy(self):
        items = self.w.getItemValues()
        for identifier in ("sources", "help"):
            if identifier in items:
                del items[identifier]
        setExtensionDefault("com.typemytype.batch", items)

    def sourcesAddRemoveButtonAddCallback(self, sender):
        # add item
        def result(paths):
            tableAddPathItems(self.w.getItem("sources"), paths)

        self.showGetFile(
            callback=result,
            fileTypes=self.supportedFileTypes,
            allowsMultipleSelection=True
        )

    def sourcesAddRemoveButtonRemoveCallback(self, sender):
        # remove selected items
        table = self.w.getItem("sources")
        table.removeSelectedItems()

    def sourcesDropCandidateCallback(self, info):
        table = self.w.getItem("sources")
        sender = info["sender"]
        droppedItems = sender.getDropItemValues(info["items"], "fileURL")
        existing = [item["source"] for item in table.getItems()]

        items = []
        for item in droppedItems:
            path = item.path()
            if path in existing:
                # already in the list
                continue
            if os.path.isdir(path) or item.pathExtension() in self.supportedFileTypes:
                items.append(path)
        if not items:
            return "none"
        return "link"

    def sourcesPerformDropCallback(self, info):
        sender = info["sender"]
        items = sender.getDropItemValues(info["items"], "fileURL")
        items = [item.path() for item in items]
        tableAddPathItems(self.w.getItem("sources"), items)

    def sourcesDoubleClickCallback(self, sender):
        appPath = AppKit.NSBundle.mainBundle().bundlePath()
        for item in sender.getSelectedItems():
            os.system(f"open -a {appPath} {item['source']}")

    def helpCallback(self, sender):
        ExtensionBundle("Batch").openHelp()

    def settingsCallback(self, sender):
        BatchSettingsController(self.w)

    report = None

    def generateCallback(self, sender):

        def result(path):
            if path:
                path = path[0]

                progress = self.startProgress("Generating...")
                try:
                    self.report = Report()
                    self.report.writeTitle("Batch Generate:")
                    self.report.indent()

                    settings = getExtensionDefault("com.typemytype.batch.setting", dict())

                    generateOptions = self.w.getItemValues()
                    generateOptions["sourceUFOPaths"] = self.getAllUFOPaths()
                    generateOptions["sourceDesignspacePaths"] = self.getAllDesignspacePaths()

                    # self.report.write(generateOptions)

                    for generator in generators:
                        generator.build(path, generateOptions, settings, progress, self.report)

                finally:
                    self.report.dedent()
                    self.report.save(os.path.join(path, "Batch Generate Report.txt"))
                    self.report = None
                    progress.close()

        self.showGetFolder(
            result,
            messageText="Generate in...",
            allowsMultipleSelection=False,
        )

    # helpers

    def getAllUFOPaths(self, flattenDesignSpace=True):
        table = self.w.getItem("sources")
        items = table.getSelectedItems()
        if not items:
            items = table.getArrangedItems()
        ufoPaths = []
        for item in items:
            path = item["source"]
            ext = os.path.splitext(path)[1].lower()
            if ext == ".ufo":
                dummyFont = defcon.Font(path)
                if dummyFont.info.familyName is not None and dummyFont.info.styleName is not None:
                    ufoPaths.append(path)
                elif self.report is not None:
                    self.report.write(f"'{path}' has no family name or style name")
            elif os.path.isdir(path):
                for ext in self.supportedFontFileFormats:
                    ufoPaths.extend(walkDirectoryForFile(path, ext=ext))
            elif flattenDesignSpace and ext == ".designspace":
                if "designspaceDocument" not in item:
                    item["designspaceDocument"] = BatchEditorOperator(path)
                designspaceDocument = item["designspaceDocument"]
                designspaceDocument.generateUFOs()
                for sourceDescriptor in designspaceDocument.sources:
                    ufoPaths.append(sourceDescriptor.path)
                for instanceDescriptor in designspaceDocument.instances:
                    if instanceDescriptor.path is not None:
                        ufoPaths.append(instanceDescriptor.path)
        return ufoPaths

    def getAllDesignspacePaths(self):
        table = self.w.getItem("sources")
        items = table.getSelectedItems()
        if not items:
            items = table.getArrangedItems()
        return [item["source"] for item in items if item["source"].lower().endswith(".designspace")]

    def startProgress(self, *args, **kwargs):
        progress = super().startProgress(*args, **kwargs)
        # keep api in sync with older progress windows
        progress.update = progress.setText
        progress.setTickCount = progress.setMaxValue
        return progress


if __name__ == "__main__":
    paths = [
        "../../tests/designspace_simple/test.designspace",
        "../../tests/designspace_simple/thick.ufo"
    ]
    paths = [os.path.abspath(path) for path in paths]
    BatchController(paths)
