import tempfile, unittest
from pathlib import Path
import numpy as np, soundfile as sf
from recording_tool.analysis import extract_p2_features

class P2Tests(unittest.TestCase):
    def test_p2_feature_shapes_and_finite_values(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"tone.wav"; sr=44100
            t=np.arange(sr//3)/sr
            sf.write(p,(0.15*np.sin(2*np.pi*220*t)).astype("float32"),sr,subtype="PCM_24")
            f=extract_p2_features(p)
            n=len(f["f0_hz"])
            self.assertEqual(f["spectral_envelope"].shape,(n,1025))
            self.assertEqual(f["formants_hz_estimate"].shape,(n,3))
            for key in ("hnr_db_proxy","aperiodicity_proxy","breathiness_proxy"):
                self.assertEqual(f[key].shape,(n,))
                self.assertTrue(np.isfinite(f[key]).all())
            self.assertEqual(f["voice_quality_proxy"].shape,(n,3))
            self.assertTrue(np.isfinite(f["spectral_envelope"]).all())

if __name__=="__main__": unittest.main()
