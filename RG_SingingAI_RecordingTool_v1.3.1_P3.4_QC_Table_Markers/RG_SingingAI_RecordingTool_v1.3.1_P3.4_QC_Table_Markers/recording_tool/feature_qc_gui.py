from __future__ import annotations

import csv
import json
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import soundfile as sf

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    import matplotlib
    matplotlib.use("TkAgg")
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False

from recording_tool.analysis import extract_p2_features


class FeatureQCApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RG Singing AI — Feature & F0 QC")
        self.geometry("1320x860")
        self.minsize(1000, 680)
        self.configure(bg="#f5f8fc")
        self.wav_path = None
        self.npz_path = None
        self.data = None
        self.qc_rows = []
        self.busy = False
        self._style()
        self._build_ui()
        if not MATPLOTLIB_OK:
            messagebox.showerror("依存関係不足", "matplotlib が必要です。\nPowerShellで .\\.venv\\Scripts\\python.exe -m pip install matplotlib を実行してください。")

    def _style(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except tk.TclError: pass
        s.configure("TFrame", background="#f5f8fc")
        s.configure("TLabel", background="#f5f8fc", foreground="#1e293b", font=("Yu Gothic UI", 10))
        s.configure("Title.TLabel", font=("Yu Gothic UI", 17, "bold"), foreground="#102a43")
        s.configure("TButton", font=("Yu Gothic UI", 10), padding=7)
        s.configure("Accent.TButton", background="#087cf0", foreground="white", padding=8)
        s.map("Accent.TButton", background=[("active", "#0066d0")])
        s.configure("Treeview", rowheight=25, font=("Yu Gothic UI", 9))
        s.configure("Treeview.Heading", font=("Yu Gothic UI", 9, "bold"))

    def _build_ui(self):
        top = ttk.Frame(self, padding=(16, 12))
        top.pack(fill="x")
        ttk.Label(top, text="RG Singing AI  /  音声特徴量・F0 品質検証", style="Title.TLabel").pack(side="left")
        self.status = tk.StringVar(value="WAV または NPZ を読み込んでください")
        ttk.Label(top, textvariable=self.status).pack(side="right")

        files = ttk.LabelFrame(self, text="入力と処理", padding=10)
        files.pack(fill="x", padx=16, pady=(0, 8))
        self.wav_var = tk.StringVar()
        self.npz_var = tk.StringVar()
        row1 = ttk.Frame(files); row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="WAV").pack(side="left")
        ttk.Entry(row1, textvariable=self.wav_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row1, text="選択…", command=self.choose_wav).pack(side="left", padx=3)
        ttk.Button(row1, text="特徴量を抽出してNPZ保存", style="Accent.TButton", command=self.extract).pack(side="left", padx=3)
        row2 = ttk.Frame(files); row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="NPZ").pack(side="left")
        ttk.Entry(row2, textvariable=self.npz_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row2, text="選択…", command=self.choose_npz).pack(side="left", padx=3)
        ttk.Button(row2, text="NPZを読み込む", command=self.load_npz).pack(side="left", padx=3)
        ttk.Button(row2, text="QC検証を実行", style="Accent.TButton", command=self.run_qc).pack(side="left", padx=3)
        ttk.Button(row2, text="QC CSVを保存…", command=self.save_csv).pack(side="left", padx=3)

        settings = ttk.LabelFrame(self, text="QC 閾値（診断用。自動修正は行いません）", padding=8)
        settings.pack(fill="x", padx=16, pady=(0, 8))
        self.conf_var = tk.StringVar(value="0.35")
        self.rms_var = tk.StringVar(value="0.0001")
        self.jump_var = tk.StringVar(value="700")
        for label, var, width in [("信頼度プロキシ下限", self.conf_var, 8), ("RMS下限", self.rms_var, 10), ("F0ジャンプ閾値 (cents)", self.jump_var, 8)]:
            ttk.Label(settings, text=label).pack(side="left", padx=(5, 3))
            ttk.Entry(settings, textvariable=var, width=width).pack(side="left", padx=(0, 12))
        self.summary = tk.StringVar(value="特徴量未読み込み")
        ttk.Label(settings, textvariable=self.summary).pack(side="right", padx=8)

        main = ttk.Panedwindow(self, orient="vertical")
        main.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        chart_frame = ttk.LabelFrame(main, text="時系列グラフ（ツールバーで拡大・移動可能）", padding=6)
        table_frame = ttk.LabelFrame(main, text="QC フレーム一覧 — 行を選択すると該当時刻を強調", padding=6)
        main.add(chart_frame, weight=3); main.add(table_frame, weight=2)

        self.selected_info = tk.StringVar(value="検出箇所を選択すると、グラフを該当時刻へ移動します")
        inspect_bar = ttk.Frame(chart_frame)
        inspect_bar.pack(fill="x", pady=(0, 4))
        ttk.Label(inspect_bar, textvariable=self.selected_info).pack(side="left", fill="x", expand=True)
        ttk.Button(inspect_bar, text="全体表示", command=self.show_full_plot).pack(side="right")

        if MATPLOTLIB_OK:
            self.fig = Figure(figsize=(10, 5.2), dpi=100, constrained_layout=True)
            self.ax_f0 = self.fig.add_subplot(311)
            self.ax_conf = self.fig.add_subplot(312, sharex=self.ax_f0)
            self.ax_rms = self.fig.add_subplot(313, sharex=self.ax_f0)
            self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            toolbar = NavigationToolbar2Tk(self.canvas, chart_frame, pack_toolbar=False)
            toolbar.update(); toolbar.pack(fill="x")
        cols = ("frame", "time", "f0", "confidence", "rms", "jump", "flags")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        # Color-coded table markers match the markers drawn on the plots.
        self.tree.tag_configure("qc_jump", foreground="#dc2626")
        self.tree.tag_configure("qc_conf", foreground="#c2410c")
        self.tree.tag_configure("qc_rms", foreground="#b91c1c")
        self.tree.tag_configure("qc_multi", foreground="#7c3aed")
        labels = {"frame":"Frame", "time":"時刻 (s)", "f0":"F0 (Hz)", "confidence":"信頼度", "rms":"RMS", "jump":"変化 (cents)", "flags":"検出フラグ"}
        widths = {"frame":70, "time":100, "f0":100, "confidence":100, "rms":110, "jump":120, "flags":420}
        for c in cols:
            self.tree.heading(c, text=labels[c]); self.tree.column(c, width=widths[c], anchor="w")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.log = tk.Text(self, height=5, wrap="word", bg="#ffffff", fg="#334155", font=("Consolas", 9))
        self.log.pack(fill="x", padx=16, pady=(0, 12))
        self.log.configure(state="disabled")
        self._log("グラフ上の赤い×=大きなF0ジャンプ、橙色の丸=低信頼度、赤丸=低RMS。QC一覧の行を選択すると該当時刻を赤い破線で示し、前後1.5秒を拡大します。")
        self._log("元NPZは読み取り専用で扱います。F0・HNR・フォルマント等の推定値は診断用であり、正解値ではありません。")

    def _log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def choose_wav(self):
        p = filedialog.askopenfilename(title="WAVを選択", filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")])
        if p:
            self.wav_path = Path(p); self.wav_var.set(p)
            try:
                info = sf.info(p)
                self._log(f"WAV: {p} | {info.samplerate} Hz / {info.channels} ch / {info.duration:.3f} s / {info.subtype}")
            except Exception as e: self._log(f"WAV情報取得エラー: {e}")

    def choose_npz(self):
        p = filedialog.askopenfilename(title="特徴量NPZを選択", filetypes=[("NPZ", "*.npz"), ("All files", "*.*")])
        if p: self.npz_path = Path(p); self.npz_var.set(p)

    def _set_busy(self, value, text=None):
        self.busy = value
        self.status.set(text or ("処理中…" if value else "待機中"))
        self.update_idletasks()

    def extract(self):
        p = Path(self.wav_var.get().strip()).expanduser()
        if not p.is_file():
            messagebox.showwarning("入力不足", "先に有効な WAV ファイルを選択してください。"); return
        out = filedialog.asksaveasfilename(title="特徴量NPZの保存先", defaultextension=".npz",
            initialfile=p.stem + "_features.npz", filetypes=[("NPZ", "*.npz")])
        if not out: return
        if Path(out).exists() and not messagebox.askyesno("上書き確認", "選択したNPZは既に存在します。上書きしますか？"): return
        self._set_busy(True, "特徴量抽出中…")
        def worker():
            try:
                result = extract_p2_features(p)
                payload = {k:v for k,v in result.items() if isinstance(v, np.ndarray)}
                payload["config_json"] = np.asarray(json.dumps(result["config"], ensure_ascii=False, sort_keys=True))
                payload["feature_note"] = np.asarray(result["feature_note"])
                payload["source_file_name"] = np.asarray(p.name)
                tmp = Path(out).with_name(Path(out).name + ".tmp")
                with tmp.open("wb") as f: np.savez_compressed(f, **payload)
                tmp.replace(out)
                self.after(0, lambda: self._extraction_done(out, len(result["frame_times_sec"]), result["duration_sec"]))
            except Exception as e:
                msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                self.after(0, lambda m=msg: self._error("特徴量抽出失敗", m))
        threading.Thread(target=worker, daemon=True).start()

    def _extraction_done(self, out, frames, duration):
        self._set_busy(False, "抽出完了")
        self.npz_path = Path(out); self.npz_var.set(out)
        self._log(f"特徴量抽出完了: {out} | {frames} frames / {duration:.3f} s")
        self.load_npz()

    def load_npz(self):
        p = Path(self.npz_var.get().strip()).expanduser()
        if not p.is_file():
            messagebox.showwarning("入力不足", "有効な NPZ ファイルを選択してください。"); return
        try:
            with np.load(p, allow_pickle=False) as d:
                required = ("frame_times_sec", "f0_hz", "f0_confidence_proxy", "frame_rms")
                missing = [k for k in required if k not in d]
                if missing: raise ValueError("必要な配列がありません: " + ", ".join(missing))
                data = {k: np.array(d[k], copy=True) for k in d.files if d[k].dtype.kind not in ("O",)}
            n = len(data["frame_times_sec"])
            for key in required:
                if data[key].ndim != 1 or len(data[key]) != n: raise ValueError(f"配列サイズ不一致: {key}")
                if not np.isfinite(data[key]).all(): raise ValueError(f"NaN/Inf を含む配列: {key}")
            self.data = data; self.npz_path = p
            self.wav_path = None
            self.wav_var.set(str(p.with_suffix(".wav")) if p.with_suffix(".wav").exists() else self.wav_var.get())
            self.npz_var.set(str(p))
            self._draw()
            self._set_busy(False, "NPZ読み込み完了")
            self._log(f"NPZ読込: {p} | {n} frames | 配列数 {len(data)}")
            self.run_qc()
        except Exception as e: self._error("NPZ読み込み失敗", f"{type(e).__name__}: {e}")

    def _draw(self, selected_time=None, zoom=False):
        if not MATPLOTLIB_OK or self.data is None: return
        t = self.data["frame_times_sec"].astype(float)
        f0 = self.data["f0_hz"].astype(float)
        conf = self.data["f0_confidence_proxy"].astype(float)
        rms = self.data["frame_rms"].astype(float)
        self.ax_f0.clear(); self.ax_conf.clear(); self.ax_rms.clear()

        # Base traces
        self.ax_f0.plot(t, np.where(f0 > 0, f0, np.nan), linewidth=1.0, color="#2563eb", label="F0")
        self.ax_conf.plot(t, conf, linewidth=.8, color="#0f766e", label="Confidence proxy")
        self.ax_rms.plot(t, rms, linewidth=.8, color="#7c3aed", label="RMS")

        # QC flags are overlaid directly on the corresponding timeline.
        if self.qc_rows:
            jump_idx = np.array([r["frame_index"] for r in self.qc_rows if r["large_jump_candidate"] == 1], dtype=int)
            low_conf_idx = np.array([r["frame_index"] for r in self.qc_rows if "low_confidence_proxy" in r["flags"].split(";")], dtype=int)
            low_rms_idx = np.array([r["frame_index"] for r in self.qc_rows if "low_rms" in r["flags"].split(";")], dtype=int)
            if len(jump_idx):
                self.ax_f0.scatter(t[jump_idx], f0[jump_idx], s=48, marker="x", color="#dc2626", linewidths=2, zorder=5, label="Large F0 jump")
            if len(low_conf_idx):
                self.ax_conf.scatter(t[low_conf_idx], conf[low_conf_idx], s=13, marker="o", facecolors="none", edgecolors="#ea580c", linewidths=.8, zorder=4, label="Low confidence")
            if len(low_rms_idx):
                self.ax_rms.scatter(t[low_rms_idx], rms[low_rms_idx], s=20, marker="o", color="#dc2626", zorder=4, label="Low RMS")

        self.ax_f0.set_ylabel("F0 (Hz)"); self.ax_f0.grid(True, alpha=.25)
        self.ax_conf.set_ylabel("Confidence"); self.ax_conf.set_ylim(-.03, 1.03); self.ax_conf.grid(True, alpha=.25)
        self.ax_rms.set_ylabel("RMS"); self.ax_rms.set_xlabel("Time (s)"); self.ax_rms.grid(True, alpha=.25)
        for ax in (self.ax_f0, self.ax_conf, self.ax_rms):
            handles, labels = ax.get_legend_handles_labels()
            if handles: ax.legend(loc="upper right", fontsize=8)
        if selected_time is not None:
            for ax in (self.ax_f0, self.ax_conf, self.ax_rms):
                ax.axvline(selected_time, color="#dc2626", linestyle="--", linewidth=1.5, alpha=.9)
            # Keep nearby context visible when an issue row is selected.
            if zoom and len(t):
                half_window = 0.75
                left = max(float(t[0]), selected_time - half_window)
                right = min(float(t[-1]), selected_time + half_window)
                if right > left:
                    for ax in (self.ax_f0, self.ax_conf, self.ax_rms):
                        ax.set_xlim(left, right)
        self.canvas.draw_idle()

    def show_full_plot(self):
        if self.data is not None:
            self._draw()
            self.selected_info.set("全体表示：QC 検出マーカーを表示中")

    def run_qc(self):
        if self.data is None:
            messagebox.showinfo("NPZ未読み込み", "先に NPZ を読み込んでください。"); return
        try:
            conf_th = float(self.conf_var.get()); rms_th = float(self.rms_var.get()); jump_th = float(self.jump_var.get())
            if not 0 <= conf_th <= 1 or rms_th < 0 or jump_th <= 0: raise ValueError("閾値の範囲が不正です")
        except ValueError as e:
            messagebox.showerror("閾値エラー", f"数値を確認してください。\n{e}"); return
        t = self.data["frame_times_sec"].astype(float); f0 = self.data["f0_hz"].astype(float)
        conf = self.data["f0_confidence_proxy"].astype(float); rms = self.data["frame_rms"].astype(float)
        voiced = f0 > 0; low_conf = conf < conf_th; low_rms = rms < rms_th
        jumps = np.full(len(t), np.nan)
        for i in range(1, len(t)):
            if voiced[i-1] and voiced[i]:
                jumps[i] = abs(1200.0 * np.log2(f0[i] / f0[i-1]))
        large = np.isfinite(jumps) & (jumps > jump_th)
        self.qc_rows = []
        for i in range(len(t)):
            flags=[]
            if not voiced[i]: flags.append("f0_unvoiced_or_unestimated")
            if low_conf[i]: flags.append("low_confidence_proxy")
            if low_rms[i]: flags.append("low_rms")
            if large[i]: flags.append("large_adjacent_f0_jump")
            self.qc_rows.append({"frame_index":i,"time_sec":float(t[i]),"f0_hz_original":float(f0[i]),
                "confidence_proxy":float(conf[i]),"frame_rms":float(rms[i]),
                "jump_cents_from_previous":float(jumps[i]) if np.isfinite(jumps[i]) else None,
                "voiced_candidate":int(voiced[i]),"large_jump_candidate":int(large[i]),
                "flags":";".join(flags) if flags else "none"})
        self.tree.delete(*self.tree.get_children())
        # Show actionable QC findings first; ordinary unvoiced/unestimated frames
        # are still recorded in CSV but do not flood the on-screen findings list.
        for row in self.qc_rows:
            actionable = any(flag in row["flags"].split(";") for flag in
                             ("low_confidence_proxy", "low_rms", "large_adjacent_f0_jump"))
            if actionable:
                raw_flags = row["flags"].split(";")
                marker_flags = []
                if "large_adjacent_f0_jump" in raw_flags:
                    marker_flags.append("× 大F0ジャンプ")
                if "low_confidence_proxy" in raw_flags:
                    marker_flags.append("○ 低信頼度")
                if "low_rms" in raw_flags:
                    marker_flags.append("● 低RMS")
                if "f0_unvoiced_or_unestimated" in raw_flags:
                    marker_flags.append("— F0未推定/無声音候補")
                display_flags = "  ".join(marker_flags) if marker_flags else "✓ フラグなし"
                vals=(row["frame_index"],f'{row["time_sec"]:.6f}',f'{row["f0_hz_original"]:.3f}',
                      f'{row["confidence_proxy"]:.4f}',f'{row["frame_rms"]:.8f}',
                      "" if row["jump_cents_from_previous"] is None else f'{row["jump_cents_from_previous"]:.2f}',display_flags)
                active_types = sum(flag in raw_flags for flag in
                                   ("large_adjacent_f0_jump", "low_confidence_proxy", "low_rms"))
                if active_types >= 2:
                    row_tag = "qc_multi"
                elif "large_adjacent_f0_jump" in raw_flags:
                    row_tag = "qc_jump"
                elif "low_confidence_proxy" in raw_flags:
                    row_tag = "qc_conf"
                elif "low_rms" in raw_flags:
                    row_tag = "qc_rms"
                else:
                    row_tag = ""
                self.tree.insert("", "end", iid=str(row["frame_index"]), values=vals,
                                 tags=(row_tag,) if row_tag else ())
        self.summary.set(f"全{len(t)} / 有声候補{int(voiced.sum())} / 低信頼度{int(low_conf.sum())} / 低RMS{int(low_rms.sum())} / 大ジャンプ{int(large.sum())}")
        self._draw()
        self._log(f"QC完了: frames={len(t)}, voiced={int(voiced.sum())}, low_conf={int(low_conf.sum())}, low_rms={int(low_rms.sum())}, large_jump={int(large.sum())}")
        self.status.set("QC完了（フラグは要確認候補）")

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel or self.data is None: return
        idx = int(sel[0]); t = float(self.data["frame_times_sec"][idx])
        row = next((r for r in self.qc_rows if r["frame_index"] == idx), None)
        if row:
            flags = row["flags"].replace("large_adjacent_f0_jump", "大きなF0ジャンプ").replace(
                "low_confidence_proxy", "低信頼度").replace("low_rms", "低RMS").replace(
                "f0_unvoiced_or_unestimated", "F0未推定/無声音候補")
            self.selected_info.set(
                f'選択: frame {idx} / {t:.4f} 秒 / F0 {row["f0_hz_original"]:.2f} Hz / {flags}')
        self._draw(t, zoom=True)

    def save_csv(self):
        if not self.qc_rows:
            messagebox.showinfo("QC結果なし", "先に QC 検証を実行してください。"); return
        default = (self.npz_path.stem if self.npz_path else "features") + "_f0_qc.csv"
        out = filedialog.asksaveasfilename(title="QC CSVを保存", defaultextension=".csv", initialfile=default, filetypes=[("CSV", "*.csv")])
        if not out: return
        try:
            fields=list(self.qc_rows[0].keys())
            with open(out,"w",newline="",encoding="utf-8-sig") as f:
                writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
                for row in self.qc_rows:
                    writer.writerow({k:("" if v is None else v) for k,v in row.items()})
            self._log(f"QC CSV保存: {out}")
            messagebox.showinfo("保存完了", f"CSVを保存しました。\n{out}")
        except Exception as e: self._error("CSV保存失敗", str(e))

    def _error(self, title, detail):
        self._set_busy(False, "エラー")
        self._log(title + ": " + detail)
        messagebox.showerror(title, detail)


def main():
    app=FeatureQCApp()
    app.mainloop()

if __name__ == "__main__":
    main()
