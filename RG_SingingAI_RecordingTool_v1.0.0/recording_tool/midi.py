from dataclasses import dataclass
@dataclass
class Note:
 start:float;end:float;number:int;velocity:int
 @property
 def name(self):return ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][self.number%12]+str(self.number//12-1)
def load(path):
 import mido
 mid=mido.MidiFile(str(path));now=0.;active={};notes=[]
 for msg in mid:
  now+=msg.time
  if msg.type=='note_on' and msg.velocity:active[(msg.channel,msg.note)]=(now,msg.velocity)
  elif msg.type=='note_off' or (msg.type=='note_on' and not msg.velocity):
   k=(msg.channel,msg.note)
   if k in active:s,v=active.pop(k);notes.append(Note(s,now,msg.note,v))
 return sorted(notes,key=lambda x:x.start)
