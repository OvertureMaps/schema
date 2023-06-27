import json
from typing import Dict, Iterable
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
import constants

class MatchableFeature:
    """
    Convenience class to hold an id, a shapely geometry, and optionally a dictionary of properties for use in matching.
    It can be trivially populated from geojson and overture as an extension of geojson.
    """
    def __init__(self, id: str, geometry:BaseGeometry, properties: dict=None) -> None:
        self.id = str(id)
        self.geometry = geometry
        self.properties = properties
    
    def __str__(self) -> str:
        return json.dumps({ 
            "id": self.id, 
            "geometry": self.geometry.wkt, 
            "properties": self.properties
        })

    def get_connectors(self) -> Iterable[str]:
        return self.properties["connectors"] if self.properties is not None and "connectors" in self.properties else []        
    
class MatchableFeaturesSet:
    """Collection of matchable features, indexed by id, and by cells (H3 in current implementation)"""
    def __init__(self, features: Dict[str, Iterable[MatchableFeature]], cells_by_id: Dict[str, Iterable[str]], features_by_cell: Dict[str, Iterable[MatchableFeature]]) -> None:
        self.features_by_id = features
        self.cells_by_id = cells_by_id
        self.features_by_cell = features_by_cell

class MatchedFeature:
    """One matched feature with match-relevant information"""
    def __init__(self, id: str, matched_feature: MatchableFeature, overlapping_geometry: BaseGeometry, score: float, source_lr: Iterable[float]=None, candidate_lr: Iterable[float]=None) -> None:
        """
        Attributes:
            id: the gers id of the matched feature
            matched_feature: the matched feature itself
            overlapping_geometry: the sub-part of the matched features' geometry that overlaps with the source feature
            score: the score of the match
            source_lr: the Location Reference in the source geometry of the part that matched as array of from-to points projection factors
            candidate_lr: the Location Reference in the matched geometry of the part that matched the source geometry
        """
        self.id = id # the gers id of the matched feature
        self.matched_feature = matched_feature
        self.overlapping_geometry = overlapping_geometry
        self.score = score
        self.source_lr = source_lr
        self.candidate_lr = candidate_lr

    def to_json(self):
        j = { 
            "id": str(self.id), 
            "candidate_wkt": self.matched_feature.geometry.wkt,
            "overlapping_wkt": self.overlapping_geometry.wkt if self.overlapping_geometry is not None else None,
            "score": self.score,
        } 
        if self.source_lr is not None:
            j["source_lr"] = self.source_lr
        if self.candidate_lr is not None:
            j["candidate_lr"] = self.candidate_lr
        return j
    
    def __str__(self) -> str:
        return json.dumps(self.to_json())

class MatchResult:
    """"Result of matching a feature to a set of features"""
    def __init__(self, id: str, source_feature: MatchableFeature, matched_features: Iterable[MatchedFeature]=None, elapsed: float=None) -> None:
        self.id = id
        self.source_feature = source_feature
        self.matched_features = matched_features
        self.elapsed = elapsed

    def to_json(self, min_score:float=None):
        j = { 
            "id": str(self.id), 
            "source_wkt": self.source_feature.geometry.wkt,
            "elapsed": self.elapsed,
            "matched_features": [f.to_json() for f in self.matched_features if min_score is None or f.score >= min_score],
        } 
        return j
    
    def __str__(self) -> str:
        return json.dumps(self.to_json())

class TraceSnapOptions:
    """"Parameters for matching a trace to road segments"""
    def __init__(self, \
                 sigma=constants.DEFAULT_SIGMA,\
                    beta=constants.DEFAULT_BETA,\
                    max_point_to_road_distance=constants.DEFAULT_MAX_POINT_TO_ROAD_DISTANCE,\
                    max_route_to_trace_distance_difference=constants.DEFAULT_MAX_ROUTE_TO_TRACE_DISTANCE_DIFFERENCE,\
                    allow_loops=constants.DEFAULT_ALLOW_LOOPS,
                    revisit_segment_penalty_weight=constants.DEFAULT_SEGMENT_REVISIT_PENALTY,
                    revisit_via_point_penalty_weight=constants.DEFAULT_VIA_POINT_PENALTY_WEIGHT,
                    broken_time_gap_reset_sequence=constants.DEFAULT_BROKEN_TIME_GAP_RESET_SEQUENCE,
                    broken_distance_gap_reset_sequence=constants.DEFAULT_BROKEN_DISTANCE_GAP_RESET_SEQUENCE) -> None:
        self.sigma = sigma
        self.beta = beta
        self.allow_loops = allow_loops
        self.max_point_to_road_distance = max_point_to_road_distance
        self.max_route_to_trace_distance_difference = max_route_to_trace_distance_difference
        self.revisit_segment_penalty_weight = revisit_segment_penalty_weight
        self.revisit_via_point_penalty_weight = revisit_via_point_penalty_weight
        self.broken_time_gap_reset_sequence = broken_time_gap_reset_sequence
        self.broken_distance_gap_reset_sequence = broken_distance_gap_reset_sequence

class RouteStep:
    """One step in a route, corresponding to one road segment feature"""
    def __init__(self, feature: MatchableFeature, via_point: Point) -> None:
        """
        Attributes:
            feature: the matched feature
            via_point: the point on the feature where the route enters the feature as a shapely Point
        """
        self.feature = feature
        self.via_point = via_point

class Route:
    """A route, consisting of a sequence of steps"""
    def __init__(self, distance: float, steps: Iterable[RouteStep]) -> None:
        self.distance = distance
        self.steps = steps

class SnappedPointPrediction:    
    """A road segment feature as a snap prediction for point in a trace, with relevant match signals"""
    def __init__(self, id: str, snapped_point: Point, referenced_feature: MatchableFeature, distance_to_snapped_road: float, route_distance_to_prev_point: float, emission_prob: float, best_transition_prob: float, best_log_prob: float, best_prev_prediction: float, best_sequence: Iterable[str], best_route_via_points: Iterable[str], best_revisited_via_points_count:int, best_revisited_segments_count:int) -> None:
        self.id = str(id)
        self.snapped_point = snapped_point
        self.referenced_feature = referenced_feature
        self.distance_to_snapped_road = distance_to_snapped_road
        self.route_distance_to_prev_point = route_distance_to_prev_point
        self.emission_prob = emission_prob
        self.best_transition_prob = best_transition_prob
        self.best_log_prob = best_log_prob
        self.best_prev_prediction = best_prev_prediction
        self.best_sequence = best_sequence
        self.best_route_via_points = best_route_via_points
        self.best_revisited_via_points_count = best_revisited_via_points_count
        self.best_revisited_segments_count = best_revisited_segments_count

    def to_json(self, diagnostic_mode=False):
        best_prev_prediction_id = ""
        if self.best_prev_prediction is not None:
            best_prev_prediction_id = self.best_prev_prediction.id
            
        j = { 
            "id": self.id,
            "snapped_point": self.snapped_point.wkt,
            "distance_to_snapped_road": self.distance_to_snapped_road,
            "route_distance_to_prev_point": self.route_distance_to_prev_point,
        } 

        if diagnostic_mode:
            j["referenced_feature"] = self.referenced_feature.geometry.wkt
            j["emission_prob"] = self.emission_prob
            j["best_transition_prob"] = self.best_transition_prob
            j["best_log_prob"] = self.best_log_prob
            j["best_prev_prediction"] = best_prev_prediction_id
            j["best_route_via_points"] = self.best_route_via_points
            j["best_revisited_via_points_count"] = self.best_revisited_via_points_count
            j["best_revisited_segments_count"] = self.best_revisited_segments_count 

        return j

class PointSnapInfo:
    """Snap-to-road match information corresponding to one point in a trace"""
    def __init__(self, index: int, original_point: Point, time: str, seconds_since_prev_point: float=None, predictions:Iterable[SnappedPointPrediction]=[]) -> None:
        self.index = index
        self.original_point = original_point
        self.time = time
        self.seconds_since_prev_point = seconds_since_prev_point
        self.predictions = predictions
        self.best_prediction = None
        self.ignore = False
    
    def to_json(self, diagnostic_mode: bool=False, include_all_predictions: bool=False,):
        best_prediction_json = None if self.best_prediction is None else self.best_prediction.to_json(diagnostic_mode)

        j = {
            "original_point": self.original_point.wkt,
            "time": self.time,
            "seconds_since_prev_point": self.seconds_since_prev_point,
            "snap_prediction": best_prediction_json,
        }

        if self.ignore:
            j["ignore"] = True

        if diagnostic_mode:
            j["point_index"] = self.index

        if include_all_predictions:
            j["predictions"] = list(map(lambda x: x.to_json(diagnostic_mode), self.predictions))
        return j

class TraceMatchResult:
    """Result of a matching trace to road segments"""
    def __init__(self, id: str, source_wkt: str, points: Iterable[PointSnapInfo], source_length: float, target_candidates_count: int, matched_target_ids: Iterable[str]=None, elapsed: float=None, sequence_breaks: int=0, points_with_matches: int=0, route_length: float=0, avg_dist_to_road: float=None, revisited_via_points: int=0, revisited_segments: int=0) -> None:
        self.id = id
        self.source_wkt = source_wkt
        self.points = points
        self.source_length = source_length
        self.target_candidates_count = target_candidates_count
        self.matched_target_ids = matched_target_ids
        self.elapsed = elapsed
        self.sequence_breaks = sequence_breaks
        self.points_with_matches = points_with_matches
        self.route_length = route_length
        self.avg_dist_to_road = avg_dist_to_road
        self.revisited_via_points = revisited_via_points
        self.revisited_segments = revisited_segments        

    def to_json(self, diagnostic_mode=False, include_all_predictions=False):
        points_json = list(map(lambda x: x.to_json(diagnostic_mode, include_all_predictions), self.points))
        return { 
            "id": str(self.id), 
            "elapsed": self.elapsed,
            "source_length": self.source_length,
            "route_length": self.route_length,
            "points": len(self.points),
            "points_with_matches": self.points_with_matches,
            "avg_dist_to_road": self.avg_dist_to_road,
            "sequence_breaks": self.sequence_breaks,
            "revisited_via_points": self.revisited_via_points,
            "revisited_segments": self.revisited_segments,
            "target_candidates_count": self.target_candidates_count,
            "target_ids": self.matched_target_ids,
            "points": points_json
        }

    def __str__(self) -> str:
        return json.dumps(self.to_json())