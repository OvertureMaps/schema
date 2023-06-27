# GERS Sidecar Match Examples

## Context

Consumers of geospatial data sets usually need to solve a complex and costly process of matching them.
A data set that also has GERS IDs can be easily used to augment the Overture data set itself, or other data sets that also have GERS IDs via simple join by id.

Because Overture data sets are modeled and produced with prioritizing for stability of its identifiers (GERS IDs) over time, and the cost of matching being offset to the owner of the data sets, the consumers of data sets with GERS IDs can conflate, evaluate and onboard such feeds much cheaper and faster.

## Purpose

Matching a geospatial data set with overture (or any other) data set is a common problem and many solutions exist for this, from generic to highly specialized for particular data types. 

Depending on the match requirements, this can be achieved with a open source or commercial tools or services, with a few click or couple of lines of code or with large scale distributed system with complex match logic. 

The purpose of these examples is not to provide a solution to fit all purposes well, or to be particularly good on any data scenario.

Main purpose is to provide a few examples as options to start exploring your feed's compatibility with overture data set and to find GERS IDs that correspond to your features.
Once you evaluate the results for sample of your feed, you can decide if the overlap with overture and match quality is sufficient for your feed with some tweaking of the available parameters, or if not, you can use a different solution that fits better your scenario, or customize the existing example code for your needs.

## Types of Match

Below are a few examples of match scenarios by category:

- **MatchGeneric**: find most similar feature(s) of same or similar type from overture. Input types examples:
   - Building -> Building
   - Place -> Place
   - Curbside parking info (road-like or road-adjacent LineStrings) -> Road segments
- **Nearest**: sometimes simply finding nearest overture feature of a particular type can be valuable. Input types examples:
   - Traffic sensor with lat-long -> Road segments
   - Building-> Road Segments
- **Containment**: if you want to find the overture feature(s) of a particular type that geometrically contain your feature. Input types examples:
   - Retail store with lat-long -> Neighborhoods, airports, retail venues
   - Address -> Building
   - Taxi pickup points -> Place
- **SnapTraces**: most likely traveled overture road segments given a GPS trace. Input types:
   - GPS trace -> Road segments

## Match Options
### Script
One option to get gers ids is with [sidecar_match.py](sidecar_match.py) script:
```
sidecar_match.py <match-mode> --input-to-match <features-to-match-file> --input-overture <overture-file> --output <results-file>
```

Currently supported match-mode: MatchGeneric|SnapTraces.

Inputs can be geojson files or tab separated text files with geometries as WKT.  

The script uses [H3 tiles](https://h3geo.org/) to first filter candidates spatially, and then it calls a matcher.

See examples:
- [snap traces to roads](MATCH_TRACES.md)
- [match lines to roads](MATCH_LINESTRINGS.md)

### Geopandas
Another option is to use geopandas for spatial filtering. 
First applies a buffer to each geometry to match then sjoin overture candidates on intersects predicate.

See examples:
- [point to nearest road](match_nearest.ipynb)
- [match road-like to roads](match_linestrings.ipynb)
- [snap traces to roads](match_traces.ipynb)


### Dependencies

```
pip install shapely h3 geopandas geojson haversine gpxpy 
```