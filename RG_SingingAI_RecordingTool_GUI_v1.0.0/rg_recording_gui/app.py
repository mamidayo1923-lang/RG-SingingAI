from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading, time, json, re
from .backend import RecordingBackend, RecordingSettings

BLUE="#087BFF"; BLUE_DARK="#0759C7"; BG="#F5F8FC"; PANEL="#FFFFFF"; TEXT="#182335"; MUTED="#6C7A90"; LINE="#DCE5F0"; CYAN="#20C8F5"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RG Singing AI Recording Tool")
        self.geometry("1420x900"); self.minsize(1120,720); self.configure(bg=BG)
        self.backend=RecordingBackend(); self.recording_started=None; self.timer_job=None
        self.output_dir=tk.StringVar(value=str(Path.home()/"RG_SingingAI_Recordings"))
        self.speaker=tk.StringVar(value="SPK001"); self.session=tk.StringVar(value="SESSION001")
        self.take=tk.IntVar(value=1); self.rate=tk.StringVar(value="44100")
        self.device=tk.StringVar(value="既定の入力デバイス")
        self.status=tk.StringVar(value="待機中"); self.elapsed=tk.StringVar(value="00:00.0")
        self.midi_label=tk.StringVar(value="MIDI未読み込み"); self.lyrics=tk.StringVar(value="歌詞を入力、または .txt / .lrc ファイルを読み込んでください。")
        self.notes=[]; self.lyric_path=None; self._build(); self._refresh_devices()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        style=ttk.Style(self); style.theme_use("clam")
        style.configure("TFrame", background=BG); style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Yu Gothic UI",10))
        style.configure("Title.TLabel", font=("Yu Gothic UI",17,"bold"), foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Primary.TButton", font=("Yu Gothic UI",10,"bold"), background=BLUE, foreground="white", padding=(14,9))
        style.map("Primary.TButton", background=[("active",BLUE_DARK)])
        style.configure("TButton", padding=(10,7), font=("Yu Gothic UI",10))
        style.configure("TEntry", padding=6); style.configure("TCombobox", padding=5)
        top=tk.Frame(self,bg="white",height=68,highlightbackground=LINE,highlightthickness=1); top.pack(fill="x")
        tk.Label(top,text="RG",bg="white",fg=BLUE,font=("Yu Gothic UI",22,"bold")).pack(side="left",padx=(22,10),pady=10)
        tk.Label(top,text="SINGING AI",bg="white",fg=TEXT,font=("Yu Gothic UI",15,"bold")).pack(side="left")
        tk.Label(top,text="RECORDING TOOL  /  v1.0.0",bg="white",fg=MUTED,font=("Yu Gothic UI",9)).pack(side="left",padx=18)
        tk.Label(top,text="●  LOCAL WORKSPACE",bg="white",fg=BLUE,font=("Yu Gothic UI",9,"bold")).pack(side="right",padx=22)
        body=tk.Frame(self,bg=BG); body.pack(fill="both",expand=True,padx=18,pady=16)
        nav=tk.Frame(body,bg="#FFFFFF",width=185,highlightbackground=LINE,highlightthickness=1); nav.pack(side="left",fill="y",padx=(0,14)); nav.pack_propagate(False)
        tk.Label(nav,text="ワークスペース",bg="white",fg=MUTED,font=("Yu Gothic UI",9,"bold")).pack(anchor="w",padx=16,pady=(20,10))
        for i,(label,active) in enumerate([("⌂  ホーム",False),("●  レコーディング",True),("♫  MIDI / 楽譜",False),("▤  テイク管理",False),("✓  QC・メタデータ",False),("⚙  設定",False)]):
            b=tk.Label(nav,text=label,bg="#EAF3FF" if active else "white",fg=BLUE if active else TEXT,anchor="w",padx=15,pady=12,font=("Yu Gothic UI",10,"bold" if active else "normal"))
            b.pack(fill="x",padx=8,pady=2)
        tk.Label(nav,text="データ保存先",bg="white",fg=MUTED,font=("Yu Gothic UI",9,"bold")).pack(anchor="w",padx=16,pady=(24,4))
        tk.Label(nav,textvariable=self.output_dir,bg="white",fg=TEXT,wraplength=150,justify="left",font=("Yu Gothic UI",8)).pack(anchor="w",padx=16)
        ttk.Button(nav,text="保存先を変更",command=self._choose_dir).pack(fill="x",padx=12,pady=10)
        main=tk.Frame(body,bg=BG); main.pack(side="left",fill="both",expand=True)
        head=tk.Frame(main,bg=BG); head.pack(fill="x",pady=(0,12))
        tk.Label(head,text="レコーディング",bg=BG,fg=TEXT,font=("Yu Gothic UI",21,"bold")).pack(side="left")
        tk.Label(head,text="録音・MIDI・歌詞をまとめて管理",bg=BG,fg=MUTED,font=("Yu Gothic UI",10)).pack(side="left",padx=15,pady=(8,0))
        grid=tk.Frame(main,bg=BG); grid.pack(fill="both",expand=True)
        grid.columnconfigure(0,weight=3); grid.columnconfigure(1,weight=2); grid.rowconfigure(1,weight=1)
        meta=self._panel(grid,0,0,"プロジェクト / テイク情報")
        fields=tk.Frame(meta,bg="white"); fields.pack(fill="x",padx=14,pady=(2,14))
        for col,(label,var) in enumerate([("Speaker ID",self.speaker),("Session ID",self.session)]):
            tk.Label(fields,text=label,bg="white",fg=MUTED,font=("Yu Gothic UI",9)).grid(row=0,column=col,sticky="w",padx=(0,12),pady=(4,5))
            ttk.Entry(fields,textvariable=var,width=22).grid(row=1,column=col,sticky="ew",padx=(0,12))
        tk.Label(fields,text="Take No.",bg="white",fg=MUTED,font=("Yu Gothic UI",9)).grid(row=0,column=2,sticky="w",pady=(4,5))
        ttk.Spinbox(fields,from_=1,to=9999,textvariable=self.take,width=8).grid(row=1,column=2,sticky="ew")
        fields.columnconfigure(0,weight=1); fields.columnconfigure(1,weight=1)
        score=self._panel(grid,1,0,"楽譜 / 歌詞",stretch=True)
        bar=tk.Frame(score,bg="white"); bar.pack(fill="x",padx=14,pady=(0,8))
        ttk.Button(bar,text="MIDIを読み込む",command=self._load_midi).pack(side="left")
        ttk.Button(bar,text="歌詞ファイル",command=self._load_lyrics).pack(side="left",padx=7)
        ttk.Button(bar,text="歌詞を保存",command=self._save_lyrics).pack(side="left")
        tk.Label(bar,textvariable=self.midi_label,bg="white",fg=MUTED,font=("Yu Gothic UI",9)).pack(side="right")
        self.canvas=tk.Canvas(score,bg="white",height=255,highlightthickness=0); self.canvas.pack(fill="both",expand=True,padx=10)
        self.canvas.bind("<Configure>",lambda e:self._draw_score())
        tk.Label(score,text="歌詞テキスト（1行またはモーラごとにスペース区切り）",bg="white",fg=MUTED,font=("Yu Gothic UI",9)).pack(anchor="w",padx=14,pady=(8,3))
        self.lyrics_text=tk.Text(score,height=3,wrap="word",font=("Yu Gothic UI",10),relief="solid",bd=1,highlightthickness=1,highlightbackground=LINE)
        self.lyrics_text.pack(fill="x",padx=14,pady=(0,14)); self.lyrics_text.insert("1.0",self.lyrics.get())
        transport=self._panel(grid,2,0,"録音コントロール")
        ctl=tk.Frame(transport,bg="white"); ctl.pack(fill="x",padx=14,pady=(0,14))
        self.rec_btn=ttk.Button(ctl,text="●  録音開始",style="Primary.TButton",command=self._toggle_record); self.rec_btn.pack(side="left")
        tk.Label(ctl,textvariable=self.elapsed,bg="white",fg=TEXT,font=("Consolas",18,"bold")).pack(side="left",padx=18)
        self.status_lbl=tk.Label(ctl,textvariable=self.status,bg="#EAF3FF",fg=BLUE,font=("Yu Gothic UI",9,"bold"),padx=10,pady=6); self.status_lbl.pack(side="left")
        tk.Label(ctl,text="※ クリック音はヘッドホン使用を推奨",bg="white",fg=MUTED,font=("Yu Gothic UI",9)).pack(side="right")
        side=tk.Frame(grid,bg=BG); side.grid(row=0,column=1,rowspan=3,sticky="nsew",padx=(14,0)); side.columnconfigure(0,weight=1)
        audio=self._panel(side,0,0,"オーディオ設定")
        for label,widget in [
            ("入力デバイス",ttk.Combobox(audio,textvariable=self.device,state="readonly")),
            ("サンプルレート",ttk.Combobox(audio,textvariable=self.rate,values=["44100","48000"],state="readonly"))]:
            tk.Label(audio,text=label,bg="white",fg=MUTED,font=("Yu Gothic UI",9)).pack(anchor="w",padx=14,pady=(5,3)); widget.pack(fill="x",padx=14,pady=(0,8))
            if label=="入力デバイス": self.device_combo=widget
        self.click_var=tk.BooleanVar(value=True); self.ref_var=tk.BooleanVar(value=False)
        ttk.Checkbutton(audio,text="クリック音（準備中）",variable=self.click_var).pack(anchor="w",padx=14,pady=3)
        ttk.Checkbutton(audio,text="基準音（準備中）",variable=self.ref_var).pack(anchor="w",padx=14,pady=3)
        tk.Label(audio,text="入力レベル",bg="white",fg=MUTED,font=("Yu Gothic UI",9)).pack(anchor="w",padx=14,pady=(12,4))
        self.level=tk.Canvas(audio,height=14,bg="#E7EDF5",highlightthickness=0); self.level.pack(fill="x",padx=14,pady=(0,14)); self.level.create_rectangle(0,0,18,14,fill=CYAN,outline="")
        takepanel=self._panel(side,1,0,"直近の録音")
        self.recent=tk.Listbox(takepanel,height=9,relief="flat",font=("Yu Gothic UI",9),bg="white",fg=TEXT,selectbackground="#D9EAFF")
        self.recent.pack(fill="both",expand=True,padx=10,pady=(0,10))
        qc=self._panel(side,2,0,"QC / システム状態")
        for line in ["●  WAV: PCM 24-bit","●  チャンネル: Mono","●  保存先: ローカル","○  ピーク / クリッピング解析"]:
            tk.Label(qc,text=line,bg="white",fg=BLUE if line.startswith("●") else MUTED,font=("Yu Gothic UI",9)).pack(anchor="w",padx=14,pady=4)
        self._draw_score()

    def _panel(self,parent,row,col,title,stretch=False):
        frame=tk.Frame(parent,bg="white",highlightbackground=LINE,highlightthickness=1)
        if parent.winfo_class()=="Frame" and parent is not None:
            if parent==self: pass
        if parent is not None and parent==getattr(self,"_main_dummy",None): pass
        # parent is grid container or side; use grid for panel layout
        frame.grid(row=row,column=col,sticky="nsew",pady=(0,12))
        if stretch: frame.grid_propagate(True)
        tk.Label(frame,text=title,bg="white",fg=TEXT,font=("Yu Gothic UI",11,"bold")).pack(anchor="w",padx=14,pady=(12,10))
        return frame

    def _refresh_devices(self):
        devices=self.backend.devices()
        vals=["既定の入力デバイス"]+[f"{i}: {name}" for i,name in devices]
        self.device_combo["values"]=vals
        if self.device.get() not in vals: self.device.set(vals[0])

    def _choose_dir(self):
        d=filedialog.askdirectory(initialdir=self.output_dir.get())
        if d: self.output_dir.set(d)

    def _load_midi(self):
        path=filedialog.askopenfilename(filetypes=[("MIDI files","*.mid *.midi"),("All files","*.*")])
        if not path:return
        try:
            import mido
            mid=mido.MidiFile(path); tempo=500000; tpb=mid.ticks_per_beat; active={}; notes=[]; absolute=0
            for msg in mid:
                absolute+=msg.time
                if msg.type=="set_tempo": tempo=msg.tempo
                if msg.type=="note_on" and msg.velocity>0: active[(msg.channel,msg.note)]=(absolute,msg.velocity)
                elif msg.type=="note_off" or (msg.type=="note_on" and msg.velocity==0):
                    key=(msg.channel,msg.note)
                    if key in active:
                        start,vel=active.pop(key); notes.append((start/tpb,msg.note,max(.05,(absolute-start)/tpb),vel))
            self.notes=sorted(notes,key=lambda n:n[0]); self.midi_label.set(f"{Path(path).name} / {len(notes)} notes")
            self._draw_score()
        except Exception as e: messagebox.showerror("MIDI読み込みエラー",f"MIDIを解析できませんでした。\n{e}")

    def _load_lyrics(self):
        p=filedialog.askopenfilename(filetypes=[("歌詞","*.txt *.lrc"),("All files","*.*")])
        if not p:return
        try:
            self.lyrics_text.delete("1.0","end"); self.lyrics_text.insert("1.0",Path(p).read_text(encoding="utf-8-sig")); self.lyric_path=p
        except Exception as e: messagebox.showerror("読み込みエラー",str(e))

    def _save_lyrics(self):
        p=filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Text","*.txt")])
        if p: Path(p).write_text(self.lyrics_text.get("1.0","end-1c"),encoding="utf-8")

    def _draw_score(self):
        if not hasattr(self,"canvas"): return
        c=self.canvas; c.delete("all"); w=max(600,c.winfo_width()); h=max(200,c.winfo_height())
        x0=65; x1=w-25; y0=55; spacing=12
        # staff lines and treble clef glyph
        for i in range(5): c.create_line(x0,y0+i*spacing,x1,y0+i*spacing,fill="#8796AA",width=1)
        c.create_text(28,y0+25,text="𝄞",font=("Segoe UI Symbol",36),fill=BLUE)
        for x in range(x0+10,x1,160):
            c.create_line(x,y0-10,x,y0+58,fill=LINE,dash=(2,3))
        lyrics=re.sub(r"\s+"," ",self.lyrics_text.get("1.0","end-1c").strip()).split(" ") if hasattr(self,"lyrics_text") else []
        if not self.notes:
            for i in range(4): c.create_text(x0+40+i*150,y0+26,text=["MIDIを読み込むと","ノートと歌詞を","ここに表示します",""][i],anchor="w",fill=MUTED,font=("Yu Gothic UI",10))
            return
        minbeat=min(n[0] for n in self.notes); maxbeat=max(n[0]+n[2] for n in self.notes); span=max(4,maxbeat-minbeat)
        usable=max(300,x1-x0); px=usable/span
        def ypitch(pitch): return y0+48-(pitch-60)*3
        for idx,(beat,pitch,dur,vel) in enumerate(self.notes):
            x=x0+(beat-minbeat)*px; y=ypitch(pitch); xe=x+max(8,dur*px)
            # note stem/head and duration bar
            c.create_oval(x-5,y-3,x+5,y+3,fill=BLUE,outline=BLUE)
            c.create_line(x+4,y,x+4,y-27,fill=BLUE,width=2)
            if dur>=.8: c.create_line(x+5,y-27,x+16,y-20,fill=BLUE,width=2)
            if idx<len(lyrics): c.create_text(x,y+20,text=lyrics[idx],fill=TEXT,font=("Yu Gothic UI",10))
        c.create_text(x1-5,18,text=f"{len(self.notes)} notes",anchor="e",fill=MUTED,font=("Yu Gothic UI",9))

    def _toggle_record(self):
        if not self.backend.recording:
            try:
                device=None
                m=re.match(r"(\d+):",self.device.get())
                if m: device=int(m.group(1))
                settings=RecordingSettings(Path(self.output_dir.get()),int(self.rate.get()),1,3,device)
                self.backend.start(settings); self.recording_started=time.monotonic()
                self.status.set("録音中"); self.rec_btn.configure(text="■  録音停止")
                self.status_lbl.configure(bg="#FFE8EA",fg="#C62B43"); self._tick()
            except Exception as e:
                messagebox.showerror("録音を開始できません",f"入力デバイスを確認してください。\n\n{e}")
        else:
            try:
                path,duration=self.backend.stop(self.speaker.get().strip(),self.session.get().strip(),int(self.take.get()))
                self.recent.insert(0,f"{path.name}  ({duration:.1f}s)")
                self.take.set(int(self.take.get())+1); self.status.set("保存完了"); self.elapsed.set(f"{int(duration//60):02d}:{duration%60:04.1f}")
                self.rec_btn.configure(text="●  録音開始"); self.status_lbl.configure(bg="#EAF3FF",fg=BLUE)
                messagebox.showinfo("録音を保存しました",f"WAVとメタデータを保存しました。\n\n{path}")
            except Exception as e: messagebox.showerror("保存エラー",str(e))
    def _tick(self):
        if self.backend.recording:
            sec=time.monotonic()-self.recording_started; self.elapsed.set(f"{int(sec//60):02d}:{sec%60:04.1f}")
            self.timer_job=self.after(100,self._tick)
    def _close(self):
        if self.backend.recording:
            if not messagebox.askyesno("終了確認","録音中です。録音を破棄して終了しますか？"): return
            try: self.backend._stream.stop(); self.backend._stream.close()
            except: pass
        self.destroy()

def main():
    app=App(); app.mainloop()
