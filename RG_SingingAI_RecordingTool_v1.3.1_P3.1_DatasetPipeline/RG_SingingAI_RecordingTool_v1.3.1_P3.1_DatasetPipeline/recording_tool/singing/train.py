"""Train experimental SingingMelNet from frame-aligned NPZ files.

NPZ schema: log_mel[T,80], phoneme_ids[T], midi_pitch[T], velocity[T].
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import Dataset, DataLoader
from .model import SingingMelNet

class FrameDataset(Dataset):
    def __init__(self, paths):
        self.items=[]
        needed={"log_mel","phoneme_ids","midi_pitch","velocity"}
        for path in paths:
            with np.load(path,allow_pickle=False) as z:
                if not needed.issubset(z.files): raise ValueError(f"{path}: missing arrays {sorted(needed-set(z.files))}")
                x={k:np.asarray(z[k]) for k in needed}
            if x['log_mel'].ndim!=2 or x['log_mel'].shape[1]!=80: raise ValueError(f"{path}: log_mel must have shape [T,80]")
            lengths=[len(x[k]) for k in needed]
            if not lengths[0] or len(set(lengths))!=1: raise ValueError(f"{path}: empty or inconsistent frame lengths")
            if not np.isfinite(x['log_mel']).all(): raise ValueError(f"{path}: log_mel contains NaN/Inf")
            for k,lo,hi in [('phoneme_ids',0,None),('midi_pitch',0,127),('velocity',0,127)]:
                a=x[k]
                if not np.issubdtype(a.dtype,np.number) or not np.isfinite(a).all() or np.any(a<lo) or (hi is not None and np.any(a>hi)):
                    raise ValueError(f"{path}: invalid values in {k}")
            self.items.append({k:np.asarray(x[k]) for k in needed})
    def __len__(self): return len(self.items)
    def __getitem__(self,i):
        x=self.items[i]
        return tuple(torch.from_numpy(x[k].astype(np.int64 if k!="log_mel" else np.float32)) for k in ("phoneme_ids","midi_pitch","velocity","log_mel"))

def collate(batch):
    maxlen=max(x[0].shape[0] for x in batch); out=[]
    for j in range(4):
        padval=0.0 if j==3 else 0
        arr=torch.full((len(batch),maxlen)+(batch[0][j].shape[1:] if batch[0][j].ndim>1 else ()),padval,dtype=batch[0][j].dtype)
        for i,x in enumerate(batch): arr[i,:len(x[j])]=x[j]
        out.append(arr)
    mask=torch.zeros((len(batch),maxlen),dtype=torch.float32)
    for i,x in enumerate(batch): mask[i,:len(x[0])]=1
    return (*out,mask)

def evaluate(model,dl,device):
    model.eval(); vals=[]
    with torch.no_grad():
        for ph,mi,ve,target,mask in dl:
            ph,mi,ve,target,mask=[x.to(device) for x in (ph,mi,ve,target,mask)]
            pred=model(ph,mi,ve); vals.append(float((((pred-target)**2).mean(dim=-1)*mask).sum()/mask.sum().clamp_min(1)))
    return float(np.mean(vals)) if vals else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data',required=True,help='folder containing aligned *.npz files'); ap.add_argument('--out',default='singing_melnet.pt'); ap.add_argument('--vocab-size',type=int,required=True,help='must match the vocabulary ID mapping'); ap.add_argument('--epochs',type=int,default=30); ap.add_argument('--batch-size',type=int,default=2); ap.add_argument('--lr',type=float,default=1e-3); ap.add_argument('--validation-ratio',type=float,default=0.2); ap.add_argument('--seed',type=int,default=20261015); a=ap.parse_args()
    if a.epochs<1 or a.batch_size<1 or a.vocab_size<2 or a.lr<=0: raise SystemExit('epochs/batch-size/lr/vocab-size must be positive and vocab-size >= 2')
    if not 0<=a.validation_ratio<1: raise SystemExit('validation-ratio must be in [0,1)')
    paths=sorted(Path(a.data).glob('*.npz'))
    if not paths: raise SystemExit('No NPZ files found')
    # This is a file-level split only. Use make_splits.py first for song/group-safe splits.
    rng=np.random.default_rng(a.seed); order=rng.permutation(len(paths)); nval=int(round(len(paths)*a.validation_ratio))
    if a.validation_ratio>0 and len(paths)>=2: nval=max(1,min(len(paths)-1,nval))
    elif a.validation_ratio>0 and len(paths)<2: print('WARNING: only one file; validation disabled')
    validx=set(order[:nval]) if len(paths)>=2 else set(); train_paths=[p for i,p in enumerate(paths) if i not in validx]; val_paths=[p for i,p in enumerate(paths) if i in validx]
    train_ds=FrameDataset(train_paths); val_ds=FrameDataset(val_paths) if val_paths else None
    dl=DataLoader(train_ds,batch_size=a.batch_size,shuffle=True,collate_fn=collate); vdl=DataLoader(val_ds,batch_size=a.batch_size,shuffle=False,collate_fn=collate) if val_ds else None
    device='cuda' if torch.cuda.is_available() else 'cpu'; print(f'Device: {device}; train_files={len(train_paths)}; validation_files={len(val_paths)}')
    model=SingingMelNet(a.vocab_size).to(device); opt=torch.optim.AdamW(model.parameters(),lr=a.lr); best=float('inf'); history=[]
    for epoch in range(a.epochs):
        model.train(); losses=[]
        for ph,mi,ve,target,mask in dl:
            ph,mi,ve,target,mask=[x.to(device) for x in (ph,mi,ve,target,mask)]
            pred=model(ph,mi,ve); loss=(((pred-target)**2).mean(dim=-1)*mask).sum()/mask.sum().clamp_min(1)
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); losses.append(float(loss.detach()))
        tr=float(np.mean(losses)); vl=evaluate(model,vdl,device) if vdl else None
        history.append({'epoch':epoch+1,'train_mse':tr,'validation_mse':vl}); metric=vl if vl is not None else tr
        print(f"epoch {epoch+1}/{a.epochs} train_mse={tr:.6f}"+(f" validation_mse={vl:.6f}" if vl is not None else ''))
        if metric<best:
            best=metric; dest=Path(a.out); dest.parent.mkdir(parents=True,exist_ok=True)
            torch.save({'state_dict':model.cpu().state_dict(),'vocab_size':a.vocab_size,'mel_bins':80,'architecture':'SingingMelNet-v0.1','training_config':{'epochs':a.epochs,'batch_size':a.batch_size,'lr':a.lr,'seed':a.seed,'device':device,'validation_ratio':a.validation_ratio},'history':history,'best_metric':best,'training_files':[str(p) for p in train_paths],'validation_files':[str(p) for p in val_paths],'feature_config_note':'Training feature config is stored in each NPZ; verify consistency before inference.'},dest); model.to(device)
    print(f'Saved best checkpoint: {a.out}; this is an experimental mel predictor, not proof of intelligible singing.')
if __name__=='__main__': main()
