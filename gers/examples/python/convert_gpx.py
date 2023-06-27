import os
import random
import gpxpy
import geojson
import constants
from shapely import Point
from utils import get_distance, get_seconds_elapsed

OUTPUT_FILENAME = os.path.join(constants.DATA_DIR, "macon-osm-traces-combined.geojson")
MIN_DIST_GAP_TO_SPLIT_TRACES = 300.0 # meters
MIN_DIST_GAP_BETWEEN_POINTS = 50 # meters
MIN_TIME_GAP_BETWEEN_POINTS = 1 # seconds
MAX_POINTS_PER_TRACE = 100 
MAX_TRACES = 100

def get_point(p):
    return Point(p.longitude, p.latitude)

def gpx_to_geojson(gpx):
    return geojson.LineString([(p.longitude, p.latitude) for p in gpx.tracks[0].segments[0].points])    

def add_feature(filename, track, track_no, seg_no, split_no, points, times, features):
    if len(points) < 10 or random.random() < 0.75:
        return # ignore traces with too few points and random ones
    
    id = "trace#" + str(len(features))
    properties = {
        "filename": filename,
        "track.number": track_no,
        "track.link": track.link,
        "track.name": track.name,
        #"description": gpx.description,
        #"creator": gpx.creator,
        "track.segment.number": seg_no,
        "track.segment.split.number": split_no,
        "track.description": track.description,
        "times": times
    }
    feature = geojson.Feature(id, geojson.LineString(points), properties)           
    features.append(feature)

def gpx_to_geojson_geojson_features(raw_traces_download_dir):
    features = []
    for filename in os.listdir(raw_traces_download_dir):
        print(f"processing {filename}")
        with open(os.path.join(raw_traces_download_dir, filename), "r") as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            track_no = 0
            for track in gpx.tracks:
                print(f"processing track {track_no}")
                seg_no = 0
                for segment in track.segments:
                    print(f"processing segment {seg_no}")
                    points = []
                    times = []
                    split_no = 0
                    prev_point = None
                    for point in segment.points:
                        if not(point.time is None):
                            if not prev_point is None:
                                seconds_since_prev_point = get_seconds_elapsed(str(prev_point.time), str(point.time))
                                if seconds_since_prev_point < MIN_TIME_GAP_BETWEEN_POINTS:
                                    continue # ignore points that are too close to each other time-wise, they won"t produce useful speed data                            
                                dist_to_prev = get_distance(get_point(prev_point), get_point(point))
                                if dist_to_prev < MIN_DIST_GAP_BETWEEN_POINTS:
                                    continue # ignore points that are too close to each other distance-wise

                                if dist_to_prev > MIN_DIST_GAP_TO_SPLIT_TRACES or len(points) > MAX_POINTS_PER_TRACE:
                                    #print(f"gap too big: {dist_to_prev:.2f} meters, splitting trace")
                                    add_feature(filename, track, track_no, seg_no, split_no, points, times, features)                                    
                                    points = []
                                    times = []                                
                                    split_no += 1
                            points.append((point.longitude, point.latitude))
                            times.append(str(point.time))
                            prev_point = point
                    add_feature(filename, track, track_no, seg_no, split_no, points, times, features)
                    if len(features) >= MAX_TRACES:
                        break
                    seg_no += 1
                track_no += 1
    return features

if __name__ == "__main__":
    features = gpx_to_geojson_geojson_features(constants.RAW_TRACES_DOWNLOAD_DIR)
    feature_collection = geojson.FeatureCollection(features)
    with open(OUTPUT_FILENAME, "w") as output_file:
        geojson.dump(feature_collection, output_file)
