import json, tempfile, unittest
from pathlib import Path
import numpy as np, soundfile as sf
from recording_tool.qc import inspect
from recording_tool.dataset import sha256_file, atomic_write_json, validate_metadata

class P0Tests(unittest.TestCase):
 def test_qc_pass_for_valid_wav(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"ok.wav"; sf.write(p, np.sin(np.arange(44100)*2*np.pi*440/44100).astype("float32")*.1,44100,subtype="PCM_24")
   r=inspect(p); self.assertTrue(r["passed"]); self.assertEqual(r["status"],"PASS")
 def test_silence_is_warning_not_failure(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"silence.wav"; sf.write(p,np.zeros(44100,dtype="float32"),44100,subtype="PCM_24")
   r=inspect(p); self.assertTrue(r["passed"]); self.assertEqual(r["status"],"WARN")
 def test_atomic_json_and_hash(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"a.json"; atomic_write_json(p,{"ok":True}); self.assertTrue(json.loads(p.read_text())["ok"]); self.assertEqual(len(sha256_file(p)),64)
 def test_metadata_validation_reports_missing_fields(self):
  r=validate_metadata({}); self.assertFalse(r["passed"]); self.assertGreater(len(r["errors"]),0)
if __name__ == "__main__": unittest.main()
