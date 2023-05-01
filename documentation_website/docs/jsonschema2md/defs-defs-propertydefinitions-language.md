# Untitled undefined type in Overture Maps Transportation Segment Schema Schema

```txt
defs.yaml#/$defs/propertyDefinitions/nameProperty/properties/language
```

Describes the language, script and other variants used to describe names. It must be either the literal "local" or a language tag according to definition in IETF-BCP47 <https://www.rfc-editor.org/rfc/bcp/bcp47.txt>.
The value of "local" is used to indicate the name in the local language and script. Such is the case when capturing data from OpenStreetMap where only a "name" tag is supplied with no further information.
Although the BCP47 language tag definition is complex, a very simplified view defines a language as "language-script-region" where script and region are optional. The spec lists allowed values for language, script, and region. It further describes how to include variants, extensions and other private custom extensions, which are allowed but not described here.
For some languages, the "Suppress-Script" property in BCP47 defines a script that can be omitted from the language tag. For example, the "Latn" script can be omitted for the "en" language. By convention, Overture will always omit the script when it matches the Suppress-Script property for a language. In other words, "en-Latn" is forbidden in favor of "en", and same for "ru-Cyrl" in favor of "ru".
The complete lists of allowed values can be found at: <https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry>

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [defs.yaml\*](../../../../../../../tmp/jsonschema/schema/defs.yaml "open original schema") |

## language Type

merged type ([Details](defs-defs-propertydefinitions-language.md))

one (and only one) of

*   [Untitled string in Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-language-oneof-0.md "check type definition")

*   [Untitled string in Overture Maps Transportation Segment Schema](defs-defs-propertydefinitions-language-oneof-1.md "check type definition")
