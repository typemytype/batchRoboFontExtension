import ezui

from mojo.extensions import getExtensionDefault, setExtensionDefault


webFontsHtmlPreviewCSS = """.test {
    word-wrap: break-word;
}

.title {
    font-size: 30px;
    background-color: black;
    color: white;
    display: inline-block;
    padding-left: 5px;
    padding-right: 5px;
    margin-bottom: 3px;
    margin-top: 10px;
}

.small {
    font-size: 10px;
}

.big {
    font-size: 50px;
}
"""

webFontsHtmlPreview = """<div class="title">%(familyName)s %(styleName)s (%(fileName)s)</div>
<div class="test small" contenteditable>
    <div>abcdefghijklmnopqrstuvwxyz</div>
    <div>ABCDEFGHIJKLMNOPQRSTUVWXYZ</div>
    <div>0123456789</div>
</div>

<div class="test big" contenteditable>
    <div>abcdefghijklmnopqrstuvwxyz</div>
    <div>ABCDEFGHIJKLMNOPQRSTUVWXYZ</div>
    <div>0123456789</div>
</div>
"""


defaultSettings = dict(
    batchSettingExportDebug=0,
    batchSettingExportInSubFolders=0,
    batchSettingExportKeepFileNames=0,
    batchSettingStoreReport=1,

    desktopFontsAutohint=0,
    desktopFontsDecompose=1,
    desktopFontsReleaseMode=0,
    desktopFontsRemoveOverlap=1,
    desktopFontsSuffix="",

    ttfautohintAddTTFAutohintInfo=0,
    ttfautohintCDIClearType=0,
    ttfautohintDWClearType=0,
    ttfautohintFallbackScript=0,
    ttfautohintGrayScale=0,
    ttfautohintHintLimit=50,
    ttfautohintHintSetRangeMaximum=50,
    ttfautohintHintSetRangeMinimum=50,
    ttfautohintNoHintLimit=0,
    ttfautohintNoXHeightIncreaseLimit=0,
    ttfautohintOverrideFontLicenseRestrictions=0,
    ttfautohintPreHinted=0,
    ttfautohintSymbolFont=0,
    ttfautohintXHeightIncreaseLimit=50,

    variableFontsAutohint=0,
    variableFontsInterpolateToFitAxesExtremes=0,
    variableFontsSuffix="",

    webFontsAutohint=0,
    webFontsDecompose=0,
    webFontsGenerateHTML=0,
    webFontsHtmlPreview=webFontsHtmlPreview,
    webFontsHtmlPreviewCSS=webFontsHtmlPreviewCSS,
    webFontsReleaseMode=0,
    webFontsRemoveOverlap=0,
    webFontsSuffix="",
)

# update settings when new keys are added
settings = getExtensionDefault("com.typemytype.batch.settings", dict())
for key, value in defaultSettings.items():
    if key not in settings:
        settings[key] = value
setExtensionDefault("com.typemytype.batch.settings", settings)


class BatchSettingsController(ezui.WindowController):

    def build(self, parent):
        content = """
        = Tabs
        * Tab: Desktop Fonts = ScrollingTwoColumnForm   @desktopFontsForm
        > : Generate:
        > [ ] Decompose                                 @desktopFontsDecompose
        > [ ] Remove Overlap                            @desktopFontsRemoveOverlap
        > [ ] Autohint                                  @desktopFontsAutohint
        > [ ] Release Mode                              @desktopFontsReleaseMode
        > : Suffix:
        > [_ _]                                         @desktopFontsSuffix


        * Tab: Web Fonts  = ScrollingTwoColumnForm      @webFontsForm
        > : Generate:
        > [ ] Decompose                                 @webFontsDecompose
        > [ ] Remove Overlap                            @webFontsRemoveOverlap
        > [ ] Autohint                                  @webFontsAutohint
        > [ ] Release Mode                              @webFontsReleaseMode
        > [ ] Generate HTML                             @webFontsGenerateHTML
        > : Suffix:
        > [_ _]                                         @webFontsSuffix

        > !§ TTF Autohint

        > : Hint Set Range Minimum:
        > ---X--- [__]                               @ttfautohintHintSetRangeMinimum
        > : Hint Set Range Maximum:
        > ---X--- [__]                               @ttfautohintHintSetRangeMaximum
        > : Hint Limit:
        > ---X--- [__]                               @ttfautohintHintLimit
        > [ ] No Hinting Limit                       @ttfautohintNoHintLimit
        > : X Height Increase Limit:
        > ---X--- [__]                               @ttfautohintXHeightIncreaseLimit
        > [ ] No X Height Increase Limit             @ttfautohintNoXHeightIncreaseLimit
        > ---
        > [ ] Fallback Script (Latin)                @ttfautohintFallbackScript
        > [ ] Pre Hinted                             @ttfautohintPreHinted
        > [ ] Symbol Font                            @ttfautohintSymbolFont
        > [ ] Add ttfautohint Info                   @ttfautohintAddTTFAutohintInfo
        > [ ] Override Font License Restrictions     @ttfautohintOverrideFontLicenseRestrictions
        > : Stem Width and Positioning:
        > [ ] Gray Scale                             @ttfautohintGrayScale
        > [ ] GDI ClearType                          @ttfautohintCDIClearType
        > [ ] DW ClearType                           @ttfautohintDWClearType

        > !§ HTML Preview
        > : HTML Preview:
        > * CodeEditor                              @webFontsHtmlPreview
        > : CSS Style:
        > * CodeEditor                              @webFontsHtmlPreviewCSS


        * Tab: Variable Fonts = ScrollingTwoColumnForm @variableFontsForm
        > : Generate:
        > [ ] Interpolate to Fit Axis Extremes         @variableFontsInterpolateToFitAxesExtremes
        > [ ] Autohint                                 @variableFontsAutohint
        > : Suffix:
        > [_ _]                                        @variableFontsSuffix

        * Tab: Batch Settings = ScrollingTwoColumnForm @batchSettingsForm
        > :
        > [ ] Export in sub-folders           @batchSettingExportInSubFolders
        > ---
        > :
        > ( ) Use familyName-styleName        @batchSettingExportKeepFileNames
        > ( ) Keep file names
        > ---
        > [ ] Store Export Report             @batchSettingStoreReport
        > ---
        > [ ] Debug                           @batchSettingExportDebug

        =---=
        ( Cancel )     @cancel
        ( Apply )      @apply
        """
        descriptionData = dict(
            desktopFontsForm=dict(
                titleColumnWidth=180,
                itemColumnWidth=300,
            ),
            webFontsForm=dict(
                titleColumnWidth=180,
                itemColumnWidth=300,
            ),
            variableFontsForm=dict(
                titleColumnWidth=180,
                itemColumnWidth=300,
            ),
            batchSettingsForm=dict(
                titleColumnWidth=180,
                itemColumnWidth=300,
            ),
            ttfautohintHintSetRangeMinimum=dict(
                valueType="integer",
            ),
            ttfautohintHintSetRangeMaximum=dict(
                valueType="integer",
            ),
            ttfautohintHintLimit=dict(
                valueType="integer",
            ),
            ttfautohintXHeightIncreaseLimit=dict(
                valueType="integer",
            ),
            cancel=dict(
                width=85,
                keyEquivalent=chr(27),
            ),
            apply=dict(
                width=85,
            ),
        )
        self.w = ezui.EZSheet(
            parent=parent,
            content=content,
            descriptionData=descriptionData,
            size=(700, 500),
            minSize=(700, 250),
            defaultButton="apply",
            controller=self
        )
        data = getExtensionDefault("com.typemytype.batch.settings", defaultSettings)
        self.w.setItemValues(data)

        self.ttfautohintHintLimit = self.w.getItem("ttfautohintHintLimit")
        self.ttfautohintXHeightIncreaseLimit = self.w.getItem("ttfautohintXHeightIncreaseLimit")
        self.ttfautohintNoHintLimitCallback(self.w.getItem("ttfautohintNoHintLimit"))
        self.ttfautohintNoXHeightIncreaseLimitCallback(self.w.getItem("ttfautohintNoXHeightIncreaseLimit"))

    def started(self):
        self.w.open()

    def ttfautohintNoHintLimitCallback(self, sender):
        self.ttfautohintHintLimit.enable(not sender.get())

    def ttfautohintNoXHeightIncreaseLimitCallback(self, sender):
        self.ttfautohintXHeightIncreaseLimit.enable(not sender.get())

    def cancelCallback(self, sender):
        self.w.close()

    def applyCallback(self, sender):
        setExtensionDefault("com.typemytype.batch.settings", self.w.getItemValues())
        self.w.close()
