import os

from fontTools.ttLib import TTFont

from mojo.compile import executeCommand

from batchGenerators.batchTools import updateWithDefaultValues


ttfautohint = os.path.join(os.path.dirname(__file__), "ttfautohint")
os.chmod(ttfautohint, 0o0777)


defaultOptions = {
    "ttfautohintHintSetRangeMinimum": 8,
    "ttfautohintHintSetRangeMaximum": 50,

    "ttfautohintHintLimit": 200,
    "ttfautohintNoHintLimit": False,

    "ttfautohintXHeightIncreaseLimit": 14,
    "ttfautohintNoXHeightIncreaseLimit": False,

    "ttfautohintFallbackScript": False,

    "ttfautohintPreHinted": False,
    "ttfautohintSymbolFont": False,
    "ttfautohintAddTTFAutohintInfo": False,
    "ttfautohintOverrideFontLicenseRestrictions": False,

    "ttfautohintGrayScale": False,
    "ttfautohintCDIClearType": True,
    "ttfautohintDWClearType": False,
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

    hintRangeMinimum = str(options["ttfautohintHintSetRangeMinimum"])
    hintRangeMaximum = str(options["ttfautohintHintSetRangeMaximum"])
    fallbackScript = options["ttfautohintFallbackScript"]
    hintingLimit = options["ttfautohintHintLimit"]
    noHintingLimit = options["ttfautohintNoHintLimit"]
    if noHintingLimit:
        hintingLimit = 0
    hintingLimit = str(hintingLimit)

    xHeightIncreaseLimit = options["ttfautohintXHeightIncreaseLimit"]
    noXHeightIncreaseLimit = options["ttfautohintNoXHeightIncreaseLimit"]
    if noXHeightIncreaseLimit:
        xHeightIncreaseLimit = 0
    xHeightIncreaseLimit = str(xHeightIncreaseLimit)

    preHinting = options["ttfautohintPreHinted"]
    symbolFont = options["ttfautohintSymbolFont"]
    if not symbolFont:
        f = TTFont(sourcePath)
        symbolFont = "o" not in f.getGlyphOrder()
        f.close()

    addTTFAutoHintInfo = options["ttfautohintAddTTFAutohintInfo"]
    overRideFontLicense = options["ttfautohintOverrideFontLicenseRestrictions"]

    grayScale = options["ttfautohintGrayScale"]
    if grayScale:
        grayScale = "g"
    else:
        grayScale = ""

    gdiClearType = options["ttfautohintCDIClearType"]
    if gdiClearType:
        gdiClearType = "G"
    else:
        gdiClearType = ""

    dwClearType = options["ttfautohintDWClearType"]
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
