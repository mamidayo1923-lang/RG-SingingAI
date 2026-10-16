import wave,math,json
import numpy as np
def analyze(path):
 r={'status':'PASS','critical':[],'major':[],'sample_rate':None,'channels':None,'bits_per_sample':None,'duration_sec':0,'peak_dbfs':None,'rms_dbfs':None}
 try:
  with wave.open(str(path),'rb') as w:sr,ch,sw,n=w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes();raw=w.readframes(n)
  r.update(sample_rate=sr,channels=ch,bits_per_sample=sw*8,duration_sec=n/sr if sr else 0)
  if sr!=44100:r['critical'].append('sample rate is not 44100 Hz')
  if ch!=1:r['critical'].append('recording is not mono')
  if sw!=3:r['critical'].append('recording is not 24-bit PCM')
  if not raw:r['critical'].append('empty recording');a=np.zeros(1)
  else:
   u=np.frombuffer(raw,np.uint8).reshape(-1,3);v=(u[:,0].astype(np.int32)|(u[:,1].astype(np.int32)<<8)|(u[:,2].astype(np.int32)<<16));v=np.where(v&0x800000,v-0x1000000,v)/8388608.;a=np.asarray(v,float)
  peak=float(np.max(np.abs(a)));rms=float(np.sqrt(np.mean(a*a)));r['peak_dbfs']=20*math.log10(max(peak,1e-12));r['rms_dbfs']=20*math.log10(max(rms,1e-12))
  if peak>=.999999:r['critical'].append('possible clipping')
  if r['duration_sec']<.5:r['major'].append('very short recording')
 except Exception as e:r['critical'].append('WAV read error: '+str(e))
 if r['critical']:r['status']='FAIL'
 elif r['major']:r['status']='WARN'
 return r
def save(path,r):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
