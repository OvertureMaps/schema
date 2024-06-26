# Height

This document describes how to construct the Overture height fields from an
OpenStreetMap height value.

OSM uses many different formats in the height fields to describe the height
of an object. The OSM wiki describes a number of different ways to format the
string that is used to describe the height of a feature. Since Overture's
height fields are floating point values and all have a unit of meters we must
convert many of the height values from the current OSM string formats to a
singular field of type double that has unit of meters. This document explains
how to translate OSM's set of tags into Overture's height fields.

Height values are pulled from the following tags in OSM:

- tags['height'] - The overall height of a building or building part.
- tags['est_height'] - The estimated height of a building or building part.
- tags['min_height'] - The minimum height of a building part
- tags['roof_height'] - The height of the roof of a building or building part

The OSM wiki specifically lists the following height values as valid:

- height=`4`
- height=`4 m`
- height=`1.35`
- height=`7'4"`

In the current OSM dataset some other formats and unit types are used to
indicate height. Currently (Jun-2024) there are the following counts for
some of the popular formats of the height tag:
- `X`: 16,222,092
- `X m`: 615,927
- `X meter`: 212
- `X metre`: 2
- `X'`: 142,366
- `X ft`: 721
- `X feet`: 7
- `X'Y"`: 2,432
- `X"`: 6

### Overture Height Tags
Overture uses a double type to indicate the number of meters for all heights.
To convert from OSM's multi format string to Overture's float we use the
following logic. Each section describes a type of OSM formatting, how it is
matched using regex and an exmaple. Because the height feild in OSM is a string
it is important to allow for some common errors that mappers make when they are
setting the height of a building. The following are some requirements to help
convert some of the issues that are commonly seen in OSM:
- Allow numbers that may have white space before or after the number.
- Allow numbers that may have white space after the unit string.
- Allow numbers with or without a decimal
- Allow numbers with or without numbers after a decimal point

#### Basic Heights with No Units
Height strings that contain only a number value with no indicated units are
assumed to be meters. These values are NOT rounded.
Regex Match: `^\s*\d+(\.\d*)?\s*$`
Examples:
- `10` => 10
- ` 10 ` => 10
- `10.0` => 10
- `10.` => 10
- `10.6543` => 10.6543

#### Metric Heights
Height strings with a number follwed by a metric unit that matches the singular
or plural version form of `m`, `meter`, and `metre` strings after the number are
also treated as meters and the units are stripped. These values are not rounded.
Regex Match: `^\s*\d+(\.\d*)?\s*(m|meter|metre)s?\s*$`
Examples:
- `10m` => 10
- ` 10 meters` => 10
- `10.0 metre ` => 10
- `10. meter` => 10
- `10.6543meter` => 10.6543

#### Imperial Heights (Feet)
Height strings with a number followed by an imperial unit are matched and
converted to meters. Strings that are recognized as indicating units of feet
are `'`, `ft`, and `feet`. Strings that are recognized as indicating units of
inches are `"`. Inches and feet are matched in combination with each other or
alone. When both feet and inches are indicated the `'` string must be used to
indicate feet and the inches value and `"` string must be after the feet value.
The imperial values matched are then converted into meters by multiplying feet
by `0.3048`. Inches are multiplied by `0.0254` to convert to meters. The final
meters value is then rounded to two decimal places.
Regex Match (feet only): `^\s*\d+(\.\d*)?\s*(''|ft|feet)\s*$`
Regex Match (feet and inches): `^\s*\d+(\.\d*)?\s*''\s*\d+(\.\d*)?\s*"\s*$`
Regex Match (inches only): `^\s*\d+(\.\d*)?"\s*$`
Examples:
- `10'` => 3.05
- `10.65 ft` => 3.25
- `10.65 feet ` => 3.25
- `10. '` => 3.05
- ` 10.65feet ` => 3.05
- `10' 13"` => 3.38
- `10'  13" ` => 3.38
- `10'13"` => 3.38
- `10' 13"` => 3.38
- `10'  13" ` => 3.38
- `10'13"` => 3.38
