import argparse, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from recording_tool.analysis import extract_p2_features

def main():
    ap=argparse.ArgumentParser(description="Extract P1 baseline and P2 acoustic descriptors (diagnostic estimates)")
    ap.add_argument("wav"); ap.add_argument("--output",default=None)
    a=ap.parse_args(); p=Path(a.wav); out=Path(a.output) if a.output else p.with_suffix(".features_p2.npz")
    f=extract_p2_features(p)
    arrays={k:v for k,v in f.items() if isinstance(v,np.ndarray)}
    arrays["config_json"]=json.dumps(f["config"],ensure_ascii=False)
    arrays["feature_note"]=f["feature_note"]
    np.savez_compressed(out,**arrays)
    print(f"Saved {out}: frames={len(f['f0_hz'])}, log_mel={f['log_mel'].shape}, spectral_envelope={f['spectral_envelope'].shape}")
    print("P2 HNR/formant/breathiness/aperiodicity outputs are diagnostic proxies, not ground truth.")
if __name__=="__main__": main()
