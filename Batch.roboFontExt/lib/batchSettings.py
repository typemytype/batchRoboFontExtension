import ezui

from mojo.extensions import getExtensionDefault, setExtensionDefault


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
        > ---X--- [__](±)                            @ttfautohintHintSetRangeMinimum
        > : Hint Set Range Maximum:
        > ---X--- [__](±)                            @ttfautohintHintSetRangeMaximum
        > : Hint Limit:
        > ---X--- [__](±)                            @ttfautohintHintLimit
        > [ ] No Hinting Limit                       @ttfautohintNoHintLimit
        > : X Height Increase Limit:
        > ---X--- [__](±)                            @ttfautohintXHeightIncreaseLimit
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
        > [ ] Interpolate to Fit Axes Extremes         @variableFontsInterpolateToFitAxesExtremes
        > [ ] Autohint                                 @variableFontsAutohint
        > : Suffix:
        > [_ _]                                        @variableFontsSuffix

        * Tab: Batch Settings = ScrollingTwoColumnForm @batchSettingsForm
        > :
        > [ ] Export in sub-folders           @batchSettingExportInSubFolders
        > ---
        > :
        > (X) Keep file names                 @batchSettingExportKeepFileNames
        > ( ) Use familyName-styleName
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
            cancel=dict(
                keyEquivalent=chr(27)
            ),
        )
        self.w = ezui.EZSheet(
            parent=parent,
            content=content,
            descriptionData=descriptionData,
            size=(700, 500),
            minSize=(700, 250),
            controller=self
        )
        data = getExtensionDefault("com.typemytype.batch.settting", dict())
        self.w.setItemValues(data)

    def started(self):
        self.w.open()

    def cancelCallback(self, sender):
        self.w.close()

    def applyCallback(self, sender):
        setExtensionDefault("com.typemytype.batch.settting", self.w.getItemValues())
        self.w.close()
