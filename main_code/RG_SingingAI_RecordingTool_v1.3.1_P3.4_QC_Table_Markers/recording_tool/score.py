import tkinter as tk
from tkinter import ttk
from .midi import pname
# Simplified treble-clef staff renderer; not a full music engraving engine.
LETTERS={0:0,2:1,4:2,5:3,7:4,9:5,11:6}
def step(p):
    octv=p//12-1; pc=p%12
    sharp={1:0,3:1,6:3,8:4,10:5}
    letter=sharp.get(pc,LETTERS.get(pc,0))
    return octv*7+letter-(4*7+2)
class Score(ttk.Frame):
    def __init__(self,master):
        super().__init__(master); self.notes=[]; self.lyrics=[]; self.zoom=1
        row=ttk.Frame(self); row.pack(fill='x')
        ttk.Label(row,text='ト音記号・歌詞付き簡易譜面').pack(side='left')
        ttk.Button(row,text='−',command=lambda:self.setzoom(self.zoom/1.15)).pack(side='right')
        ttk.Button(row,text='+',command=lambda:self.setzoom(self.zoom*1.15)).pack(side='right')
        self.c=tk.Canvas(self,bg='white',height=290); self.c.pack(fill='both',expand=True)
        self.xbar=ttk.Scrollbar(self,orient='horizontal',command=self.c.xview); self.xbar.pack(fill='x')
        self.c.configure(xscrollcommand=self.xbar.set)
    def setzoom(self,z): self.zoom=max(.5,min(2.5,z)); self.draw()
    def setdata(self,midi,lyrics):
        self.midi=midi; self.notes=midi.notes if midi else []; self.lyrics=lyrics; self.draw()
    def draw(self):
        c=self.c;c.delete('all'); z=self.zoom
        if not self.notes:
            c.create_text(15,20,anchor='nw',text='MIDIを読み込むと簡易譜面を表示します'); c.configure(scrollregion=(0,0,800,280)); return
        left=75*z; top=55*z; gap=10*z; scale=70*z
        width=max(850*z,left+(self.midi.duration+1)*scale)
        for i in range(5): c.create_line(left,top+i*gap,width,top+i*gap,fill='#222')
        c.create_text(28*z,top+2*gap,text='𝄞',font=('Segoe UI Symbol',int(34*z)))
        # Approximate bar grid from time signature; exact notation is outside this version's scope.
        tick=0; bar=0; max_tick=max(1,self.midi.total_ticks)
        sigs=self.midi.signatures
        while tick<=max_tick and bar<3000:
            sec=self.ticksec(tick); x=left+sec*scale
            c.create_line(x,top-6*z,x,top+4*gap+8*z,fill='#aaa',dash=(2,3))
            c.create_text(x+2,top-15*z,anchor='w',text=str(bar+1),fill='#666')
            active=sigs[0]
            for s in sigs:
                if s[0]<=tick: active=s
            length=max(1,int(self.midi.tpb*active[1]*4/active[2]))
            nexts=[s[0] for s in sigs if tick<s[0]<tick+length]
            nt=min(nexts) if nexts else tick+length
            if nt<=tick: break
            tick=nt;bar+=1
        for i,n in enumerate(self.notes):
            x=left+n.start_sec*scale; y=top+4*gap-step(n.pitch)*gap/2
            c.create_oval(x-5*z,y-3*z,x+5*z,y+3*z,fill='#111')
            c.create_line(x+4*z,y,x+4*z,y-25*z,fill='#111')
            nm=pname(n.pitch)
            if '#' in nm: c.create_text(x-9*z,y,text='♯',anchor='e',font=('Segoe UI Symbol',int(12*z)))
            if y<top or y>top+4*gap: c.create_line(x-8*z,y,x+8*z,y)
            if i<len(self.lyrics) and self.lyrics[i]:
                c.create_text(x,top+4*gap+22*z,text=self.lyrics[i],font=('Yu Gothic UI',max(7,int(10*z))))
            c.create_text(x,top+4*gap+36*z,text=nm,fill='#666',font=('Segoe UI',max(6,int(8*z))))
        c.configure(scrollregion=(0,0,width,top+4*gap+55*z))
    def ticksec(self,target):
        sec,last,tempo=0.,0,500000
        for t,tm in self.midi.tempos:
            if t==0: tempo=tm; continue
            if t>=target: break
            sec+=(t-last)*tempo/self.midi.tpb/1e6;last,tempo=t,tm
        return sec+(target-last)*tempo/self.midi.tpb/1e6
