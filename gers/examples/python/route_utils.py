from collections.abc import Iterable

from match_classes import MatchableFeature, Route, RouteStep
from shapely.geometry import Point
from shapely.ops import nearest_points
from utils import get_distance


def get_route_step_dist(feat_before_from: MatchableFeature, feat_from: MatchableFeature, feat_to: MatchableFeature, start_feature: MatchableFeature, end_feature: MatchableFeature, start_point: Point, end_point: Point) -> tuple[Point, float]:
    """get distance traveled on one feature `feat_from` having entering from `feat_before_from` and exiting to `feat_to`, given that the whole route starts at `start_feature` and ends at `end_feature`"""
    # todo: this a distance approximation for now as length of straight line from entry point to exit point on the feat_from feature, but works reasonably well for the data seen so far
    feat_from_exit_point, p2 = nearest_points(feat_from.geometry, feat_to.geometry)
    d = 0

    if feat_from.id == start_feature.id:
        d += get_distance(start_point, feat_from_exit_point)
    else:
        p0_before, feat_from_entry_point = nearest_points(feat_before_from.geometry, feat_from.geometry)
        d += get_distance(feat_from_entry_point, feat_from_exit_point)

    if feat_to.id == end_feature.id:
        d += get_distance(end_point, p2)
    # else there is no distance to add

    # todo: add basic penalties like allowed travel direction disagreement, road class change cost, etc.
    return feat_from_exit_point, d

def get_shortest_route(features: Iterable[MatchableFeature], feature_id_to_connected_features: dict[str, Iterable[MatchableFeature]], start_feature: MatchableFeature, end_feature: MatchableFeature, start_point: Point, end_point: Point, allowed_ids: Iterable[str], blocked_ids: Iterable[str]) -> Route:
    """
    Dijsktra's algorithm to find shortest route between start and end features. Remember for each traveled feature the entry via_point.
    """

    # start and end are same feature, no route calculation needed, just distance
    if start_feature.id == end_feature.id:
        dist = get_distance(start_point, end_point)
        return Route(dist, [RouteStep(start_feature, None)])
    x = set()

    dist = {}
    prev = {}
    prev_via_point = {}
    feats_to_visit = []
    ids_to_visit = set()
    for f in features:
        if f.id in blocked_ids and f.id != start_feature.id:
            continue
        dist[f.id] = float('inf')
        prev[f.id] = None
        prev_via_point[f.id] = None
        feats_to_visit.append(f)
        ids_to_visit.add(f.id)
    dist[start_feature.id] = 0

    while len(feats_to_visit) > 0:
        current_feature = feats_to_visit[0]
        min_dist = float('inf')
        for f in feats_to_visit:
            if dist[f.id] < min_dist:
                min_dist = dist[f.id]
                current_feature = f

        if min_dist == float('inf'):
            break # no more allowed connected features to visit

        if current_feature.id == end_feature.id:
            break # done, visited end_feature, don't need to calculate shortest path to all features

        feats_to_visit.remove(current_feature)
        ids_to_visit.remove(current_feature.id)
        connected_features = feature_id_to_connected_features[current_feature.id]
        for v in connected_features:
            if v.id not in allowed_ids or (v.id in blocked_ids) or v.id not in ids_to_visit:
                continue

            if v.id not in ids_to_visit:
                continue # have already visited this feature

            via_point, d = get_route_step_dist(prev[current_feature.id], current_feature, v, start_feature, end_feature, start_point, end_point)
            alternate_dist = dist[current_feature.id] + d
            if alternate_dist < dist[v.id]:
                dist[v.id] = alternate_dist
                prev[v.id] = current_feature
                prev_via_point[v.id] = via_point

    steps = []
    current_feature = end_feature
    if prev[current_feature.id] is not None or current_feature.id == start_feature.id:
        while current_feature is not None:
            steps.insert(0, RouteStep(current_feature, prev_via_point[current_feature.id]))
            current_feature = prev[current_feature.id]

    r = Route(round(dist[end_feature.id], 2), steps)
    return r
