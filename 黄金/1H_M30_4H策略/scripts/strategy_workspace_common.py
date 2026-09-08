# -*- coding: utf-8 -*-
"""Shared helpers for the 1H_M30_4H strategy workspace."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_NAME = "1H_M30_4H"
STRATEGY_TITLE = "1H_M30_4H 策略"
COMBO = "1H_M30_4H"
SOURCE_COMBO = "H1_M30_H4"
FRAMES = ["30M", "1H", "4H"]
PERIOD_LABEL = "30M / 1H / 4H"
FOCUS_TF = "30M"

STRATEGY_DIR = ROOT / "黄金" / f"{STRATEGY_NAME}策略"
SCRIPTS_DIR = STRATEGY_DIR / "scripts"
DATA_DIR = STRATEGY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SIGNALS_DIR = DATA_DIR / "signals"
VALIDATION_DIR = DATA_DIR / "validation"

REF_ROOT = ROOT / "黄金" / "30m2H策略" / "参考实现工程"
REF_BASE_DATA_DIR = REF_ROOT / "base_data"
REF_MULTI_TF_DIR = REF_ROOT / "shadow_tests" / "multi_tf_matrix"
REF_VALIDATION_DIR = REF_MULTI_TF_DIR / "data" / "validation_20260701"
REF_MULTI_TF_SCRIPT_DIR = REF_MULTI_TF_DIR / "scripts"

for candidate in [REF_MULTI_TF_SCRIPT_DIR, REF_ROOT / "scripts", REF_ROOT]:
    candidate_text = str(candidate)
    if candidate_text not in sys.path:
        sys.path.insert(0, candidate_text)
root_scripts = str(ROOT / "scripts")
if root_scripts not in sys.path:
    sys.path.insert(0, root_scripts)

from _multi_tf_matrix_common import (  # type: ignore  # noqa: E402
    add_context,
    build_combo_variant_frames,
    build_tf,
    load_m30_raw,
    load_mainline_bundle,
    metric,
    recompute_focus_sd,
    summarize_variant_item,
    tf_slug,
)

from strategy_research_common import (  # noqa: E402
    add_context,
    build_combo_variant_frames,
    build_tf,
    recompute_stop_distance as recompute_focus_sd,
    tf_slug,
)


CONTEXT_FILE = PROCESSED_DIR / f"{STRATEGY_NAME.lower()}_context_trades.csv"
RAW_M30_FILE = RAW_DIR / "XAUUSDm30.csv"
RAW_SOURCE_MANIFEST = RAW_DIR / "raw_source_manifest.json"
FORBIDDEN_SHARED_RAW_DIRS = [REF_BASE_DATA_DIR]


@contextmanager
def reference_cwd():
    old_cwd = Path.cwd()
    os.chdir(REF_ROOT)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def ensure_reference_ready() -> None:
    required = [
        REF_ROOT,
        REF_BASE_DATA_DIR / "XAUUSDm30.csv",
        REF_MULTI_TF_SCRIPT_DIR / "_multi_tf_matrix_common.py",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing reference assets: " + ", ".join(missing))


def ensure_dirs() -> None:
    for path in [
        RAW_DIR,
        PROCESSED_DIR,
        SIGNALS_DIR,
        VALIDATION_DIR,
        SCRIPTS_DIR / "data_source",
        SCRIPTS_DIR / "prepare",
        SCRIPTS_DIR / "signals",
        SCRIPTS_DIR / "validate",
        SCRIPTS_DIR / "bundle",
        STRATEGY_DIR / "说明文档" / "01_总览说明",
        STRATEGY_DIR / "说明文档" / "02_策略流程",
        STRATEGY_DIR / "说明文档" / "03_验证结果",
        STRATEGY_DIR / "说明文档" / "04_项目清单",
        STRATEGY_DIR / "参考实现工程",
        STRATEGY_DIR / "归档",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def strategy_spec() -> dict:
    return {"name": COMBO, "frames": FRAMES}


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def read_csv_with_fallback(path: Path, encodings: list[str] | None = None) -> pd.DataFrame:
    attempts = encodings or ["utf-8-sig", "utf-8", "gbk"]
    last_error: Exception | None = None
    for encoding in attempts:
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise RuntimeError(f"Unable to read CSV: {path}") from last_error


def write_text(relative_path: str, text: str) -> None:
    path = STRATEGY_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def copy_source_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_strategy_raw_source(src: Path) -> None:
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(f"Raw source does not exist: {src}")
    if src.resolve() == RAW_M30_FILE.resolve():
        return
    for forbidden in FORBIDDEN_SHARED_RAW_DIRS:
        if _is_inside(src, forbidden):
            raise RuntimeError(
                "Raw source independence rule violated: "
                f"{STRATEGY_NAME} cannot use shared/reference raw data from {forbidden}. "
                "Export or place a strategy-dedicated raw file instead."
            )


def build_raw_source_manifest(src: Path, source_id: str = "") -> dict:
    src = Path(src).resolve()
    stat = src.stat()
    return {
        "strategy": STRATEGY_NAME,
        "raw_file": RAW_M30_FILE.name,
        "source_path": str(src),
        "source_id": source_id or src.stem,
        "source_sha256": file_sha256(src),
        "source_size": stat.st_size,
        "source_mtime": stat.st_mtime,
        "rule": "strategy_dedicated_raw_source_required",
    }


def manifest_primary_hash(manifest: dict) -> str:
    return str(manifest.get("source_sha256") or manifest.get("bundle_sha256") or "")


def manifest_source_path(manifest: dict) -> str:
    return str(manifest.get("source_path") or "")


def manifest_component_hashes(manifest: dict) -> set[str]:
    hashes: set[str] = set()
    for key in ["source_sha256", "compatibility_raw_sha256"]:
        value = str(manifest.get(key, ""))
        if value:
            hashes.add(value)
    for item in manifest.get("files", []) or []:
        if isinstance(item, dict):
            value = str(item.get("sha256", ""))
            if value:
                hashes.add(value)
    return hashes


def manifest_raw_file(manifest: dict) -> Path:
    value = manifest.get("source_path") or manifest.get("compatibility_raw_file") or RAW_M30_FILE
    return Path(str(value))


def _other_raw_manifests() -> list[Path]:
    manifests: list[Path] = []
    for path in ROOT.glob("*/data/raw/raw_source_manifest.json"):
        if path.resolve() != RAW_SOURCE_MANIFEST.resolve():
            manifests.append(path)
    return manifests


def validate_raw_source_uniqueness(manifest: dict) -> None:
    current_hash = manifest_primary_hash(manifest)
    current_path = manifest_source_path(manifest)
    current_components = manifest_component_hashes(manifest)
    for path in _other_raw_manifests():
        try:
            other = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if str(other.get("strategy", "")) == STRATEGY_NAME:
            continue
        other_hash = manifest_primary_hash(other)
        other_path = manifest_source_path(other)
        shared_components = current_components.intersection(manifest_component_hashes(other))
        if current_hash and current_hash == other_hash:
            raise RuntimeError(
                "Raw source independence rule violated: "
                f"{STRATEGY_NAME} raw data has the same sha256 as {other.get('strategy')} ({path})."
            )
        if shared_components:
            raise RuntimeError(
                "Raw source independence rule violated: "
                f"{STRATEGY_NAME} raw data shares component sha256 with {other.get('strategy')} ({path})."
            )
        if current_path and current_path == other_path:
            raise RuntimeError(
                "Raw source independence rule violated: "
                f"{STRATEGY_NAME} raw data points to the same source path as {other.get('strategy')} ({path})."
            )


def install_strategy_raw_source(src: Path, source_id: str = "") -> dict:
    src = Path(src)
    validate_strategy_raw_source(src)
    manifest = build_raw_source_manifest(src, source_id=source_id)
    validate_raw_source_uniqueness(manifest)
    copy_source_file(src, RAW_M30_FILE)
    RAW_SOURCE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8-sig",
    )
    return manifest


def load_raw_source_manifest() -> dict | None:
    if not RAW_SOURCE_MANIFEST.exists():
        return None
    return json.loads(RAW_SOURCE_MANIFEST.read_text(encoding="utf-8-sig"))


def load_strategy_raw_m30() -> pd.DataFrame:
    manifest = ensure_strategy_raw_data_ready()
    if manifest.get("source_type") == "mt5_api_history":
        frame = read_csv_with_fallback(RAW_M30_FILE, encodings=["utf-8-sig", "utf-8"])
        if "date_utc" in frame.columns:
            dates = pd.to_datetime(frame["date_utc"], utc=True).dt.tz_convert(None)
        elif "time" in frame.columns:
            dates = pd.to_datetime(frame["time"], utc=True).dt.tz_convert(None)
        else:
            raise RuntimeError(f"MT5 raw file is missing date_utc/time column: {RAW_M30_FILE}")
        volume = frame["tick_volume"] if "tick_volume" in frame.columns else frame.get("volume", 0)
        out = pd.DataFrame(
            {
                "date": dates,
                "open": frame["open"].astype(float),
                "high": frame["high"].astype(float),
                "low": frame["low"].astype(float),
                "close": frame["close"].astype(float),
                "volume": volume,
                "spread": frame["spread"] if "spread" in frame.columns else 0,
                "real_volume": frame["real_volume"] if "real_volume" in frame.columns else 0,
                "symbol": frame["symbol"] if "symbol" in frame.columns else manifest.get("symbol", ""),
                "time_diff": 0,
            }
        )
        return out.sort_values("date").reset_index(drop=True)
    return load_m30_raw(str(RAW_M30_FILE))


def ensure_strategy_raw_data_ready() -> dict:
    if not RAW_M30_FILE.exists():
        raise FileNotFoundError(
            f"Missing {RAW_M30_FILE}. Run sync_raw_data.py --source <strategy-specific XAUUSDm30.csv> first."
        )
    manifest = load_raw_source_manifest()
    if not manifest:
        raise RuntimeError(
            f"Missing {RAW_SOURCE_MANIFEST}. Each strategy must declare its own raw source before generation."
        )
    if manifest.get("strategy") != STRATEGY_NAME:
        raise RuntimeError(f"Raw source manifest strategy mismatch: {manifest.get('strategy')} != {STRATEGY_NAME}")
    validate_strategy_raw_source(manifest_raw_file(manifest))
    validate_raw_source_uniqueness(manifest)
    return manifest


def load_reference_bundle() -> dict:
    if os.environ.get("ALLOW_REFERENCE_SIGNAL_BOOTSTRAP") != "1":
        raise RuntimeError(
            "Reference signal bootstrap is blocked by the raw-data independence rule. "
            "Generate signals from this strategy's own raw data, or set ALLOW_REFERENCE_SIGNAL_BOOTSTRAP=1 "
            "only for explicit legacy migration checks."
        )
    ensure_reference_ready()
    with reference_cwd():
        return load_mainline_bundle()


def build_context_trades(raw_m30: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    ctx = signals.copy()
    for label in FRAMES:
        ctx = add_context(ctx, build_tf(raw_m30, label), tf_slug(label))
    return ctx.sort_values("date").reset_index(drop=True)


def rename_source_combo(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        if out[column].dtype == object:
            mask = out[column].notna()
            out.loc[mask, column] = out.loc[mask, column].astype(str).str.replace(
                SOURCE_COMBO,
                COMBO,
                regex=False,
            )
    if len(out.columns) > 0:
        combo_col = out.columns[0]
        out.loc[out[combo_col].astype(str) == SOURCE_COMBO, combo_col] = COMBO
    return out


def export_reference_validation(src_name: str, dst_name: str) -> bool:
    src = REF_VALIDATION_DIR / src_name
    if not src.exists():
        return False
    frame = read_csv_with_fallback(src)
    if frame.empty:
        export_csv(frame, VALIDATION_DIR / dst_name)
        return True
    combo_col = frame.columns[0]
    filtered = frame.loc[frame[combo_col].astype(str) == SOURCE_COMBO].copy().reset_index(drop=True)
    export_csv(rename_source_combo(filtered), VALIDATION_DIR / dst_name)
    return True


def pick_primary_variant(summary: pd.DataFrame) -> pd.Series:
    scoped = summary.copy()
    scoped["is_control"] = scoped["variant"].astype(str).str.contains("recent2|atr", case=False, regex=True)
    if (~scoped["is_control"]).any():
        scoped = scoped.loc[~scoped["is_control"]].copy()
    scoped["sample_ok"] = scoped["n"].astype(float) >= 50
    if scoped["sample_ok"].any():
        scoped = scoped.loc[scoped["sample_ok"]].copy()
    scoped["is_stack"] = scoped["variant"].astype(str).str.endswith("__stack_core")
    scoped["_score"] = (
        scoped["pf"].astype(float) * 10.0
        + scoped["test_pf"].astype(float).clip(upper=50) * 2.0
        + scoped["ev"].astype(float) * 0.02
        - scoped["is_stack"].astype(int) * 100.0
    )
    return scoped.sort_values(["_score", "test_ev", "n"], ascending=[False, False, False]).iloc[0]


def variant_family(variant: str) -> str:
    key = variant.split("__", 1)[1] if "__" in variant else variant
    if key == "baseline":
        return "基线"
    if "recent" in key or "atr" in key:
        return "对照实验"
    if "dir_align" in key or "dir_against" in key:
        return "方向族"
    if "close" in key:
        return "位置族"
    if "bias" in key:
        return "带方向强度族"
    if "stack" in key or "all_" in key:
        return "组合族"
    return "其他"


def focus_from_variant(variant: str) -> str:
    key = variant.split("__", 1)[1] if "__" in variant else variant
    if key == "baseline":
        return FOCUS_TF.lower()
    return key.split("_", 1)[0]


def build_gate_scan(summary: pd.DataFrame, primary_variant: str) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "combo": COMBO,
                "current_variant": primary_variant,
                "focus_tf": focus_from_variant(str(row["variant"])),
                "gate_family": variant_family(str(row["variant"])),
                "gate_param": row["variant"],
                "desc": row["desc"],
                "trades": int(row["n"]),
                "wr": float(row["wr"]),
                "pf": float(row["pf"]),
                "ev": float(row["ev"]),
                "test_pf": float(row["test_pf"]),
                "test_ev": float(row["test_ev"]),
            }
        )
    return pd.DataFrame(rows)


def build_yearly_performance(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["year", "trades", "wr", "pf", "ev", "pnl"])
    scoped = trades.copy()
    scoped["date"] = pd.to_datetime(scoped["date"])
    rows = []
    for year, frame in scoped.groupby(scoped["date"].dt.year):
        points = frame["pnl"].astype(float).values
        stats = metric(points)
        rows.append(
            {
                "year": int(year),
                "trades": stats["n"],
                "wr": stats["wr"],
                "pf": stats["pf"],
                "ev": stats["ev"],
                "pnl": stats["pnl"],
            }
        )
    return pd.DataFrame(rows)


def strategy_split_metrics(points: pd.Series, dates: pd.Series) -> tuple[dict, dict, pd.Timestamp]:
    ts = pd.to_datetime(dates)
    if len(ts) == 0:
        cutoff = pd.Timestamp("1970-01-01")
        return metric([]), metric([]), cutoff
    ordered = ts.sort_values().reset_index(drop=True)
    cutoff_idx = min(max(int(len(ordered) * 0.70), 1), len(ordered) - 1)
    cutoff = pd.Timestamp(ordered.iloc[cutoff_idx])
    values = pd.Series(points).astype(float).reset_index(drop=True)
    ts_reset = ts.reset_index(drop=True)
    train = metric(values[ts_reset < cutoff].values)
    test = metric(values[ts_reset >= cutoff].values)
    return train, test, cutoff


def summarize_variant_item(item: dict) -> dict:
    frame = item["frame"].copy().sort_values("date").reset_index(drop=True)
    points = frame["pnl"].astype(float)
    m = metric(points.values)
    train_m, test_m, cutoff = strategy_split_metrics(points, pd.to_datetime(frame["date"]))
    return {
        "combo": item["combo"],
        "variant": item["variant"],
        "desc": item["desc"],
        "n": m["n"],
        "wr": m["wr"],
        "pf": m["pf"],
        "ev": m["ev"],
        "pnl": m["pnl"],
        "max_loss_streak": m["ml"],
        "train_n": train_m["n"],
        "test_n": test_m["n"],
        "test_pf": test_m["pf"],
        "test_ev": test_m["ev"],
        "split_date": cutoff.strftime("%Y-%m-%d"),
    }


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "| 空 | 空 |\n| --- | --- |"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(str(x) for x in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(lines)
