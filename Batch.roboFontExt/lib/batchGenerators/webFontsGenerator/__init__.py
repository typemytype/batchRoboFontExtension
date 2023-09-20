import os
import re
import string

from fontTools.ttLib import TTFont

from mojo.extensions import getExtensionDefault, setExtensionDefault

from batchGenerators.batchTools import generatePaths, WOFF2Builder, postProcessCollector, CSSWriter, HTMLWriter, settingsIdentifier

from .autohint import TTFAutohint


_percentageRe = re.compile(r"%(?!\((familyName|styleName)\)s)")
htmlPreviewDefault = string.ascii_letters + string.digits


def htmlBuilder(previewHTML, previewCSS, reportHTML, reportCSS):

    def wrapper(sourcePath, destinationPath):
        font = TTFont(sourcePath)
        familyName = font["name"].getBestFamilyName()
        styleName = font["name"].getBestSubFamilyName()

        cssFontName = f"{familyName}_{styleName}"

        reportCSS.write("@font-face {")
        reportCSS.indent()
        reportCSS.write(f"font-family: '{cssFontName}';")
        reportCSS.write("src:  url('{destinationPath}') format('woff2');")
        reportCSS.write("font-weight: normal;")
        reportCSS.write("font-style: normal;")
        reportCSS.dedent()
        reportCSS.write("}")
        reportCSS.newLine()

        reportHTML.write(f"<div style='font-family: \"{cssFontName}\", \"AdobeBlank\";'>")
        html = previewHTML
        html = _percentageRe.sub("&#37;", html)
        html = html % dict(familyName=familyName, styleName=styleName)
        reportHTML.write(html.encode("ascii", 'xmlcharrefreplace').decode("utf-8"))
        reportHTML.write("</div>")

    return wrapper


def autohintBuilder(autohintOptions, report):

    def wrapper(sourcePath, destinationPath):
        result = TTFAutohint(sourcePath, destinationPath, autohintOptions)
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
    if generateOptions["webFontGenerate_OTF"]:
        binaryFormats.append(("otf", postProcessCollector(autohintFunc, htmlBuilderFunc)))
    if generateOptions["webFontGenerate_OTFWoff2"]:
        binaryFormats.append(("otf", postProcessCollector(WOFF2Builder, autohintFunc, htmlBuilderFunc)))
    if generateOptions["webFontGenerate_TTF"]:
        binaryFormats.append(("ttf", postProcessCollector(autohintFunc, htmlBuilderFunc)))
    if generateOptions["webFontGenerate_TTFWoff2"]:
        binaryFormats.append(("ttf", postProcessCollector(WOFF2Builder, autohintFunc, htmlBuilderFunc)))
    if generateOptions["webFontGenerate_SVG"]:
        binaryFormats.append(("svg", None))

    if not binaryFormats:
        return

    webFontsRoot = os.path.join(root, "Web")

    report.writeTitle("Batch Generated Web Fonts:")
    progress.update("Collecting Data...")

    generatePaths(
        ufoPaths=generateOptions["sourceUFOPaths"],
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
