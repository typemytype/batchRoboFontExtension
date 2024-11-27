import os
import shutil
import re

from fontTools.ttLib import TTFont

from mojo.compile import autohint as OTFAutohint

from batchGenerators.batchTools import generatePaths, WOFF2Builder, removeTree, postProcessCollector, CSSWriter, HTMLWriter

from .autohint import TTFAutohint


percentageRe = re.compile(r"%(?!\((familyName|styleName)\)s)")


cssFormatExtMap = {
    ".otf": "opentype",
    ".ttf": "truetype",
    ".woff": "woff",
    ".woff2": "woff2"

}


def htmlBuilder(htmlPreview, reportHTML, reportCSS):

    def wrapper(sourcePath, destinationPath):
        font = TTFont(sourcePath)
        familyName = font["name"].getBestFamilyName()
        styleName = font["name"].getBestSubFamilyName()
        font.close()

        _, ext = os.path.splitext(sourcePath)

        cssFontName = f"{familyName}_{styleName}"

        reportCSS.write("@font-face {")
        reportCSS.indent()
        reportCSS.write(f"font-family: '{cssFontName}';")
        reportCSS.write(f"src:  url('{destinationPath}') format('{cssFormatExtMap[ext]}');")
        reportCSS.write("font-weight: normal;")
        reportCSS.write("font-style: normal;")
        reportCSS.dedent()
        reportCSS.write("}")
        reportCSS.newLine()

        reportHTML.write(f"<div style='font-family: \"{cssFontName}\", \"AdobeBlank\";'>")
        html = htmlPreview
        html = percentageRe.sub("&#37;", html)
        html = html % dict(familyName=familyName, styleName=styleName, fileName=os.path.basename(destinationPath))
        reportHTML.write(html.encode("ascii", 'xmlcharrefreplace').decode("utf-8"))
        reportHTML.write("</div>")

    return wrapper


def autohintBuilder(autohintOptions, report):

    def wrapper(sourcePath, destinationPath):
        font = TTFont(sourcePath)
        isTTF = "glyf" in font
        font.close()
        if isTTF:
            result = TTFAutohint(sourcePath, destinationPath, autohintOptions)
        else:
            result = OTFAutohint(sourcePath)
            shutil.copyfile(sourcePath, destinationPath)
        report.writeItems(result)
    return wrapper


def build(root, generateOptions, settings, progress, report):
    if settings["webFontsAutohint"]:
        autohintFunc = autohintBuilder(settings, report)
    else:
        autohintFunc = None

    if settings["webFontsGenerateHTML"]:
        reportHTML = HTMLWriter(cssFileName="font.css", style=settings["webFontsHtmlPreviewCSS"])
        reportCSS = CSSWriter()

        htmlBuilderFunc = htmlBuilder(
            htmlPreview=settings["webFontsHtmlPreview"],
            reportHTML=reportHTML,
            reportCSS=reportCSS
        )
    else:
        htmlBuilderFunc = None

    binaryFormats = []
    if generateOptions.get("webFontGenerate_OTF"):
        binaryFormats.append(("otf", postProcessCollector(autohintFunc, htmlBuilderFunc)))
    if generateOptions.get("webFontGenerate_OTFWOFF2"):
        binaryFormats.append(("otf-woff2", postProcessCollector(autohintFunc, WOFF2Builder, htmlBuilderFunc)))
    if generateOptions.get("webFontGenerate_TTF"):
        binaryFormats.append(("ttf", postProcessCollector(autohintFunc, htmlBuilderFunc)))
    if generateOptions.get("webFontGenerate_TTFWOFF2"):
        binaryFormats.append(("ttf-woff2", postProcessCollector(autohintFunc, WOFF2Builder, htmlBuilderFunc)))
    # if generateOptions["webFontGenerate_SVG"]:
    #    binaryFormats.append(("svg", None))

    if not binaryFormats:
        return

    webFontsRoot = os.path.join(root, "Web")
    removeTree(webFontsRoot)

    report.writeTitle("Batch Generated Web Fonts:")
    progress.setText("Collecting Data...")

    generatePaths(
        sourceUFOs=generateOptions["sourceUFOs"],
        binaryFormats=binaryFormats,
        decompose=settings["webFontsDecompose"],
        removeOverlap=settings["webFontsRemoveOverlap"],
        autohint=False,
        releaseMode=settings["webFontsReleaseMode"],
        keepFileNames=settings["batchSettingExportKeepFileNames"],
        suffix=settings["webFontsSuffix"],
        exportInFolders=settings["batchSettingExportInSubFolders"],
        root=webFontsRoot,
        report=report,
        progress=progress
    )

    if settings["webFontsGenerateHTML"]:
        reportCSS.save(os.path.join(webFontsRoot, "font.css"))
        reportHTML.save(os.path.join(webFontsRoot, "preview.html"))
