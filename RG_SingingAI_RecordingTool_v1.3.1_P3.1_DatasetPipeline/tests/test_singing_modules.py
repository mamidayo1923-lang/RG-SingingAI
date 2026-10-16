import unittest
from recording_tool.singing.alignment import align_labels_to_midi

class AlignmentTests(unittest.TestCase):
    def test_draft_alignment_flags_estimates(self):
        out=align_labels_to_midi([{"label":"k"},{"label":"a"},{"label":"N"}],
                                 [{"start":0,"end":0.5,"pitch":60},{"start":0.5,"end":1.0,"pitch":62}],duration_s=1.0)
        self.assertTrue(out["needs_manual_review"])
        self.assertEqual(len(out["phonemes"]),3)
        self.assertAlmostEqual(out["phonemes"][-1]["end"],1.0)
    def test_supplied_boundaries(self):
        out=align_labels_to_midi([{"label":"a","start":0.1,"end":0.4}], [{"start":0,"end":1,"pitch":69}])
        self.assertFalse(out["needs_manual_review"])
        self.assertEqual(out["phonemes"][0]["midi_pitch"],69)
    def test_bad_note(self):
        with self.assertRaises(ValueError): align_labels_to_midi([{"label":"a"}],[{"start":1,"end":0,"pitch":60}])
if __name__=="__main__": unittest.main()
