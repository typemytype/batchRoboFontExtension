from ufo2svg import convertUFOToSVGFont
from defcon import Font
from extractor import extractUFO
from fontTools.ufoLib.errors import UFOLibError


def generateSVG(source, dest):
    try:
        font = Font(source)
    except UFOLibError:
        font = Font()
        extractUFO(source, font)
    except Exception as e:
        return f"Failed to extract path {source}: {e}."

    try:
        convertUFOToSVGFont(font, dest)
    except Exception as e:
        return f"Failed to generate SVG: {e}."
    return ""


def SVGBuilder(sourcePath, destinationPath):
    return generateSVG(sourcePath, destinationPath)
