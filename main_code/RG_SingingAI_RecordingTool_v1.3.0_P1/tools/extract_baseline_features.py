import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from recording_tool.analysis import extract_baseline_features

def main():
    ap=argparse.ArgumentParser(description='Extract baseline log-mel and rough F0 features for diagnostics')
    ap.add_argument('wav'); ap.add_argument('--output',default=None)
    a=ap.parse_args(); p=Path(a.wav); out=Path(a.output) if a.output else p.with_suffix('.features.npz')
    f=extract_baseline_features(p)
    np.savez_compressed(out,log_mel=f['log_mel'],f0_hz=f['f0_hz'],frame_times_sec=f['frame_times_sec'],config_json=__import__('json').dumps(f['config']))
    print(f"Saved {out}: frames={len(f['f0_hz'])}, mel_bins={f['log_mel'].shape[1]}; baseline/diagnostic only")
if __name__=='__main__': main()
