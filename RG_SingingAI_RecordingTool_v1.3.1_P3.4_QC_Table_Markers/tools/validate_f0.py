from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate extracted F0 without modifying source features."
    )
    parser.add_argument("npz", help="Input feature NPZ")
    parser.add_argument(
        "--csv",
        default=None,
        help="Output CSV path (default: <input>_f0_qc.csv)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.35,
        help="Low-confidence warning threshold",
    )
    parser.add_argument(
        "--rms-threshold",
        type=float,
        default=1e-4,
        help="Low-RMS warning threshold",
    )
    parser.add_argument(
        "--jump-cents",
        type=float,
        default=700.0,
        help="Flag adjacent voiced F0 changes exceeding this many cents",
    )
    args = parser.parse_args()

    if not 0.0 <= args.confidence_threshold <= 1.0:
        parser.error("--confidence-threshold must be in [0, 1]")
    if args.rms_threshold < 0:
        parser.error("--rms-threshold must be >= 0")
    if args.jump_cents <= 0:
        parser.error("--jump-cents must be > 0")

    source = Path(args.npz).expanduser().resolve()
    if not source.is_file():
        parser.error(f"NPZ not found: {source}")

    output = (
        Path(args.csv).expanduser().resolve()
        if args.csv
        else source.with_name(source.stem + "_f0_qc.csv")
    )

    with np.load(source, allow_pickle=False) as data:
        required = (
            "frame_times_sec",
            "f0_hz",
            "f0_confidence_proxy",
            "frame_rms",
        )
        missing = [key for key in required if key not in data]
        if missing:
            parser.error("Missing NPZ arrays: " + ", ".join(missing))

        times = np.asarray(data["frame_times_sec"], dtype=np.float64)
        f0 = np.asarray(data["f0_hz"], dtype=np.float64)
        confidence = np.asarray(data["f0_confidence_proxy"], dtype=np.float64)
        rms = np.asarray(data["frame_rms"], dtype=np.float64)

    n = len(times)
    if any(len(a) != n for a in (f0, confidence, rms)):
        parser.error("Feature arrays have inconsistent frame counts")
    if not all(np.isfinite(a).all() for a in (times, f0, confidence, rms)):
        parser.error("Input contains NaN or infinite values")

    voiced = f0 > 0
    low_confidence = confidence < args.confidence_threshold
    low_rms = rms < args.rms_threshold

    jump_cents = np.full(n, np.nan, dtype=np.float64)
    jump_cents[0] = np.nan if n else np.nan

    for i in range(1, n):
        if voiced[i - 1] and voiced[i]:
            jump_cents[i] = abs(1200.0 * np.log2(f0[i] / f0[i - 1]))

    large_jump = np.isfinite(jump_cents) & (jump_cents > args.jump_cents)

    # These are review flags, not automatic corrections or proof of errors.
    rows = []
    for i in range(n):
        flags = []
        if not voiced[i]:
            flags.append("f0_unvoiced_or_unestimated")
        if low_confidence[i]:
            flags.append("low_confidence_proxy")
        if low_rms[i]:
            flags.append("low_rms")
        if large_jump[i]:
            flags.append("large_adjacent_f0_jump")

        rows.append({
            "frame_index": i,
            "time_sec": f"{times[i]:.6f}",
            "f0_hz_original": f"{f0[i]:.6f}",
            "confidence_proxy": f"{confidence[i]:.6f}",
            "frame_rms": f"{rms[i]:.8f}",
            "jump_cents_from_previous": (
                f"{jump_cents[i]:.2f}" if np.isfinite(jump_cents[i]) else ""
            ),
            "voiced_candidate": int(voiced[i]),
            "large_jump_candidate": int(large_jump[i]),
            "flags": ";".join(flags) if flags else "none",
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else [
        "frame_index", "time_sec", "f0_hz_original",
        "confidence_proxy", "frame_rms",
        "jump_cents_from_previous", "voiced_candidate",
        "large_jump_candidate", "flags",
    ]
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Input: {source}")
    print(f"CSV: {output}")
    print(f"Frames: {n}")
    print(f"Voiced F0 candidates: {int(voiced.sum())}/{n}")
    print(f"Low-confidence frames: {int(low_confidence.sum())}/{n}")
    print(f"Low-RMS frames: {int(low_rms.sum())}/{n}")
    print(f"Large adjacent F0 jumps: {int(large_jump.sum())}/{n}")
    print("Original F0 values were not modified.")
    print("Flags are review candidates, not confirmed errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
