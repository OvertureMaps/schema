# Lanes attribution modeling 

## Lanes 
Lanes is a complex property that describes lanes organization on given segment (how many lanes there are, in what directions and more). 
Everything that is required to navigate through lanes is captured in that property. 
In case of lack of that property number of lanes is implicitly assumed as one in each traffic direction captured for given segment.

## Lanes number & numbering 
Lanes are provided as array. Number of elements in array informs about number of lanes on a segment (Either all lanes are provided in array 
with at minimum information about direction or none lane information is given on segment).
Index of lane in that array is assumed to be its identifier when referencing to given lane is needed. 
Lanes should be captured in array starting from left to right when looking on segment in direction of segment's geometry digitization.

### Examples:

```text

S->N digitization         N->S digitization         E->W digitization         W->E digitization
                                                     _____________            _____________
 | | |                        | | |                  1____________            0____________
 | | |                        | | |                  0                        1
 |0|1|                        |1|0|                  -------------            -------------
 
```

## Lane direction
Lane direction in a mandatory property of a single lane. It informs if traffic on that lane happens in direction of segment's geometry digitization order
(forward direction) or in opposite direction (backward) or both-ways. In case of both-ways additional information MUST be provided to specify how traffic
is organized on such lanes: reversible or alternating.
Reversible means that route has to be changed to avoid that lane if at moment of lane's conditions evaluation for given direction (forward or backward) are not met. 
Alternating means you route can include that lane and traffic in direction assumed but route is open on such lane in short, periodic cycles 
(usually signaled by lights signalisation or has to be judged by driver with safety consideration).

## Lane Connectivity 
Lanes connectivity has a single purpose to guide during navigation how to transition between given lane of:
   1. one portion of a segment to another portion of same segment when number of lanes changes in a way it is ambiguous to infer lane's continuation 
   2. one segment to another segment when change in lanes number makes it ambiguous to infer lane's continuation

Connectivity when provided on given segment (or on part of a segment with geometry scoping property) then it gives comprehensive 
information about what transitions between lanes are possible when navigating through that segment (or through that part of a segment). It means that:
* only transitions between lanes specified in connectivity are possible
* if lane connectivity is not provided for any lane on a segment (or on part of a that segment) then connectivity CAN be inferred.

OSM has other concepts that seems to serve similar purpose like i.e. [turns](https://wiki.openstreetmap.org/wiki/Key:turn) but this model in not able to encode enough
information to deal with ambiguous situations on multiline junctions ([example](https://wiki.openstreetmap.org/wiki/File:Lane_use_diagram_sign_at_Bass_Pro_Shops,_San_Jose,_California.jpg))

Lane connectivity is complementary information to restrictions on whole segment - means road restrictions for transitions between segments has precedence
over lanes connectivity and for connectivity between such segments SHOULD NOT be provided. 

## Lanes alignment and road outline estimation
In map visualization use case where roads are presented not as lines but as areas lane information CAN be used to infer outline of a road. Connectivity is not solution to
road outline calculation. For that OSM proposes other concept called [placement](https://wiki.openstreetmap.org/wiki/Proposed_features/placement) which could be considered
as valid modeling solution for Overture (currently as of 4th April 2023 OSM proposal is in draft status).

#### Why connectivity is not enough?
In simple situation when one lane segment transitions into two connectivity can say only lane 0 transition into lane 0 and 1. It can't say how exactly the outline should look 
a like... is lane 0 of first segment fully aligned with lane 0 of other segment and lane 1 is added on right side of road, or is lane 0 fully aligned with lane 1 on other segment and
lane 0 id added on left side of road, or maybe it's a delta shape situation where lane 0 of one road evenly widens int two lanes situation on next segment. 

# TODO:
* add toll on lane information (including payment types) -> toll information outside v1 scope since it was discarded from being simple road flag
* add connectors information to connectivity to support segmentation that is independent of topology what means specifying toConnector next toSegment (optionally) may be needed when there is more than one connector that leads to target segment
* add (potentially) optional via(s) to connectivity modeling if there are examples when more than one set of intermediate segments (without lanes information on them) can lead to same target segment



