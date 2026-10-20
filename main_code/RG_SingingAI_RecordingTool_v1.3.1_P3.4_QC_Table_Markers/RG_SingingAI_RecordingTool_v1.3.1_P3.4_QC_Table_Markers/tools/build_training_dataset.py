"""Build frame-aligned NPZ from WAV + reviewed phoneme/MIDI annotation JSON.

Annotation JSON:
{
  "phonemes": [{"label":"a", "start":0.0, "end":0.4}, ...],
  "notes": [{"start":0.0, "end":0.4, "pitch":60, "velocity":90}, ...]
}
Times are seconds relative to the WAV. Phoneme boundaries must be manually reviewed
or produced by an external aligner and reviewed. This tool does not infer boundaries.
"""
from __future__ import annotations
import argparse, json, os, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from recording_tool.analysis import extract_baseline_features, FEATURE_CONFIG

VOWEL_LABELS = {"a","i","u","e","o","aa","ii","uu","ee","oo","n","N"}

def validate_annotations(obj, duration):
    if not isinstance(obj, dict): raise ValueError("annotation root must be an object")
    phonemes, notes = obj.get("phonemes"), obj.get("notes")
    if not isinstance(phonemes,list) or not phonemes: raise ValueError("phonemes must be a non-empty array")
    if not isinstance(notes,list) or not notes: raise ValueError("notes must be a non-empty array")
    ps=[]
    for i,p in enumerate(phonemes):
        if not isinstance(p,dict) or not str(p.get("label","")).strip(): raise ValueError(f"phonemes[{i}].label is required")
        try: st,en=float(p['start']),float(p['end'])
        except (KeyError,TypeError,ValueError): raise ValueError(f"phonemes[{i}] requires numeric start/end seconds")
        if not np.isfinite([st,en]).all() or st<0 or en<=st or en>duration+0.05: raise ValueError(f"phonemes[{i}] has invalid/out-of-range times")
        ps.append({"label":str(p['label']),"start":st,"end":en})
    ns=[]
    for i,n in enumerate(notes):
        try: st,en=float(n['start']),float(n['end']); pitch=int(n['pitch']); vel=int(n.get('velocity',100))
        except (KeyError,TypeError,ValueError): raise ValueError(f"notes[{i}] requires start/end/pitch and optional velocity")
        if not np.isfinite([st,en]).all() or st<0 or en<=st or en>duration+0.05: raise ValueError(f"notes[{i}] has invalid/out-of-range times")
        if not 0<=pitch<=127 or not 1<=vel<=127: raise ValueError(f"notes[{i}] pitch must be 0..127 and velocity 1..127")
        ns.append({"start":st,"end":en,"pitch":pitch,"velocity":vel})
    # reject overlapping phoneme labels; overlapping MIDI notes are ambiguous for this baseline
    ps.sort(key=lambda x:x['start']); ns.sort(key=lambda x:x['start'])
    for a,b in zip(ps,ps[1:]):
        if b['start'] < a['end']-1e-6: raise ValueError("phoneme intervals overlap; resolve them before dataset generation")
    for a,b in zip(ns,ns[1:]):
        if b['start'] < a['end']-1e-6: raise ValueError("MIDI note intervals overlap; resolve polyphony/overlap before dataset generation")
    return ps,ns

def build_arrays(wav, annotation, out, *, overwrite=False, vocab_json=None):
    wav=Path(wav); annotation=Path(annotation); out=Path(out)
    if out.exists() and not overwrite: raise FileExistsError(f"Refusing to overwrite {out}; pass --overwrite")
    meta=json.loads(annotation.read_text(encoding='utf-8'))
    info=sf.info(str(wav)); duration=float(info.frames/info.samplerate)
    ps,ns=validate_annotations(meta,duration)
    feat=extract_baseline_features(str(wav))
    times=np.asarray(feat['frame_times_sec'],dtype=np.float32); T=len(times)
    if T==0: raise ValueError("WAV produced no feature frames")
    # IDs are deterministic within this dataset item; a vocabulary map is saved for reuse.
    labels=sorted({p['label'] for p in ps})
    vocab_path=Path(vocab_json) if vocab_json else out.parent/'phoneme_vocab.json'
    if vocab_path.exists():
        saved=json.loads(vocab_path.read_text(encoding='utf-8'))
        vocab={str(k):int(v) for k,v in saved.get('label_to_id',saved).items()}
        if any(v<=0 for v in vocab.values()) or len(set(vocab.values()))!=len(vocab):
            raise ValueError(f"Invalid shared vocabulary mapping in {vocab_path}; IDs must be unique positive integers")
    else: vocab={}
    next_id=max(vocab.values(),default=0)+1
    for label in labels:
        if label not in vocab: vocab[label]=next_id; next_id+=1
    vocab_path.parent.mkdir(parents=True,exist_ok=True)
    vocab_path.write_text(json.dumps({"schema_version":"1.0","padding_id":0,"label_to_id":vocab},ensure_ascii=False,indent=2),encoding='utf-8')
    ph=np.zeros(T,dtype=np.int64); pitch=np.zeros(T,dtype=np.int64); vel=np.zeros(T,dtype=np.int64)
    # Frames outside reviewed phoneme or MIDI intervals remain unlabeled/unvoiced.
    for i,t in enumerate(times.astype(float)):
        for p in ps:
            if p['start'] <= t < p['end']:
                ph[i]=vocab[p['label']]; break
        for n in ns:
            if n['start'] <= t < n['end']:
                pitch[i]=n['pitch']; vel[i]=n['velocity']; break
    # Do not silently create mostly-empty targets from sparse/incompatible annotations.
    if np.count_nonzero(ph)==0: raise ValueError("No feature frames overlap phoneme annotations")
    if np.count_nonzero(pitch)==0: raise ValueError("No feature frames overlap MIDI note annotations")
    log_mel=np.asarray(feat['log_mel'],dtype=np.float32)
    if log_mel.ndim!=2 or log_mel.shape[0]!=T or not np.isfinite(log_mel).all(): raise ValueError("invalid/non-finite log_mel features")
    out.parent.mkdir(parents=True,exist_ok=True)
    payload={"log_mel":log_mel,"phoneme_ids":ph,"midi_pitch":pitch,"velocity":vel,
             "frame_times_sec":times,"vocab_json":np.asarray(json.dumps(vocab,ensure_ascii=False)),
             "feature_config_json":np.asarray(json.dumps(feat['config'],ensure_ascii=False)),
             "source_wav":np.asarray(wav.name),"annotation_source":np.asarray(annotation.name),
             "label_status":np.asarray("reviewed_annotation_required"),
             "vocab_path":np.asarray(str(vocab_path))}
    fd,tmp=tempfile.mkstemp(prefix=out.name+'.',suffix='.tmp',dir=str(out.parent)); os.close(fd)
    try:
        with open(tmp,'wb') as f: np.savez_compressed(f,**payload)
        if out.exists() and not overwrite: raise FileExistsError(out)
        os.replace(tmp,out)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return {"output":str(out),"frames":T,"mel_shape":list(log_mel.shape),"vocabulary_size":max(vocab.values(),default=0)+1,"phoneme_labeled_frames":int(np.count_nonzero(ph)),"pitch_labeled_frames":int(np.count_nonzero(pitch)),"sample_rate":feat['sample_rate'],"hop_length":feat['config']['hop_length'],"vocab_file":str(vocab_path)}

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--wav',required=True); ap.add_argument('--annotations',required=True,help='JSON with reviewed phonemes and MIDI notes'); ap.add_argument('--out',required=True); ap.add_argument('--vocab-json',default=None,help='shared vocabulary JSON reused across all takes; defaults to <out-dir>/phoneme_vocab.json'); ap.add_argument('--overwrite',action='store_true'); a=ap.parse_args()
    result=build_arrays(a.wav,a.annotations,a.out,overwrite=a.overwrite,vocab_json=a.vocab_json); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
