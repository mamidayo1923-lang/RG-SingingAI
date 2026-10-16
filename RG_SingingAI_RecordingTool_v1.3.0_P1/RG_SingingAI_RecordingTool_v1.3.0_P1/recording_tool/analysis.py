"""Dependency-light baseline acoustic features. Not a trained singing synthesis model.
Produces log-mel frames and a rough autocorrelation F0 track for diagnostics only.
"""
from pathlib import Path
import numpy as np
import soundfile as sf

FEATURE_CONFIG={"feature_schema_version":"1.0.0","sample_rate":44100,"n_fft":2048,"hop_length":256,"n_mels":80,"f0_min_hz":65.0,"f0_max_hz":1000.0,"window":"hann","mel_scale":"htk","log_floor":1e-10,"f0_method":"normalized_autocorrelation_baseline_not_production_grade"}

def _hz_to_mel(hz): return 2595.0*np.log10(1.0+np.asarray(hz)/700.0)
def _mel_to_hz(mel): return 700.0*(10.0**(np.asarray(mel)/2595.0)-1.0)
def _mel_filter(sr,n_fft,n_mels):
    low,high=_hz_to_mel(0),_hz_to_mel(sr/2)
    hz=_mel_to_hz(np.linspace(low,high,n_mels+2))
    bins=np.floor((n_fft+1)*hz/sr).astype(int)
    filt=np.zeros((n_mels,n_fft//2+1),dtype=np.float32)
    for m in range(1,n_mels+1):
        left,center,right=bins[m-1:m+2]
        center=max(center,left+1); right=max(right,center+1)
        for k in range(max(0,left),min(center,filt.shape[1])): filt[m-1,k]=(k-left)/(center-left)
        for k in range(max(0,center),min(right,filt.shape[1])): filt[m-1,k]=(right-k)/(right-center)
    return filt

def extract_baseline_features(path, config=None):
    cfg=dict(FEATURE_CONFIG); cfg.update(config or {})
    audio,sr=sf.read(str(path),dtype='float32',always_2d=True)
    if sr!=cfg['sample_rate']: raise ValueError(f"Expected {cfg['sample_rate']} Hz, got {sr}; resample explicitly before extraction")
    if audio.shape[1]!=1: raise ValueError("Expected mono audio")
    x=audio[:,0]; n_fft=int(cfg['n_fft']); hop=int(cfg['hop_length'])
    if n_fft<2 or hop<1: raise ValueError("Invalid FFT/hop configuration")
    if len(x)==0: raise ValueError("Audio is empty")
    if len(x)<n_fft: x=np.pad(x,(0,n_fft-len(x)))
    frames=np.lib.stride_tricks.sliding_window_view(x,n_fft)[::hop]
    window=np.hanning(n_fft).astype(np.float32)
    spec=np.abs(np.fft.rfft(frames*window[None,:],axis=1)).astype(np.float32)
    power=spec*spec
    mel=power @ _mel_filter(sr,n_fft,int(cfg['n_mels'])).T
    log_mel=np.log(np.maximum(mel,float(cfg['log_floor']))).astype(np.float32)
    # Baseline F0 estimator: normalized autocorrelation on each frame; low-confidence frames -> 0.
    f0=np.zeros(len(frames),dtype=np.float32); lo=max(1,int(sr/float(cfg['f0_max_hz']))); hi=min(n_fft-2,int(sr/float(cfg['f0_min_hz'])))
    for i,frame in enumerate(frames):
        y=frame.astype(np.float64); y-=y.mean(); rms=np.sqrt(np.mean(y*y))
        if rms<1e-5: continue
        ac=np.correlate(y,y,mode='full')[n_fft-1:]; ac=ac/(ac[0]+1e-12)
        if hi<=lo: continue
        lag=lo+int(np.argmax(ac[lo:hi+1])); confidence=float(ac[lag])
        if confidence>=0.35: f0[i]=sr/lag
    return {"config":cfg,"sample_rate":sr,"duration_sec":len(audio)/sr,"frame_times_sec":(np.arange(len(frames))*hop/sr).astype(np.float32),"log_mel":log_mel,"f0_hz":f0,"feature_note":"Baseline diagnostic features only; validate F0 manually and do not treat as forced alignment or a production vocoder representation."}
