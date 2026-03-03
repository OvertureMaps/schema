# Instrument

A musical instrument.

Instruments produce sound through vibration. They are classified
by how sound is produced.

## Fields

| Name | Type | Description |
| -----: | :----: | ------------- |
| `id` | `Id` | Unique identifier |
| `category` | `"music"` | |
| `kind` | `"instrument"` | |
| `name` | `string` | Common name |
| `tuning` | `float64` (optional) | Concert pitch in Hz.<br/><br/>Standard tuning is 440 Hz. |
| `num_strings` | `int32` (optional) | |
| `family` | `InstrumentFamily` (optional) | |
| `color` | `HexColor` (optional) | Body color |
| `tags` | `list<string>` (optional) | *All items must be unique. (`UniqueItemsConstraint`)* |
