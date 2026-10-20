from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import json

from .config import Phase0Config
from .io_utils import ensure_dirs
from .builder import build_dataset, build_sample

def main():
    parser = argparse.ArgumentParser(
        prog="rg-dataset",
        description="RG Singing AI Phase 0 Dataset Builder"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create dataset directory structure")
    p_init.add_argument("--dataset", required=True, type=Path)

    p_build = sub.add_parser("build", help="Extract all WAV files")
    p_build.add_argument("--dataset", required=True, type=Path)
    p_build.add_argument("--config", type=Path, default=Path("config.yaml"))

    p_extract = sub.add_parser("extract", help="Extract one WAV")
    p_extract.add_argument("--dataset", required=True, type=Path)
    p_extract.add_argument("--audio", required=True)
    p_extract.add_argument("--config", type=Path, default=Path("config.yaml"))

    p_qc = sub.add_parser("qc", help="Print QC summary")
    p_qc.add_argument("--dataset", required=True, type=Path)

    args = parser.parse_args()

    if args.command == "init":
        ensure_dirs(args.dataset)
        print(f"Initialized: {args.dataset.resolve()}")
        return

    if args.command in {"build", "extract"}:
        cfg = Phase0Config.from_yaml(args.config)
        ensure_dirs(args.dataset)

        if args.command == "build":
            reports = build_dataset(args.dataset, cfg)
            ok = sum(r.get("status") == "ok" for r in reports)
            warn = sum(r.get("status") == "warning" for r in reports)
            err = sum(r.get("status") == "error" for r in reports)
            print(f"Processed: {len(reports)} | OK={ok} WARNING={warn} ERROR={err}")
        else:
            audio = Path(args.audio)
            if not audio.is_absolute():
                audio = args.dataset / "raw" / "audio" / audio
            report = build_sample(args.dataset, audio, cfg)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if args.command == "qc":
        p = args.dataset / "manifests" / "dataset_manifest.json"
        if not p.exists():
            print("No dataset manifest found. Run build first.")
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        for r in data["samples"]:
            print(f'{r.get("sample_id")}: {r.get("status")}')
