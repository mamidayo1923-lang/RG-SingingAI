from dataclasses import dataclass,asdict
from pathlib import Path
import json
@dataclass
class Config:
    sample_rate:int=44100; channels:int=1; blocksize:int=1024
    input_device:int|None=None; output_device:int|None=None
    bpm:float=120.; reference_hz:float=440.; click:bool=True; reference:bool=True
    preroll_beats:int=4; click_volume:float=.22; reference_volume:float=.12
    def save(self,p): Path(p).write_text(json.dumps(asdict(self),indent=2,ensure_ascii=False),encoding='utf-8')
    @classmethod
    def load(cls,p):
        try:
            d=json.loads(Path(p).read_text(encoding='utf-8')); return cls(**{k:v for k,v in d.items() if k in cls.__dataclass_fields__})
        except Exception:return cls()
