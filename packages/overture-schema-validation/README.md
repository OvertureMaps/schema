Vic notes:
    Feature is ExtensibleBaseModel -> Migrate that up into Feature and deprecate.
                                      Note: It doesn't really work e2e since how does it apply in codegen context?

Summary of the different mixins:
    @required_if(condition_field, condition_value, required_fields) -> if/then
    @not_required_if(condition_field, condition_value, not_required_fields) -> if/then
    @exactly_one_of(field_names) -> oneOf . const True
    @min_properties -> minProperties

Next steps roadmap:
    2) Test `@no_extra_fields`.
    3) PR.
    4) List and finish mixins that need migrating, drop `ConstrainedBaseModel`
    5) Update `ModelConstraint` test with some multi-constraint cases.
    6) Drop validation package.
    7) *Possibly* move `Id` and `Ref` down into `system`.
    8) PR.
    9) Organization pass #1 on core.
   10) Drop `pct` or move it up into `core`.
   11) Finish scoping and migrate transportation theme onto it.
   12) Finish organizing core.
   13) Organization/docs passes on the themes.
   14) Turn on `make docformat` rule and make sure it includes `docformatter` as well as `pydocstyle`.
   15) FieldPointer (JsonPointer to a field) in system.


### Differences from Traditional Validators

#### Replacing @field_validator

Instead of using Pydantic's `@field_validator` decorator, use constraint annotations. This will
enable support for richer JSON Schema constraints and preservation of constraint logic in generated
code.

**Before (using @field_validator):**

```python
class PlaceProperties(BaseModel):
    country: str = Field(..., description="Country code")
    language: str = Field(..., description="Language tag")
    categories: List[str] = Field(..., description="Categories")
    wikidata_id: Optional[str] = Field(None, description="Wikidata ID")

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v):
        if not re.match(r"^[A-Z]{2}$", v):
            raise ValueError("Invalid ISO 3166-1 alpha-2 country code")
        return v

    @field_validator("language")
    @classmethod
    def validate_language_tag(cls, v):
        if not re.match(r"^[a-z]{2,3}(-[A-Za-z]{2,8})*$", v):
            raise ValueError("Invalid IETF BCP-47 language tag")
        return v

    @field_validator("categories")
    @classmethod
    def validate_unique_categories(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("Categories must be unique")
        return v

    @field_validator("wikidata_id")
    @classmethod
    def validate_wikidata_format(cls, v):
        if v is not None and not re.match(r"^Q\d+$", v):
            raise ValueError("Invalid Wikidata identifier format")
        return v
```

**After (using constraints):**

```python
class PlaceProperties(BaseModel):
    country: Annotated[str, CountryCodeAlpha2Constraint()] = Field(
        ..., description="Country code"
    )
    language: Annotated[str, LanguageTagConstraint()] = Field(
        ..., description="Language tag"
    )
    categories: Annotated[List[str], UniqueItemsConstraint()] = Field(
        ..., description="Categories"
    )
    # Domain-specific constraints removed for incremental approach
```

#### Using Constraint-Based Validation

For complex model-level validation, use the mixin-based constraint system:

```python
from overture.schema.validation.mixin import ConstraintValidatedModel, at_least_one_of

@at_least_one_of("max_speed", "min_speed")
class SpeedLimitRule(ConstraintValidatedModel, BaseModel):
    max_speed: Optional[Speed] = None
    min_speed: Optional[Speed] = None
```

##### ⚠️ CRITICAL: Inheritance Order Matters

When using `ConstraintValidatedModel`, it **MUST** come first in the inheritance list:

```python
# ✅ CORRECT - ConstraintValidatedModel first
class MyModel(ConstraintValidatedModel, BaseModel):
    pass

# ❌ WRONG - Will not generate JSON Schema metadata
class MyModel(BaseModel, ConstraintValidatedModel):
    pass
```

This is due to Python's Method Resolution Order (MRO). When `ConstraintValidatedModel` comes first,
its `model_json_schema` method is called, which adds constraint metadata to the generated JSON
Schema.

## Error Messages

Constraints provide detailed, consistent error messages:

```python
# Invalid country code
ValidationError: 1 validation error for MyModel
country
  Invalid ISO 3166-1 alpha-2 country code: USA [type=value_error]

# Mutual exclusion violation
ValidationError: 1 validation error for BoundaryModel
is_land, is_territorial
  Fields is_land, is_territorial are mutually exclusive and cannot all be true [type=value_error]
```

## JSON Schema Generation

Constraints automatically enhance generated JSON schemas with appropriate metadata:

```python
model_schema = MyModel.model_json_schema()
# Results in enhanced JSON schema with pattern, format, and constraint information
{
  "properties": {
    "language": {
      "type": "string",
      "pattern": "^[a-z]{2,3}(-[A-Za-z]{2,8})*(-[0-9][A-Za-z0-9]{3})*$",
      "description": "IETF BCP-47 language tag"
    },
    "categories": {
      "type": "array",
      "items": {"type": "string"},
      "uniqueItems": true,
      "minItems": 1
    }
  }
}
```

## Integration with Overture Schema

This validation package integrates with Overture Maps schema packages using a hybrid approach:

- **Field-level constraints**: Used for single-field validation
- **Mixin-based constraints**: Used for complex model-level validation
- **@model_validator**: Used for custom cross-field validation

```python
# In your schema models
from typing import Annotated, Literal
from pydantic import model_validator
from overture.schema.validation import CountryCodeAlpha2, LanguageTag
from overture.schema.validation.mixin import ConstraintValidatedModel

# Base properties with field-level validation
class OvertureFeatureProperties(BaseModel):
    theme: str = Field(..., description="Overture theme")
    type: str = Field(..., description="Feature type")
    country: Optional[CountryCodeAlpha2] = None
    names: Annotated[
        dict[LanguageTag, str],
        Field(json_schema_extra={"additionalProperties": False})
    ]

# Division-specific validation with mixin constraints
@required_if("subtype", "region", ["parent_division_id"])
class DivisionProperties(ConstraintValidatedModel, OvertureFeatureProperties):
    theme: Literal["divisions"] = Field(...)
    type: Literal["division"] = Field(...)

    subtype: PlaceType = Field(..., description="Administrative level")
    parent_division_id: Optional[str] = Field(None, description="Parent ID")
```
