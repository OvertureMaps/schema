# Names

This document describes how to construct the Overture names field from an
OpenStreetMap element.

OSM uses many different tags to describe the many names a feature can have.
There are tagging conventions to indicate translations of names for different
languages as well tags for describing name variants such as alternate, official,
abbreviations, regional, international, historic and other kinds of names. This
explains how to translate OSM's set of tags into Overture's names field.

OSM name tags follow the pattern:

`(variant_)name(:language-tag)`

where `variant` and `language-tag` are both separately optional.


For example:

| Tag | OSM Variant | OSM Language Tag |
| --- | ------- | ------------ |
| name | none | none |
| name:el | none | el | 
| loc_name | loc | none |
| loc_name:es | loc | es |
| official_name | official | none |
| old_name:es | old | es |

### Overture Language Tags

Overture uses [BCP47](https://en.wikipedia.org/wiki/IETF_language_tag) language
tags to specify the language of a name value. Not all OSM language tags are
valid BCP47 tags. In a few cases, we convert popular language tags in OSM to
proper BCP47 values but in most cases, these tags will be dropped entirely.

Because complete validation of a BCP47 tag is difficult we simplify the logic
to use a regular expression with a few extra rules.

The process is as follows:
1. If the language tag matches any of the following, do not include it in Overture's names

```
botanical
cadastre
etymology
etymology:wikidata
etymology:wikipedia
ga:genitive
historic
int_name
language
prefix
pronunciation
signed
source
start_date
statcan_rbuid
```

2. If the language tag matches the following regular expression, do not include it.
`[a-z]{2}[0-9]+$`

3. If the language tag matches the following regular expression, then keep it for Overture's name field.
`(?:(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}?)|(?:[A-Za-z]{4,8}))(?:-[A-Za-z]{4})?(?:-[A-Za-z]{2}|[0-9]{3})?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*(?:-[A-WY-Za-wy-z0-9](?:-[A-Za-z0-9]{2,8})+)*$`

4. Remap the following OSM language tags to their BCP47 counterpart. Note - do
not overwrite a tag that already exists

```
ja_kana -> ja-Kana
ja_hira -> ja-Hira
zh_pinyin -> zh-Latn-pinyin
zh_zhuyin -> zh-Bopo
be-tarask -> be-Latn-tarask
nan-POJ -> nan-Latn
```

### Overture Variants

Overture only defines a few variants. At the time of this document's writing
they are: `common`, `official`, `local`, and `short`.   The formal list is
defined in the Overture schema.

OSM has many variants which are mapped to one of the Overture variants:
| OSM Variant | Overture Variant |
| ----------- | ---------------- |
| none | common |
| official | official |
| short | short |
| loc | local |
| int | alternate |
| nat | alternate |
| old | alternate |
| ref | alternate |
| reg | alternate |
| alt | alternate |
| nick | alternate |

All other variants are ignored.


## Populating the Overture Names Field

Once all valid variants and language tags have been derived from OSM tags, populating
the Overture names field is as follows:

* primary
`primary` is always the "common" variant with no language tag. This amounts to the bar `name=*` tag in OSM

* common
`common` is a map of the common variants where the keys are the BCP47 language tags and the values are their corresponding
tag values. Because it is a map there can only be one entry for each language.

* rules
`rules` is an array of structs that captures all other variants. Each rule structure has the following fields:

`language` - the converted language tag
`variant` - the name variant
`value` - the tag value
`between` - used for linear-referencing of transportation segments. This is always null for non-transportation elements.
`side` - used when one side of a transportation segment has a name. This is always null for non-transportation elements.

Because `rules` is a list there are no restrictions on the number of variants or
languages. It is possible to have multiple instances of the same variant and
language combination. 




## Example

For example, the New York City label node (https://www.openstreetmap.org/node/61785451) has some of the following
name tags:
```
name=New York
name:br=Evrog Nevez
name:el=Νέα Υόρκη
name:es=Nueva York
name:be-tarask=Нью-Ёрк
old_name:es=Nueva Ámsterdam
loc_name=Big Apple
loc_name:es=La Gran Manzana
official_name=City of New York
...
```

Here is how this is converted into the corresponding Overture names.

```
{
    primary: "New York",
    common: {
        "br": "Evrog Nevez",
        "el": "Νέα Υόρκη",
        "es": "Nueva York",
        "be-Latn-tarask": "Нью-Ёрк"
    },
    rules: [
        {
            "value": "City of New York",
            "variant": "official",
            "language": null,
            "between": null,
            "side": null
        },
        {
            "value": "Nueva Ámsterdam",
            "variant": "alternate",
            "language": "es",
            "between": null,
            "side": null
        },
        {
            "value": "Big Apple",
            "variant": "local",
            "language": null,
            "between": null,
            "side": null
        },
        {
            "value": "La Gran Manzana",
            "variant": "local",
            "language": "es",
            "between": null,
            "side": null
        },
    ]
}
```




