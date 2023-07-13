# Match Example: GPS Traces to Overture Road Segments

This page describes an example of how one could match a data set with GPS traces to the corresponding overture road segments.

Alternative approaches include converting the Overture data set to OSM format, loading it in one of the routing engines available and use the map matching services available, like [OSRM](http://project-osrm.org/docs/v5.5.1/api/#match-service), [GraphHopper](https://github.com/graphhopper/map-matching), [Valhalla](https://valhalla.github.io/valhalla/api/map-matching/api-reference/).

We are providing for demo purposes a basic implementation in python based on an approach commonly used, described in this paper: [Hidden Markov Map Matching](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf), that takes overture road segments as input. It is not intended to be a solution for all types of GPS trace data, but it can be a starting place in understanding how this can be achieved.

The match process is exemplified below using a few mock traces as well as a few GPS traces from [OpenStreetMap.org](https://www.openstreetmap.org/traces) in the city of Macon Georgia, USA. This data is used only for purposes of illustrating the match process, and the results will be different for different quality of traces data.

## Inputs
We will use two inputs for the example:

1. Overture road segments: [data\overture-transportation-macon.geojson](data\overture-transportation-macon.geojson) - Please note that this data set is included for demonstrative purposes, it is a sample that doesn't contain the latest properties defined in the Overture schema and its GERS IDs are provisional.
2. GPS traces to be matched:     
   [data\macon-osm-traces-combined.geojson](data\macon-osm-traces-combined.geojson) - sampled from OSM, see below for details.

   [data\macon-manual-traces.geojson](data\macon-manual-traces.geojson) - mock traces simulating some noise edge cases with labeled expected prediction.
   
Below we describe how we prepared the two data sets for matching for reference, but we also include them so you can experiment with matching directly.

## Overture Data Set

Please see instructions <todo: link here> on how to use Athena to select the subset of the overture data set within a city for example. 

## GPS Traces to be matched

GPS traces can be stored in many formats, some of the most common including GPX, KML, CSV, GeoJSON.

In the case of OpenStreetMaps GPS traces we have GPX input traces, but we convert to GeoJSON for convenience, since having both data sets as GeoJSONs makes it very easy to initialize them both in the common class `MatchableFeature`.

Since conversion between these formats is trivial, we consider it outside the scope for this exercise. 

In our example we downloaded public traces from openstreetmap.org. 

A sample sub-set of the raw GPX OpenStreetMaps traces were converted to geojson format, with the times for each point stored as `properties.times`.

Points that are too close to each other, either distance-wise (<50 meters) or time-wise (<1sec), were filtered out.
We also split traces that have big gaps between points (>100 meters) into separate traces. This was done to avoid processing a lot of data that doesn't add much useful information to the trace. Parameters are chosen arbitrarily, and appropriate values depend on the traces data and what type of sidecar feed we're trying to produce with what type of quality and performance constraints. There are more elaborate approaches for picking which points to drop, when to split traces and other preprocessing, but that is outside the scope of this exercise. 

Result is a demo-size set of traces that can be used to obtain for example the average travel speeds per overture road segment or other traffic relevant information.

An `id` is generated to uniquely identify each such trace and source properties are added to help identify each processed trace and its original source of data.

An example trace to match as geojson:
```json
{
    "type": "Feature",
    "id": "trace#0",
    "geometry": {
        "type": "LineString",
        "coordinates": [[-83.630794, 32.850851], ]
    },
    "properties": {
        "filename": "osm-traces-page-0.gpx",
        "track.number": 0,
        "track.link": "/user/sunnypilot/traces/7824504",
        "track.name": "2023_06_05T12_07_14.093431Z.gpx",
        "track.segment.number": 0,
        "track.segment.split.number": 0,
        "track.description": "Routes from sunnypilot 2022.11.13 (HYUNDAI SONATA 2020).",
        "times": ["2023-06-05 12:07:14+00:00", ]
    }
}        
```

### Dependencies

```
pip install shapely h3 geopandas geojson haversine gpxpy
```
Or:
```
pip install -r gers/examples/python/requirements.txt
```

## Run with script

Example parameters for running traces matching with the sidecar_match.py script:
```
cd gers/examples/python/data
python match_traces.py --input-to-match data/macon-manual-traces.geojson --input-overture data/overture-transportation-macon.geojson --output data/match-result.json
```

See all (optional) parameters by running it with `-h`.

The script uses [H3 tiles](https://h3geo.org/) to first filter road segment candidates spatially.

## Run with notebook
Alternative is to perform the traces match via notebook available here: [match_traces.ipynb](match_traces.ipynb)

This approach uses geopandas for spatial join step of finding road candidates, then constructs both data sets into the same python object `MatchableFeature` and calls same trace match code.

## Output

The output file will contain per each point in each trace the prediction of the most likely traveled road. The original point from the trace as well as the predicted point on the road segment are provided, along with useful information that can be used to infer the actual route traveled and the speed like the timestamp for the point, distance traveled on the road network since last point.

Additional metrics are provided for the whole trace in the match result object. 

Below is an example of the output for a trace:
```json
    {
        "id": "trace#1",
        "elapsed": 0.6450104000105057,
        "source_length": 5165.4,
        "route_length": 5167.13,
        "points": [


            {
                "original_point": "POINT (-83.586113 32.818006)",
                "time": "2023-06-04 21:01:52+00:00",
                "seconds_since_prev_point": 2.0,
                "snap_prediction": {
                    "id": "8544c0bbfffffff-17976b4158ac1b2f",
                    "snapped_point": "POINT (-83.58613449627562 32.81796863910759)",
                    "distance_to_snapped_road": 4.61,
                    "route_distance_to_prev_point": 50.35
                }
            },


        ],
        "points_with_matches": 101,
        "avg_dist_to_road": 3.12,
        "sequence_breaks": 0,
        "revisited_via_points": 0,
        "revisited_segments": 0,
        "target_candidates_count": 34,
        "target_ids": [
            "8744c0a36ffffff-13d7eb54760e4d65",
            "8744c0a36ffffff-13979f2200827e1f",
            "8544c0bbfffffff-17976b4158ac1b2f",
            "8744c0a36ffffff-17d7b86aff4e68cd"
        ]
    },
```

## Metrics
### Match Quality
The match quality between your feed and overture roads is influenced by multiple factors:
1. Noise level of the traces data.
2. Disagreement between traces data and overture data.
3. Match quality of the algorithm.

We propose two types for metrics, error rate via manually labeled set, which allows you to decouple the data disagreements problems to be able to focus on the algorithm itself, and automatic quality proxy metrics, like indicators associated with match problems, which are provided automatically for your whole feed when you run the match algorithm, but are only indirect approximations of how good the match is.

**Error Rate via Manually Labeled Set**

This approach provides highest level of insight into how well the algorithm performs, but because it requires human labeling which is costly to obtain, we only recommend it if planning to debug or develop the algorithm. 
Below are instructions on how to obtain the metric for your feed, and we exemplify it with a few manually labeled traces.

1. Select the traces that will make up the truth set.
2. Run the match algorithm as described above, with -j parameter. This will create as one of the outputs a file ending in `for_judgment.txt` which is a tab separated text file with a row for each point in each trace and the GERS ID that the algorithm found:

   |trace_id|point_index|trace_point_wkt|gers_id|
   |-|-|-|-|
   |manual_trace#1|0|POINT (-83.6455155 32.8246168)|`8844c0b1a7fffff-17fff78c078ff50b`|
   |manual_trace#1|1|POINT (-83.64514 32.8251578)|`8844c0b1a7fffff-13def9663b8c091b`|
   |...||||

   This will serve as a starting point for our "truth set", by using the results of the match to "pre-label" the data.
3. Review the matches in QGIS. Load the overture features, the "pre-labeled" for_judgment.txt points, and the `snapped_points.txt` file. This should make it easy to observe which of the matches are incorrect. Optionally you could add an OSM tiles layer for example to add more context. 
4. Save the corrected labels file as `.labeled.txt`. In our example this file can be found here: [data\macon-manual-traces.labeled.txt](data\macon-manual-traces.labeled.txt)
5. Compute **Error Rate** metric. This is done automatically by the script if a .labeled.txt file exists corresponding to the input traces file. 
Error Rate is defined as the ratio between the length of the traces for which the prediction is matching the labeled set and the total length of the traces.

**Automatic Quality Proxy Metrics**

Because obtaining labeled data for a representative set can be difficult, we provide as alternative the metrics below that are calculated automatically when running the script. 

**Note**: all the metrics are averaged for the whole set and per each trace in the output. For most of them (all except first two) they are also provided per-km of length of trace, which are independent of trace lengths to facilitate cross-set comparisons. Length of trace in this context is calculated as sum of distances between each point of the input GPS trace. While a more "correct" length of trace would be the route distance, and you can still compute that yourself from the match result, we are using this definition because for some traces we won't be able to find a full or even partial route. Side effect is that the per-km metrics give more importance to points with noise, which artificially adds length to the truly traveled length.

1. **Average distance to snapped road** - per trace. How far away are the GPS points from the snapped road in meters. Not counting points without matches.
2. **Snapped route length to GPS length ratio** - per trace. The ratio between the sum of route distances between points that we were able to match and the sum if distances between trace points. In ideal case with no GPS noise, agreement with the map and perfect match result this metric would get close to 1. Lower number can mean higher disagreement, missing roads in overture data set, or incorrect matches. 0 means nothing got matched. Values greater than 1 are also possible and valid, but could indicate incorrect route matches. 
3. **Number of candidate segments** - per trace, per km. This counts how many roads are considered by the algorithm, as having common H3 tiles with the k-ringed H3 tiles of the trace. 
4. **Number of matched segments** - per trace, per km. This will naturally vary from one type of road to another, but correlated with other dimensions it can be useful to detect outliers or problems. Zero means no match was found for any point of the trace. Also, a high discrepancy between number of candidate segments and number of matched segments could mean the algo is spending too much time considering too many candidates, see how to tweak performance in the section below.
5. **Number of sequence breaks** - per trace, per km. A sequence break can happen when there is missing or bad data in overture roads or in the trace or simply they disagree enough that a gap of no possible route is detected. 
6. **Via-point revisits** - per trace, per km. A high number can be an indicator a lot of U-turns are predicted, which although can occur naturally, past some threshold can be a sign that the matches are incorrect.
7. **Segment revisits** - per trace, per km. Depending on your data, some traces will validly pass through same road segment again after having left it, but in many cases this is probably rare. An unusually high number can indicate wrong matches. 

For example, when matching the sample OSM traces with these options:
```json
{
    "sigma": 4.1,
    "beta": 0.9,
    "allow_loops": "True",
    "max_point_to_road_distance": 30.0,
    "max_route_to_trace_distance_difference": 300,
    "revisit_segment_penalty_weight": 100,
    "revisit_via_point_penalty_weight": 100,
    "broken_time_gap_reset_sequence": 60,
    "broken_distance_gap_reset_sequence": 300
}
```
The script will output these metrics (runtimes will vary depending on machine):
```
Traces.............................157
Target features....................22324
Elapsed:...........................1min 50.846s
Avg runtime/trace..................0.706s
Avg runtime/km.....................0.178s
Avg distance to snapped road.......2.92m
Snapped route length...............574.95km
GPS traces length..................622.47km
Snapped route len/gps len..........0.92
Avg number of candidate segments...58.69/trace, 14.80/km
Avg number of matched segments.....8.43/trace, 2.13/km
Avg number of sequence breaks......0.26/trace, 0.07/km
Avg number of revisited via points.0.31/trace, 0.08/km
Avg number of revisited segments...0.18/trace, 0.05/km
```

### Performance notes
While this demo match algorithm is not designed for performance, various parameters of the allow controlling the tradeoff between match quality and runtime. For example increasing `max_point_to_road_distance` will allow matching traces that are further away from the roads, thus increasing match recall for noisy GPS traces. However, this can increase significantly the runtime needed, since it increases the number of candidate roads to consider.

For each each trace to be matched we provide the time elapsed in the output property `TraceMatchResult.elapsed` in seconds. This can be used to analyze how runtime correlates with various properties of the data, like trace length, number of points, number of sequence breaks or the various match parameters, or for identifying bottlenecks.

