import os
from mojo.roboFont import RFont

from batchGenerators.batchTools import removeTree, generatePaths, postProcessCollector


def build(root, generateOptions, settings, progress, report):
    binaryFormats = []
    if generateOptions.get("desktopFontGenerate_OTF"):
        binaryFormats.append(("otf", postProcessCollector()))
    if generateOptions.get("desktopFontGenerate_TTF"):
        binaryFormats.append(("ttf", postProcessCollector()))
    # if generateOptions.get("desktopFontGenerate_PFA"):
    #     binaryFormats.append(("pfa", postProcessCollector()))
    # if generateOptions.get("desktopFontGenerate_VFB"):
    #     binaryFormats.append(("vfb", postProcessCollector()))

    if not binaryFormats:
        return

    report.writeTitle("Batch Generated Desktop Fonts:")
    progress.setText("Collecting Data...")

    desktopFontsRoot = os.path.join(root, "Desktop")
    removeTree(desktopFontsRoot)

    generatePaths(
        ufoPaths=generateOptions["sourceUFOPaths"],
        binaryFormats=binaryFormats,
        decompose=settings["desktopFontsDecompose"],
        removeOverlap=settings["desktopFontsRemoveOverlap"],
        autohint=settings["desktopFontsAutohint"],
        releaseMode=settings["desktopFontsReleaseMode"],
        keepFileNames=settings["batchSettingExportKeepFileNames"],
        suffix=settings["desktopFontsSuffix"],
        exportInFolders=settings["batchSettingExportInSubFolders"],
        root=desktopFontsRoot,
        report=report,
        progress=progress
    )
