"""Train SingingMelNet from frame-aligned NPZ files.

Each NPZ must contain log_mel [T,80], phoneme_ids [T], midi_pitch [T], velocity [T].
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import Dataset, DataLoader
from .model import SingingMelNet

class FrameDataset(Dataset):
    def __init__(self, paths):
        self.items=[]
        for path in paths:
            z=np.load(path)
            needed={"log_mel","phoneme_ids","midi_pitch","velocity"}
            if not needed.issubset(z.files): raise ValueError(f"{path}: missing arrays {sorted(needed-set(z.files))}")
            lengths=[len(z[k]) for k in needed]
            if len(set(lengths)) != 1: raise ValueError(f"{path}: frame lengths differ")
            self.items.append({k:np.asarray(z[k]) for k in needed})
    def __len__(self): return len(self.items)
    def __getitem__(self,i):
        x=self.items[i]
        return tuple(torch.from_numpy(x[k].astype(np.int64 if k!="log_mel" else np.float32)) for k in ("phoneme_ids","midi_pitch","velocity","log_mel"))

def collate(batch):
    maxlen=max(x[0].shape[0] for x in batch)
    out=[]
    for j in range(4):
        padval=0.0 if j==3 else 0
        arr=torch.full((len(batch),maxlen)+(batch[0][j].shape[1:] if batch[0][j].ndim>1 else ()),padval,dtype=batch[0][j].dtype)
        for i,x in enumerate(batch): arr[i,:len(x[j])]=x[j]
        out.append(arr)
    mask=torch.zeros((len(batch),maxlen),dtype=torch.float32)
    for i,x in enumerate(batch): mask[i,:len(x[0])]=1
    return (*out,mask)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data",required=True,help="folder containing aligned *.npz files")
    ap.add_argument("--out",default="singing_melnet.pt"); ap.add_argument("--vocab-size",type=int,required=True)
    ap.add_argument("--epochs",type=int,default=30); ap.add_argument("--batch-size",type=int,default=2); ap.add_argument("--lr",type=float,default=1e-3)
    a=ap.parse_args(); paths=sorted(Path(a.data).glob("*.npz"))
    if not paths: raise SystemExit("No NPZ files found")
    ds=FrameDataset(paths); dl=DataLoader(ds,batch_size=a.batch_size,shuffle=True,collate_fn=collate)
    device="cuda" if torch.cuda.is_available() else "cpu"; model=SingingMelNet(a.vocab_size).to(device)
    opt=torch.optim.AdamW(model.parameters(),lr=a.lr)
    for epoch in range(a.epochs):
        model.train(); losses=[]
        for ph,mi,ve,target,mask in dl:
            ph,mi,ve,target,mask=[x.to(device) for x in (ph,mi,ve,target,mask)]
            pred=model(ph,mi,ve); loss=(((pred-target)**2).mean(dim=-1)*mask).sum()/mask.sum().clamp_min(1)
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); losses.append(float(loss.detach()))
        print(f"epoch {epoch+1}/{a.epochs} loss={np.mean(losses):.6f}")
    dest=Path(a.out); dest.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"state_dict":model.cpu().state_dict(),"vocab_size":a.vocab_size,"mel_bins":80,"architecture":"SingingMelNet-v0.1"},dest)
    print(f"Saved {dest}; this checkpoint is a research baseline, not proof of intelligible singing")
if __name__=="__main__": main()
