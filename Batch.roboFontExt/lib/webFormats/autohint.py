import os

from fontTools.ttLib import TTFont

from mojo.compile import executeCommand

import vanilla

from lib.UI.stepper import SliderEditIntStepper

from batchTools import updateWithDefaultValues

ttfautohint = os.path.join(os.path.dirname(__file__), "ttfautohint")
os.chmod(ttfautohint, 0o0777)


defaultOptions = {
            "hintRangeMinimum": 8,
            "hintRangeMaximum": 50,

            "hintingLimit": 200,
            "noHintingLimit": False,

            "xHeightIncreaseLimit": 14,
            "noXHeightIncreaseLimit": False,

            "fallbackScript": False,

            "preHinting": False,
            "symbolFont": False,
            "addTTFAutoHintInfo": False,
            "overRideFontLicense": False,

            "grayScale": False,
            "gdiClearType": True,
            "dwClearType": False,
        }


def TTFAutohint(sourcePath, destinationPath, options=dict()):
    """
    Options:
          --debug                print debugging information
      -f, --latin-fallback       set fallback script to latin
      -G, --hinting-limit=N      switch off hinting above this PPEM value
                                 (default: 200); value 0 means no limit
      -h, --help                 display this help and exit
      -i, --ignore-restrictions  override font license restrictions
      -l, --hinting-range-min=N  the minimum PPEM value for hint sets
                                 (default: 8)
      -n  --no-info              don't add ttfautohint info
                                 to the version string(s) in the `name' table
      -p, --pre-hinting          apply original hints in advance
      -r, --hinting-range-max=N  the maximum PPEM value for hint sets
                                 (default: 50)
      -s, --symbol               input is symbol font
      -v, --verbose              show progress information
      -V, --version              print version information and exit
      -w, --strong-stem-width=S  use strong stem width routine for modes S,
                                 where S is a string of up to three letters
                                 with possible values `g' for grayscale,
                                 `G' for GDI ClearType, and `D' for
                                 DirectWrite ClearType (default: G)
      -x, --increase-x-height=N  increase x height for sizes in the range
                                 6<=PPEM<=N; value 0 switches off this feature
                                 (default: 14)
      -X, --x-height-snapping-exceptions=STRING
                                 specify a comma-separated list of
                                 x-height snapping exceptions

    """
    updateWithDefaultValues(options, defaultOptions)

    hintRangeMinimum = str(options["hintRangeMinimum"])
    hintRangeMaximum = str(options["hintRangeMaximum"])
    fallbackScript = options["fallbackScript"]
    hintingLimit = options["hintingLimit"]
    noHintingLimit = options["noHintingLimit"]
    if noHintingLimit:
        hintingLimit = 0
    hintingLimit = str(hintingLimit)

    xHeightIncreaseLimit = options["xHeightIncreaseLimit"]
    noXHeightIncreaseLimit = options["noXHeightIncreaseLimit"]
    if noXHeightIncreaseLimit:
        xHeightIncreaseLimit = 0
    xHeightIncreaseLimit = str(xHeightIncreaseLimit)

    preHinting = options["preHinting"]
    symbolFont = options["symbolFont"]
    if not symbolFont:
        f = TTFont(sourcePath)
        symbolFont = "o" not in f.getGlyphOrder()
        f.close()

    addTTFAutoHintInfo = options["addTTFAutoHintInfo"]
    overRideFontLicense = options["overRideFontLicense"]

    grayScale = options["grayScale"]
    if grayScale:
        grayScale = "g"
    else:
        grayScale = ""

    gdiClearType = options["gdiClearType"]
    if gdiClearType:
        gdiClearType = "G"
    else:
        gdiClearType = ""

    dwClearType = options["dwClearType"]
    if dwClearType:
        dwClearType = "D"
    else:
        dwClearType = ""

    cmd = [ttfautohint]
    cmd.extend(["-G", hintingLimit])
    cmd.extend(["-l", hintRangeMinimum])
    cmd.extend(["-r", hintRangeMaximum])
    cmd.extend(["-x", xHeightIncreaseLimit])

    if fallbackScript:
        cmd.append("-f")
    if not addTTFAutoHintInfo:
        cmd.append("-n")
    if preHinting:
        cmd.append("-p")
    if symbolFont:
        cmd.append("-s")
    if not overRideFontLicense:
        cmd.append("-i")

    cmd.extend(["-w", grayScale + gdiClearType + dwClearType])
    cmd.extend([sourcePath, destinationPath])
    result = executeCommand(cmd)
    return result


class TTFAutoHintGroup(vanilla.Group):

    def __init__(self, posSize):
        super(TTFAutoHintGroup, self).__init__(posSize)
        self.getNSView().setFrame_((((0, 0), (400, 400))))
        self.options = dict()

        updateWithDefaultValues(self.options, defaultOptions)

        column = 180
        gutter = 15

        y = 10

        self.hintRangeMininmumText = vanilla.TextBox((10, y+2, column, 22), "Hint Set Range Minimum:", alignment="right")
        self.hintRangeMinimum = SliderEditIntStepper((column + gutter, y, -10, 22), self.options["hintRangeMinimum"], callback=self.hintRangeMinimumMaximumCallback)

        y += 30
        self.hintRangeMaximumText = vanilla.TextBox((10, y+2, column, 22), "Hint Set Range Maximum:", alignment="right")
        self.hintRangeMaximum = SliderEditIntStepper((column + gutter, y, -10, 22), self.options["hintRangeMaximum"], callback=self.hintRangeMinimumMaximumCallback)

        y += 50

        self.hintingLimitText = vanilla.TextBox((10, y+2, column, 22), "Hinting Limit:", alignment="right")
        self.hintingLimit = SliderEditIntStepper((column + gutter, y, -10, 22), self.options["hintingLimit"])

        y += 28
        self.noHintingLimit = vanilla.CheckBox((column + gutter, y, -10, 22), "No Hinting Limit", callback=self.noHintingLimitCallback, sizeStyle="small")

        y += 30

        self.xHeightIncreaseLimitText = vanilla.TextBox((10, y+2, column, 22), "X Height Increase Limit:", alignment="right")
        self.xHeightIncreaseLimit = SliderEditIntStepper((column + gutter, y, -10, 22), self.options["xHeightIncreaseLimit"])

        y += 28
        self.noXHeightIncreaseLimit = vanilla.CheckBox((column + gutter, y, -10, 22), "No X Height Increase Limit", callback=self.noXHeightIncreaseLimitCallback, sizeStyle="small")

        y += 50

        self.fallbackScript = vanilla.CheckBox((column + gutter, y, -10, 22), "Fallback Script (Latin)", value=self.options["fallbackScript"])

        y += 50

        self.preHinting = vanilla.CheckBox((column + gutter, y, -10, 22), "Pre Hinted", value=self.options["preHinting"])

        y += 30
        self.symbolFont = vanilla.CheckBox((column + gutter, y, -10, 22), "Symbol Font", value=self.options["symbolFont"])

        y += 30
        self.addTTFAutoHintInfo = vanilla.CheckBox((column + gutter, y, -10, 22), "Add ttfautohint Info", value=self.options["addTTFAutoHintInfo"])

        y += 30
        self.overRideFontLicense = vanilla.CheckBox((column + gutter, y, -10, 22), "Override Font License Restrictions", value=self.options["overRideFontLicense"])

        y += 50

        self.stemWidthAndStemPos = vanilla.TextBox((0, y, column+10, 22), "Stem Width and Positioning:", alignment="right")

        self.grayScale = vanilla.CheckBox((column + gutter, y, -10, 22), "Gray Scale", value=self.options["grayScale"])

        y += 30
        self.gdiClearType = vanilla.CheckBox((column + gutter, y, -10, 22), "GDI ClearType", value=self.options["gdiClearType"])

        y += 30
        self.dwClearType = vanilla.CheckBox((column + gutter, y, -10, 22), "DW ClearType", value=self.options["dwClearType"])

    def hintRangeMinimumMaximumCallback(self, sender):
        minValue = int(round(self.hintRangeMinimum.get()))
        maxValue = int(round(self.hintRangeMaximum.get()))

        if minValue > maxValue:
            self.hintRangeMaximum.set(minValue)

        if maxValue < minValue:
            self.hintRangeMinimum.set(maxValue)

    def noHintingLimitCallback(self, sender):
        self.hintingLimit.enable(not sender.get())

    def noXHeightIncreaseLimitCallback(self, sender):
        self.xHeightIncreaseLimit.enable(not sender.get())

    def get(self):
        return {
            "hintRangeMinimum": int(round(self.hintRangeMinimum.get())),
            "hintRangeMaximum": int(round(self.hintRangeMaximum.get())),

            "hintingLimit": int(round(self.hintingLimit.get())),
            "noHintingLimit": self.noHintingLimit.get(),

            "xHeightIncreaseLimit": int(round(self.xHeightIncreaseLimit.get())),
            "noXHeightIncreaseLimit": self.noXHeightIncreaseLimit.get(),

            "fallbackScript": self.fallbackScript.get(),

            "preHinting": self.preHinting.get(),
            "symbolFont": self.symbolFont.get(),
            "addTTFAutoHintInfo": self.addTTFAutoHintInfo.get(),
            "overRideFontLicense": self.overRideFontLicense.get(),

            "grayScale": self.grayScale.get(),
            "gdiClearType": self.gdiClearType.get(),
            "dwClearType": self.dwClearType.get(),
        }

    def set(self, options):
        if options is None:
            options = dict()
        updateWithDefaultValues(options, defaultOptions)

        self.hintRangeMinimum.set(options["hintRangeMinimum"])
        self.hintRangeMaximum.set(options["hintRangeMaximum"])

        self.hintingLimit.set(options["hintingLimit"])
        self.noHintingLimit.set(options["noHintingLimit"])
        self.noHintingLimitCallback(self.noHintingLimit)

        self.xHeightIncreaseLimit.set(options["xHeightIncreaseLimit"])
        self.noXHeightIncreaseLimit.set(options["noXHeightIncreaseLimit"])
        self.noXHeightIncreaseLimitCallback(self.noXHeightIncreaseLimit)

        self.fallbackScript.set(options["fallbackScript"])

        self.preHinting.set(options["preHinting"])
        self.symbolFont.set(options["symbolFont"])
        self.addTTFAutoHintInfo.set(options["addTTFAutoHintInfo"])
        self.overRideFontLicense.set(options["overRideFontLicense"])

        self.grayScale.set(options["grayScale"])
        self.gdiClearType.set(options["gdiClearType"])
        self.dwClearType.set(options["dwClearType"])


if __name__ == "__main__":

    class Test(object):

        def __init__(self):
            self.w = vanilla.Window((600, 500), minSize=(300, 300))
            self.w.ttfah = TTFAutoHintGroup((0, 0, 500, 500))
            self.w.open()

    Test()
