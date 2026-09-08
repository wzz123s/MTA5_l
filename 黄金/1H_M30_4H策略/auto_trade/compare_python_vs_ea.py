# -*- coding: utf-8 -*-
"""Compare Python expected stage ledger with an EA-exported trade ledger."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
ROOT_NAME = ROOT.name
STRATEGY = ROOT_NAME[:-2] if ROOT_NAME.endswith("策略") else ROOT_NAME
VALIDATION_DIR = ROOT / "data" / "validation"
SIGNALS_DIR = ROOT / "data" / "signals"
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = VALIDATION_DIR / "ea_alignment"
DEFAULT_LEDGER_NAME = f"{STRATEGY}_strategy_trade_ledger.csv"
DEFAULT_STAGE_LOTS = {1: 0.02, 2: 0.01, 3: 0.03}
DEFAULT_ANCHOR_SHIFT_MINUTES = 30


def load_parameter_pack() -> dict:
    path = VALIDATION_DIR / "ea_parameter_pack.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def stage_lots_from_pack(pack: dict) -> dict[int, float]:
    lots = str(pack.get("position", {}).get("lots", "")).strip()
    values = [item for item in lots.split("/") if item]
    if len(values) != 3:
        return DEFAULT_STAGE_LOTS.copy()
    return {idx + 1: float(value) for idx, value in enumerate(values)}


def parse_stop_range(text: object) -> tuple[float, float] | None:
    value = str(text or "").strip().lower().replace("pt", "")
    if "-" not in value:
        return None
    left, right = value.split("-", 1)
    try:
        return float(left), float(right)
    except ValueError:
        return None


def stop_range_from_pack(pack: dict) -> tuple[float, float] | None:
    return parse_stop_range(pack.get("stop_spec", {}).get("primary"))


def read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "gbk", "ansi"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def time_key(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.replace(".", "-", regex=False)
    parsed = pd.to_datetime(text, errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d %H:%M:%S")


def shift_key_text(value: object, minutes: int) -> str:
    parsed = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(parsed):
        return str(value)
    if minutes:
        parsed = parsed + pd.Timedelta(minutes=minutes)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def norm_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "1"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL", "-1"}:
        return "SELL"
    return text


def norm_mode(value: object) -> str:
    text = str(value).strip().lower()
    if text.endswith("_rescue"):
        text = text[: -len("_rescue")]
    return text


def norm_signal_source(value: object) -> str:
    text = norm_mode(value)
    if text == "mt5_basic_cross_v1":
        return "cross"
    return text


def focus_from_variant(variant: str) -> str:
    key = variant.split("__", 1)[1] if "__" in variant else variant
    if key == "baseline":
        return "30m"
    return key.split("_", 1)[0].lower()


def context_trade_path() -> Path | None:
    matches = sorted(PROCESSED_DIR.glob("*_context_trades.csv"))
    return matches[0] if matches else None


def recompute_focus_sd(frame: pd.DataFrame, focus_label: str) -> pd.DataFrame:
    out = frame.copy()
    prefix = focus_label.lower()
    high_col = f"{prefix}_high"
    low_col = f"{prefix}_low"
    sma13_col = f"{prefix}_sma13"
    idx_col = f"{prefix}_idx"

    stops: list[object] = []
    sds: list[object] = []
    for _, row in out.iterrows():
        try:
            entry = float(row["entry"])
        except (TypeError, ValueError):
            stops.append(pd.NA)
            sds.append(pd.NA)
            continue
        if idx_col not in out.columns or pd.isna(row.get(idx_col)) or int(row.get(idx_col)) < 0:
            stops.append(pd.NA)
            sds.append(pd.NA)
            continue

        values = [row.get(low_col, pd.NA), row.get(sma13_col, pd.NA)] if row["dir"] == "L" else [
            row.get(high_col, pd.NA),
            row.get(sma13_col, pd.NA),
        ]
        candidates = []
        for value in values:
            if pd.isna(value):
                continue
            value = float(value)
            if (row["dir"] == "L" and value < entry) or (row["dir"] != "L" and value > entry):
                candidates.append(value)
        stop = min(candidates) if row["dir"] == "L" and candidates else max(candidates) if candidates else pd.NA
        stops.append(stop)
        sds.append(abs(entry - stop) if not pd.isna(stop) else pd.NA)

    out["focus_stop"] = stops
    out["focus_sd"] = sds
    return out


def sign_value(value: object) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if abs(number) < 1e-9:
        return 0
    return 1 if number > 0 else -1


def build_expected(
    stop_lo: float,
    stop_hi: float,
    apply_stop_filter: bool,
    stage_lots: dict[int, float],
    anchor_shift_minutes: int,
) -> pd.DataFrame:
    best_path = VALIDATION_DIR / "combo_best_stage12_trades.csv"
    candidate_path = SIGNALS_DIR / "strategy_candidate_trades.csv"
    if not best_path.exists():
        raise FileNotFoundError(best_path)

    best = read_csv(best_path)
    primary_variant = str(best["variant"].dropna().iloc[0]) if "variant" in best.columns else f"{STRATEGY}__baseline"

    best = best.copy()
    best["_key_time"] = time_key(best["date"])

    join_cols = ["_key_time", "mode", "dir"]
    context_path = context_trade_path()
    if context_path:
        context = read_csv(context_path)
        context["_key_time"] = time_key(context["date"])
        context = recompute_focus_sd(context, focus_from_variant(primary_variant))
        extra_cols = [c for c in ["entry", "focus_stop", "focus_sd", "source_variant"] if c in context.columns]
        context_slice = context[join_cols + extra_cols].drop_duplicates(join_cols)
        best = best.merge(context_slice, on=join_cols, how="left")
        best["stop"] = best["focus_stop"]
        best["sd"] = best["focus_sd"]
        best["stop_source"] = "focus_sd"
    else:
        if not candidate_path.exists():
            raise FileNotFoundError(candidate_path)
        candidates = read_csv(candidate_path)
        candidates["_key_time"] = time_key(candidates["date"])
        if "variant" in candidates.columns:
            candidates = candidates.loc[candidates["variant"].astype(str) == primary_variant].copy()
        extra_cols = [c for c in ["entry", "stop", "sd", "source_variant"] if c in candidates.columns]
        candidate_slice = candidates[join_cols + extra_cols].drop_duplicates(join_cols)
        best = best.merge(candidate_slice, on=join_cols, how="left")
        best["stop_source"] = "source_sd"

    if apply_stop_filter:
        if "sd" not in best.columns:
            raise ValueError("Cannot apply stop filter: sd column is missing from candidate trades.")
        best["sd"] = pd.to_numeric(best["sd"], errors="coerce")
        best = best.loc[(best["sd"] >= stop_lo) & (best["sd"] <= stop_hi)].copy()

    rows = []
    for _, row in best.sort_values("_key_time").iterrows():
        anchor_key = shift_key_text(row["_key_time"], anchor_shift_minutes)
        for stage in (1, 2, 3):
            rows.append(
                {
                    "anchor_key": anchor_key,
                    "dir_key": norm_dir(row["dir"]),
                    "stage": stage,
                    "expected_time": row["_key_time"],
                    "expected_mode": row.get("mode", ""),
                    "expected_mode_norm": norm_mode(row.get("mode", "")),
                    "expected_signal_source": row.get("signal_source", ""),
                    "expected_signal_src_norm": norm_signal_source(row.get("signal_source", "")),
                    "expected_dir_raw": row.get("dir", ""),
                    "expected_lots": stage_lots[stage],
                    "expected_points": row.get(f"stage{stage}_pnl", pd.NA),
                    "expected_exit_reason": row.get(f"stage{stage}_exit", ""),
                    "expected_total_points": row.get("total_points", pd.NA),
                    "expected_entry": row.get("entry", pd.NA),
                    "expected_stop": row.get("stop", pd.NA),
                    "expected_sd": row.get("sd", pd.NA),
                    "expected_stop_source": row.get("stop_source", ""),
                    "variant": row.get("variant", primary_variant),
                    "combo": row.get("combo", STRATEGY),
                }
            )

    expected = pd.DataFrame(rows)
    if expected.empty:
        return expected
    expected["_seq"] = expected.groupby(["anchor_key", "dir_key", "stage"]).cumcount()
    expected["expected_points_sign"] = expected["expected_points"].map(sign_value)
    return expected


def resolve_ledger(path_text: str | None) -> Path | None:
    if path_text:
        path = Path(path_text)
        if path.exists():
            return path
        raise FileNotFoundError(path)

    for candidate in (
        SCRIPT_DIR / DEFAULT_LEDGER_NAME,
        OUT_DIR / DEFAULT_LEDGER_NAME,
        Path.cwd() / DEFAULT_LEDGER_NAME,
    ):
        if candidate.exists():
            return candidate
    return None


def read_ea_ledger(path: Path) -> pd.DataFrame:
    ea = read_csv(path).copy()
    if "signal_anchor_time" not in ea.columns:
        raise ValueError(f"{path} does not contain signal_anchor_time.")
    if "stage" not in ea.columns:
        raise ValueError(f"{path} does not contain stage.")

    ea["anchor_key"] = time_key(ea["signal_anchor_time"])
    ea["dir_key"] = ea.get("dir", "").map(norm_dir)
    ea["stage"] = pd.to_numeric(ea["stage"], errors="coerce")
    ea = ea.loc[ea["stage"].notna()].copy()
    ea["stage"] = ea["stage"].astype(int)
    ea["_seq"] = ea.groupby(["anchor_key", "dir_key", "stage"]).cumcount()

    profit_source = "net_profit" if "net_profit" in ea.columns else "profit" if "profit" in ea.columns else None
    out = pd.DataFrame(
        {
            "anchor_key": ea["anchor_key"],
            "dir_key": ea["dir_key"],
            "stage": ea["stage"],
            "_seq": ea["_seq"],
            "ea_signal_src": ea["signal_src"] if "signal_src" in ea.columns else "",
            "ea_signal_src_norm": ea["signal_src"].map(norm_signal_source) if "signal_src" in ea.columns else "",
            "ea_lots": pd.to_numeric(ea["lots"], errors="coerce") if "lots" in ea.columns else pd.NA,
            "ea_profit": pd.to_numeric(ea[profit_source], errors="coerce") if profit_source else pd.NA,
            "ea_ticket": ea["ticket"] if "ticket" in ea.columns else "",
            "ea_position_id": ea["position_id"] if "position_id" in ea.columns else "",
            "ea_exit_time": ea["exit_time"] if "exit_time" in ea.columns else "",
            "ea_local_exit_reason": ea["local_exit_reason"] if "local_exit_reason" in ea.columns else "",
            "ea_deal_reason": ea["deal_reason"] if "deal_reason" in ea.columns else "",
        }
    )
    out["ea_profit_sign"] = out["ea_profit"].map(sign_value)
    return out


def compare(expected: pd.DataFrame, ledger_path: Path | None) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if ledger_path is None:
        detail = expected.copy()
        detail["match_status"] = "waiting_for_ea_ledger"
        summary = pd.DataFrame(
            [
                {
                    "strategy": STRATEGY,
                    "status": "ledger_missing",
                    "ea_ledger": "",
                    "expected_rows": len(expected),
                    "ea_rows": 0,
                    "matched": 0,
                    "python_only": len(expected),
                    "ea_only": 0,
                    "mode_mismatch": 0,
                    "lot_mismatch": 0,
                    "pnl_sign_mismatch": 0,
                }
            ]
        )
        return detail, summary, "ledger_missing"

    ea = read_ea_ledger(ledger_path)
    detail = expected.merge(
        ea,
        on=["anchor_key", "dir_key", "stage", "_seq"],
        how="outer",
        indicator=True,
    )
    detail["match_status"] = detail["_merge"].map(
        {"both": "matched", "left_only": "python_only", "right_only": "ea_only"}
    )
    both = detail["_merge"].eq("both")
    detail["mode_mismatch"] = both & (
        detail["expected_signal_src_norm"].fillna("") != detail["ea_signal_src_norm"].fillna("")
    )
    detail["lot_diff"] = pd.to_numeric(detail["ea_lots"], errors="coerce") - pd.to_numeric(
        detail["expected_lots"], errors="coerce"
    )
    detail["lot_mismatch"] = both & detail["lot_diff"].abs().gt(1e-9)
    detail["pnl_sign_mismatch"] = (
        both
        & detail["expected_points_sign"].fillna(0).ne(0)
        & detail["ea_profit_sign"].fillna(0).ne(0)
        & detail["expected_points_sign"].ne(detail["ea_profit_sign"])
    )

    matched = int(detail["_merge"].eq("both").sum())
    python_only = int(detail["_merge"].eq("left_only").sum())
    ea_only = int(detail["_merge"].eq("right_only").sum())
    issue_count = int(detail["mode_mismatch"].sum() + detail["lot_mismatch"].sum() + detail["pnl_sign_mismatch"].sum())
    status = "pass" if python_only == 0 and ea_only == 0 and issue_count == 0 else "mismatch"
    summary = pd.DataFrame(
        [
            {
                "strategy": STRATEGY,
                "status": status,
                "ea_ledger": str(ledger_path),
                "expected_rows": len(expected),
                "ea_rows": len(ea),
                "matched": matched,
                "python_only": python_only,
                "ea_only": ea_only,
                "mode_mismatch": int(detail["mode_mismatch"].sum()),
                "lot_mismatch": int(detail["lot_mismatch"].sum()),
                "pnl_sign_mismatch": int(detail["pnl_sign_mismatch"].sum()),
            }
        ]
    )
    return detail, summary, status


def write_report(
    summary: pd.DataFrame,
    status: str,
    ledger_path: Path | None,
    apply_stop_filter: bool,
    stop_lo: float,
    stop_hi: float,
    parameter_pack: dict,
    anchor_shift_minutes: int,
) -> None:
    row = summary.iloc[0].to_dict()
    stop_label = f"{stop_lo:g}-{stop_hi:g}pt current profile" if apply_stop_filter else "disabled"
    research_set = parameter_pack.get("research_set") or f"{STRATEGY}_Strategy_EA.mt5_raw_research_20260725.set"
    lines = [
        f"# {STRATEGY} Python vs EA Alignment",
        "",
        f"- status: `{status}`",
        f"- EA ledger: `{ledger_path if ledger_path else 'missing'}`",
        f"- stop filter: `{stop_label}`",
        f"- anchor shift: `{anchor_shift_minutes} minutes`",
        f"- research set: `{research_set}`",
        f"- expected rows: `{int(row['expected_rows'])}`",
        f"- EA rows: `{int(row['ea_rows'])}`",
        f"- matched: `{int(row['matched'])}`",
        f"- Python only: `{int(row['python_only'])}`",
        f"- EA only: `{int(row['ea_only'])}`",
        f"- mode mismatch: `{int(row['mode_mismatch'])}`",
        f"- lot mismatch: `{int(row['lot_mismatch'])}`",
        f"- PnL sign mismatch: `{int(row['pnl_sign_mismatch'])}`",
        "",
    ]
    if status == "ledger_missing":
        lines.extend(
            [
                "## Next",
                "",
                "1. Compile the dedicated EA in MetaEditor.",
                f"2. Run MT5 Strategy Tester with `{research_set}` and CSV export enabled.",
                f"3. Put `{DEFAULT_LEDGER_NAME}` next to this script or pass its full path to this script.",
            ]
        )
    elif status == "pass":
        lines.extend(
            [
                "## Next",
                "",
                "Alignment passed for this exported ledger. Keep the ledger, set file, compile log, and data manifest together as the deployment evidence pack.",
            ]
        )
    else:
        lines.extend(
            [
                "## Diagnosis",
                "",
                "The EA ran and exported a ledger, but the EA trade keys do not match the Python expected stage ledger. Deployment remains blocked until the EA signal model, time axis, stop filter, and stage exit model reproduce the Python profile.",
            ]
        )
    (OUT_DIR / "alignment_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", nargs="?", help="Path to EA-exported *_strategy_trade_ledger.csv")
    parser.add_argument("--no-stop-filter", action="store_true", help="Compare all Python trades instead of the current primary StopSpec profile")
    parser.add_argument("--stop-lo", type=float, default=None)
    parser.add_argument("--stop-hi", type=float, default=None)
    parser.add_argument("--anchor-shift-minutes", type=int, default=DEFAULT_ANCHOR_SHIFT_MINUTES)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parameter_pack = load_parameter_pack()
    pack_stop = stop_range_from_pack(parameter_pack)
    if args.stop_lo is None or args.stop_hi is None:
        if pack_stop is None:
            stop_lo, stop_hi = 14.0, 70.0
        else:
            stop_lo, stop_hi = pack_stop
    else:
        stop_lo, stop_hi = float(args.stop_lo), float(args.stop_hi)
    stage_lots = stage_lots_from_pack(parameter_pack)
    apply_stop_filter = not args.no_stop_filter
    expected = build_expected(stop_lo, stop_hi, apply_stop_filter, stage_lots, args.anchor_shift_minutes)
    ledger_path = resolve_ledger(args.ledger)
    detail, summary, status = compare(expected, ledger_path)

    expected.to_csv(OUT_DIR / "python_expected_stage_ledger.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUT_DIR / "alignment_detail.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_DIR / "alignment_summary.csv", index=False, encoding="utf-8-sig")
    write_report(summary, status, ledger_path, apply_stop_filter, stop_lo, stop_hi, parameter_pack, args.anchor_shift_minutes)

    row = summary.iloc[0]
    print(
        f"{STRATEGY}: {row['status']} | expected={row['expected_rows']} "
        f"ea={row['ea_rows']} matched={row['matched']} python_only={row['python_only']} ea_only={row['ea_only']}"
    )


if __name__ == "__main__":
    main()
