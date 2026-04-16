import csv
import json
from collections.abc import Iterable
from typing import Any

from dateutil import parser
from h3 import h3
from haversine import Unit, haversine
from match_classes import MatchableFeature, MatchableFeaturesSet

# from shapely.ops import transform
from shapely import wkt
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

# from pyproj import Geod


def get_seconds_elapsed(t1_str, t2_str):
    t1 = parser.parse(t1_str)
    t2 = parser.parse(t2_str)
    return (t2 - t1).total_seconds()


def get_linestring_length(ls):
    length = 0
    for i in range(len(ls.coords) - 1):
        lon1, lat1 = ls.coords[i]
        lon2, lat2 = ls.coords[i + 1]
        # _, _, d = geod.inv(lon1, lat1, lon2, lat2)
        d = haversine((lat1, lon1), (lat2, lon2), unit=Unit.METERS)
        length += d
    return round(length, 2)


def get_distance(point1, point2):
    # _, _, d = geod.inv(point1.x, point1.y, point2.x, point2.y)
    d = haversine((point1.y, point1.x), (point2.y, point2.x), unit=Unit.METERS)
    return round(d, 2)


def get_intersecting_h3_cells_for_line(coords, res):
    """for coordinates of a linestring, gets all h3 cells of given resolution that intersect the line"""
    cells = set()
    prevCell = None
    for coord in coords:
        cell = h3.geo_to_h3(coord[1], coord[0], res)
        cells.add(cell)
        if prevCell is None:
            prevCell = cell
        else:
            if prevCell != cell:
                # two consecutive coordinates in the linestring may be more than one cell apart
                # need to find intermediate cells between previous cell and the current one
                if not h3.h3_indexes_are_neighbors(prevCell, cell):
                    intermediateCells = h3.h3_line(prevCell, cell)
                    for intermediateCell in intermediateCells:
                        cells.add(intermediateCell)
                prevCell = cell
    return cells


def get_intersecting_h3_cells_for_geo_json(geometry: Any, res: int) -> Iterable[str]:
    """gets all h3 cells of given resolution that intersect the geometry."""
    # h3 api wants two floats for point, geojson dict for polygon and custom code is needed for line and multi* geometries
    geojson = mapping(geometry) if isinstance(geometry, BaseGeometry) else geometry
    geom_type = geojson["type"]
    coords = geojson["coordinates"]
    if geom_type.startswith("Multi"):
        sub_geom_type = geom_type.replace("Multi", "")
        sub_geoms = [
            {"type": sub_geom_type, "coordinates": sub_geom_coords}
            for sub_geom_coords in coords
        ]
        sub_cells = [
            sub_cell
            for sub_geom in sub_geoms
            for sub_cell in get_intersecting_h3_cells_for_geo_json(sub_geom, res)
        ]
        return set(sub_cells)
    if geom_type == "Point":
        return set([h3.geo_to_h3(coords[1], coords[0], res)])
    if geom_type == "LineString":
        return get_intersecting_h3_cells_for_line(coords, res)
    if geom_type == "Polygon":
        innerCells = h3.polyfill(
            geojson, res, True
        )  # this only covers the tiles whose centers are inside the polygon
        boundaryCells = get_intersecting_h3_cells_for_line(coords[0], res)
        return innerCells | boundaryCells


def matches_properties_filter(
    feature: dict[str, Any], properties_filter: dict[str, Any]
) -> bool:
    if properties_filter is None:
        return True
    feat_props = feature.get("properties")
    for prop in properties_filter:
        if prop == "id":
            return feature.get("id") == properties_filter[prop]

        if prop not in feat_props or (
            properties_filter[prop] != "*"
            and feat_props[prop] != properties_filter[prop]
        ):
            return False
    return True


def get_matchable_feature(feature_dict: dict[str, Any]) -> MatchableFeature:
    """creates a MatchableFeature from a dict with expected keys [id, geometry, properties], which could be either a geojson or parsed from a csv file with wkt geometry"""
    id = feature_dict.get("id")
    geom = feature_dict.get("geometry")
    if type(geom) is dict and "type" in geom and "coordinates" in geom:
        # if it"s a geojson feature
        s = shape(geom)
    elif isinstance(geom, str):
        # if it"s a wkt string
        s = wkt.loads(geom)
    props = feature_dict.get("properties")
    return MatchableFeature(id, s, props)


def get_feature_cells(geom: Any, res: int, k_rings_to_add: int = 1):
    """gets all h3 cells of given resolution that intersect the geometry, and also the cells that are k rings around the intersecting cells"""
    h3_cells = get_intersecting_h3_cells_for_geo_json(geom, res)
    if k_rings_to_add == 0:
        return list(h3_cells)

    rings = [h3.k_ring(h, k_rings_to_add) for h in h3_cells]
    return list(set(cell for r in rings for cell in r))


def parse_geojson(filename: str, is_multiline: bool) -> Iterable[dict[str, Any]]:
    with open(filename, errors="ignore") as file:
        if is_multiline:
            # text file with one geojson per line
            i = 0
            features = []
            for line in file:
                i += 1
                try:
                    geojson = json.loads(line.strip().rstrip(","))
                    features.append(geojson)
                except Exception as x:
                    print(rf"Line {i}: " + str(x))
            return features
        else:
            full_gj = json.loads(file.read())
            if full_gj.get("type") == "FeatureCollection":
                return full_gj.get("features")
            else:
                return [full_gj]


def get_matchable_set(
    features: Iterable[dict[str, Any]],
    properties_filter: dict = None,
    res: int = 12,
    limit_feature_count=-1,
) -> MatchableFeaturesSet:
    features_by_id = {}
    cells_by_id = {}
    features_by_cell = {}
    for feature_dict in features:
        try:
            if not matches_properties_filter(feature_dict, properties_filter):
                continue

            feature = get_matchable_feature(feature_dict)
            features_by_id[feature.id] = feature
            cells_by_id[feature.id] = get_feature_cells(feature.geometry, res)
            for cell in cells_by_id[feature.id]:
                if cell not in features_by_cell:
                    features_by_cell[cell] = []
                features_by_cell[cell].append(feature)
        except Exception as x:
            print(str(x))

        if limit_feature_count > 0 and len(features_by_id) >= limit_feature_count:
            break
    return MatchableFeaturesSet(features_by_id, cells_by_id, features_by_cell)


def parse_csv(filename: str, delimiter: str = ",") -> MatchableFeaturesSet:
    features = []
    i = 0
    with open(filename, errors="ignore") as file:
        reader = csv.DictReader(file, delimiter=delimiter)
        for row in reader:
            feat_dict = {}
            feat_dict["properties"] = {}
            for k, v in row.items():
                default_id = str(i)
                i += 1
                key = k.lower()
                if "id" not in feat_dict and "id" in key:
                    feat_dict["id"] = v
                elif "geometry" not in feat_dict and (
                    "geometry" in key or "wkt" in key
                ):
                    feat_dict["geometry"] = v
                else:
                    feat_dict["properties"][k] = v

            if "id" not in feat_dict:
                feat_dict["id"] = default_id

            if "geometry" not in feat_dict:
                if (
                    "lat" in feat_dict["properties"]
                    and "lon" in feat_dict["properties"]
                ):
                    feat_dict["geometry"] = (
                        f"POINT({feat_dict['properties']['lon']} {feat_dict['properties']['lat']})"
                    )
                else:
                    continue

            features.append(feat_dict)
    return features


def load_matchable_set(
    filename: str,
    properties_filter: dict = None,
    res: int = 12,
    limit_feature_count=-1,
    is_multiline: bool = False,
    delimiter: str = ",",
) -> MatchableFeaturesSet:
    """loads a MatchableFeaturesSet from a geojson or csv file"""
    extension = filename.split(".")[-1]
    match extension:
        case "geojson" | "json":
            features = parse_geojson(filename, is_multiline=is_multiline)
        case "csv":
            features = parse_csv(filename, delimiter=delimiter)
        case _:
            raise Exception(f"Unsupported file type: {extension}")

    s = get_matchable_set(features, properties_filter, res, limit_feature_count)
    return s


def get_features_with_cells(
    features_by_cell: dict[str, Iterable[MatchableFeature]], cells_filter: Iterable[str]
) -> Iterable[MatchableFeature]:
    """gets all features in `features_by_cell` that intersect any of the cells in `cells_filter`"""
    with_cells = []
    candidate_ids = set()
    for cell in cells_filter:
        if cell in features_by_cell:
            for candidate in features_by_cell[cell]:
                if candidate.id not in candidate_ids:
                    candidate_ids.add(candidate.id)
                    with_cells.append(candidate)
    return with_cells


def write_json(results_json: Any, output_file_name: str):
    with open(output_file_name, "w") as f:
        json.dump(results_json, f, indent=4)
