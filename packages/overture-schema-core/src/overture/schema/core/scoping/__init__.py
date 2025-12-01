"""
Decorates Pydantic models with scoping fields.

What is scoping?
================
In the Overture schema, a scoped value is one that applies only when certain conditions are true.

A simple example is geometric range scoping, better known as linear referencing. In geometric
scoping, the scoped values apply only to designated sub-segments along a linear geometry.

Suppose you are modeling subterranean infrastructure with a LineString feature representing tunnels,
and suppose you want to record depth observations for each tunnel along different sub-segments.
Perhaps a tunnel is 10 meters deep for the first 100 meters, then rises a bit to only 7 meters deep
for the next 100 meters. These depth observations would be modeled in the Overture schema using
geometric range scoping (linear referencing): you would give your tunnel model an array of depth
obervations, and each observation would contain a linearly-referenced depth value.

>>> from typing import Annotated, Literal
>>> from pydantic import BaseModel
>>> from overture.schema.core.models import OvertureFeature
>>> from overture.schema.system.primitive import (
...     float32,
...     Geometry,
...     GeometryType,
...     GeometryTypeConstraint
... )
...
>>> @scoped(Scope.GEOMETRIC_RANGE)
... class Depth(BaseModel):
...     value: float32
...
>>> class Tunnel(OvertureFeature[Literal['underground'], Literal['tunnel']]):
...     geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.LINE_STRING)]
...     depth: list[Depth] | None = None
...
>>> tunnel = Tunnel(
...     id='tunnel_001',
...     theme='underground',
...     type='tunnel',
...     version=1,
...     geometry=Geometry.from_wkt('LINESTRING (0 0, 1 1)'),
...     depth=[Depth(between=[0, 0.15], value=10), Depth(between=[0.15, 0.30], value=7)]
... )


Why use scoping?
================
Scoping provides a repeatable, consistent, framework for expressing the idea that a specific value
only applies in specific circumstances, such as: at specific times, in specific places, to specific
individuals or vehicle, *etc.*

By using scoping, you ensure that your schema is consistent with the Overture schema, will be
widely understood by humans, and will be able to be consumed by automated tools that understand
Overture structure and conventions.


Types of scoping
================
The authoritative list of available scopes is enumerated in `overture.schema.core.scoping.Scope`.

The following scopes are available:

Geometric position scope (point events):
----------------------------------------
Geometric position scoping allows a value to be tied to a specific point along a linear path using
linear referencing. When a model is decorated with geometric position scoping, an `at` field is
automatically added to the model. This `at` field is used to specify the position along the linear
path. As with geometric range scoping, `at` values are specified as percentage offsets from the
start of the path, where `0.0` represents the start of the path, `0.5` represents the point halfway
along the path, `1.0` represents the end of the path, and so on.

>>> from typing import Annotated, Literal
>>> from pydantic import BaseModel
>>> from overture.schema.core.models import OvertureFeature
>>> from overture.schema.system.primitive import (
...     Geometry,
...     GeometryType,
...     GeometryTypeConstraint,
...     uint32,
... )
...
>>> @scoped(required=Scope.GEOMETRIC_POSITION)
... class Transformer(BaseModel):
...     power_capacity: uint32
...
>>> class PowerLine(OvertureFeature[Literal['power'], Literal['line']]):
...     geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.LINE_STRING)]
...     transformers: list[Transformer] | None = None
...
>>> power_line = PowerLine(
...     id='power_line_001',
...     theme='power',
...     type='line',
...     version=1,
...     geometry=Geometry.from_wkt('LINESTRING (0 0, 1 1)'),
...     transformers=[Transformer(at=0.73, power_capacity=167)]
... )


Geometric range scope (linear events):
--------------------------------------
Geometric range scoping allows a value to be tied to a sub-segment of a linear path using linear
referencing. When a model is decorated with geometric range scoping, a `between` field is
automatically added to the model. This `between` field is used to specify the start and end
positions of the range along the linear path. The `between` field is a pair (a list or array of
length exactly two) and as with the geometric point scoping `at` field, the `between` pair values
indicate percentage offsets from the start of the path, where `0.0` represents the start of the
path and `1.0` represents the end.

See the section *What is scoping?*, above, for an example of geometric range scoping.


Heading scope (forward and backward):
-------------------------------------
Heading scoping allows a value to be tied to one of the two possible headings or facings along a
linear path: forward (toward the end of the path) or backward (toward the start of the path). When
a model is decorated with heading scoping, a `when.heading` field is automatically added to the
model.

>>> from typing import Annotated, Literal
>>> from pydantic import BaseModel, Field
>>> from overture.schema.core.models import OvertureFeature
>>> from overture.schema.system.primitive import (
...     Geometry,
...     GeometryType,
...     GeometryTypeConstraint,
...     uint32,
... )
>>> from overture.schema.system.string import StrippedString
...
>>> @scoped(required=Scope.HEADING)
... class Designation(BaseModel):
...     value: StrippedString
...
>>> class Runway(OvertureFeature[Literal['airport'], Literal['runway']]):
...     geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.LINE_STRING)]
...     designations: list[Designation] = Field(min_length=1, max_length=2)
...
>>> jfk_04l_22r = Runway(
...     id='jfk_04l_22r',
...     theme='airport',
...     type='runway',
...     version=1,
...     geometry=Geometry.from_wkt(
...         'LINESTRING (-73.785585 40.622035, -73.763323 40.650515)'
...     ),
...     designations=[
...         Designation(value='04L', when=Designation.When(heading=Heading.FORWARD)),
...         Designation(value='22R', when=Designation.When(heading=Heading.BACKWARD)),
...     ]
... )


Temporal scoping (recurring time patterns):
-------------------------------------------
Temporal scoping allows a value to be tied to specific one-time or recurring time ranges. When a
model is decorated with temporal scoping, a `when.during` field is automatically added to the model.
The `during` field contains a time pattern formatted according to the OpenStreetMap
[opening hours specification](https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification).

>>> from pydantic import BaseModel
>>> from overture.schema.system.string import StrippedString
>>> @scoped(Scope.TEMPORAL)
... class WiFiHotspot(BaseModel):
...     '''A public WiFi hotspot'''
...     ssid: StrippedString
...
>>> hotspots=[
...     WiFiHotspot(ssid="always_on"),
...     WiFiHotspot(ssid="daytime_use_only", when=WiFiHotspot.When(during="06:00-22:00"))
... ]


Travel mode:
------------
Travel mode scoping allows a value to be tied to one or more modes of travel, for example driving a
motor vehicle, driving a car, or walking on foot. When a model is decorated with travel mode
scoping, a `when.mode` field is automatically added to the model. The `mode` field is a list
accepting one or more unique members of the `TravelMode` enumeration. Travel mode scoping can be
used to express concepts such as "access is only allowed if you are traveling in this way", or
"turns are prohibited unless you are traveling in this way".


Purpose of use:
---------------
Purpose of use scoping allows a value to be tied to one or more reasons why an actor might be using
a feature. Examples include "I am only using this road to make a delivery and then will leave", or
"I am not through traffic; I am using this road because it is my destination."

When a model is decorated with purpose of use scoping, a `when.using` field is automatically added
to the model. The `using` field is a list accepting one or more unique members of the `PurposeOfUse`
enumeration. Purpose of use scoping can be used to express concepts such as "access is only allowed
if you are here for this reason".


Recognized status:
------------------
Recognized status scoping allows a value to be tied to one or more statuses that an actor might be
recognized as having. Examples include "I am an employee of this business", "I have a permit", or
"I have a recognized disability".

When a model is decorated with recognized status scoping, a `when.recognized` field is automatically
added to the model. The `recognized` field is a list accepting one or more unique members of the
`RecognizedStatus` enumeration. Recognized status scoping can be used to express concepts such as
"access is only allowed if you are recognized as having this status".


Side (left or right):
---------------------
Side scoping allows a value to be tied to the left- or right-hand side of something. When a model
is decorated with side scoping, a `side` field  is automatically added to the model.

>>> from typing import Annotated, Literal
>>> from pydantic import BaseModel
>>> from overture.schema.core.models import OvertureFeature
>>> from overture.schema.system.primitive import (
...     Geometry,
...     GeometryType,
...     GeometryTypeConstraint,
... )
>>> from overture.schema.system.string import StrippedString
...
>>> @scoped(required=(Scope.SIDE, Scope.GEOMETRIC_POSITION))
... class BusStop(BaseModel):
...     route: StrippedString
...
>>> class BusLoadingIsland(OvertureFeature[Literal['bus_terminal'], Literal['loading_island']]):
...     geometry: Annotated[Geometry, GeometryTypeConstraint(GeometryType.LINE_STRING)]
...     stops: list[BusStop] | None = None
...
>>> island = BusLoadingIsland(
...     id='island_001',
...     theme='bus_terminal',
...     type='loading_island',
...     version=1,
...     geometry=Geometry.from_wkt('LINESTRING (0 0, 1 1)'),
...     stops=[
...         BusStop(route='15', side=Side.LEFT, at=0.10),
...         BusStop(route='B-Line', side=Side.RIGHT, at=0.25),
...     ]
... )

When used on a linear feature, the side is interpreted with reference to the geometry's orientation.
Specifically, the value `Side.LEFT` is on the left of a person who is facing forward (toward the
end of the geometry), and `Side.RIGHT` is likewise on this person's right.


Vehicle:
--------
Vehicle scoping allows a value to be tied to one or more properties of a vehicle, such as height,
weight, or number of axles. This enables a wide variety of use cases such as restricting the
allowed weight of trucks on bridges, limiting the allowed height of vehicles crossing under
bridges or entering garages, applying differential speed limits to different classes of vehicle,
*etc.* When a model is decorated with vehicle scoping, a `when.vehicle` field is automatically
added to the model.

>>> from overture.schema.core.unit import LengthUnit
>>> from overture.schema.system.primitive import float32
...
>>> @scoped(Scope.VEHICLE)
... class Fare(BaseModel):
...     value: float32
...
>>> fare_schedule: list[Fare] = [
...     Fare(
...         value=10,
...         when=Fare.When(vehicle=[
...             VehicleAxleCountSelector(
...                 dimension=VehicleDimension.AXLE_COUNT,
...                 comparison=VehicleRelation.LESS_THAN,
...                 value=3
...             ),
...             VehicleLengthSelector(
...                dimension=VehicleDimension.LENGTH,
...                comparison=VehicleRelation.LESS_THAN_EQUAL,
...                value=18,
...                unit=LengthUnit.FT,
...             )
...         ]),
...     ),
...     Fare(value=30),
... ]



Mixing scopes
==============
The `@scoped` decorator can mix any desired combination of scopes onto your Pydantic model.

For example, suppose you are modeling a value type that can apply at certain times, along a certain
sub-segment of a linear path, depending on whether one is traveling forward or backward along the
path, or any combination of these three. This can be achieved easily with:

>>> @scoped(Scope.TEMPORAL, Scope.GEOMETRIC_RANGE, Scope.HEADING)
... class MyModel(BaseModel):
...     pass


Optional and required scopes
============================
When using the `@scoped` decorator, scopes are optional by default but some or all scopes may be
made required.

The following example makes all the scopes required:

>>> from enum import Enum
...
>>> class SignalType(str, Enum):
...    STOP_SIGN = 'stop_sign'
...
>>> @scoped(required=(Scope.GEOMETRIC_POSITION, Scope.HEADING))
... class TrafficSignal(BaseModel):
...    signal_type: SignalType

The following example mixes an optional scope (temporal) with two required scopes (geometric
position and heading).

>>> @scoped(Scope.TEMPORAL, required=(Scope.GEOMETRIC_POSITION, Scope.HEADING))
... class TrafficSignal(BaseModel):
...    signal_type: SignalType


The `when` clause
=================
For historical reasons, some scope fields are added directly to the decorated model, while others
are added as children of a synthetic `when` field.

| Scope                      | Field             |
|----------------------------|-------------------|
| `Scope.GEOMETRIC_POSITION` | `at`              |
| `Scope.GEOMETRIC_RANGE`    | `between`         |
| `Scope.HEADING`            | `when.heading`    |
| `Scope.TEMPORAL`           | `when.during`     |
| `Scope.TRAVEL_MODE`        | `when.mode`       |
| `Scope.PURPOSE_OF_USE`     | `when.using`      |
| `Scope.RECOGNIZED_STATUS`  | `when.recognized` |
| `Scope.SIDE`               | `side`            |
| `Scope.VEHICLE`            | `when.vehicle`    |


If a `when` field is added to the model, the model is also decorated with a nested `When` class to
simplify instantiating values for the `when` field, for example:

>>> from overture.schema.system.primitive import uint8
...
>>> @scoped(Scope.HEADING)
... class MyModel(BaseModel):
...     value: uint8
...
>>> MyModel(value=10)
MyModel(value=10, when=None)
>>> MyModel(value=15, when=MyModel.When(heading=Heading.BACKWARD))
MyModel(value=15, when=MyModel.When(heading=<Heading.BACKWARD: 'backward'>))
"""

from .heading import Heading
from .lr import LinearlyReferencedPosition, LinearlyReferencedRange
from .opening_hours import OpeningHours
from .purpose_of_use import PurposeOfUse
from .recognized_status import RecognizedStatus
from .scoped import Scope, scoped
from .side import Side
from .travel_mode import TravelMode
from .vehicle import (
    VehicleAxleCountSelector,
    VehicleDimension,
    VehicleHeightSelector,
    VehicleLengthSelector,
    VehicleRelation,
    VehicleSelector,
    VehicleWeightSelector,
    VehicleWidthSelector,
)

__all__ = [
    "Heading",
    "LinearlyReferencedPosition",
    "LinearlyReferencedRange",
    "OpeningHours",
    "PurposeOfUse",
    "RecognizedStatus",
    "Scope",
    "scoped",
    "Side",
    "TravelMode",
    "VehicleAxleCountSelector",
    "VehicleDimension",
    "VehicleHeightSelector",
    "VehicleLengthSelector",
    "VehicleRelation",
    "VehicleSelector",
    "VehicleWeightSelector",
    "VehicleWidthSelector",
]
