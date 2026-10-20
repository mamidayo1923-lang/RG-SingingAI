import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recording_tool.dataset_split import make_splits

def main():
    ap=argparse.ArgumentParser(description='Create group-aware train/validation/test split manifest from metadata JSON files')
    ap.add_argument('--metadata-dir',default='RG_SingingAI_Dataset/metadata')
    ap.add_argument('--output',default='RG_SingingAI_Dataset/splits/split_manifest.json')
    ap.add_argument('--seed',type=int,default=20261015)
    ap.add_argument('--group-key',choices=['group_id','phrase_id','song_id','source_group_id'])
    a=ap.parse_args(); rows=[]
    for p in sorted(Path(a.metadata_dir).glob('*.json')):
        d=json.loads(p.read_text(encoding='utf-8')); d.setdefault('take_id',p.stem); rows.append(d)
    manifest=make_splits(rows,seed=a.seed,group_key=a.group_key)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Wrote {out}: {manifest['item_counts']}; group counts={manifest['group_counts']}")
if __name__=='__main__': main()
