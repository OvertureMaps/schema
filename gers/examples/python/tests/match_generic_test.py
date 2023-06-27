import test_setup
import os
import json
import unittest
import constants
from match_classes import TraceSnapOptions
from match_generic import get_matches
from utils import load_matchable_set, get_features_with_cells

class TestMatchGeneric(unittest.TestCase):

    def test_match_lines(self):
        features_to_match_file = os.path.join(constants.DATA_DIR, "macon-line-segments.csv")
        overture_file = os.path.join(constants.DATA_DIR, "overture-transportation-macon.geojson")
        res = 12

        to_match = load_matchable_set(features_to_match_file, res=res)
        self.assertIsNotNone(to_match)
        self.assertEqual(len(to_match.features_by_id), 4)

        id_to_match = "ID100D"
        self.assertIn(id_to_match, to_match.features_by_id)
        source_feature = to_match.features_by_id[id_to_match]

        overture = load_matchable_set(overture_file, is_multiline=True, properties_filter = {"type": "segment"}, res=res)
        self.assertIsNotNone(overture.features_by_id)
        self.assertGreater(len(overture.features_by_id), 20000)

        target_candidates = get_features_with_cells(overture.features_by_cell, to_match.cells_by_id[source_feature.id])
        self.assertIsNotNone(target_candidates)
        self.assertGreater(len(target_candidates), 30)
        
        match_res = get_matches(source_feature, target_candidates, buffer=0.0001, min_buffered_overlap_ratio=0.3)
        self.assertIsNotNone(match_res)
        self.assertIsNotNone(match_res.matched_features)
        self.assertGreater(len(match_res.matched_features), 30)

        json_res = match_res.to_json()
        self.assertIsNotNone(json_res)
        j = json.dumps(json_res, indent=4)

        for p in match_res.matched_features:
            self.assertIsNotNone(p.id)
            self.assertIsNotNone(p.matched_feature)
            self.assertIsNotNone(p.score)            
            if p.score > 0:
                self.assertIsNotNone(p.overlapping_geometry)
            if p.source_lr is not None:
                self.assertEqual(len(p.source_lr), 2)
            if p.candidate_lr is not None:
                self.assertEqual(len(p.candidate_lr), 2)

if __name__ == '__main__':
    unittest.main()