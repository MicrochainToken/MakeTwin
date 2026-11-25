import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from guide_schema import validate_guides


class GuideTests(unittest.TestCase):
    def guide(self):
        return dict(id='use', title='How to use', clip='how_to_use', initialState='assembled_off', steps=[dict(
            id='open', instruction='Open lid', startSeconds=0, actionEndSeconds=1, endSeconds=2,
            evidence=[dict(source='manual.pdf', locator='page 4, opening figure')], pauseAfter=True)])

    def test_valid_and_legacy(self):
        self.assertEqual(validate_guides([self.guide()], {'how_to_use':2}), [])
        self.assertEqual(validate_guides([], {}), [])

    def test_missing_clip_caption_evidence_and_invalid_range_fail(self):
        for key,value in [('instruction',''),('evidence',[]),('startSeconds',.5),
                          ('endSeconds',3),('actionEndSeconds',float('nan')),('pauseAfter','yes')]:
            g=self.guide();g['steps'][0][key]=value
            self.assertTrue(validate_guides([g], {'how_to_use':2}), key)
        self.assertTrue(validate_guides([self.guide()], {}))

    def test_duplicate_ids_fail(self):
        g=self.guide();self.assertTrue(validate_guides([g,copy.deepcopy(g)], {'how_to_use':2}))
