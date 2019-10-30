from fontTools.ttLib import TTFont


def WOFF2Builder(sourcePath, destinationPath):
    font = TTFont(sourcePath)
    font.flavor("woff2")
    font.save(destinationPath)
