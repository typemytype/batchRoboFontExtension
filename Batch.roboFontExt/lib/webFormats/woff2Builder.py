import os
import shutil

from mojo.compile import executeCommand

woff2_compress = os.path.join(os.path.dirname(__file__), "woff2_compress")
os.chmod(woff2_compress, 0777)


def generateWOFF2(source, dest):
    cmds = [woff2_compress, source]
    result = executeCommand(cmds)
    resultWoff = os.path.splitext(source)[0] + ".woff2"
    shutil.move(resultWoff, dest)
    return result


def WOFF2Builder(sourcePath, destinationPath):
    fileName, ext = os.path.splitext(sourcePath)
    if ext.lower() != ".ttf":
        return
    result = generateWOFF2(sourcePath, destinationPath)
    return result


def WOFF2BuilderFromFolder(sourceDir, destinationDir):
    for fileName in os.listdir(sourceDir):
        name, ext = os.path.splitext(fileName)
        path = os.path.join(sourceDir, fileName)
        destinationPath = os.path.join(destinationDir, name+".woff2")
        WOFF2Builder(path, destinationPath)
