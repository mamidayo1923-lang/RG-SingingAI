import tkinter as tk, json, shutil, time
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from datetime import datetime
import sounddevice as sd
from .audio import Recorder,tone
from .midi import load
from .score import Score
from .qc import inspect
from .dataset import sha256_file, atomic_write_json, validate_metadata, build_note_reference
class App(tk.Tk):
 def __init__(self):
    super().__init__();self.title('RG Singing AI Recording Tool v1.3.0 P2.1');self.geometry('1100x760')
    self.midi=None;self.midi_path=None;self.lyric_path=None;self.lyrics=[];self.rec=None;self.recording=False
    f=ttk.Frame(self,padding=10);f.pack(fill='both',expand=True)
    self.rootvar=tk.StringVar(value=str(Path.cwd()/'RG_SingingAI_Dataset'));self.speaker=tk.StringVar(value='S001');self.session=tk.StringVar(value='01');self.song_id=tk.StringVar(value='');self.phrase_id=tk.StringVar(value='');self.group_id=tk.StringVar(value='')
    ttk.Label(f,text='保存先').grid(row=0,column=0,sticky='w');ttk.Entry(f,textvariable=self.rootvar,width=55).grid(row=0,column=1,sticky='ew');ttk.Button(f,text='参照',command=self.pickroot).grid(row=0,column=2)
    ttk.Label(f,text='話者ID').grid(row=1,column=0,sticky='w');ttk.Entry(f,textvariable=self.speaker,width=12).grid(row=1,column=1,sticky='w')
    ttk.Label(f,text='セッション(2桁)').grid(row=1,column=1,padx=(150,0),sticky='w');ttk.Entry(f,textvariable=self.session,width=5).grid(row=1,column=1,padx=(260,0),sticky='w')
    try:
      self.devices=[(i,d) for i,d in enumerate(sd.query_devices()) if d.get('max_input_channels',0)>0]
      opts=['既定']+[f'{i}: {d["name"]}' for i,d in self.devices]
    except Exception: opts=['既定']
    self.dev=tk.StringVar(value=opts[0]);self.combo=ttk.Combobox(f,textvariable=self.dev,values=opts,state='readonly',width=35);self.combo.grid(row=1,column=2,sticky='w')
    ttk.Label(f,text='曲ID').grid(row=2,column=0,sticky='w');ttk.Entry(f,textvariable=self.song_id,width=18).grid(row=2,column=1,sticky='w');ttk.Label(f,text='フレーズID').grid(row=2,column=1,padx=(150,0),sticky='w');ttk.Entry(f,textvariable=self.phrase_id,width=18).grid(row=2,column=1,padx=(230,0),sticky='w');ttk.Label(f,text='グループID').grid(row=2,column=2,sticky='w');ttk.Entry(f,textvariable=self.group_id,width=20).grid(row=2,column=2,padx=(80,0),sticky='w')
    bar=ttk.Frame(f);bar.grid(row=3,column=0,columnspan=3,sticky='w',pady=8)
    self.startbtn=ttk.Button(bar,text='● 録音開始',command=self.start);self.startbtn.pack(side='left',padx=3)
    self.stopbtn=ttk.Button(bar,text='■ 停止・保存',command=self.stop,state='disabled');self.stopbtn.pack(side='left',padx=3)
    ttk.Button(bar,text='クリック音',command=lambda:self.play(1000)).pack(side='left',padx=3);ttk.Button(bar,text='A4基準音',command=lambda:self.play(440)).pack(side='left',padx=3)
    ttk.Button(bar,text='MIDI読込',command=self.loadmidi).pack(side='left',padx=(15,3));ttk.Button(bar,text='歌詞TXT/LRC',command=self.loadlyrics).pack(side='left',padx=3)
    self.status=tk.StringVar(value='待機中');ttk.Label(f,textvariable=self.status).grid(row=4,column=0,columnspan=3,sticky='w')
    self.score=Score(f);self.score.grid(row=5,column=0,columnspan=3,sticky='nsew',pady=8)
    self.logbox=tk.Text(f,height=8);self.logbox.grid(row=6,column=0,columnspan=3,sticky='ew')
    self.log('注意: 基準音/クリック音はスピーカー出力です。録音への回り込みを避けるためヘッドホンを推奨します。')
    f.columnconfigure(1,weight=1);f.rowconfigure(5,weight=1)
 def log(self,s): self.logbox.insert('end',s+'\n');self.logbox.see('end')
 def pickroot(self):
    p=filedialog.askdirectory()
    if p:self.rootvar.set(p)
 def play(self,freq):
    try:tone(freq,.08 if freq==1000 else .6);self.status.set(f'{freq} Hz 出力')
    except Exception as e:messagebox.showerror('音声出力エラー',str(e))
 def loadmidi(self):
    p=filedialog.askopenfilename(filetypes=[('MIDI','*.mid *.midi')])
    if not p:return
    try:self.midi=load(p);self.midi_path=Path(p);self.update_score();self.log(f'MIDI: {p} / {len(self.midi.notes)} notes / {self.midi.duration:.2f}s')
    except Exception as e:messagebox.showerror('MIDIエラー',str(e))
 def loadlyrics(self):
    p=filedialog.askopenfilename(filetypes=[('歌詞','*.txt *.lrc')])
    if not p:return
    self.lyric_path=Path(p);text=self.lyric_path.read_text(encoding='utf-8-sig')
    if self.lyric_path.suffix.lower()=='.lrc':
      import re
      vals=[]
      for line in text.splitlines():
       stamps=re.findall(r'\\[(\\d{1,2}):(\\d{2})(?:\\.(\\d{1,3}))?\\]',line);ly=re.sub(r'\\[[^\\]]+\\]','',line).strip()
       for mm,ss,ff in stamps: vals.append((int(mm)*60+int(ss)+(float('0.'+ff) if ff else 0),ly))
      self.lyrics=[]
      for n in (self.midi.notes if self.midi else []):
       a=[ly for sec,ly in vals if sec<=n.start_sec];self.lyrics.append(a[-1] if a else '')
    else:self.lyrics=[c for c in text if not c.isspace()]
    self.update_score();self.log(f'歌詞: {p}')
 def update_score(self):
    if self.midi:self.score.setdata(self.midi,self.lyrics)
 def takeid(self,root):
    sid=self.session.get().zfill(2)[-2:];speaker=self.speaker.get().strip()
    folder=root/'raw'/'audio';folder.mkdir(parents=True,exist_ok=True)
    used=[]
    for p in folder.glob(f'{speaker}_{sid}*.wav'):
      tail=p.stem[len(speaker)+1:]
      if tail.startswith(sid) and tail[2:].isdigit():used.append(int(tail[2:]))
    return f'{speaker}_{sid}{max(used,default=0)+1:04d}'
 def start(self):
    try:
      root=Path(self.rootvar.get()).expanduser().resolve();root.mkdir(parents=True,exist_ok=True)
      if not self.speaker.get().strip():raise ValueError('話者IDを入力してください')
      if not self.session.get().isdigit() or len(self.session.get())>2:raise ValueError('セッションIDは1〜2桁の数字です')
      dev=None if self.dev.get()=='既定' else int(self.dev.get().split(':')[0])
      self.rootpath=root;self.stem=self.takeid(root);self.rec=Recorder(dev);self.rec.start();self.t0=time.monotonic();self.recording=True
      self.startbtn.configure(state='disabled');self.stopbtn.configure(state='normal');self.status.set('録音中');self.tick()
    except Exception as e:messagebox.showerror('録音開始エラー',str(e))
 def tick(self):
    if self.recording:self.status.set(f'録音中 {time.monotonic()-self.t0:.1f} 秒');self.after(100,self.tick)
 def stop(self):
    if not self.recording:return
    self.recording=False
    try:
      root=self.rootpath;stem=self.stem;audio=root/'raw'/'audio'/f'{stem}.wav';duration=self.rec.stop(audio)
      report=inspect(audio)
      meta={'version':'1.3.0-P2','metadata_schema_version':'1.0.0','created_at':datetime.now().astimezone().isoformat(),'speaker_id':self.speaker.get().strip(),'session_id':self.session.get().zfill(2),'take_id':stem,'audio':{'path':str(audio.relative_to(root)).replace('\\','/'),'sample_rate':44100,'channels':1,'subtype':'PCM_24','duration_sec':round(duration,6),'sha256':sha256_file(audio)},'qc':{'status':report['status'],'report_path':f'qc/{stem}.json'},'alignment':{'status':'not_available','note':'MIDI event reference is not the same as audio/phoneme alignment'}}
      for key,var in (('song_id',self.song_id),('phrase_id',self.phrase_id),('group_id',self.group_id)):
       value=var.get().strip()
       if value: meta[key]=value
      if self.midi_path:
       dst=root/'reference'/'midi'/f'{stem}{self.midi_path.suffix.lower()}';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(self.midi_path,dst);meta['midi_file']=str(dst.relative_to(root)).replace('\\','/')
       if self.midi:
        ann=build_note_reference(self.midi,self.lyrics)
        ap=root/'annotations'/'note'/f'{stem}.json';atomic_write_json(ap,ann)
        meta['note_annotation_file']=str(ap.relative_to(root)).replace('\\','/')
        meta['alignment']={'status':'midi_event_reference_pending_audio_alignment','note':'MIDIイベントの参照のみ。音声・音素境界の自動推定結果ではありません'}
      if self.lyric_path:
       dst=root/'reference'/'lyrics'/f'{stem}{self.lyric_path.suffix.lower()}';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(self.lyric_path,dst);meta['lyrics_file']=str(dst.relative_to(root)).replace('\\','/')
      validation=validate_metadata(meta)
      meta['validation']=validation
      if not validation['passed']: raise ValueError('メタデータ検証に失敗しました: '+'; '.join(validation['errors']))
      atomic_write_json(root/'metadata'/f'{stem}.json',meta)
      atomic_write_json(root/'qc'/f'{stem}.json',report)
      self.log(f'保存: {audio}');self.log('QC: '+json.dumps(report,ensure_ascii=False));self.log('メタデータ検証: PASS')
      self.status.set(f'保存完了: {stem}.wav ({duration:.2f}s) / QC {report["status"]}')
    except Exception as e:messagebox.showerror('保存エラー',str(e))
    finally:self.startbtn.configure(state='normal');self.stopbtn.configure(state='disabled')
def main():
 app=App();app.mainloop()
if __name__=='__main__':main()
