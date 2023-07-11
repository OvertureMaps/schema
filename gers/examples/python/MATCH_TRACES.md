# Match Example: GPS Traces to Overture Road Segments

This page describes an example of how one could match a data set with GPS traces to the corresponding overture road segments.

Alternative approaches include converting the Overture data set to OSM format, loading it in one of the routing engines available and use the map matching services available, like [OSRM](http://project-osrm.org/docs/v5.5.1/api/#match-service), [GraphHopper](https://github.com/graphhopper/map-matching), [Valhalla](https://valhalla.github.io/valhalla/api/map-matching/api-reference/).

We are providing for demo purposes a basic implementation in python based on an approach commonly used, described in this paper: [Hidden Markov Map Matching](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/map-matching-ACM-GIS-camera-ready.pdf), that takes overture road segments as input. It is not intended to be a solution for all types of GPS trace data, but it can be a starting place in understanding how this can be achieved.

The match process is exemplified below using a few mock traces as well as a few GPS traces from [OpenStreetMap.org](https://www.openstreetmap.org/traces) in the city of Macon Georgia, USA. This data is used only for purposes of illustrating the match process, and the results will be different for different quality of traces data.

## Inputs
We will use two inputs for the example:

1. Overture road segments: [overture-transportation-macon.geojson.zip](https://wiki.overturemaps.org/download/attachments/393588/macon.json.zip?version=1&modificationDate=1680018861266&api=v2)
2. GPS traces to be matched:  

   [data\macon-manual-traces.geojson](data\macon-manual-traces.geojson) - mock traces with manually labeled expected prediction
   
   [data\macon-osm-traces-combined.geojson](data\macon-osm-traces-combined.geojson) - mock

Below we describe how we prepared the two data sets for matching for reference, but we also provide a sample traces feed so you can experiment matching it directly.

## Overture Data Set

Please see instructions <todo: link here> on how to use Athena to select the subset of the overture data set within a city for example. 

## GPS Traces to be matched

GPS traces can be stored in many formats, some of the most common including GPX, KML, CSV, GeoJSON.

In the case of OpenStreetMaps GPS traces we have GPX input traces, but we convert to GeoJSON for convenience, since having both data sets as GeoJSONs makes it very easy to initialize them both in the common class `MatchableFeature`.

We plan to add native support for more input formats in the future, but since conversion between these formats is trivial, we consider it outside the scope for now. 

### Downloading example traces

In our example we downloaded public traces from openstreetmap.org via a paged web API. 

A simple script [download_osm_traces.py](download_osm_traces.py) downloads and saves the traces in `data\osm_traces` 

### Preprocessing Traces

[convert_gpx.py](convert_gpx.py) takes the raw GPX OSM traces and converts them to geojson format, with the times for each point stored as `properties.times`, while also doing some processing of the traces for obtaining a small demo-size set of traces that can be used to obtain for example the average travel speeds per road segment or other traffic relevant information corresponding overture road segments.

We filter out the points that are too close to each other, either distance-wise (<50 meters) or time-wise (<1sec).
We also split traces that have big gaps between points (>100 meters) into separate traces.

The parameters were chosen arbitrarily to avoid processing a lot of data that doesn't add much useful information to the trace. Appropriate values depend on the traces data and what type of sidecar feed we're trying to produce with what type of quality and performance constraints. 

There are more elaborate approaches for picking which points to drop, when to split traces and other preprocessing, but that is outside the scope of this exercise.

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

See all (optional) parameters by running it with -h

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
        "id": "trace#5", 
        "elapsed": 2.356133099994622,
        "source_length": 8843,
        "route_length": 8842.56,
        "points": [

            {
                "original_point": "POINT (-83.586161 32.818036)",
                "time": "2023-04-15 16:45:16+00:00",
                "seconds_since_prev_point": 1.0,
                "snap_prediction": {
                    "id": "300000000658",
                    "snapped_point": "POINT (-83.5861835260731 32.81799684930207)",
                    "distance_to_snapped_road": 4.83,
                    "route_distance_to_prev_point": 52.36
                }
            },

        ],
        "points_with_matches": 172,
        "avg_dist_to_road": 2.55,
        "sequence_breaks": 0,
        "revisited_via_points": 0,
        "revisited_segments": 0,
        "target_candidates_count": 64,
        "target_ids": [
            37382754,
            300000000259,

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
   |trace#0|0|POINT (-83.585667 32.817693)|300000000658|
   |trace#0|1|POINT (-83.586115 32.817949)|300000000658|

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

