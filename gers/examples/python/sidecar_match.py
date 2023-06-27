import argparse
import constants
from constants import SidecarMatchType
from match_classes import TraceSnapOptions
from match_generic import match
from match_traces import snap_traces

def get_args():
    mode_parser = argparse.ArgumentParser(description="GERS demo matcher - matches a file with geospatial features to corresponding overture features from another file.",
                                          add_help=False,
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    mode_parser.add_argument("mode", help="Modality of matching", choices=[t.name for t in SidecarMatchType])

    mode_arg, remaining_args = mode_parser.parse_known_args()

    parser = argparse.ArgumentParser(parents=[mode_parser], add_help=True, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--input-to-match", help="Input file containing features to match in geojson format", required=True)
    parser.add_argument("--input-overture", help="Input file containing overture features", required=True)
    parser.add_argument("--output", help="Output file containing match results", required=True)
    parser.add_argument("--resolution", help="H3 cell resolution used to pre-filter candidates", type=int, default=constants.DEFAULT_H3_RESOLUTION, choices=range(0,15))

    match mode_arg.mode:
        case SidecarMatchType.MatchGeneric.name:
            parser.add_argument("--buffer", type=float, help="Buffer to use when matching", required=False, default=constants.DEFAULT_GENERIC_MATCH_BUFFER)
            parser.add_argument("--min_buffered_overlap_ratio", type=float, help="Buffer in meters to use when matching", required=False, default=constants.DEFAULT_GENERIC_MATCH_MIN_BUFFERED_OVERLAP_RATIO)
        case SidecarMatchType.Nearest.name:
            parser.add_argument("--nearest_max_distance", type=float, help="Maximum distance to the overture feature in meters", required=False, default=constants.DEFAULT_NEAREST_MAX_DISTANCE)
        case SidecarMatchType.SnapTraces.name:
            parser.add_argument("--sigma", type=float, help=f"Sigma param - controlling tolerance to GPS noise", required=False, default=constants.DEFAULT_SIGMA)
            parser.add_argument("--beta", type=float, help=f"Beta param - controlling confidence in route", required=False, default=constants.DEFAULT_BETA)
            parser.add_argument("--allow_loops", type=bool, help=f"Allow same sequence to revisit same segment with other segment(s) in between", required=False, default=constants.DEFAULT_ALLOW_LOOPS)
            parser.add_argument("--max_point_to_road_distance", type=float, help=f"{SidecarMatchType.SnapTraces}: Maximum distance in meters between a trace point and a match candidate road", required=False, default=constants.DEFAULT_MAX_POINT_TO_ROAD_DISTANCE)
            parser.add_argument("--max_route_to_trace_distance_difference", type=float, help=f"{SidecarMatchType.SnapTraces}: Maximum difference between route and trace lengths in meters", required=False, default=constants.DEFAULT_MAX_ROUTE_TO_TRACE_DISTANCE_DIFFERENCE)
            parser.add_argument("--revisit_segment_penalty_weight", type=float, help="How much to penalize a route with one segment revisit", required=False, default=constants.DEFAULT_SEGMENT_REVISIT_PENALTY)
            parser.add_argument("--revisit_via_point_penalty_weight", type=float, help="How much to penalize a route with one via-point revisit", required=False, default=constants.DEFAULT_VIA_POINT_PENALTY_WEIGHT)
            parser.add_argument("--broken_time_gap_reset_sequence", type=float, help="How big the time gap in seconds between points without valid route options before we consider it a broken sequence", required=False, default=constants.DEFAULT_BROKEN_TIME_GAP_RESET_SEQUENCE)
            parser.add_argument("--broken_distance_gap_reset_sequence", type=float, help="How big the distance gap in meters between points without valid route options before we consider it a broken sequence", required=False, default=constants.DEFAULT_BROKEN_DISTANCE_GAP_RESET_SEQUENCE)
            parser.add_argument("--j", help="Also output the matches as a 'pre-labeled' file for judgment", default=False, required=False)
    
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
        broken_distance_gap_reset_sequence=args.broken_distance_gap_reset_sequence)    

if __name__ == "__main__":
    args = get_args()
    mode = SidecarMatchType[args.mode]

    match mode:
        case SidecarMatchType.MatchGeneric:
            filter = {"type": "segment"} # todo: parametrize this filter
            match(args.input_to_match, args.input_overture, args.output, args.resolution, filter, args.buffer, args.min_buffered_overlap_ratio)
        case SidecarMatchType.SnapTraces:    
            trace_snap_options = get_trace_snap_options_from_args(args)
            snap_traces(args.input_to_match, args.input_overture, args.output, args.resolution, trace_snap_options, output_for_judgment=args.j)            
        case _:
            print("mode not supported: " + mode.name)