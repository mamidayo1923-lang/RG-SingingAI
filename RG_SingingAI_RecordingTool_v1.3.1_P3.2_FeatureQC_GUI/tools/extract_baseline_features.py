"""Extract diagnostic P1/P2 features to a compressed NPZ without overwriting by default."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recording_tool.analysis import extract_p2_features


def _write_npz_atomic(path, payload, overwrite=False):
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {path}. Use --overwrite to replace it.")
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    try:
        with open(temp_name, "wb") as f:
            np.savez_compressed(f, **payload)
            f.flush()
            os.fsync(f.fileno())
        if path.exists() and not overwrite:
            raise FileExistsError(f"Output appeared during extraction: {path}")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract diagnostic P1/P2 acoustic features (not a synthesis model)")
    ap.add_argument("wav", help="Input mono PCM WAV, 44.1 kHz")
    ap.add_argument("--output", default=None, help="Output NPZ path (default: <input>.features_p2.npz)")
    ap.add_argument("--overwrite", action="store_true", help="Allow replacing an existing output file")
    args = ap.parse_args(argv)
    source = Path(args.wav).expanduser().resolve()
    output = Path(args.output).expanduser() if args.output else source.with_suffix(".features_p2.npz")
    try:
        features = extract_p2_features(source)
        payload = {k: v for k, v in features.items() if isinstance(v, np.ndarray)}
        payload["config_json"] = np.asarray(json.dumps(features["config"], ensure_ascii=False, sort_keys=True))
        payload["feature_note"] = np.asarray(features["feature_note"])
        payload["source_file_name"] = np.asarray(source.name)
        saved = _write_npz_atomic(output, payload, overwrite=args.overwrite)
        print(f"Input: {source}")
        print(f"Saved: {saved}")
        print(f"Frames: {len(features['frame_times_sec'])}; duration={features['duration_sec']:.6f}s; sample_rate={features['sample_rate']}")
        for key, value in payload.items():
            if isinstance(value, np.ndarray) and value.ndim:
                print(f"  {key}: shape={value.shape}, dtype={value.dtype}")
        print("WARNING: HNR/formant/breathiness/aperiodicity outputs are diagnostic proxies, not ground truth.")
        return 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
