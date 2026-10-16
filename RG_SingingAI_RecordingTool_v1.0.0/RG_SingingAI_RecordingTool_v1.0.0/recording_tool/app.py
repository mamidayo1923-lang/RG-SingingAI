import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
import json,time,math
from .config import Config
from .audio import AudioEngine
from .midi import load
from .qc import analyze,save
VERSION='1.0.0';PROTOCOL='1.0.0'
class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title('RG Singing AI Recording Tool v'+VERSION);self.geometry('1180x760');self.cfg=Config.load('recording_tool_config.json');self.dataset=Path('RG_SingingAI_Dataset');self.notes=[];self.lyrics=[];self.midi=None;self.recording=False;self.engine=None;self.peak=0;self._ui()
 def _ui(self):
  h=ttk.Frame(self,padding=10);h.pack(fill='x');ttk.Label(h,text='RG Singing AI Recording Tool',font=('Segoe UI',18,'bold')).pack(side='left');ttk.Label(h,text='v'+VERSION+' / Protocol '+PROTOCOL).pack(side='right')
  f=ttk.LabelFrame(self,text='Take / Sync',padding=10);f.pack(fill='x',padx=10,pady=5)
  self.speaker=tk.StringVar(value='S001');self.session=tk.StringVar(value='01');self.bpm=tk.DoubleVar(value=self.cfg.bpm);self.ref=tk.DoubleVar(value=self.cfg.reference_hz)
  for i,(t,var) in enumerate([('Speaker ID',self.speaker),('Session',self.session),('BPM',self.bpm),('Reference Hz',self.ref)]):ttk.Label(f,text=t).grid(row=0,column=i*2,sticky='w');ttk.Entry(f,textvariable=var,width=12).grid(row=0,column=i*2+1,padx=5)
  ttk.Button(f,text='MIDI読込',command=self.open_midi).grid(row=0,column=8,padx=5);ttk.Button(f,text='歌詞読込',command=self.open_lyrics).grid(row=0,column=9,padx=5);ttk.Button(f,text='保存先',command=self.choose).grid(row=0,column=10,padx=5)
  p=ttk.Panedwindow(self,orient='horizontal');p.pack(fill='both',expand=True,padx=10,pady=5);l=ttk.Frame(p,padding=10);r=ttk.Frame(p,padding=10);p.add(l,weight=3);p.add(r,weight=2)
  self.clock=ttk.Label(l,text='00:00.000',font=('Consolas',34,'bold'));self.clock.pack(pady=10);self.note=ttk.Label(l,text='MIDI: --',font=('Segoe UI',18));self.note.pack();self.lyric=ttk.Label(l,text='歌詞: --',font=('Segoe UI',25,'bold'),wraplength=650);self.lyric.pack(pady=20);self.bar=ttk.Progressbar(l,maximum=1);self.bar.pack(fill='x');self.level=ttk.Label(l,text='Peak: -- dBFS');self.level.pack(pady=5);self.status=ttk.Label(l,text='待機');self.status.pack(pady=10)
  ttk.Label(r,text='MIDIノート',font=('Segoe UI',14,'bold')).pack(anchor='w');self.list=tk.Listbox(r);self.list.pack(fill='both',expand=True);ttk.Label(r,text='クリック/基準音は入力WAVに混入しません。ヘッドホン推奨。').pack(anchor='w',pady=8)
  b=ttk.Frame(self,padding=10);b.pack(fill='x');self.start=ttk.Button(b,text='● 録音開始',command=self.start_rec);self.start.pack(side='left',padx=4);self.stop=ttk.Button(b,text='■ 停止',command=self.stop_rec,state='disabled');self.stop.pack(side='left',padx=4);ttk.Button(b,text='デバイス',command=self.devices).pack(side='left',padx=4);ttk.Button(b,text='Take一覧',command=self.takes).pack(side='right',padx=4);self.after(40,self.tick)
 def choose(self):
  p=filedialog.askdirectory();
  if p:self.dataset=Path(p)
 def open_midi(self):
  p=filedialog.askopenfilename(filetypes=[('MIDI','*.mid *.midi')]);
  if not p:return
  try:self.notes=load(p);self.midi=Path(p);self.list.delete(0,'end');[self.list.insert('end',f'{n.start:.2f}-{n.end:.2f} {n.name} vel={n.velocity}') for n in self.notes]
  except Exception as e:messagebox.showerror('MIDI',str(e))
 def open_lyrics(self):
  p=filedialog.askopenfilename(filetypes=[('Text/LRC','*.txt *.lrc')]);
  if not p:return
  self.lyrics=[]
  for line in Path(p).read_text(encoding='utf-8-sig').splitlines():
   line=line.strip()
   if not line:continue
   if line.startswith('[') and ']' in line:
    a,t=line.split(']',1)
    try:mm,ss=a[1:].split(':');self.lyrics.append((int(mm)*60+float(ss),t))
    except:self.lyrics.append((0,t))
   else:self.lyrics.append((0,line))
  self.lyrics.sort();self.lyrics_path=Path(p)
 def next_take(self):
  d=self.dataset/'raw'/'audio';d.mkdir(parents=True,exist_ok=True);pre=f'{self.speaker.get()}_{int(self.session.get()):02d}'
  nums=[]
  for p in d.glob(pre+'*.wav'):
   try:nums.append(int(p.stem[-4:]))
   except:pass
  return max(nums,default=0)+1
 def start_rec(self):
  if self.recording:return
  try:
   self.cfg.bpm=float(self.bpm.get());self.cfg.reference_hz=float(self.ref.get());self.cfg.save('recording_tool_config.json');self.take=self.next_take();self.engine=AudioEngine(self.cfg,on_level=self.on_level,on_error=lambda e:self.status.config(text=e));self.engine.start();self.recording=True;self.start.config(state='disabled');self.stop.config(state='normal');self.status.config(text=f'録音準備中… {self.cfg.preroll_beats}拍後に同期開始');self.after(int(self.cfg.preroll_beats*60/self.cfg.bpm*1000),self.engine.begin)
  except Exception as e:messagebox.showerror('録音開始',str(e))
 def stop_rec(self):
  if not self.recording:return
  self.recording=False;a=self.engine.stop();stem=f'{self.speaker.get()}_{int(self.session.get()):02d}{self.take:04d}';out=self.dataset/'raw'/'audio';out.mkdir(parents=True,exist_ok=True);wav=out/(stem+'.wav');AudioEngine.write24(wav,a);meta={'app_version':VERSION,'protocol_version':PROTOCOL,'stem':stem,'speaker_id':self.speaker.get(),'session_id':int(self.session.get()),'take_id':self.take,'sample_rate':44100,'bit_depth':24,'channels':1,'processing':'none','original_wav':True,'bpm':self.cfg.bpm,'reference_hz':self.cfg.reference_hz}
  md=self.dataset/'reference'/'metadata';md.mkdir(parents=True,exist_ok=True);(md/(stem+'.json')).write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
  if self.midi:
   d=self.dataset/'reference'/'midi';d.mkdir(parents=True,exist_ok=True);(d/(stem+'.mid')).write_bytes(self.midi.read_bytes())
  if hasattr(self,'lyrics_path'):
   d=self.dataset/'reference'/'lyrics';d.mkdir(parents=True,exist_ok=True);(d/(stem+'.txt')).write_text(self.lyrics_path.read_text(encoding='utf-8-sig'),encoding='utf-8')
  q=analyze(wav);save(self.dataset/'qc'/(stem+'.json'),q);self.start.config(state='normal');self.stop.config(state='disabled');self.status.config(text='保存完了 / QC='+q['status']);messagebox.showinfo('録音後QC',f"{q['status']}\n{q['duration_sec']:.2f}s / Peak {q['peak_dbfs']:.2f} dBFS\nSR {q['sample_rate']} Hz / {q['bits_per_sample']}-bit / mono")
 def on_level(self,rms,peak):self.peak=peak
 def tick(self):
  if self.recording and self.engine:
   t=self.engine.elapsed();self.clock.config(text=f'{int(t//60):02d}:{t%60:06.3f}');db=20*math.log10(max(self.peak,1e-9));self.level.config(text=f'Peak: {db:.2f} dBFS');self.bar['value']=min(1,self.peak);n=next((x for x in self.notes if x.start<=t<x.end),None);self.note.config(text='MIDI: '+(n.name if n else '--'));ls=[x for x in self.lyrics if x[0]<=t];self.lyric.config(text='歌詞: '+(ls[-1][1] if ls else '--'))
  self.after(40,self.tick)
 def devices(self):
  w=tk.Toplevel(self);w.title('Audio Devices');w.geometry('850x500');x=tk.Text(w);x.pack(fill='both',expand=True)
  try:
   for i,d in enumerate(AudioEngine.devices()):x.insert('end',f"{i}: {d['name']} | in={d['max_input_channels']} out={d['max_output_channels']} | {d['default_samplerate']} Hz\n")
  except Exception as e:x.insert('end',str(e))
 def takes(self):
  w=tk.Toplevel(self);w.title('Take一覧');lb=tk.Listbox(w);lb.pack(fill='both',expand=True);d=self.dataset/'raw'/'audio';[lb.insert('end',p.name) for p in sorted(d.glob('*.wav'))]
def main():App().mainloop()
