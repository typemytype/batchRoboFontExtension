# Batch

An extension to batch generate fonts.

Drag and drop or open a one or multiple UFO's. If a folder is provided Batch will search in that folder for UFO's. 
Binary fonts are also supported (otf, ttf), they will be imported and generated.


#### Generate supports:
	
* TTF 
* OTF
* PFA
* VFB (only if ufo2vfb is installed)

## Web Fonts

#### Web font supports:

* ttf
* woff
* eot
* svg

there are options to preserve hints, only optionall when a TTF is provided. It has full support for ttfautohint and all of the different settings.  Batch will also generate a HTML preview that with some simple presents.

The html preview can replace `%(familyName)s` and `%(styleName)s` by the values retrieved from the corresponding font.

## Binary Merge 

Will merge specific tables from a source. Only avaialbe when when a UFO is provided and when the UFO has the source path in the font.lib.

