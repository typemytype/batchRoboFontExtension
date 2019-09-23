import os, shutil
from mojo.extensions import ExtensionBundle

basePath = os.path.dirname(__file__)
sourcePath = os.path.join(basePath, 'source')
libPath = os.path.join(sourcePath, 'code')
htmlPath = os.path.join(sourcePath, 'docs')
resourcesPath = None # os.path.join(sourcePath, 'resources')
licensePath = os.path.join(basePath, 'LICENSE')
pycOnly = False
extensionFile = 'Batch.roboFontExt'
extensionPath = os.path.join(basePath, extensionFile)

# extension settings

B = ExtensionBundle()
B.name = "Batch"
B.developer = 'TypeMyType'
B.developerURL = 'http://www.typemytype.com'
B.icon = None # os.path.join(basePath, 'BatchMechanicIcon.png')
B.version = '1.9.9'
B.launchAtStartUp = True
B.mainScript = 'main.py'
B.html = True
B.requiresVersionMajor = '3'
B.requiresVersionMinor = '2'
B.addToMenu = []

with open(licensePath) as license:
    B.license = license.read()

# copy README & imgs to extension docs

shutil.copyfile(os.path.join(basePath, 'README.md'), os.path.join(htmlPath, 'index.md'))

imgsFolder = os.path.join(basePath, 'imgs')
htmlImgsFolder = os.path.join(htmlPath, 'imgs')
for f in os.listdir(imgsFolder):
    if not os.path.splitext(f)[-1] in ['.png', '.jpg', '.jpeg']:
        continue
    imgPath = os.path.join(imgsFolder, f)
    shutil.copy2(imgPath, htmlImgsFolder)

# build extension package

print('building extension...', end=' ')
B.save(extensionPath, libPath=libPath, htmlPath=htmlPath, resourcesPath=resourcesPath, pycOnly=pycOnly)
print('done!')

print()
print(B.validationErrors())
