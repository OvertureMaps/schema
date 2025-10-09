import test_setup
import os
import json
import unittest
import constants
from match_classes import TraceSnapOptions
from match_traces import get_trace_matches
from utils import load_matchable_set, get_features_with_cells

class TestTraces(unittest.TestCase):

    def test_match_traces(self):
        features_to_match_file = os.path.join(constants.DATA_DIR, "macon-manual-traces.geojson")
        overture_file = os.path.join(constants.DATA_DIR, "overture-transportation-macon.geojson")
        res = 12

        to_match = load_matchable_set(features_to_match_file, is_multiline=False, res=res)
        self.assertIsNotNone(to_match)
        self.assertEqual(len(to_match.features_by_id), 4)

        id_to_match = "manual_trace#1"
        self.assertIn(id_to_match, to_match.features_by_id)
        source_feature = to_match.features_by_id[id_to_match]

        overture = load_matchable_set(overture_file, is_multiline=True, properties_filter = {"type": "segment"}, res=res)
        self.assertIsNotNone(overture.features_by_id)
        self.assertGreater(len(overture.features_by_id), 20000)

        options = TraceSnapOptions(max_point_to_road_distance=30)
        target_candidates = get_features_with_cells(overture.features_by_cell, to_match.cells_by_id[source_feature.id])
        match_res = get_trace_matches(source_feature, target_candidates, options)
        self.assertIsNotNone(match_res)
        self.assertIsNotNone(match_res.points)
        self.assertEqual(len(match_res.points), len(source_feature.geometry.coords))

        self.assertGreater(match_res.source_length, 5000)
        self.assertGreater(match_res.route_length, 5000)       

        json_res = match_res.to_json()
        self.assertIsNotNone(json_res)
        j = json.dumps(json_res, indent=4)

        for idx, p in enumerate(match_res.points):
            bp = p.best_prediction
            self.assertIsNotNone(bp, f"best prediction for point {idx} is None")
            self.assertIsNotNone(bp.id, f"best prediction for point {idx} has no id")
            self.assertGreater(bp.distance_to_snapped_road, 0.0)
            if idx > 0:
                self.assertGreater(bp.route_distance_to_prev_point, 0.0)

if __name__ == '__main__':
    unittest.main()