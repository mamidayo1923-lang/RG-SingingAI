import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf
from recording_tool.analysis import extract_p2_features, extract_baseline_features

class P2Tests(unittest.TestCase):
    def _wav(self, root, name, signal, sr=44100, subtype="PCM_24"):
        p = Path(root) / name
        sf.write(p, np.asarray(signal, dtype=np.float32), sr, subtype=subtype)
        return p

    def test_p2_feature_shapes_finite_and_aligned(self):
        with tempfile.TemporaryDirectory() as td:
            sr = 44100
            t = np.arange(sr // 3) / sr
            p = self._wav(td, "tone.wav", 0.15 * np.sin(2 * np.pi * 220 * t))
            f = extract_p2_features(p)
            n = len(f["frame_times_sec"])
            self.assertGreater(n, 0)
            for key in ("frame_rms", "f0_hz", "f0_confidence_proxy", "hnr_db_proxy", "aperiodicity_proxy", "breathiness_proxy"):
                self.assertEqual(f[key].shape, (n,), key)
                self.assertTrue(np.isfinite(f[key]).all(), key)
            for key in ("log_mel", "spectral_envelope"):
                self.assertEqual(f[key].shape[0], n, key)
                self.assertTrue(np.isfinite(f[key]).all(), key)
            self.assertEqual(f["log_mel"].shape[1], 80)
            self.assertEqual(f["spectral_envelope"].shape[1], 1025)
            self.assertEqual(f["formants_hz_estimate"].shape, (n, 3))
            self.assertEqual(f["formant_peak_strength_proxy"].shape, (n, 3))
            self.assertEqual(f["voice_quality_proxy"].shape, (n, 3))
            self.assertTrue(np.all(f["frame_times_sec"][1:] > f["frame_times_sec"][:-1]))

    def test_silence_is_finite_and_f0_zero(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._wav(td, "silence.wav", np.zeros(4410))
            f = extract_p2_features(p)
            self.assertTrue(np.all(f["f0_hz"] == 0))
            self.assertTrue(np.isfinite(f["spectral_envelope"]).all())

    def test_short_audio_is_padded_to_one_frame(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._wav(td, "short.wav", [0.1, -0.1, 0.0])
            f = extract_p2_features(p)
            self.assertEqual(f["log_mel"].shape[0], 1)

    def test_wrong_sample_rate_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._wav(td, "wrong.wav", np.zeros(1000), sr=48000)
            with self.assertRaisesRegex(ValueError, "Expected 44100 Hz"):
                extract_p2_features(p)

    def test_stereo_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "stereo.wav"
            sf.write(p, np.zeros((3000, 2), dtype=np.float32), 44100, subtype="PCM_24")
            with self.assertRaisesRegex(ValueError, "Expected mono"):
                extract_p2_features(p)

    def test_missing_file_rejected(self):
        with self.assertRaises(FileNotFoundError):
            extract_p2_features("not-a-real-file.wav")

    def test_invalid_hop_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._wav(td, "tone.wav", np.zeros(5000))
            with self.assertRaisesRegex(ValueError, "hop_length"):
                extract_p2_features(p, {"hop_length": 4096})

    def test_baseline_and_p2_share_frame_convention(self):
        with tempfile.TemporaryDirectory() as td:
            sr = 44100
            t = np.arange(sr // 4) / sr
            p = self._wav(td, "tone.wav", .1 * np.sin(2 * np.pi * 330 * t))
            a, b = extract_baseline_features(p), extract_p2_features(p)
            np.testing.assert_array_equal(a["frame_times_sec"], b["frame_times_sec"])
            self.assertEqual(a["log_mel"].shape, b["log_mel"].shape)

if __name__ == "__main__":
    unittest.main(verbosity=2)
