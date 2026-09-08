# -*- coding: utf-8 -*-
"""Source audit for M30 CLOSE/post_n true no-candidate MT5 signals.

Diagnostic-only:
- audits mt5_0026 and mt5_0061
- compares MT5 M30 CLOSE/post_n source to Python raw/Layer1/2/Layer3/dynamic chain
- does not edit EA, signal builders, dynamic-risk outputs, or the canonical mapper
"""

from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
ROOT = STRATEGY_DIR.parents[0]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
DATA_DIR = STRATEGY_DIR / "data"

INDEPENDENT_DIR = VALIDATION_DIR / "stage_state_independent_mt5_signal_gap_audit_20260718"
RAW_REPLAY_DIR = VALIDATION_DIR / "stage_state_targeted_raw_signal_replay_20260717"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"

EA_SOURCE = ROOT / "auto_trade" / "30m2H_Strategy_EA.mq5"
PY_DIRECTION = ROOT / "processing" / "direction.py"
PY_PRE_CROSS = ROOT / "scripts" / "_pre_cross_range_test.py"
PY_PREPARE = ROOT / "processing" / "prepare.py"

OUT_DIR = VALIDATION_DIR / "stage_state_m30_close_postn_true_no_candidate_source_audit_20260718"

TARGET_IDS = ["mt5_0026", "mt5_0061"]
WINDOWS_MINUTES = [0, 60, 120, 180, 1440, 10080]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def parse_dt(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def fmt_dt(value: object) -> str:
    dt = parse_dt(value)
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    return text


def mode_family(value: object) -> str:
    text = str(value).strip()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def post_n_number(value: object) -> int | None:
    text = str(value)
    marker = "post_n"
    if marker not in text:
        return None
    pos = text.find(marker) + len(marker)
    digits = []
    while pos < len(text) and text[pos].isdigit():
        digits.append(text[pos])
        pos += 1
    if not digits:
        return None
    return int("".join(digits))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def signal_file(name: str) -> Path:
    direct = SIGNAL_DIR / name
    if direct.exists():
        return direct
    matches = list(SIGNAL_DIR.glob(name))
    if not matches:
        raise FileNotFoundError(name)
    return matches[0]


def infer_trigger(row: pd.Series) -> str:
    trigger = str(row.get("trigger", row.get("trigger_family", ""))).strip()
    if trigger:
        return trigger
    text = " ".join(str(row.get(col, "")) for col in ["variant", "mode", "signal_src"]).lower()
    if "slot1" in text or "m15" in text:
        return "M15 SLOT1"
    return "M30 CLOSE"


def prep_signal_table(frame: pd.DataFrame, source_table: str) -> pd.DataFrame:
    out = frame.copy()
    out["source_table"] = source_table
    out["target_time"] = out["date"].map(parse_dt)
    out["dir_norm"] = out["dir"].map(normalize_dir)
    out["trigger_family"] = out.apply(infer_trigger, axis=1)
    out["mode_family"] = out["mode"].map(mode_family)
    out["mode_or_signal_src"] = out["mode"]
    out["post_n_number"] = out["mode"].map(post_n_number)
    out["profit"] = pd.to_numeric(out.get("total_$", out.get("pnl", 0.0)), errors="coerce")
    return out


def load_signal_chain() -> dict[str, pd.DataFrame]:
    raw = prep_signal_table(read_csv(SIGNAL_DIR / "raw_candidates.csv"), "python_raw_candidates")
    layer12 = prep_signal_table(read_csv(signal_file("候选信号_Layer1_Layer2通过.csv")), "python_layer12_pass")
    layer3 = prep_signal_table(read_csv(signal_file("最终信号_Layer3入选.csv")), "python_layer3_selected")
    stage = read_csv(signal_file("执行交易_Stage结果.csv")).copy()
    stage = prep_signal_table(stage, "python_stage_result_export")

    dynamic = read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv").copy()
    dynamic["py_trade_id"] = [f"python_mt5_{idx + 1:04d}" for idx in range(len(dynamic))]
    dynamic["source_table"] = "python_dynamic_executed"
    dynamic["target_time"] = dynamic["date"].map(parse_dt)
    dynamic["dir_norm"] = dynamic["dir"].map(normalize_dir)
    dynamic["trigger_family"] = dynamic["trigger_family"].astype(str)
    dynamic["mode_family"] = dynamic["mode_family"].map(mode_family)
    dynamic["mode_or_signal_src"] = dynamic["mode"]
    dynamic["post_n_number"] = dynamic["mode"].map(post_n_number)
    dynamic["profit"] = pd.to_numeric(dynamic["dynamic_total_$"], errors="coerce")

    return {
        "python_raw_candidates": raw,
        "python_layer12_pass": layer12,
        "python_layer3_selected": layer3,
        "python_stage_result_export": stage,
        "python_dynamic_executed": dynamic,
    }


def load_targets() -> pd.DataFrame:
    audit = read_csv(INDEPENDENT_DIR / "independent_mt5_signal_gap_case_audit.csv")
    targets = audit[audit["trade_id"].astype(str).isin(TARGET_IDS)].copy()
    targets["target_dt"] = targets["target_time"].map(parse_dt)
    targets["raw_anchor_dt"] = targets["raw_anchor"].map(parse_dt)
    targets["post_n_number"] = targets["mode_or_signal_src"].map(post_n_number)
    return targets


def load_mt5_unique() -> pd.DataFrame:
    mt5 = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv").copy()
    mt5["mt5_trade_id"] = [f"mt5_{idx + 1:04d}" for idx in range(len(mt5))]
    mt5["signal_anchor_dt"] = mt5["signal_anchor_time"].map(parse_dt)
    mt5["target_time"] = mt5["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    mt5["post_n_number"] = mt5["signal_src"].map(post_n_number)
    return mt5


def context_for_target(target: pd.Series, chain: dict[str, pd.DataFrame]) -> list[dict[str, object]]:
    target_dt = target["target_dt"]
    raw_anchor_dt = target["raw_anchor_dt"]
    target_dir = str(target["dir_norm"])
    target_trigger = str(target["trigger_family"])
    target_mode_family = str(target["mode_family"])
    target_post_n = target["post_n_number"]

    rows: list[dict[str, object]] = []
    for source_table, frame in chain.items():
        if frame.empty:
            continue
        work = frame.copy()
        work["abs_minutes_to_target"] = (
            (work["target_time"] - target_dt).dt.total_seconds().abs() / 60.0
        )
        work["signed_minutes_to_target"] = (
            (work["target_time"] - target_dt).dt.total_seconds() / 60.0
        )
        work["abs_minutes_to_raw_anchor"] = (
            (work["target_time"] - raw_anchor_dt).dt.total_seconds().abs() / 60.0
        )
        work["same_dir"] = work["dir_norm"].astype(str).eq(target_dir)
        work["same_trigger"] = work["trigger_family"].astype(str).eq(target_trigger)
        work["same_mode_family"] = work["mode_family"].astype(str).eq(target_mode_family)
        work["same_post_n_number"] = work["post_n_number"].eq(target_post_n)
        work["same_family"] = work["same_dir"] & work["same_trigger"] & work["same_mode_family"]
        near = work[
            (work["abs_minutes_to_target"] <= max(WINDOWS_MINUTES))
            | (work["abs_minutes_to_raw_anchor"] <= max(WINDOWS_MINUTES))
        ].copy()
        if near.empty:
            continue
        near = near.sort_values(["abs_minutes_to_target", "abs_minutes_to_raw_anchor"]).head(60)
        for _, row in near.iterrows():
            rows.append(
                {
                    "mt5_trade_id": target["trade_id"],
                    "source_table": source_table,
                    "row_time": fmt_dt(row["target_time"]),
                    "signed_minutes_to_target": row["signed_minutes_to_target"],
                    "abs_minutes_to_target": row["abs_minutes_to_target"],
                    "abs_minutes_to_raw_anchor": row["abs_minutes_to_raw_anchor"],
                    "dir_norm": row.get("dir_norm", ""),
                    "trigger_family": row.get("trigger_family", ""),
                    "mode_family": row.get("mode_family", ""),
                    "mode_or_signal_src": row.get("mode_or_signal_src", ""),
                    "variant": row.get("variant", ""),
                    "profit": row.get("profit", ""),
                    "same_dir": row.get("same_dir", False),
                    "same_trigger": row.get("same_trigger", False),
                    "same_mode_family": row.get("same_mode_family", False),
                    "same_post_n_number": row.get("same_post_n_number", False),
                    "same_family": row.get("same_family", False),
                }
            )
    return rows


def count_window(frame: pd.DataFrame, minutes: int, filter_expr: pd.Series) -> int:
    if frame.empty:
        return 0
    return int((frame["abs_minutes_to_target"].le(minutes) & filter_expr).sum())


def summarize_target(target: pd.Series, context: pd.DataFrame, mt5_unique: pd.DataFrame) -> dict[str, object]:
    tid = str(target["trade_id"])
    ctx = context[context["mt5_trade_id"].astype(str).eq(tid)].copy()
    mt5_row = mt5_unique[mt5_unique["mt5_trade_id"].astype(str).eq(tid)]
    raw_ctx = ctx[ctx["source_table"].eq("python_raw_candidates")].copy()
    layer12_ctx = ctx[ctx["source_table"].eq("python_layer12_pass")].copy()
    layer3_ctx = ctx[ctx["source_table"].eq("python_layer3_selected")].copy()
    dynamic_ctx = ctx[ctx["source_table"].eq("python_dynamic_executed")].copy()

    exact_same_family = count_window(raw_ctx, 0, raw_ctx.get("same_family", pd.Series(False, index=raw_ctx.index)).astype(bool))
    same_family_60 = count_window(raw_ctx, 60, raw_ctx.get("same_family", pd.Series(False, index=raw_ctx.index)).astype(bool))
    same_family_7d = count_window(raw_ctx, 10080, raw_ctx.get("same_family", pd.Series(False, index=raw_ctx.index)).astype(bool))
    same_dir_7d = count_window(raw_ctx, 10080, raw_ctx.get("same_dir", pd.Series(False, index=raw_ctx.index)).astype(bool))
    same_postn_number_7d = count_window(
        raw_ctx,
        10080,
        (
            raw_ctx.get("same_dir", pd.Series(False, index=raw_ctx.index)).astype(bool)
            & raw_ctx.get("same_mode_family", pd.Series(False, index=raw_ctx.index)).astype(bool)
            & raw_ctx.get("same_post_n_number", pd.Series(False, index=raw_ctx.index)).astype(bool)
        ),
    )
    any_raw_7d = int(raw_ctx["abs_minutes_to_target"].le(10080).sum()) if not raw_ctx.empty else 0
    exact_raw_same_mode_any_trigger = count_window(
        raw_ctx,
        0,
        (
            raw_ctx.get("same_dir", pd.Series(False, index=raw_ctx.index)).astype(bool)
            & raw_ctx.get("same_mode_family", pd.Series(False, index=raw_ctx.index)).astype(bool)
            & raw_ctx.get("same_post_n_number", pd.Series(False, index=raw_ctx.index)).astype(bool)
        ),
    )
    exact_layer12_same_mode_any_trigger = count_window(
        layer12_ctx,
        0,
        (
            layer12_ctx.get("same_dir", pd.Series(False, index=layer12_ctx.index)).astype(bool)
            & layer12_ctx.get("same_mode_family", pd.Series(False, index=layer12_ctx.index)).astype(bool)
            & layer12_ctx.get("same_post_n_number", pd.Series(False, index=layer12_ctx.index)).astype(bool)
        ),
    )
    exact_layer3_same_mode_any_trigger = count_window(
        layer3_ctx,
        0,
        (
            layer3_ctx.get("same_dir", pd.Series(False, index=layer3_ctx.index)).astype(bool)
            & layer3_ctx.get("same_mode_family", pd.Series(False, index=layer3_ctx.index)).astype(bool)
            & layer3_ctx.get("same_post_n_number", pd.Series(False, index=layer3_ctx.index)).astype(bool)
        ),
    )
    exact_dynamic_same_mode_any_trigger = count_window(
        dynamic_ctx,
        0,
        (
            dynamic_ctx.get("same_dir", pd.Series(False, index=dynamic_ctx.index)).astype(bool)
            & dynamic_ctx.get("same_mode_family", pd.Series(False, index=dynamic_ctx.index)).astype(bool)
            & dynamic_ctx.get("same_post_n_number", pd.Series(False, index=dynamic_ctx.index)).astype(bool)
        ),
    )

    nearest_raw = raw_ctx.sort_values("abs_minutes_to_target").head(1)
    nearest_same_dir = raw_ctx[raw_ctx.get("same_dir", False).astype(bool)].sort_values("abs_minutes_to_target").head(1)

    mt5_signal_src = mt5_row.iloc[0]["signal_src"] if not mt5_row.empty else target.get("mode_or_signal_src", "")
    mt5_net = mt5_row.iloc[0]["net_profit"] if not mt5_row.empty else target.get("gap_effect_$", "")
    mt5_stop = mt5_row.iloc[0]["stop_pts_spec"] if not mt5_row.empty else ""

    if exact_raw_same_mode_any_trigger > 0 and exact_layer12_same_mode_any_trigger > 0 and exact_layer3_same_mode_any_trigger == 0:
        classification = "python_raw_parent_transformed_then_layer3_filtered"
        gate = False
        note = "Python has exact raw post_n evidence, but Layer1/2 transforms it away from M30 family and it does not reach Layer3/dynamic."
    elif exact_raw_same_mode_any_trigger > 0 and exact_dynamic_same_mode_any_trigger == 0:
        classification = "python_raw_present_but_not_executed"
        gate = False
        note = "Python has exact raw post_n evidence, but it is not an executed dynamic trade."
    elif same_family_7d == 0 and same_dir_7d == 0:
        classification = "python_raw_generation_absent_broad_window"
        gate = False
        note = "No Python raw same-dir or same-family candidate within 7d; source audit cannot mutate an existing raw row."
    elif same_family_7d == 0 and same_dir_7d > 0:
        classification = "python_raw_same_dir_but_no_same_family"
        gate = False
        note = "Python has same-dir raw evidence only outside the target family; needs broader source replay before any prototype."
    elif same_family_7d > 0 and same_postn_number_7d == 0:
        classification = "postn_number_or_counter_drift"
        gate = False
        note = "Same-family raw exists within 7d but not same post_n number; counter audit required before prototype."
    else:
        classification = "same_family_far_window_accounting"
        gate = False
        note = "Same-family raw evidence is outside reliable mapping window; keep diagnostic."

    return {
        "mt5_trade_id": tid,
        "target_time": fmt_dt(target["target_time"]),
        "raw_anchor": fmt_dt(target["raw_anchor"]),
        "dir_norm": target.get("dir_norm", ""),
        "trigger_family": target.get("trigger_family", ""),
        "mt5_signal_src": mt5_signal_src,
        "mt5_post_n_number": target.get("post_n_number", ""),
        "mt5_net_profit": mt5_net,
        "mt5_stop_pts_spec": mt5_stop,
        "raw_exact_same_family_count": exact_same_family,
        "raw_exact_same_mode_any_trigger_count": exact_raw_same_mode_any_trigger,
        "raw_60m_same_family_count": same_family_60,
        "raw_7d_same_family_count": same_family_7d,
        "raw_7d_same_dir_count": same_dir_7d,
        "raw_7d_same_postn_number_count": same_postn_number_7d,
        "raw_7d_any_count": any_raw_7d,
        "layer12_exact_same_mode_any_trigger_count": exact_layer12_same_mode_any_trigger,
        "layer3_exact_same_mode_any_trigger_count": exact_layer3_same_mode_any_trigger,
        "dynamic_exact_same_mode_any_trigger_count": exact_dynamic_same_mode_any_trigger,
        "nearest_raw_time": fmt_dt(nearest_raw.iloc[0]["row_time"]) if not nearest_raw.empty else "",
        "nearest_raw_abs_minutes": nearest_raw.iloc[0]["abs_minutes_to_target"] if not nearest_raw.empty else "",
        "nearest_raw_dir": nearest_raw.iloc[0]["dir_norm"] if not nearest_raw.empty else "",
        "nearest_raw_trigger": nearest_raw.iloc[0]["trigger_family"] if not nearest_raw.empty else "",
        "nearest_raw_mode": nearest_raw.iloc[0]["mode_or_signal_src"] if not nearest_raw.empty else "",
        "nearest_same_dir_raw_time": fmt_dt(nearest_same_dir.iloc[0]["row_time"]) if not nearest_same_dir.empty else "",
        "nearest_same_dir_raw_abs_minutes": nearest_same_dir.iloc[0]["abs_minutes_to_target"] if not nearest_same_dir.empty else "",
        "nearest_same_dir_raw_trigger": nearest_same_dir.iloc[0]["trigger_family"] if not nearest_same_dir.empty else "",
        "nearest_same_dir_raw_mode": nearest_same_dir.iloc[0]["mode_or_signal_src"] if not nearest_same_dir.empty else "",
        "primary_classification": classification,
        "low_blast_signal_prototype_gate_open": gate,
        "classification_note": note,
    }


def find_code_hits() -> pd.DataFrame:
    specs = [
        (EA_SOURCE, "ea_m30_close_postn", ["g_merged_post_n_counter", "strict_merged_post_n_counter", "SKIP_STRICT_MERGED_POSTN", "ExecuteSignalByMarket(signal_dir, signal_src"]),
        (PY_DIRECTION, "python_counter_state", ["last_cross", "counter = 0", "post_n[i]", "elif d == 'up'"]),
        (PY_PRE_CROSS, "python_build_post_n", ["def build_post_n", "merged_post_cross_n", "POST_N_MIN", "mode\": f\"post_n"]),
        (PY_PREPARE, "python_prepare_merged_counter", ["add_pre_cross_and_counter", "direction_col='方向_合并后'", "merged_"]),
    ]
    rows = []
    for path, source_area, patterns in specs:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for pattern in patterns:
                if pattern in line:
                    rows.append(
                        {
                            "source_area": source_area,
                            "file": str(path),
                            "line": lineno,
                            "pattern": pattern,
                            "text": line.strip(),
                        }
                    )
    return pd.DataFrame(rows)


def build_final_decision(summary: pd.DataFrame) -> pd.DataFrame:
    all_absent = bool(summary["primary_classification"].eq("python_raw_generation_absent_broad_window").all())
    mixed_loss_points = int(summary["primary_classification"].nunique())
    any_gate = bool(summary["low_blast_signal_prototype_gate_open"].astype(bool).any())
    return pd.DataFrame(
        [
            {
                "target_count": int(len(summary)),
                "target_ids": ";".join(summary["mt5_trade_id"].astype(str)),
                "all_targets_python_raw_generation_absent_broad_window": all_absent,
                "primary_classification_count": mixed_loss_points,
                "low_blast_signal_prototype_gate_open": any_gate,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "dynamic_risk_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_bucket": "close_independent_mt5_signal_gap_without_signal_change",
                "recommended_next_action": "do_not_modify_signal_or_ea_from_two_mixed_loss_point_samples",
            }
        ]
    )


def build_report(summary: pd.DataFrame, bucket: pd.DataFrame, final_decision: pd.DataFrame) -> list[str]:
    decision = final_decision.iloc[0]
    lines = [
        "# Stage-state M30 CLOSE post_n true no-candidate source audit",
        "",
        "## Decision",
        "",
        f"- Target count: `{decision['target_count']}`",
        f"- Target ids: `{decision['target_ids']}`",
        f"- All targets raw absent broad window: `{decision['all_targets_python_raw_generation_absent_broad_window']}`",
        f"- Primary classification count: `{decision['primary_classification_count']}`",
        f"- Low-blast signal prototype gate open: `{decision['low_blast_signal_prototype_gate_open']}`",
        "- Main signal / EA behavior / mapping / dynamic-risk / merge gates all remain `False`.",
        "",
        "## Case Summary",
        "",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"- `{row['mt5_trade_id']}` `{row['target_time']}` `{row['trigger_family']}/{row['mt5_signal_src']}`: "
            f"raw exact `{row['raw_exact_same_family_count']}`, raw 60m `{row['raw_60m_same_family_count']}`, "
            f"raw 7d same-family `{row['raw_7d_same_family_count']}`, "
            f"Layer3 exact same-mode `{row['layer3_exact_same_mode_any_trigger_count']}`, "
            f"classification `{row['primary_classification']}`"
        )
    lines += ["", "## Classification Buckets", ""]
    for _, row in bucket.iterrows():
        lines.append(
            f"- `{row['primary_classification']}`: rows `{row['rows']}`, ids `{row['mt5_trade_ids']}`"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The two targets split into different loss points: `mt5_0026` is broad-window Python raw absent, while `mt5_0061` has exact Python raw evidence but is transformed/filtered before Layer3/dynamic.",
        "- Because the cohort has mixed loss points and only two samples, it does not support a low-blast signal or EA change.",
        "- EA source shows M30 CLOSE/post_n is driven by `g_merged_post_n_counter` with strict-veto guard, while Python raw generation uses `merged_post_cross_n` produced by `add_pre_cross_and_counter()` over `方向_合并后`.",
    ]
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = load_targets()
    chain = load_signal_chain()
    mt5_unique = load_mt5_unique()

    context_rows: list[dict[str, object]] = []
    for _, target in targets.iterrows():
        context_rows.extend(context_for_target(target, chain))
    context = pd.DataFrame(context_rows)

    summary = pd.DataFrame([summarize_target(row, context, mt5_unique) for _, row in targets.iterrows()])
    bucket = (
        summary.groupby("primary_classification")
        .agg(
            rows=("mt5_trade_id", "size"),
            mt5_trade_ids=("mt5_trade_id", lambda values: ";".join(values)),
            low_blast_gate_open=("low_blast_signal_prototype_gate_open", "sum"),
        )
        .reset_index()
    )
    code_hits = find_code_hits()
    final_decision = build_final_decision(summary)

    write_csv(summary, OUT_DIR / "m30_close_postn_source_case_summary.csv")
    write_csv(context, OUT_DIR / "m30_close_postn_source_context_rows.csv")
    write_csv(bucket, OUT_DIR / "m30_close_postn_source_bucket_summary.csv")
    write_csv(code_hits, OUT_DIR / "m30_close_postn_source_code_hits.csv")
    write_csv(final_decision, OUT_DIR / "m30_close_postn_source_final_decision.csv")
    write_md(build_report(summary, bucket, final_decision), OUT_DIR / "m30_close_postn_source_audit.md")
    write_md(
        [
            "# M30 CLOSE post_n true no-candidate source audit output",
            "",
            "- `m30_close_postn_source_audit.md`",
            "- `m30_close_postn_source_final_decision.csv`",
            "- `m30_close_postn_source_case_summary.csv`",
            "- `m30_close_postn_source_context_rows.csv`",
            "- `m30_close_postn_source_bucket_summary.csv`",
            "- `m30_close_postn_source_code_hits.csv`",
        ],
        OUT_DIR / "README.md",
    )

    print(f"wrote {OUT_DIR}")
    print(final_decision.to_string(index=False))


if __name__ == "__main__":
    main()
