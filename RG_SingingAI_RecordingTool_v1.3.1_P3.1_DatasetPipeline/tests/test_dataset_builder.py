import json, tempfile, unittest
from pathlib import Path
import numpy as np
import soundfile as sf
from tools.build_training_dataset import validate_annotations, build_arrays

class DatasetBuilderTests(unittest.TestCase):
    def test_rejects_missing_times(self):
        with self.assertRaises(ValueError): validate_annotations({'phonemes':[{'label':'a'}],'notes':[{'start':0,'end':1,'pitch':60}]},1.0)
    def test_rejects_overlapping_phonemes(self):
        with self.assertRaises(ValueError): validate_annotations({'phonemes':[{'label':'a','start':0,'end':.7},{'label':'i','start':.5,'end':.8}],'notes':[{'start':0,'end':1,'pitch':60}]},1.0)
    def test_builds_frame_aligned_npz(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); wav=d/'x.wav'; ann=d/'a.json'; out=d/'out'/'x.npz'
            sr=44100; t=np.arange(sr,dtype=np.float32)/sr; sf.write(wav,.1*np.sin(2*np.pi*220*t),sr)
            ann.write_text(json.dumps({'phonemes':[{'label':'a','start':0,'end':.5},{'label':'i','start':.5,'end':1.0}], 'notes':[{'start':0,'end':.5,'pitch':57,'velocity':90},{'start':.5,'end':1.0,'pitch':60,'velocity':95}]}),encoding='utf-8')
            result=build_arrays(wav,ann,out)
            with np.load(out,allow_pickle=False) as z:
                self.assertEqual(z['log_mel'].shape[0],len(z['phoneme_ids']))
                self.assertEqual(z['log_mel'].shape[1],80)
                self.assertTrue(np.isfinite(z['log_mel']).all())
                self.assertIn(60,z['midi_pitch'])
            self.assertGreater(result['frames'],0)
    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); wav=d/'x.wav'; ann=d/'a.json'; out=d/'x.npz'; sf.write(wav,np.zeros(44100),44100); out.write_bytes(b'x')
            ann.write_text(json.dumps({'phonemes':[{'label':'a','start':0,'end':1}],'notes':[{'start':0,'end':1,'pitch':60}]}),encoding='utf-8')
            with self.assertRaises(FileExistsError): build_arrays(wav,ann,out)
if __name__=='__main__': unittest.main()
