import json, tempfile, unittest
from pathlib import Path
import numpy as np, soundfile as sf
from recording_tool.dataset_split import make_splits
from recording_tool.evaluation import pitch_metrics, onset_mae_ms
from recording_tool.analysis import extract_baseline_features

class P1Tests(unittest.TestCase):
    def test_group_split_has_no_leakage_and_is_deterministic(self):
        rows=[{"take_id":f"t{i}","group_id":f"g{i}"} for i in range(30)]
        a=make_splits(rows, seed=7); b=make_splits(rows, seed=7)
        self.assertEqual(a,b)
        groups={k:{r['group_id'] for r in v} for k,v in a['splits'].items()}
        self.assertFalse(groups['train'] & groups['validation'])
        self.assertFalse(groups['train'] & groups['test'])
        self.assertFalse(groups['validation'] & groups['test'])
    def test_split_rejects_missing_group(self):
        with self.assertRaises(ValueError): make_splits([{"take_id":"a"}])
    def test_split_requires_consistent_group_key(self):
        with self.assertRaises(ValueError): make_splits([{"take_id":"a","group_id":"g1"},{"take_id":"b","phrase_id":"p2"}])
    def test_pitch_metrics(self):
        m=pitch_metrics([220,440,0],[220,400,0])
        self.assertEqual(m['voiced_reference_frames'],2)
        self.assertAlmostEqual(m['f0_rmse_hz'],28.284271,places=5)
    def test_onset_mae(self):
        self.assertAlmostEqual(onset_mae_ms([1,2],[1.01,1.98]),15.0)
    def test_baseline_feature_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.wav'; sr=44100
            t=np.arange(sr//2)/sr
            sf.write(p,(.2*np.sin(2*np.pi*220*t)).astype('float32'),sr,subtype='PCM_24')
            f=extract_baseline_features(p)
            self.assertEqual(f['sample_rate'],sr)
            self.assertGreater(f['log_mel'].shape[0],0)
            self.assertEqual(f['log_mel'].shape[1],80)
            self.assertTrue(np.isfinite(f['log_mel']).all())
if __name__=='__main__': unittest.main()
