"""Render a frame-aligned phoneme/MIDI JSON with a trained mel model and Griffin-Lim.

Input JSON: {"vocab_size": N, "phoneme_ids": [...], "midi_pitch": [...], "velocity": [...]}.
Arrays must be frame-aligned; duration expansion/alignment is a separate step.
"""
import argparse, json
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser(); p.add_argument("--model",required=True); p.add_argument("--score",required=True); p.add_argument("--out",required=True); p.add_argument("--sr",type=int,default=22050); p.add_argument("--hop",type=int,default=256); a=p.parse_args()
    try: import torch, librosa, soundfile as sf
    except ImportError as e: raise SystemExit("Install optional dependencies: pip install torch librosa soundfile") from e
    ck=torch.load(a.model,map_location="cpu",weights_only=False); score=json.loads(Path(a.score).read_text(encoding="utf-8"))
    model=__import__("recording_tool.singing.model",fromlist=["SingingMelNet"]).SingingMelNet(int(ck["vocab_size"]),int(ck.get("mel_bins",80)))
    model.load_state_dict(ck["state_dict"]); model.eval()
    arrays=[score[k] for k in ("phoneme_ids","midi_pitch","velocity")]
    if not arrays[0] or len({len(x) for x in arrays})!=1: raise SystemExit("Score arrays must have equal nonzero lengths")
    with torch.no_grad(): mel=model(*(torch.tensor(x,dtype=torch.long).unsqueeze(0) for x in arrays)).squeeze(0).numpy().T
    # log-mel model output is approximate; invert mel -> magnitude -> waveform.
    mel_power=np.maximum(np.exp(mel),1e-8)
    S=librosa.feature.inverse.mel_to_stft(mel_power, sr=a.sr, n_fft=2048, power=2.0)
    y=librosa.griffinlim(np.sqrt(np.maximum(S,1e-10)), n_iter=64, hop_length=a.hop, win_length=2048)
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); sf.write(out,y,a.sr)
    print(f"Wrote {out}. Griffin-Lim reconstruction is a baseline and may sound buzzy/noisy; not a production vocoder.")
if __name__=="__main__": main()
