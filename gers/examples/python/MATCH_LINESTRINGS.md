# Match Example: Roads

## Scenario
We want to find gers ids of overture road segment features that correspond to a feed with roads or road-like features. 

Minimum prerequisite for matching such a data set is to have a geometry. We are simulating this scenario with a few mock  linestring geometries.

## Inputs
- features to match: [macon-line-segments.csv](data\macon-line-segments.csv)
- overture candidates: [overture-transportation-macon.geojson](data\overture-transportation-macon.geojson)

## Running the script
```
cd gers/examples/python/data
python sidecar_match.py MatchGeneric --input-to-match data/macon-line-segments.csv --input-overture data/overture-transportation-macon.geojson --output data/.output-macon-line-segments-match-results.json
```

For all available options run:
```
sidecar_match.py MatchGeneric --help
```
or see the script [here](sidecar_match.py).


## Output
Output is a collection of `MatchResult` objects per each input feature to match, saved as a json. 

Because each LineString may partially match only a sub-part of its geometry and/or match with more than one overture feature, the output will contain the geometry sub-part that matched each overture segment, along with location references (LR) for both source and corresponding overture match candidate:

```json
{
    "id": "ID100D",
    "source_wkt": "LINESTRING (-83.6449266 32.8558541, -83.6464608 32.8577287, -83.6472708 32.8587201, -83.6481628 32.8597324)",
    "elapsed": 0.013149300000804942,
    "matched_features": [
        {
            "id": "100000013111",
            "candidate_wkt": "LINESTRING (-83.6460443 32.857126300000004, -83.64613200000001 32.857234000000005)",
            "overlapping_wkt": "LINESTRING (-83.64599838582379 32.85716368786681, -83.64608635181203 32.85727117127286)",
            "score": 0.4078881726495007,
            "source_lr": [
                0.33,
                0.36
            ],
            "candidate_lr": [
                0.0,
                1.0
            ]
        },
        {
            "id": "100000013112",
            "candidate_wkt": "LINESTRING (-83.64613200000001 32.857234000000005, -83.64628900000001 32.8574219)",
            "overlapping_wkt": "LINESTRING (-83.64608682332766 32.857271747405846, -83.64624191107801 32.85746124518762)",
            "score": 0.38637060333690465,
            "source_lr": [
                0.36,
                0.41
            ],
            "candidate_lr": [
                0.0,
                1.0
            ]
        },
        {
            "id": "100000007833",
            "candidate_wkt": "LINESTRING (-83.648076 32.859554, -83.6482814 32.859795500000004)",
            "overlapping_wkt": "LINESTRING (-83.64803575906193 32.859588225626005, -83.6481628 32.8597324)",
            "score": 0.471726721045031,
            "source_lr": [
                0.96,
                1.0
            ],
            "candidate_lr": [
                0.0,
                0.6
            ]
        },        
        

    ]
}
```

## Alternative
Also see [here](match_linestrings.ipynb) the same match example with geopandas.