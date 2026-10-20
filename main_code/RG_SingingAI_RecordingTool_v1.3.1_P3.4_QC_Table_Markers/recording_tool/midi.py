from dataclasses import dataclass
from pathlib import Path
import mido
NAMES=('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
def pname(n): return f'{NAMES[n%12]}{n//12-1}'
@dataclass
class Note:
    pitch:int; velocity:int; start:int; end:int; start_sec:float=0; end_sec:float=0
@dataclass
class Midi:
    notes:list; tempos:list; signatures:list; tpb:int; total_ticks:int; duration:float
def load(path):
    mf=mido.MidiFile(str(path)); events=[]
    for ti,tr in enumerate(mf.tracks):
        t=0
        for m in tr:
            t+=m.time; events.append((t,ti,m))
    events.sort(key=lambda e:(e[0],e[1]))
    tempos=[(0,500000)]; sigs=[(0,4,4)]; active={}; notes=[]; total=0
    for t,ti,m in events:
        total=max(total,t)
        if m.type=='set_tempo': tempos.append((t,m.tempo))
        elif m.type=='time_signature': sigs.append((t,m.numerator,m.denominator))
        elif m.type=='note_on' and m.velocity:
            active.setdefault((ti,m.channel,m.note),[]).append((t,m.velocity))
        elif m.type=='note_off' or (m.type=='note_on' and not m.velocity):
            q=active.get((ti,m.channel,m.note),[])
            if q:
                s,v=q.pop(0); notes.append(Note(m.note,v,s,max(s+1,t)))
    for q in active.values():
        for s,v in q: notes.append(Note(60,v,s,max(s+1,total)))
    tempos=sorted(set(tempos)); sigs=sorted(set(sigs))
    def sec(target):
        out,last,tempo=0.,0,500000
        for t,tm in tempos:
            if t==0: tempo=tm; continue
            if t>=target: break
            out+=(t-last)*tempo/mf.ticks_per_beat/1e6; last,tempo=t,tm
        return out+(target-last)*tempo/mf.ticks_per_beat/1e6
    for n in notes: n.start_sec,n.end_sec=sec(n.start),sec(n.end)
    notes.sort(key=lambda n:(n.start,n.pitch))
    return Midi(notes,tempos,sigs,mf.ticks_per_beat,total,sec(total))
