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
* woff2
* eot
* svg

The woff option will create metadata based on the info in the font, if it is available. (openTypeNameManufacturer, openTypeNameManufacturerURL, openTypeNameDesigner, openType)NameDesignerURL, openTypeNameDescription, openTypeNameLicenseURL, openTypeNameLicense, copyright, trademark).

The woff2 option will not create any metadata, the fonts will just be compressed.

The option to preserve hints, only optional when a TTF is provided, will not autohint the binary TTF font.

Full support for `ttfautohint` and all of the different settings. 

Batch will also generate a HTML preview that with some simple presents.

The html preview can replace `%(familyName)s` and `%(styleName)s` by the values retrieved from the corresponding font.

## Binary Merge 

Will merge specific tables from a source. Only avaialbe when when a UFO is provided and when the UFO has the source path in the `font.lib`.

