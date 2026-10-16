import math,struct,time,wave,threading
from pathlib import Path
import numpy as np
try: import sounddevice as sd
except ImportError: sd=None
class AudioEngine:
 def __init__(self,cfg,on_level=None,on_error=None): self.c=cfg;self.on_level=on_level;self.on_error=on_error;self.stream=None;self.frames=[];self.lock=threading.Lock();self.running=False;self.transport_at=None
 @staticmethod
 def devices(): return sd.query_devices() if sd else []
 def start(self):
  if not sd: raise RuntimeError('sounddevice がありません。requirements.txt をインストールしてください。')
  self.frames=[];self.running=True;self.transport_at=None
  self.stream=sd.Stream(samplerate=self.c.sample_rate,blocksize=self.c.blocksize,channels=1,dtype='float32',device=(self.c.input_device,self.c.output_device),latency='low',callback=self._cb);self.stream.start()
 def begin(self): self.transport_at=time.perf_counter()
 def elapsed(self): return 0 if self.transport_at is None else max(0,time.perf_counter()-self.transport_at)
 def _cb(self,indata,outdata,frames,time_info,status):
  if status and self.on_error:self.on_error(str(status))
  x=indata[:,0].copy()
  with self.lock:
   if self.running:self.frames.append(x)
  outdata[:,0]=0
  if self.transport_at is not None:
   base=time.perf_counter()-self.transport_at; beatsec=60/max(20,self.c.bpm)
   for i in range(frames):
    t=base+i/self.c.sample_rate; b=math.floor(t/beatsec); ph=t-b*beatsec; y=0
    if self.c.click and ph<.035:
     f=1760 if b%4==0 else 1320; y+=self.c.click_volume*(1-ph/.035)*math.sin(2*math.pi*f*ph)
    if self.c.reference:y+=self.c.reference_volume*math.sin(2*math.pi*self.c.reference_hz*t)
    outdata[i,0]=max(-.8,min(.8,y))
  if self.on_level:self.on_level(float(np.sqrt(np.mean(x*x))+1e-12),float(np.max(np.abs(x))+1e-12))
 def stop(self):
  self.running=False
  if self.stream:self.stream.stop();self.stream.close();self.stream=None
  with self.lock:return np.concatenate(self.frames) if self.frames else np.zeros(0,np.float32)
 @staticmethod
 def write24(path,a,sr=44100):
  a=np.clip(np.asarray(a,np.float32),-1,1); v=np.rint(a*8388607).astype(np.int32); raw=bytearray()
  for n in v:
   if n<0:n+=1<<24
   raw.extend(struct.pack('<I',int(n))[:3])
  with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(3);w.setframerate(sr);w.writeframes(raw)
