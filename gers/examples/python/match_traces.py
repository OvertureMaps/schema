import argparse
import csv
import json
import math
import os
from collections.abc import Iterable
from timeit import default_timer as timer

import constants
from match_classes import (
    MatchableFeature,
    PointSnapInfo,
    RouteStep,
    SnappedPointPrediction,
    TraceMatchResult,
    TraceSnapOptions,
)
from route_utils import get_shortest_route
from shapely import Point
from shapely.ops import nearest_points
from utils import (
    get_distance,
    get_features_with_cells,
    get_linestring_length,
    get_seconds_elapsed,
    load_matchable_set,
)


def get_feature_id_to_connected_features(
    features_overture: Iterable[MatchableFeature],
) -> dict[str, Iterable[MatchableFeature]]:
    """returns a connected roads "graph" as a dictionary of feature id to features that are connected to it, as modeled in overture schema via connector_ids property"""
    connector_id_to_features = {}
    for feature in features_overture:
        for connector_id in feature.get_connector_ids():
            if connector_id not in connector_id_to_features:
                connector_id_to_features[connector_id] = []
            connector_id_to_features[connector_id].append(feature)

    feature_id_to_connected_features = {}
    for feature in features_overture:
        feature_id_to_connected_features[feature.id] = []
        for connector_id in feature.get_connector_ids():
            for other_feature in connector_id_to_features[connector_id]:
                if other_feature.id != feature.id:
                    feature_id_to_connected_features[feature.id].append(other_feature)
    return feature_id_to_connected_features


def read_predictions(predictions_file: str):
    """reads snap predictions from tab separated file with columns: trace_id, point_index, gers_id, score"""
    p = {}
    with open(predictions_file) as file:
        reader = csv.reader(file, delimiter=constants.COLUMN_SEPARATOR)
        for row in reader:
            try:
                trace_id = row[0]
                point_index = int(row[1])
                gers_id = row[3]
                if trace_id not in p:
                    p[trace_id] = {}
                p[trace_id][point_index] = gers_id
            except ValueError:
                continue  # header or invalid line
    return p


def calculate_error_rate(
    labeled_file: str,
    target_features_by_id: dict[str, Iterable[MatchableFeature]],
    match_results: Iterable[TraceMatchResult],
):
    """returns total error rate from a labeled file and a list of trace match results"""
    if not (os.path.exists(labeled_file)):
        print(f"no metrics to compute (file {labeled_file} does not exist)")
        return

    labels = read_predictions(labeled_file)
    total_correct_distance = 0
    total_incorrect_distance = 0
    with open(labeled_file + ".actual.txt", "w") as f:
        f.write(
            constants.COLUMN_SEPARATOR.join(
                [
                    "trace_id",
                    "point_index",
                    "label_gers_id",
                    "prediction_gers_id",
                    "label_snapped_wkt",
                    "prediction_snapped_wkt",
                    "distance_to_prev_point",
                    "is_correct",
                ]
            )
            + "\n"
        )
        for trace_match_result in match_results:
            if trace_match_result.id not in labels:
                continue

            correct_distance = 0
            incorrect_distance = 0
            prev_point = None

            for point in trace_match_result.points:
                if point.index not in labels[trace_match_result.id]:
                    print(
                        f"no label for trace_id={trace_match_result.id} point_index={point.index}"
                    )
                    break

                label_gers_id = labels[trace_match_result.id][point.index]
                dist_to_prev_point = 0
                is_correct = point.best_prediction is not None and (
                    str(point.best_prediction.id) == label_gers_id
                )
                if prev_point is not None:
                    dist_to_prev_point = get_distance(prev_point, point.original_point)
                    correct_distance += dist_to_prev_point
                    if not is_correct:
                        # in the original paper error metric is defined as: (added incorrect route distance + removed correct route distance) / total correct route distance
                        # but since it's difficult to label the correct route distance (would need to have a reliable routing engine to correctly calculate it)
                        # we'll just use the distance between the original route's points
                        # side effect is that start/end points and stopped points that usually have more gps noise will be penalized more than the route distance approach would -
                        # but that may be preferable to overweigh the more problematic/difficult points
                        incorrect_distance += dist_to_prev_point

                label_snapped_point = None
                if label_gers_id not in target_features_by_id:
                    print(f"no target feature for label_gers_id={label_gers_id}")
                else:
                    label_shape = target_features_by_id[label_gers_id].geometry
                    x, label_snapped_point = nearest_points(
                        point.original_point, label_shape
                    )

                columns = [
                    str(trace_match_result.id),
                    str(point.index),
                    str(label_gers_id),
                    str(point.best_prediction.id)
                    if point.best_prediction is not None
                    else "",
                    label_snapped_point.wkt if label_snapped_point is not None else "",
                    point.best_prediction.snapped_point.wkt
                    if point.best_prediction is not None
                    else "",
                    str(dist_to_prev_point),
                    str(is_correct),
                ]
                f.write(constants.COLUMN_SEPARATOR.join(columns) + "\n")

                prev_point = point.original_point

            trace_error_rate = incorrect_distance / correct_distance
            print(
                rf"trace_id={trace_match_result.id} trace_error_rate={trace_error_rate:.2f} correct_distance={correct_distance:.2f} incorrect_distance={incorrect_distance:.2f}"
            )
            total_correct_distance += correct_distance
            total_incorrect_distance += incorrect_distance

    if total_correct_distance == 0:
        print("no correct distance")
        return -1

    total_error_rate = total_incorrect_distance / total_correct_distance
    print(
        rf"total_error_rate={total_error_rate:.2f} total_correct_distance={total_correct_distance:.2f} total_incorrect_distance={total_incorrect_distance:.2f}"
    )
    return total_error_rate


def output_trace_snap_results(
    match_results: Iterable[TraceMatchResult],
    output_file_name: str,
    output_for_judgment: bool = False,
):
    results_json = list(
        map(
            lambda x: x.to_json(diagnostic_mode=False, include_all_predictions=False),
            match_results,
        )
    )
    with open(output_file_name, "w") as f:
        json.dump(results_json, f, indent=4)

    results_json = list(
        map(
            lambda x: x.to_json(diagnostic_mode=True, include_all_predictions=False),
            match_results,
        )
    )
    with open(output_file_name + ".with_diagnostics.json", "w") as f:
        json.dump(results_json, f, indent=4)

    results_json = list(
        map(
            lambda x: x.to_json(diagnostic_mode=True, include_all_predictions=True),
            match_results,
        )
    )
    with open(output_file_name + ".with_diagnostics-all-predictions.json", "w") as f:
        json.dump(results_json, f, indent=4)

    if output_for_judgment:
        with open(output_file_name + ".for_judgment.txt", "w") as f:
            f.write(
                constants.COLUMN_SEPARATOR.join(
                    ["trace_id", "point_index", "trace_point_wkt", "gers_id"]
                )
                + "\n"
            )
            for r in match_results:
                for idx, p in enumerate(r.points):
                    columns = [
                        str(r.id),
                        str(idx),
                        p.original_point.wkt,
                        str(p.best_prediction.id)
                        if p.best_prediction is not None
                        else "",
                    ]
                    f.write(constants.COLUMN_SEPARATOR.join(columns) + "\n")

        with open(output_file_name + ".snapped_points.txt", "w") as f:
            f.write(
                constants.COLUMN_SEPARATOR.join(
                    ["trace_id", "point_index", "gers_id", "snapped_point_wkt"]
                )
                + "\n"
            )
            for r in match_results:
                for idx, p in enumerate(r.points):
                    columns = [
                        str(r.id),
                        str(idx),
                        str(p.best_prediction.id)
                        if p.best_prediction is not None
                        else "",
                        p.best_prediction.snapped_point.wkt
                        if p.best_prediction is not None
                        else "",
                    ]
                    f.write(constants.COLUMN_SEPARATOR.join(columns) + "\n")

    with open(output_file_name + ".auto_metrics.txt", "w") as f:
        header = [
            "id",
            "source_length",
            "route_length",
            "points",
            "points_with_match",
            "percent_points_with_match",
            "target_candidates_count",
            "matched_target_ids_count",
            "avg_dist_to_road",
            "sequence_breaks",
            "revisited_via_points",
            "revisited_segments",
            "elapsed",
            "source_wkt",
        ]
        f.write(constants.COLUMN_SEPARATOR.join(header) + "\n")
        for r in match_results:
            columns = [
                str(r.id),
                str(r.source_length),
                str(r.route_length),
                str(len(r.points)),
                str(r.points_with_matches),
                rf"{(100 * r.points_with_matches / len(r.points)):.2f}",
                str(r.target_candidates_count),
                str(len(r.matched_target_ids)),
                str(r.avg_dist_to_road),
                str(r.sequence_breaks),
                str(r.revisited_via_points),
                str(r.revisited_segments),
                str(r.elapsed),
                str(r.source_wkt),
            ]
            f.write(constants.COLUMN_SEPARATOR.join(columns) + "\n")


def set_best_path_predictions(points: Iterable[PointSnapInfo]):
    """Sets the best prediction for each point in the sequence, starting from the end and going backwards following the best_prev_prediction chain"""

    last_point = points[-1]
    if (
        last_point.predictions is None
        or len(last_point.predictions) == 0
        or last_point.predictions[0].best_log_prob == 0
    ):
        return  # no path found

    last_point.best_prediction = last_point.predictions[
        0
    ]  # this is sorted descending by probability, so the first one is the best
    for idx in range(len(points) - 2, -1, -1):
        if points[idx + 1].best_prediction is not None:
            points[idx].best_prediction = points[
                idx + 1
            ].best_prediction.best_prev_prediction
        else:
            if not (points[idx].ignore) and len(points[idx].predictions) > 0:
                points[idx].best_prediction = points[idx].predictions[0]


def extend_sequence(
    steps: Iterable[RouteStep], prev_prediction: SnappedPointPrediction
):
    """Extends the sequence of the traveled segments up to the previous point with the new steps; also returns the number of revisited segments and via points"""
    revisited_via_points_count = 0
    revisited_segments_count = 0
    extended_sequence = (
        prev_prediction.best_sequence.copy()
        if prev_prediction.best_sequence is not None
        else []
    )
    revisited_segments_count = 0
    added_via_points = []
    for step in steps:
        if (
            len(extended_sequence) == 0 or step.feature.id != extended_sequence[-1]
        ):  # either first step or new feature
            if (
                len(extended_sequence) > 0 and step.feature.id in extended_sequence
            ):  # different than prev segment but present in the sequence, so we are revisiting it
                revisited_segments_count += 1
            extended_sequence.append(step.feature.id)
        if step.via_point is not None:
            added_via_points.append(step.via_point.wkt)

    if len(added_via_points) > 0:
        all_prev_via_points = set()
        p = prev_prediction
        while p is not None:
            if p.best_route_via_points is not None:
                for vp in p.best_route_via_points:
                    all_prev_via_points.add(vp)
                    if len(all_prev_via_points) > 100:
                        break  # optimization for very long traces, don't need to check all of them, just the recent ones
            p = p.best_prev_prediction

        for added_via_point in added_via_points:
            if added_via_point in all_prev_via_points:
                revisited_via_points_count += 1
    return (extended_sequence, revisited_segments_count, revisited_via_points_count)


def get_trace_matches(
    source_feature: MatchableFeature,
    target_candidates: Iterable[MatchableFeature],
    options: TraceSnapOptions,
) -> TraceMatchResult:
    """Matches a `source_feature` trace to most likely traveled `targe_candidates` road segments"""
    start = timer()

    feature_id_to_connected_features = get_feature_id_to_connected_features(
        target_candidates
    )

    filter_feature_ids = set(map(lambda x: x.id, target_candidates))

    times = source_feature.properties.get("times")
    points = []
    prev_point = None
    sequence_breaks = 0
    for idx, coord in enumerate(source_feature.geometry.coords):
        original_point = Point(coord[0], coord[1])
        predictions = []

        for target_feature in target_candidates:
            op, snapped_point = nearest_points(original_point, target_feature.geometry)
            distance_to_road = get_distance(original_point, snapped_point)
            if distance_to_road > options.max_point_to_road_distance:
                continue

            emission_prob = (
                (1 / (math.sqrt(2 * math.pi) * options.sigma))
                * math.exp(-0.5 * ((distance_to_road / options.sigma) ** 2))
            )  # measurement probability - if was on this road how likely is it to have measured the point at this distance
            best_log_prob = None
            best_transition_prob = None
            best_prev_prediction = None
            best_route_dist_from_prev_point = None
            best_sequence = None
            best_route_via_points = None
            best_revisited_via_points_count = 0
            best_revisited_segments_count = 0
            trace_dist_from_prev_point = 0
            # calculate transition probability from all prev point matches to current match candidate target_feature
            if prev_point is None:
                best_log_prob = math.log(emission_prob)
                best_transition_prob = 1
                best_sequence = [target_feature.id]
            else:
                trace_dist_from_prev_point = get_distance(
                    original_point, prev_point.original_point
                )
                for prev_prediction in prev_point.predictions:
                    if (
                        not (options.allow_loops)
                        and prev_prediction.best_sequence is not None
                        and target_feature.id in prev_prediction.best_sequence
                        and prev_prediction.referenced_feature.id != target_feature.id
                    ):
                        # already part of best sequence, but then moved to a different segment, so this is not a good candidate, it means this would walk back on itself
                        continue

                    route = get_shortest_route(
                        target_candidates,
                        feature_id_to_connected_features,
                        prev_prediction.referenced_feature,
                        target_feature,
                        prev_prediction.snapped_point,
                        snapped_point,
                        filter_feature_ids,
                        [] if options.allow_loops else prev_prediction.best_sequence,
                    )
                    # check distance is not float('inf')
                    if route is None or route.distance == float("inf"):
                        # couldn't find path, skip this prev_match as impossible to transition from it to this match
                        continue

                    dist_diff = abs(trace_dist_from_prev_point - route.distance)

                    transition_prob = (1 / options.beta) * math.exp(
                        -dist_diff / options.beta
                    )

                    (
                        extended_sequence,
                        revisited_segments_count,
                        revisited_via_points_count,
                    ) = extend_sequence(route.steps, prev_prediction)
                    transition_prob *= math.exp(
                        -revisited_via_points_count
                        * options.revisit_via_point_penalty_weight
                    )  # todo: what's the right way to penalize revisiting via points?
                    transition_prob *= math.exp(
                        -revisited_segments_count
                        * options.revisit_segment_penalty_weight
                    )  # todo: what's the right way to penalize revisiting segments?

                    if (
                        dist_diff > options.max_route_to_trace_distance_difference
                        or transition_prob <= 0
                    ):
                        continue
                    # match_prob = prev_prediction.best_prob * emission_prob * transition_prob
                    # probabilities multiplied over many points go to zero (floating point underflow), so use log of product is sum of logs
                    match_log_prob = (
                        prev_prediction.best_log_prob
                        + math.log(emission_prob)
                        + math.log(transition_prob)
                    )
                    # print(f'point#{idx} prev_prediction={prev_prediction.id} transition_prob={transition_prob} emission_prob={emission_prob} match_prob={match_prob} route_dist_from_prev_point={route_dist_from_prev_point} trace_dist_from_prev_point={trace_dist_from_prev_point} dist_diff={dist_diff}')
                    if best_log_prob is None or match_log_prob > best_log_prob:
                        best_log_prob = match_log_prob
                        best_transition_prob = transition_prob
                        best_prev_prediction = prev_prediction
                        best_route_dist_from_prev_point = route.distance
                        best_sequence = extended_sequence
                        best_route_via_points = []
                        best_revisited_via_points_count = revisited_via_points_count
                        best_revisited_segments_count = revisited_segments_count
                        for step in route.steps:
                            if step.via_point is not None:
                                best_route_via_points.append(step.via_point.wkt)
                            # todo: also include the intermediate features in route.path

            if best_log_prob is None:
                continue  # couldn't find a path to this point, skip it
            # print(f'point#{idx} candidate feature={target_feature.id} best_log_prob={best_log_prob} best_prev_point={best_prev_prediction.id if best_prev_prediction is not None else None} best_transition_prob={best_transition_prob} emission_prob={emission_prob} distance_to_road={distance_to_road}')
            prediction = SnappedPointPrediction(
                target_feature.id,
                snapped_point,
                target_feature,
                distance_to_road,
                best_route_dist_from_prev_point,
                emission_prob,
                best_transition_prob,
                best_log_prob,
                best_prev_prediction,
                best_sequence,
                best_route_via_points,
                best_revisited_via_points_count,
                best_revisited_segments_count,
            )

            predictions.append(prediction)

        predictions.sort(key=lambda x: x.best_log_prob, reverse=True)
        time_since_prev_point = (
            None
            if times is None or prev_point is None
            else get_seconds_elapsed(times[prev_point.index], times[idx])
        )
        time = None if times is None else times[idx]
        point = PointSnapInfo(
            idx, original_point, time, time_since_prev_point, predictions
        )
        points.append(point)

        if len(predictions) > 0:
            prev_point = (
                point  # don't update prev_point unless it has at least one prediction
            )
        else:
            # no predictions for this point, so ignore current point and previous point to attempt to recover sequence;
            # if gap between current point and prev_point is too big, abandon the prev_point and reset;
            # this will happen when there is no road in the target map to match the trace
            point.ignore = True
            if prev_point is not None:
                prev_point.ignore = True
                if prev_point.index > 0:
                    prev_point = points[prev_point.index - 1]
                    # gap with no candidates too big if 60seconds or 200m since last point
                    if (
                        (
                            time_since_prev_point is not None
                            and time_since_prev_point
                            > options.broken_time_gap_reset_sequence
                        )
                        or trace_dist_from_prev_point
                        > options.broken_distance_gap_reset_sequence
                    ):
                        # print(rf"#{str(idx)}: sequence break; time_since_prev_point={time_since_prev_point} trace_dist_from_prev_point={trace_dist_from_prev_point}")
                        # we have a sequence break, reset prev point, new sequence will start from next point
                        sequence_breaks += 1
                        prev_point = None
                else:
                    prev_point = None

    set_best_path_predictions(points)

    end = timer()
    elapsed = end - start
    source_feature_length = get_linestring_length(source_feature.geometry)
    t = TraceMatchResult(
        source_feature.id,
        source_feature.geometry.wkt,
        points,
        source_feature_length,
        len(target_candidates),
        elapsed=elapsed,
        sequence_breaks=sequence_breaks,
    )
    set_trace_match_metrics(t)
    return t


def set_trace_match_metrics(t: TraceMatchResult) -> None:
    matched_target_ids = set()
    route_length = 0
    dist_to_road = 0
    revisited_via_points = 0
    revisited_segments = 0
    points_with_matches = 0
    for point in t.points:
        if (
            point.best_prediction is not None
            and point.best_prediction.referenced_feature is not None
        ):
            points_with_matches += 1
            route_length += (
                point.best_prediction.route_distance_to_prev_point
                if point.best_prediction.route_distance_to_prev_point is not None
                else 0
            )
            dist_to_road += point.best_prediction.distance_to_snapped_road
            revisited_via_points += (
                point.best_prediction.best_revisited_via_points_count
            )
            revisited_segments += point.best_prediction.best_revisited_segments_count
            matched_target_ids.add(point.best_prediction.referenced_feature.id)
    t.matched_target_ids = list(matched_target_ids)
    t.points_with_matches = points_with_matches
    t.route_length = round(route_length, 2)
    t.avg_dist_to_road = (
        round(dist_to_road / points_with_matches, 2)
        if points_with_matches > 0
        else None
    )
    t.revisited_via_points = revisited_via_points
    t.revisited_segments = revisited_segments


def print_stats(
    source_features: Iterable[MatchableFeature],
    target_features: Iterable[MatchableFeature],
    match_results: Iterable[TraceMatchResult],
    total_elapsed: float,
    avg_runtime_per_feature: float,
):
    num_traces = len(source_features)
    total_route_length = sum([r.route_length for r in match_results]) / 1000  # in km
    total_traces_length = sum([r.source_length for r in match_results]) / 1000  # in km
    total_candidates = sum([r.target_candidates_count for r in match_results])
    total_matches = sum([len(r.matched_target_ids) for r in match_results])
    total_sequence_breaks = sum([r.sequence_breaks for r in match_results])
    total_revisited_via_points = sum([r.revisited_via_points for r in match_results])
    total_revisited_segments = sum([r.revisited_segments for r in match_results])
    total_traces_with_matches = sum(
        [1 for r in match_results if r.points_with_matches > 0]
    )
    total_avg_dist_to_road = sum(
        [r.avg_dist_to_road for r in match_results if r.points_with_matches > 0]
    )
    avg_runtime_per_km = (
        total_elapsed / total_traces_length if total_traces_length > 0 else None
    )
    avg_dist_to_road = (
        round(total_avg_dist_to_road / total_traces_with_matches, 2)
        if total_traces_with_matches > 0
        else None
    )

    print("==================================================================")
    print("Totals:")
    print("==================================================================")
    print(rf"Traces.............................{num_traces}")
    print(rf"Target features....................{len(target_features)}")
    print(
        rf"Elapsed:...........................{round(total_elapsed // 60)}min {total_elapsed % 60:.3f}s"
    )
    print(rf"Avg runtime/trace..................{avg_runtime_per_feature:.3f}s")
    print(rf"Avg runtime/km.....................{avg_runtime_per_km:.3f}s")
    print(rf"Avg distance to snapped road.......{avg_dist_to_road}m")
    print(rf"Snapped route length...............{total_route_length:.2f}km")
    print(rf"GPS traces length..................{total_traces_length:.2f}km")
    print(
        rf"Snapped route len/gps len..........{(total_route_length / total_traces_length):.2f}"
    )
    print(
        rf"Avg number of candidate segments...{(total_candidates / num_traces):.2f}/trace, {(total_candidates / total_traces_length):.2f}/km"
    )
    print(
        rf"Avg number of matched segments.....{(total_matches / num_traces):.2f}/trace, {(total_matches / total_traces_length):.2f}/km"
    )
    print(
        rf"Avg number of sequence breaks......{(total_sequence_breaks / num_traces):.2f}/trace, {(total_sequence_breaks / total_traces_length):.2f}/km"
    )
    print(
        rf"Avg number of revisited via points.{(total_revisited_via_points / num_traces):.2f}/trace, {(total_revisited_via_points / total_traces_length):.2f}/km"
    )
    print(
        rf"Avg number of revisited segments...{(total_revisited_segments / num_traces):.2f}/trace, {(total_revisited_segments / total_traces_length):.2f}/km"
    )
    print("==================================================================")


def snap_traces(
    features_to_match_file: str,
    overture_file: str,
    output_file: str,
    res: int,
    snap_options: TraceSnapOptions = None,
    output_for_judgment: bool = False,
) -> None:
    if snap_options is None:
        snap_options = TraceSnapOptions()  # loads default options

    # save the options we used next to the output file for debugging or comparison with other runs
    with open(output_file + ".options.json", "w") as f:
        json.dump(snap_options.__dict__, f, indent=4)

    start = timer()
    print("Loading features...")
    to_match_prop_filter = {}
    # to_match_prop_filter["id"] = "manual_trace#4"
    to_match = load_matchable_set(features_to_match_file, is_multiline=False, res=res)
    features_to_match = to_match.features_by_id.values()
    if len(features_to_match) == 0:
        print("no features to match")
        exit()

    overture = load_matchable_set(
        overture_file, is_multiline=True, properties_filter={"type": "segment"}, res=res
    )
    features_overture = overture.features_by_id.values()
    print("Features to match: " + str(len(features_to_match)))
    print("Features Overture: " + str(len(features_overture)))
    end = timer()
    print(f"Loading time: {(end - start):.2f}s")

    i = 0
    match_results = []
    total_elapsed = 0
    for source_feature in features_to_match:
        i += 1

        target_candidates = get_features_with_cells(
            overture.features_by_cell, to_match.cells_by_id[source_feature.id]
        )
        match_res = get_trace_matches(source_feature, target_candidates, snap_options)
        match_results.append(match_res)

        total_elapsed += match_res.elapsed
        avg_runtime_per_feature = total_elapsed / i

        if i % 1 == 0:
            print(
                rf"trace#{str(i)} length={match_res.source_length} route_length={round(match_res.route_length)} "
                + rf"points={len(source_feature.geometry.coords)} points_w_matches={match_res.points_with_matches} "
                + rf"candidates={match_res.target_candidates_count} matched target_ids: {str(len(match_res.matched_target_ids))} "
                + rf"elapsed: {match_res.elapsed:.2f}s; avg runtime/feature: {avg_runtime_per_feature:.3f}s"
            )

    print_stats(
        features_to_match,
        features_overture,
        match_results,
        total_elapsed,
        avg_runtime_per_feature,
    )

    print("Writing results...")
    start = timer()
    output_trace_snap_results(match_results, output_file, output_for_judgment)
    end = timer()
    print(f"Writing time: {(end - start):.2f}s")
    calculate_error_rate(
        features_to_match_file.replace(".geojson", ".labeled.txt"),
        overture.features_by_id,
        match_results,
    )


def get_args():
    parser = argparse.ArgumentParser(
        description="",
        add_help=True,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-to-match",
        help="Input file containing features to match in geojson format",
        required=True,
    )
    parser.add_argument(
        "--input-overture",
        help="Input file containing overture features",
        required=True,
    )
    parser.add_argument(
        "--output", help="Output file containing match results", required=True
    )
    parser.add_argument(
        "--resolution",
        help="H3 cell resolution used to pre-filter candidates",
        type=int,
        default=constants.DEFAULT_H3_RESOLUTION,
        choices=range(0, 15),
    )
    parser.add_argument(
        "--sigma",
        type=float,
        help="Sigma param - controlling tolerance to GPS noise",
        required=False,
        default=constants.DEFAULT_SIGMA,
    )
    parser.add_argument(
        "--beta",
        type=float,
        help="Beta param - controlling confidence in route",
        required=False,
        default=constants.DEFAULT_BETA,
    )
    parser.add_argument(
        "--allow_loops",
        type=bool,
        help="Allow same sequence to revisit same segment with other segment(s) in between",
        required=False,
        default=constants.DEFAULT_ALLOW_LOOPS,
    )
    parser.add_argument(
        "--max_point_to_road_distance",
        type=float,
        help="Maximum distance in meters between a trace point and a match candidate road",
        required=False,
        default=constants.DEFAULT_MAX_POINT_TO_ROAD_DISTANCE,
    )
    parser.add_argument(
        "--max_route_to_trace_distance_difference",
        type=float,
        help="Maximum difference between route and trace lengths in meters",
        required=False,
        default=constants.DEFAULT_MAX_ROUTE_TO_TRACE_DISTANCE_DIFFERENCE,
    )
    parser.add_argument(
        "--revisit_segment_penalty_weight",
        type=float,
        help="How much to penalize a route with one segment revisit",
        required=False,
        default=constants.DEFAULT_SEGMENT_REVISIT_PENALTY,
    )
    parser.add_argument(
        "--revisit_via_point_penalty_weight",
        type=float,
        help="How much to penalize a route with one via-point revisit",
        required=False,
        default=constants.DEFAULT_VIA_POINT_PENALTY_WEIGHT,
    )
    parser.add_argument(
        "--broken_time_gap_reset_sequence",
        type=float,
        help="How big the time gap in seconds between points without valid route options before we consider it a broken sequence",
        required=False,
        default=constants.DEFAULT_BROKEN_TIME_GAP_RESET_SEQUENCE,
    )
    parser.add_argument(
        "--broken_distance_gap_reset_sequence",
        type=float,
        help="How big the distance gap in meters between points without valid route options before we consider it a broken sequence",
        required=False,
        default=constants.DEFAULT_BROKEN_DISTANCE_GAP_RESET_SEQUENCE,
    )
    parser.add_argument(
        "--j",
        action="store_true",
        help="Also output the matches as a 'pre-labeled' file for judgment",
        default=False,
        required=False,
    )
    return parser.parse_args()


def get_trace_snap_options_from_args(args):
    return TraceSnapOptions(
        sigma=args.sigma,
        beta=args.beta,
        allow_loops=args.allow_loops,
        max_point_to_road_distance=args.max_point_to_road_distance,
        max_route_to_trace_distance_difference=args.max_route_to_trace_distance_difference,
        revisit_segment_penalty_weight=args.revisit_segment_penalty_weight,
        revisit_via_point_penalty_weight=args.revisit_via_point_penalty_weight,
        broken_time_gap_reset_sequence=args.broken_time_gap_reset_sequence,
        broken_distance_gap_reset_sequence=args.broken_distance_gap_reset_sequence,
    )


if __name__ == "__main__":
    args = get_args()
    trace_snap_options = get_trace_snap_options_from_args(args)
    snap_traces(
        args.input_to_match,
        args.input_overture,
        args.output,
        args.resolution,
        trace_snap_options,
        output_for_judgment=args.j,
    )
