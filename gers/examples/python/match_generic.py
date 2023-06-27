from typing import Any, Dict, Iterable
from match_classes import MatchResult, MatchableFeature, MatchedFeature
from timeit import default_timer as timer
from utils import get_features_with_cells, load_matchable_set, write_json
from shapely.geometry import LineString, Point
import constants

def get_matches(feature_to_match: MatchableFeature, 
                candidates: Iterable[MatchableFeature], 
                buffer=constants.DEFAULT_GENERIC_MATCH_BUFFER , 
                min_buffered_overlap_ratio=constants.DEFAULT_GENERIC_MATCH_MIN_BUFFERED_OVERLAP_RATIO) -> MatchResult:
    """
    Generic match function for matching a single feature to a set of candidates.
    This is a simple match that assumes multiple matches are possible, but does not attempt to find and resolve conflicting matches.
    A minimum matched/unmatched geometry ratio is used to prune candidates.
    Hausdorff distance of the buffered intersection to determine the match score.
    Source and candidate linear references of the matched sub-parts are returned if the source is a LineString.
    """
    start = timer()
    geometry_to_match_buffered = feature_to_match.geometry.buffer(buffer, cap_style=2)

    results = []
    for candidate in candidates:
        if candidate.geometry is None: # sjoin will return a candidate with no geometry if it is not matched
            continue

        candidate_geometry_buffered = candidate.geometry.buffer(buffer, cap_style=2)

        buffered_overlap = geometry_to_match_buffered.intersection(candidate_geometry_buffered)
        candidate_matched_ratio = buffered_overlap.area / candidate_geometry_buffered.area
        #to_match_matched_ratio = buffered_overlap.area / geometry_to_match_buffered.area
        score = 0
        
        source_lr = None
        candidate_lr = None
        intersecting_to_match = None
        if candidate_matched_ratio > min_buffered_overlap_ratio:
            # score left 0 if  candidate if less than 10% of the candidate geometry is matched, 
            # otherwise it is the hausdorff distance between the intersection of the buffered geometries and the candidate geometry
            intersecting_to_match = feature_to_match.geometry.intersection(candidate_geometry_buffered)
            intersecting_candidate = candidate.geometry.intersection(geometry_to_match_buffered)
            intersecting_hausdorff_dist = intersecting_to_match.hausdorff_distance(intersecting_candidate)
            score = 1 - intersecting_hausdorff_dist / buffer

            if isinstance(feature_to_match.geometry, LineString):
                source_lr = get_sub_geometry_lr(feature_to_match.geometry, intersecting_to_match)
                candidate_lr = get_sub_geometry_lr(candidate.geometry, intersecting_candidate)
        res = MatchedFeature(candidate.id, candidate, None if intersecting_to_match is None else intersecting_to_match, score, source_lr, candidate_lr)
        results.append(res)

    results.sort(key=lambda x: x.score, reverse=True)

    end = timer()
    elapsed = end - start
    r = MatchResult(feature_to_match.id, feature_to_match, results, elapsed)
    return r

def get_sub_geometry_lr(geometry: LineString, sub_geometry: LineString) -> Iterable[float]:
    if sub_geometry is None or geometry is None or len(sub_geometry.coords) == 0:
        return None
    
    lr_coords = [sub_geometry.coords[0], sub_geometry.coords[-1]]
    lr_points = [Point(c[0], c[1]) for c in lr_coords]
    lr = [round(geometry.project(p) / geometry.length, 2) for p in lr_points]
    return lr


def output_matches(match_results: Iterable[MatchResult], output_file_name: str):
    write_json([m.to_json(min_score=0.1) for m in match_results], output_file_name)
    write_json([m.to_json() for m in match_results], output_file_name + ".all_matches.json")

    with open(output_file_name + ".auto_metrics.txt", "w") as f:
        header = [
            "id",
            "source_wkt",
            "elapsed", 
            "matched_id",
            "matched_wkt",
            "matched_overlapping_wkt",
        ]
        f.write(constants.COLUMN_SEPARATOR.join(header) + "\n") 
        for r in match_results:        
            for partial_match in r.matched_features:
                columns = [
                    str(r.id),
                    str(r.source_feature.geometry.wkt),
                    str(r.elapsed),
                    str(partial_match.id),
                    str(partial_match.matched_feature.geometry.wkt),
                    str(partial_match.overlapping_geometry.wkt if partial_match.overlapping_geometry is not None else ""),
                ]
                f.write(constants.COLUMN_SEPARATOR.join(columns) + "\n") 

def match(features_to_match_file: str, overture_file: str, output_file: str, res: int, overture_properties_filter: Dict[str, Any]=None, buffer: float=constants.DEFAULT_GENERIC_MATCH_BUFFER, min_buffered_overlap_ratio: float=constants.DEFAULT_GENERIC_MATCH_MIN_BUFFERED_OVERLAP_RATIO):
    start = timer()
    print("Loading features...")
    to_match_prop_filter = {}
    to_match = load_matchable_set(features_to_match_file, is_multiline=False, properties_filter=to_match_prop_filter, res=res, limit_feature_count=-1)
    features_to_match = to_match.features_by_id .values()
    if len(features_to_match) == 0:
        print("no features to match")
        exit()

    overture = load_matchable_set(overture_file, is_multiline=True, properties_filter = overture_properties_filter, res=res)
    features_overture = overture.features_by_id.values()
    print("Features to match: " + str(len(features_to_match)))
    print("Features Overture: " + str(len(features_overture)))
    end = timer()
    print(f"Loading time: {(end-start):.2f}s")

    i = 0
    match_results = []
    total_elapsed = 0
    for source_feature in features_to_match:
        i += 1
        target_candidates = get_features_with_cells(overture.features_by_cell, to_match.cells_by_id[source_feature.id])
        matches = get_matches(source_feature, target_candidates, buffer, min_buffered_overlap_ratio)
        match_results.append(matches)

    print("Writing results...")
    start = timer()
    output_matches(match_results, output_file)
    end = timer()
    print(f"Writing time: {(end-start):.2f}s")