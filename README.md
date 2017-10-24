# Batch

An extension to batch generate fonts.

Drag and drop any ufo, binary font (otf, ttf), designSpace file or folder. If a folder is provided Batch will search for ufo's inside the given folder. A designSpace will be expanded with all his instances and all masters and generated instances will be generated. DesignSpace files are required to build variation font.


#### Generate supports:
	
* TTF 
* OTF
* PFA
* VFB (only if ufo2vfb is installed)

Output settings:

* Decompose
* Remove Overlap
* Autohint
* Release Mode

A suffix can be added to the file name. The suffix can contain [date time formatting](https://docs.python.org/2/library/time.html#time.strftime).

## Web Fonts

#### Web font supports:

* otf
* ttf
* woff (otf - ttf)
* woff2 (otf - ttf)
* eot
* svg

The woff option will create metadata based on the info in the font, if it is available. (openTypeNameManufacturer, openTypeNameManufacturerURL, openTypeNameDesigner, openType)NameDesignerURL, openTypeNameDescription, openTypeNameLicenseURL, openTypeNameLicense, copyright, trademark).

The woff2 option will not create any metadata, the fonts will just be compressed.

The option to preserve hints, only optional when a TTF is provided, will not autohint the binary TTF font.

Full support for `ttfautohint` and all of the different settings. 

A suffix can be added to the file name. The suffix can contain [date time formatting](https://docs.python.org/2/library/time.html#time.strftime).

Batch will also generate a HTML preview that with some simple presents.

The html preview can replace `%(familyName)s` and `%(styleName)s` by the values retrieved from the corresponding font.

## Variable Fonts

From a provided designSpace files Batch can generate variable fonts. 

Batch will optimize your designSpace file:

* Adding off curves where needed, Batch will place them on 1/3 of the line segment.
* Adding axes in the design space file, if they are missing
* Adding missing glyphs by generating them fromout the design space
* Adding kerning pairs to make kerning compatible


## Binary Merge 

Will merge specific tables from a source. Only avaialbe when when a UFO is provided and when the UFO has the source path in the `font.lib`.

Binary Merge is using the output settings as in Generate.

