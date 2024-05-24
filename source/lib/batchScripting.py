from batchGenerators.batchTools import Report
import batchGenerators
import batchSettings


def generateDesktopFonts(ufoPaths, destinationRoot, format="ttf", decompose=True, removeOverlap=True, autohint=False, releaseMode=True, suffix=""):
    if isinstance(ufoPaths, str):
        ufoPaths = [ufoPaths]
    report = Report()
    generateOptions = dict(
        sourceUFOPaths=ufoPaths,
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
        progress=None,
        report=report
    )
    return report.get()


def generateWebFonts(ufoPaths, destinationRoot, format="ttf", woff=False, decompose=True, removeOverlap=True, autohint=False, releaseMode=True, suffix="", html=False, htmlPreview=None):
    if isinstance(ufoPaths, str):
        ufoPaths = [ufoPaths]
    report = Report()
    generateOptions = dict(
        sourceUFOPaths=ufoPaths,
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
        progress=None,
        report=report
    )
    return report.get()


def generateVariableFonts(designspacePaths, destinationRoot, format="ttf", woff=False, autohint=False, fitToExtremes=False, suffix=""):
    if isinstance(designspacePaths, str):
        designspacePaths = [designspacePaths]
    report = Report()
    generateOptions = dict(
        sourceDesignspacePaths=designspacePaths,
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
        progress=None,
        report=report
    )
    return report.get()
