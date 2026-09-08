# -*- coding: utf-8 -*-
"""Prototype EA-style latest-completed M15 SLOT1 selection for Python-MT5 signals."""
from __future__ import annotations


import importlib.util
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "m15_slot1_latest_completed_prototype_20260715"
PROTO_SIGNAL_ROOT = OUT_DIR / "signals"

CURRENT_SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
TARGET_TIME = pd.Timestamp("2025-10-21 10:00:00")


def load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def parse_dt_series(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.replace(".", "-", regex=False)
    text = text.mask(text.isin(["", "nan", "NaT", "None"]))
    return pd.to_datetime(text, errors="coerce")


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    if columns is not None:
        frame = frame[[col for col in columns if col in frame.columns]]
    return frame.to_markdown(index=False)


def latest_completed_by_distance_factory(m15t):
    def choose_slot1_latest_by_distance(seg, is_long, stop):
        if len(seg) == 0:
            return None
        row = seg.iloc[-1]
        entry = float(row["close"])
        sd = abs(entry - stop)
        if not m15t.m15_same_side(row, is_long):
            return None
        if not (m15t.SPEC_LO <= sd <= m15t.SPEC_HI):
            return None
        return row

    return choose_slot1_latest_by_distance


def find_csv_by_header(directory: Path, required_columns: set[str], forbidden_columns: set[str] | None = None) -> Path:
    forbidden_columns = forbidden_columns or set()
    for path in directory.glob("*.csv"):
        try:
            cols = set(read_csv(path).columns)
        except Exception:
            continue
        if required_columns.issubset(cols) and not (forbidden_columns & cols):
            return path
    raise FileNotFoundError(f"No CSV with columns {required_columns} in {directory}")


def target_rows(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "date" in out.columns:
        out["date_dt"] = parse_dt_series(out["date"])
        out = out[out["date_dt"].between(TARGET_TIME - pd.Timedelta(hours=4), TARGET_TIME + pd.Timedelta(hours=1), inclusive="both")]
    return out


def summarize_layer(name: str, current: pd.DataFrame, proto: pd.DataFrame) -> dict[str, object]:
    row: dict[str, object] = {
        "layer": name,
        "current_rows": int(len(current)),
        "prototype_rows": int(len(proto)),
        "delta_rows": int(len(proto) - len(current)),
    }
    for frame_name, frame in [("current", current), ("prototype", proto)]:
        if "variant" in frame.columns:
            row[f"{frame_name}_runtime_rescue_rows"] = int(frame["variant"].astype(str).eq("ea_slot1_runtime_rescue").sum())
            row[f"{frame_name}_slot1_replace_rows"] = int(frame["variant"].astype(str).eq("ea_slot1_replace").sum())
        if "date" in frame.columns:
            dt = parse_dt_series(frame["date"])
            row[f"{frame_name}_target_20251021_1000_rows"] = int((dt == TARGET_TIME).sum())
    return row


def load_variant_files(variant_dir: Path) -> dict[str, pd.DataFrame]:
    files = {
        "raw_candidates": variant_dir / "raw_candidates.csv",
        "layer12_accepted": variant_dir / "候选信号_Layer1_Layer2通过.csv",
        "layer3_picked": variant_dir / "最终信号_Layer3入选.csv",
        "stage_results": variant_dir / "执行交易_Stage结果.csv",
    }
    return {name: read_csv(path) for name, path in files.items()}


def current_files() -> dict[str, pd.DataFrame]:
    return {
        "raw_candidates": read_csv(CURRENT_SIGNAL_DIR / "raw_candidates.csv"),
        "layer12_accepted": read_csv(CURRENT_SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv"),
        "layer3_picked": read_csv(CURRENT_SIGNAL_DIR / "最终信号_Layer3入选.csv"),
        "stage_results": read_csv(CURRENT_SIGNAL_DIR / "执行交易_Stage结果.csv"),
    }


def build_report(metrics: pd.DataFrame, summary: pd.DataFrame, target_compare: pd.DataFrame) -> str:
    lines = [
        "# M15 SLOT1 latest completed prototype",
        "",
        "## 结论",
        "",
        "- 该 prototype 只把 Python-MT5 的 `choose_slot1_by_distance` 从窗口第一根 M15 改成窗口最后一根 M15，用于模拟 EA `iTime(M15,1)` 的 latest completed bar 语义。",
        "- 该 prototype 不修改主线脚本，不覆盖 `signals_mt5_shift90_metadatafix_20260714`。",
        "- 如果 `2025-10-21 10:00` 的 `ea_slot1_runtime_rescue` 从 accepted/picked/stage 中消失，说明 SPEC_FAIL 分支应优先修 Python slot1 bar 选择。",
        "",
        "## Prototype metrics",
        "",
        markdown_table(metrics),
        "",
        "## Layer before/after",
        "",
        markdown_table(summary),
        "",
        "## Target-window rows",
        "",
        markdown_table(target_compare),
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))

    rebuild = load_module_from_path(
        "rebuild_python_mt5_shift90_for_latest_slot1",
        STRATEGY_DIR / "scripts" / "signals" / "rebuild_python_mt5_shift90.py",
    )
    m15t = rebuild.m15t

    old_out_root = rebuild.OUT_ROOT
    old_chooser = m15t.choose_slot1_by_distance
    try:
        rebuild.OUT_ROOT = PROTO_SIGNAL_ROOT
        m15t.choose_slot1_by_distance = latest_completed_by_distance_factory(m15t)

        mt5 = rebuild.load_mt5_export()
        mt5_m30 = rebuild.build_m30_smma(mt5)
        df, _ = rebuild.prepare(str(rebuild.M30_RAW_CSV), min_len=8, mt5_smma=mt5_m30)
        m15 = m15t.load_m15()
        h2 = rebuild.load_h2_context()

        PROTO_SIGNAL_ROOT.mkdir(parents=True, exist_ok=True)
        metrics = pd.DataFrame(
            [
                rebuild.run_variant(
                    df,
                    h2,
                    m15,
                    "python_h2_context_q2early_latest_slot1",
                    use_q2_early=True,
                )
            ]
        )
    finally:
        rebuild.OUT_ROOT = old_out_root
        m15t.choose_slot1_by_distance = old_chooser

    proto_variant_dir = PROTO_SIGNAL_ROOT / "python_h2_context_q2early_latest_slot1"
    current = current_files()
    proto = load_variant_files(proto_variant_dir)

    summary = pd.DataFrame(
        [
            summarize_layer(layer, current[layer], proto[layer])
            for layer in ["raw_candidates", "layer12_accepted", "layer3_picked", "stage_results"]
        ]
    )

    target_blocks = []
    for label, frames in [("current", current), ("prototype", proto)]:
        for layer, frame in frames.items():
            rows = target_rows(frame).copy()
            if rows.empty:
                continue
            rows.insert(0, "run", label)
            rows.insert(1, "layer", layer)
            target_blocks.append(rows)
    target_compare = pd.concat(target_blocks, ignore_index=True) if target_blocks else pd.DataFrame()

    keep_cols = [
        "run",
        "layer",
        "date",
        "entry_time",
        "mode",
        "dir",
        "variant",
        "trigger",
        "entry",
        "stop",
        "sd",
        "spec_pass",
        "spec_reason",
        "layer3_pass_ea",
        "stage1_pnl",
        "stage2_pnl",
        "stage3_pnl",
        "total_$",
    ]
    target_compare = target_compare[[col for col in keep_cols if col in target_compare.columns]]

    export_csv(metrics, OUT_DIR / "prototype_metrics.csv")
    export_csv(summary, OUT_DIR / "layer_before_after_summary.csv")
    export_csv(target_compare, OUT_DIR / "target_window_before_after.csv")
    write_text(OUT_DIR / "m15_slot1_latest_completed_prototype.md", build_report(metrics, summary, target_compare))
    write_text(
        OUT_DIR / "README.md",
        "# m15_slot1_latest_completed_prototype_20260715\n\n"
        "Prototype-only output. It monkey-patches Python-MT5 slot1 selection to use the latest completed M15 bar and writes versioned signal outputs under `signals/`.\n",
    )

    print(summary.to_string(index=False))
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
