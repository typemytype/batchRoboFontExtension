from batchGenerators.batchTools import Report, DummyProgress
import batchGenerators
import batchSettings


def generateDesktopFonts(ufoPathsOrObjects, destinationRoot, format="ttf", decompose=True, removeOverlap=True, autohint=False, releaseMode=True, suffix=""):
    if not isinstance(ufoPathsOrObjects, list):
        ufoPathsOrObjects = [ufoPathsOrObjects]
    report = Report()
    generateOptions = dict(
        sourceUFOs=ufoPathsOrObjects,
    )
    settings = dict(batchSettings.defaultSettings)
    settings.update(
        dict(
            batchSettingExportInSubFolders=False,
            desktopFontsAutohint=autohint,
            desktopFontsDecompose=decompose,
            desktopFontsReleaseMode=releaseMode,
            desktopFontsRemoveOverlap=removeOverlap,
            desktopFontsSuffix=suffix
        )
    )
    if format == "ttf":
        generateOptions["desktopFontGenerate_TTF"] = True
    if format == "otf":
        generateOptions["desktopFontGenerate_OTF"] = True

    batchGenerators.desktopFontsGenerator.build(
        root=destinationRoot,
        generateOptions=generateOptions,
        settings=settings,
        progress=DummyProgress(),
        report=report
    )
    return report.get()


def generateWebFonts(ufoPathsOrObjects, destinationRoot, format="ttf", woff=False, decompose=True, removeOverlap=True, autohint=False, releaseMode=True, suffix="", html=False, htmlPreview=None):
    if not isinstance(ufoPathsOrObjects, list):
        ufoPathsOrObjects = [ufoPathsOrObjects]
    report = Report()
    generateOptions = dict(
        sourceUFOs=ufoPathsOrObjects,
    )
    settings = dict(batchSettings.defaultSettings)
    settings.update(
        dict(
            batchSettingExportInSubFolders=False,
            webFontsAutohint=autohint,
            webFontsDecompose=decompose,
            webFontsGenerateHTML=html,
            webFontsReleaseMode=releaseMode,
            webFontsRemoveOverlap=removeOverlap,
            webFontsSuffix=suffix
        )
    )
    if htmlPreview:
        settings["webFontsHtmlPreview"] = htmlPreview
    if format == "ttf" and woff:
        generateOptions["webFontGenerate_TTFWOFF2"] = True
    if format == "otf" and woff:
        generateOptions["webFontGenerate_OTFWOFF2"] = True
    if format == "ttf" and not woff:
        generateOptions["webFontGenerate_TTF"] = True
    if format == "otf" and not woff:
        generateOptions["webFontGenerate_OTF"] = True

    batchGenerators.webFontsGenerator.build(
        root=destinationRoot,
        generateOptions=generateOptions,
        settings=settings,
        progress=DummyProgress(),
        report=report
    )
    return report.get()


def generateVariableFonts(designspacePathsOrObjects, destinationRoot, format="ttf", woff=False, autohint=False, fitToExtremes=False, suffix=""):
    if not isinstance(designspacePathsOrObjects, list):
        designspacePathsOrObjects = [designspacePathsOrObjects]
    report = Report()
    generateOptions = dict(
        sourceDesignspaces=designspacePathsOrObjects,
    )
    settings = dict(batchSettings.defaultSettings)
    settings.update(
        dict(
            batchSettingExportInSubFolders=False,
            variableFontsAutohint=autohint,
            variableFontsInterpolateToFitAxesExtremes=fitToExtremes,
            variableFontsSuffix=suffix
        )
    )
    if format == "ttf" and woff:
        generateOptions["variableFontGenerate_TTFWOFF2"] = True
    if format == "otf" and woff:
        generateOptions["variableFontGenerate_OTFWOFF2"] = True
    if format == "ttf" and not woff:
        generateOptions["variableFontGenerate_TTF"] = True
    if format == "otf" and not woff:
        generateOptions["variableFontGenerate_OTF"] = True

    batchGenerators.variableFontsGenerator.build(
        root=destinationRoot,
        generateOptions=generateOptions,
        settings=settings,
        progress=DummyProgress(),
        report=report
    )
    return report.get()
