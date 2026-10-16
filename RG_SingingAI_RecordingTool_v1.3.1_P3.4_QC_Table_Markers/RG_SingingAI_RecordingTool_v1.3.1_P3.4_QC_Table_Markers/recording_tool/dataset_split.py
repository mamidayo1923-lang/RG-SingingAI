"""Group-aware train/validation/test splitting to prevent phrase/song leakage."""
from collections import defaultdict
import random

SPLIT_SCHEMA_VERSION = "1.0.0"

def make_splits(rows, seed=20261015, ratios=(0.8, 0.1, 0.1), group_key=None):
    if len(ratios) != 3 or any(r < 0 for r in ratios) or abs(sum(ratios)-1.0) > 1e-8:
        raise ValueError("ratios must be three non-negative values summing to 1")
    if not rows: raise ValueError("No metadata rows supplied")
    groups=defaultdict(list)
    candidate_keys=(group_key,) if group_key else ("group_id","phrase_id","song_id","source_group_id")
    key=next((k for k in candidate_keys if k and all(row.get(k) not in (None, "") for row in rows)), None)
    if not key:
        raise ValueError("All metadata rows must share one non-empty grouping field: group_id, phrase_id, song_id, or source_group_id. Use the same field consistently to prevent leakage.")
    for row in rows:
        groups[str(row[key])].append(row)
    keys=sorted(groups)
    random.Random(seed).shuffle(keys)
    # Assign whole groups using target item counts, never splitting a group.
    targets=[len(rows)*r for r in ratios]; bins=[[],[],[]]; counts=[0,0,0]
    for group in sorted(keys, key=lambda k: len(groups[k]), reverse=True):
        idx=min(range(3), key=lambda i: (counts[i]-targets[i], counts[i]/max(targets[i],1)))
        bins[idx].append(group); counts[idx]+=len(groups[group])
    names=("train","validation","test")
    splits={name:[] for name in names}
    for i,name in enumerate(names):
        for g in sorted(bins[i]): splits[name].extend(sorted(groups[g],key=lambda r:str(r.get('take_id',''))))
    return {"split_schema_version":SPLIT_SCHEMA_VERSION,"seed":seed,"ratios":{"train":ratios[0],"validation":ratios[1],"test":ratios[2]},"grouping_key":group_key or "first_available_group_id/phrase_id/song_id/source_group_id","group_counts":{name:len(bins[i]) for i,name in enumerate(names)},"item_counts":{name:len(splits[name]) for name in names},"splits":splits}
