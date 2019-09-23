from ufo2svg import convertUFOToSVGFont
from defcon import Font
from extractor import extractUFO


def generateSVG(source, dest):
    font = Font()
    try:
        extractUFO(source, font)
        convertUFOToSVGFont(font, dest)
    except:
        return ("Failed to generate SVG.", "")
    return ("", "")


def SVGBuilder(sourcePath, destinationPath):
    generateSVG(sourcePath, destinationPath)
