from fontTools.ttLib import TTFont


def WOFFBuilder(sourcePath, destinationPath):
    font = TTFont(sourcePath)
    font.flavor = "woff"
    font.save(destinationPath)
