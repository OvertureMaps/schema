import os
import unittest

import constants
from shapely import LineString, Point
from utils import (
    get_distance,
    get_intersecting_h3_cells_for_geo_json,
    get_linestring_length,
    load_matchable_set,
)


class TestUtils(unittest.TestCase):
    def test_load_matchable_set_geojson(self):
        features_to_match_file = os.path.join(
            constants.DATA_DIR, "macon-manual-traces.geojson"
        )
        s = load_matchable_set(features_to_match_file, res=12, is_multiline=False)
        self.assertIsNotNone(s)
        self.assertEqual(len(s.features_by_id), 4)
        self.assertEqual(len(s.cells_by_id), 4)
        self.assertGreater(len(s.features_by_cell), 0)

    def test_get_distance(self):
        p1 = Point(-83.6878343, 32.8413587)
        p2 = Point(-83.6877941, 32.8413903)

        d = get_distance(p1, p2)
        self.assertAlmostEqual(d, 5.1, delta=0.1)

    def test_get_linestring_length(self):
        l = LineString([(-83.6878343, 32.8413587), (-83.6877941, 32.8413903)])

        d = get_linestring_length(l)
        self.assertAlmostEqual(d, 5.1, delta=0.1)

    def test_get_intersecting_h3_cells_for_geo_json(self):
        point = {"type": "Point", "coordinates": [-83.6197063, 32.8589311]}
        actual_cells = get_intersecting_h3_cells_for_geo_json(point, 10)
        expected_cells = ["8a44c0a32867fff"]
        self.assertCountEqual(actual_cells, expected_cells)

        line = {
            "type": "LineString",
            "coordinates": [
                [-83.61940200000001, 32.858034],
                [-83.61940200000001, 32.859538],
            ],
        }
        actual_cells = get_intersecting_h3_cells_for_geo_json(line, 10)
        expected_cells = ["8a44c0a3295ffff", "8a44c0a32867fff"]
        self.assertCountEqual(actual_cells, expected_cells)

        polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-83.6195695, 32.8591587],
                    [-83.6192584, 32.8583723],
                    [-83.619135, 32.8590437],
                    [-83.6195695, 32.8591587],
                ]
            ],
        }
        actual_cells = get_intersecting_h3_cells_for_geo_json(polygon, 10)
        expected_cells = ["8a44c0a32877fff", "8a44c0a32867fff", "8a44c0a3295ffff"]
        self.assertCountEqual(actual_cells, expected_cells)

        ml = {
            "type": "MultiLineString",
            "coordinates": [
                [[-83.61940200000001, 32.858034], [-83.61940200000001, 32.859538]],
                [[-83.6215878, 32.8580366], [-83.6202145, 32.8580546]],
            ],
        }
        actual_cells = get_intersecting_h3_cells_for_geo_json(ml, 10)
        expected_cells = [
            "8a44c0a3294ffff",
            "8a44c0a32867fff",
            "8a44c0a304b7fff",
            "8a44c0a3295ffff",
        ]
        self.assertCountEqual(actual_cells, expected_cells)
