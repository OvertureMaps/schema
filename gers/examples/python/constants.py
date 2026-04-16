DEFAULT_H3_RESOLUTION = 12

# default params for nearest match
DEFAULT_NEAREST_MAX_DISTANCE = 100  # meters

# default params for trace snapping
DEFAULT_SIGMA = 4.1  # 4.10351310622546;
DEFAULT_BETA = 0.9  # 0.905918746744877 -> this default beta was found to apply to a 5 second sample rate.
# also was found to have good noise rejection characteristics and performed just as well or better than 1 second data, so it
# is now our default sampling period - even if the raw data was sampled at a higher rate
DEFAULT_MAX_POINT_TO_ROAD_DISTANCE = 10  # 200m in original paper
DEFAULT_MAX_ROUTE_TO_TRACE_DISTANCE_DIFFERENCE = (
    300  # what's a good value for this? 2km in original paper but too slow
)
DEFAULT_ALLOW_LOOPS = False
DEFAULT_SEGMENT_REVISIT_PENALTY = 100  # set to 0 if no penalty is desired
DEFAULT_VIA_POINT_PENALTY_WEIGHT = 100  # set to 0 if no penalty is desired
DEFAULT_BROKEN_TIME_GAP_RESET_SEQUENCE = 60  # seconds
DEFAULT_BROKEN_DISTANCE_GAP_RESET_SEQUENCE = 300  # meters

"""default column separator of text files"""
COLUMN_SEPARATOR = "\t"

DATA_DIR = "gers/examples/python/data"
