import os
import codecs
import markdown
from markdown.extensions.toc import TocExtension

baseFolder = os.getcwd()
readmePath = os.path.join(baseFolder, 'README.md')
extensionPath = os.path.join(baseFolder, 'Batch.roboFontExt')

#---------------
# generate html
#---------------

htmlFolder = os.path.join(extensionPath, 'html')
htmlPath = os.path.join(htmlFolder, 'index.html')

htmlTemplate = '''\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Batch</title>
<link rel="stylesheet" href="github-markdown.css">
<style>
  html { margin-left: auto; margin-right: auto; }
</style>
</head>
<body>
%s
</body>
</html>
'''

with codecs.open(readmePath, mode="r", encoding="utf-8") as f:
    markdownSource = f.read()

M = markdown.Markdown(extensions=[TocExtension(permalink=False)])
html = htmlTemplate % M.convert(markdownSource)

htmlFile = codecs.open(htmlPath, mode="w", encoding="utf-8")
htmlFile.write(html)
htmlFile.close()

#-------------
# copy images
#-------------

import shutil

imgsFolder = os.path.join(baseFolder, 'imgs')
htmlImgsFolder = os.path.join(htmlFolder, 'imgs')

for f in os.listdir(imgsFolder):
    if not os.path.splitext(f)[-1] in ['.png', '.jpg', '.jpeg']:
        continue
    imgPath = os.path.join(imgsFolder, f)
    shutil.copy2(imgPath, htmlImgsFolder)
