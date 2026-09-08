# -*- coding: utf-8 -*-
"""Review stage exit rule differences for matched shift90 trades."""
from __future__ import annotations


from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
MATCHED_DIR = DATA_DIR / "validation" / "matched_profit_exit_diff_shift90_20260713"
DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_20260713"
MT5_LEDGER_DIR = DATA_DIR / "validation" / "mt5_ledger_deinitfix_full_20260713_v1"
OUT_DIR = DATA_DIR / "validation" / "stage_exit_rule_alignment_shift90_20260714"


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL"}:
        return "SELL"
    if text in {"B", "BUY", "L"}:
        return "BUY"
    return text


def mode_family(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def trigger_family_from_tag(value: object) -> str:
    text = str(value).replace("[", "").replace("]", "").strip()
    if text.startswith("M15"):
        return "M15 SLOT1"
    if text.startswith("M30"):
        return "M30 CLOSE"
    return text


def sign_label(value: object) -> str:
    try:
        number = float(value)
    except Exception:
        return "na"
    if pd.isna(number):
        return "na"
    if number > 0:
        return "win"
    if number < 0:
        return "loss"
    return "flat"


def abs_bucket(value: object) -> str:
    try:
        number = abs(float(value))
    except Exception:
        return "na"
    if pd.isna(number):
        return "na"
    if number <= 1:
        return "<=1"
    if number <= 5:
        return "<=5"
    if number <= 20:
        return "<=20"
    if number <= 50:
        return "<=50"
    if number <= 100:
        return "<=100"
    return ">100"


def ratio_bucket(value: object) -> str:
    try:
        number = float(value)
    except Exception:
        return "na"
    if pd.isna(number):
        return "na"
    if number <= 1.5:
        return "<=1.5x"
    if number <= 3:
        return "<=3x"
    if number <= 5:
        return "<=5x"
    if number <= 10:
        return "<=10x"
    return ">10x"


def split_list(value: object, cast: Any = str, count: int = 3) -> list[Any]:
    parts = [p.strip() for p in str(value).split(",")]
    out: list[Any] = []
    for part in parts[:count]:
        if part == "" or part.lower() == "nan":
            out.append(pd.NA)
            continue
        try:
            out.append(cast(part))
        except Exception:
            out.append(part)
    while len(out) < count:
        out.append(pd.NA)
    return out


def split_semicolon(value: object, count: int = 3) -> list[str]:
    parts = [p.strip() for p in str(value).split(";")]
    parts = [p for p in parts if p and p.lower() != "nan"]
    while len(parts) < count:
        parts.append("")
    return parts[:count]


def load_matched_details() -> pd.DataFrame:
    df = pd.read_csv(MATCHED_DIR / "matched_profit_exit_diff_details.csv", encoding="utf-8-sig")
    return df.copy()


def load_python_stage_detail() -> pd.DataFrame:
    df = pd.read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv", encoding="utf-8-sig")
    df = df.copy()
    df["py_trade_id"] = [f"python_mt5_{i + 1:04d}" for i in range(len(df))]
    keep = [
        "py_trade_id",
        "balance_before",
        "balance_after",
        "dynamic_total_lot",
        "stage1_lot",
        "stage2_lot",
        "stage3_lot",
        "stage1_dynamic_$",
        "stage2_dynamic_$",
        "stage3_dynamic_$",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
    ]
    return df[[c for c in keep if c in df.columns]].copy()


def load_mt5_stage_detail() -> pd.DataFrame:
    ledger = pd.read_csv(MT5_LEDGER_DIR / "30m2H_strategy_trade_ledger.csv", encoding="utf-8-sig")
    ledger = ledger.copy()
    ledger["signal_anchor_time"] = pd.to_datetime(
        ledger["signal_anchor_time"], format="%Y.%m.%d %H:%M", errors="coerce"
    )
    ledger["trigger_family"] = ledger["trigger_tag"].map(trigger_family_from_tag)
    ledger["mode_family"] = ledger["signal_src"].map(mode_family)
    ledger["dir_norm"] = ledger["dir"].map(normalize_dir)
    for col in [
        "stage",
        "signal_entry",
        "signal_stop",
        "fill_price",
        "actual_stop",
        "lots",
        "stop_pts",
        "exit_price",
        "net_profit",
    ]:
        ledger[col] = pd.to_numeric(ledger[col], errors="coerce")

    key_cols = ["signal_anchor_time", "trigger_family", "mode_family", "dir_norm"]
    rows: list[pd.DataFrame] = []
    for trade_idx, (_, grp) in enumerate(
        ledger.sort_values(["signal_anchor_time", "stage"]).groupby(key_cols, sort=False),
        start=1,
    ):
        stage_rows = grp.sort_values(["stage", "ticket"]).copy()
        stage_rows["mt5_trade_id"] = f"mt5_{trade_idx:04d}"
        rows.append(stage_rows)

    if not rows:
        return pd.DataFrame()

    out = pd.concat(rows, ignore_index=True)
    return out[
        [
            "mt5_trade_id",
            "stage",
            "ticket",
            "position_id",
            "local_exit_reason",
            "deal_reason",
            "exit_time",
            "exit_price",
            "lots",
            "stop_pts",
            "net_profit",
            "deal_comment",
            "deal_ticket",
        ]
    ].copy()


def build_stage_rows() -> pd.DataFrame:
    matched = load_matched_details()
    py = load_python_stage_detail()
    mt5 = load_mt5_stage_detail()

    details = matched.merge(py, on="py_trade_id", how="left", suffixes=("", "_py_runtime"))
    focus = details[details["primary_diff_class"].eq("stage_exit_detail_diff")].copy()

    rows: list[dict[str, object]] = []
    for _, row in focus.iterrows():
        mt5_rows = mt5[mt5["mt5_trade_id"].eq(row["mt5_trade_id"])].copy()
        mt5_by_stage = {int(r["stage"]): r for _, r in mt5_rows.iterrows() if pd.notna(r["stage"])}
        for stage in [1, 2, 3]:
            mt5_stage = mt5_by_stage.get(stage, pd.Series(dtype=object))
            py_profit = row.get(f"stage{stage}_dynamic_$")
            mt5_profit = mt5_stage.get("net_profit", pd.NA)
            py_lot = row.get(f"stage{stage}_lot")
            mt5_lot = mt5_stage.get("lots", pd.NA)
            try:
                profit_diff = float(py_profit) - float(mt5_profit)
            except Exception:
                profit_diff = pd.NA
            try:
                lot_ratio = float(py_lot) / float(mt5_lot) if float(mt5_lot) != 0 else pd.NA
            except Exception:
                lot_ratio = pd.NA

            py_exit = str(row.get(f"stage{stage}_exit", ""))
            deal_reason = str(mt5_stage.get("deal_reason", ""))
            local_reason = str(mt5_stage.get("local_exit_reason", ""))

            rows.append(
                {
                    "policy": row.get("policy"),
                    "effective_match_tier": row.get("effective_match_tier"),
                    "py_trade_id": row.get("py_trade_id"),
                    "mt5_trade_id": row.get("mt5_trade_id"),
                    "py_date": row.get("py_date"),
                    "mt5_aligned_time": row.get("mt5_aligned_time"),
                    "dir_norm": row.get("dir_norm"),
                    "py_trigger_family": row.get("py_trigger_family"),
                    "mt5_trigger_family": row.get("mt5_trigger_family"),
                    "py_mode_family": row.get("py_mode_family"),
                    "mt5_mode_family": row.get("mt5_mode_family"),
                    "py_variant": row.get("py_variant"),
                    "trade_profit_abs_diff": row.get("profit_abs_diff"),
                    "trade_profit_diff_bucket": row.get("profit_diff_bucket"),
                    "stage": stage,
                    "py_exit": py_exit,
                    "py_stage_profit": py_profit,
                    "py_stage_lot": py_lot,
                    "mt5_local_exit_reason": local_reason,
                    "mt5_deal_reason": deal_reason,
                    "mt5_exit_time": mt5_stage.get("exit_time", ""),
                    "mt5_exit_price": mt5_stage.get("exit_price", pd.NA),
                    "mt5_stage_lot": mt5_lot,
                    "mt5_stage_stop_pts": mt5_stage.get("stop_pts", pd.NA),
                    "mt5_stage_profit": mt5_profit,
                    "stage_profit_diff": profit_diff,
                    "stage_profit_abs_diff_bucket": abs_bucket(profit_diff),
                    "py_profit_sign": sign_label(py_profit),
                    "mt5_profit_sign": sign_label(mt5_profit),
                    "sign_pair": f"{sign_label(py_profit)}->{sign_label(mt5_profit)}",
                    "stage_lot_ratio_py_over_mt5": lot_ratio,
                    "stage_lot_ratio_bucket": ratio_bucket(lot_ratio),
                    "exit_relation": classify_exit_relation(stage, py_exit, local_reason, deal_reason),
                    "deal_comment": mt5_stage.get("deal_comment", ""),
                    "deal_ticket": mt5_stage.get("deal_ticket", ""),
                }
            )

    return pd.DataFrame(rows)


def classify_exit_relation(stage: int, py_exit: str, local_reason: str, deal_reason: str) -> str:
    py_text = py_exit.lower()
    local_text = local_reason.lower()
    deal_text = deal_reason.upper()

    if "tp" in py_text and deal_text == "EXPERT":
        return "py_tp_mt5_expert_close"
    if "tp" in py_text and deal_text == "SL":
        return "py_tp_mt5_sl"
    if "forced" in py_text and deal_text == "EXPERT":
        return "py_forced_mt5_expert_close"
    if "forced" in py_text and deal_text == "SL":
        return "py_forced_mt5_sl"
    if "merged cross" in py_text and "stage3_cross_exit" in local_text:
        return "both_cross_but_price_time_may_diff"
    if "merged cross" in py_text and deal_text == "SL":
        return "py_cross_mt5_sl"
    if "trail/sl" in py_text and deal_text == "SL":
        return "both_stop_or_trail"
    if "sl hit" in py_text and deal_text == "SL":
        return "both_initial_sl"
    if stage == 2 and deal_text == "SL":
        return "mt5_stage2_sl_after_trail_or_initial"
    if deal_text == "EXPERT":
        return "mt5_expert_close_other"
    return "other"


def grouped(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=cols + ["rows"])
    return (
        frame.groupby(cols, dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(cols + ["rows"], ascending=[True] * len(cols) + [False])
    )


def numeric_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    work = frame.copy()
    for col in ["stage_profit_diff", "py_stage_lot", "mt5_stage_lot", "stage_lot_ratio_py_over_mt5"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    return (
        work.groupby(["stage", "py_exit", "mt5_deal_reason"], dropna=False)
        .agg(
            rows=("py_trade_id", "size"),
            avg_stage_profit_diff=("stage_profit_diff", "mean"),
            max_abs_stage_profit_diff=("stage_profit_diff", lambda s: s.abs().max()),
            avg_py_lot=("py_stage_lot", "mean"),
            avg_mt5_lot=("mt5_stage_lot", "mean"),
            avg_lot_ratio=("stage_lot_ratio_py_over_mt5", "mean"),
        )
        .reset_index()
        .sort_values(["stage", "rows", "max_abs_stage_profit_diff"], ascending=[True, False, False])
    )


def render_report(stage_rows: pd.DataFrame, summaries: dict[str, pd.DataFrame], top_rows: pd.DataFrame) -> str:
    lines = [
        "# Stage Exit Rule Alignment Review - shift90",
        "",
        "## Scope",
        "",
        "- 输入样本：`matched_profit_exit_diff_shift90_20260713/matched_profit_exit_diff_details.csv` 中 `primary_diff_class = stage_exit_detail_diff` 的 18 笔。",
        "- 展开口径：每笔拆成 Stage1/Stage2/Stage3，共 54 行 stage 明细。",
        "- 回补字段：Python stage exit/profit/lot，MT5 local_exit_reason/deal_reason/net_profit/lot/exit_price。",
        "",
        "## Exit Relation Summary",
        "",
        summaries["exit_relation"].to_markdown(index=False),
        "",
        "## Direction Summary",
        "",
        summaries["direction"].to_markdown(index=False),
        "",
        "## Stage / Python Exit / MT5 Deal Summary",
        "",
        summaries["stage_exit_deal"].to_markdown(index=False),
        "",
        "## Sign Pair Summary",
        "",
        summaries["sign_pair"].to_markdown(index=False),
        "",
        "## Lot Ratio Summary",
        "",
        summaries["lot_ratio"].to_markdown(index=False),
        "",
        "## Numeric Summary",
        "",
        summaries["numeric"].to_markdown(index=False),
        "",
        "## Top Stage Profit Differences",
        "",
        top_rows.to_markdown(index=False),
        "",
        "## Source Rule Comparison",
        "",
        "- Python `scripts/_stage12_combo_test.py:93-155`：Stage1/Stage2/Stage3 以 M30 bar 的 high/low/close 回放；Stage1 先判 SL 再判 2.0R TP；Stage2 先判 4.0R forced，再判 trail_sl 命中，再更新 SMA13 trail；Stage3 先判 SL，再在 M30 merged direction flip 的 close 出场。",
        "- EA `auto_trade/30m2H_Strategy_EA.mq5:1389-1445`：Stage1/2 在 tick 上用 `rr` 管理；Stage1 到 2.0R 即 `ClosePos`；Stage2 到 4.0R 即 `ClosePos`，到 1.5R 后只修改 broker SL 到 SMA13，实际 trail exit 多数会表现为 deal reason `SL`。",
        "- EA `auto_trade/30m2H_Strategy_EA.mq5:2540-2562`：Stage1/2 当前把 `SYMBOL_BID` 缓存为统一 `cur_price` 传入 `CheckStageExit`。SELL 持仓的平仓/盈利阈值通常应以 ASK 侧确认，这是下一步必须 smoke 验证的强嫌疑点。",
        "- EA `auto_trade/30m2H_Strategy_EA.mq5:2577-2612`：Stage3 用 M30 SMA5/SMA13 buffer 在 tick 上检测 cross 后市价平仓；Python Stage3 是 M30 merged direction flip close 出场。两者同名但不是完全同一价格源/时点。",
        "- EA `auto_trade/30m2H_Strategy_EA.mq5:1465-1540`：动态手数按真实账户余额、真实 stop_pts 和交易品种 tick value 计算；Python 动态风险按模拟资金曲线重算。只要前序 PnL 不同，后续 stage lots 会继续分叉。",
        "",
        "## Current Decision",
        "",
        "- 不建议继续扩大 signal mapping 或 M15 parent filter；Stage exit 明细已经成为当前 PnL 残差主线。",
        "- 本次 `stage_exit_detail_diff` 的 18 笔全部是 SELL；下一步不应做全局 Stage 行为大改，应先验证 SELL 的 price-side 和出场时点。",
        "- 下一步优先做 EA Stage1/2 price-side smoke：按 BUY/SELL 分别记录 `bid/ask/current_price/rr/action/local_exit_reason`，验证 SELL 使用 BID 是否导致提前 TP/forced/trail-on。",
        "- Stage2 trailing 不宜直接按 Python `trail/SL hit` 等价 MT5 `SL`；需要补 ledger 字段记录 trail_on、SMA13 trail SL、修改时间，才能判断是规则差异还是记录口径差异。",
        "- 资金曲线对齐前，应先把 Python runtime-style Stage exit 改成更接近 EA tick/broker SL 模型，或把 EA ledger 诊断字段补齐后再决定是否改 EA 行为。",
        "",
        "## Output Files",
        "",
        "- `stage_exit_rule_alignment_stage_rows.csv`",
        "- `stage_exit_rule_alignment_exit_relation_summary.csv`",
        "- `stage_exit_rule_alignment_stage_exit_deal_summary.csv`",
        "- `stage_exit_rule_alignment_sign_pair_summary.csv`",
        "- `stage_exit_rule_alignment_lot_ratio_summary.csv`",
        "- `stage_exit_rule_alignment_numeric_summary.csv`",
        "- `stage_exit_rule_alignment_top_stage_diffs.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stage_rows = build_stage_rows()
    for col in ["stage_profit_diff", "trade_profit_abs_diff"]:
        stage_rows[col] = pd.to_numeric(stage_rows[col], errors="coerce")

    summaries = {
        "exit_relation": grouped(stage_rows, ["stage", "exit_relation"]),
        "direction": grouped(stage_rows[["py_trade_id", "dir_norm"]].drop_duplicates(), ["dir_norm"]),
        "stage_exit_deal": grouped(stage_rows, ["stage", "py_exit", "mt5_deal_reason", "mt5_local_exit_reason"]),
        "sign_pair": grouped(stage_rows, ["stage", "sign_pair", "exit_relation"]),
        "lot_ratio": grouped(stage_rows, ["stage", "stage_lot_ratio_bucket"]),
        "numeric": numeric_summary(stage_rows),
    }
    top_rows = stage_rows.sort_values("stage_profit_diff", key=lambda s: s.abs(), ascending=False).head(20)
    top_cols = [
        "py_trade_id",
        "mt5_trade_id",
        "py_date",
        "dir_norm",
        "stage",
        "py_exit",
        "mt5_local_exit_reason",
        "mt5_deal_reason",
        "py_stage_profit",
        "mt5_stage_profit",
        "stage_profit_diff",
        "py_stage_lot",
        "mt5_stage_lot",
        "stage_lot_ratio_py_over_mt5",
        "mt5_exit_price",
        "deal_comment",
        "exit_relation",
    ]
    top_rows = top_rows[[c for c in top_cols if c in top_rows.columns]].copy()

    export_csv(stage_rows, OUT_DIR / "stage_exit_rule_alignment_stage_rows.csv")
    export_csv(summaries["exit_relation"], OUT_DIR / "stage_exit_rule_alignment_exit_relation_summary.csv")
    export_csv(summaries["stage_exit_deal"], OUT_DIR / "stage_exit_rule_alignment_stage_exit_deal_summary.csv")
    export_csv(summaries["sign_pair"], OUT_DIR / "stage_exit_rule_alignment_sign_pair_summary.csv")
    export_csv(summaries["lot_ratio"], OUT_DIR / "stage_exit_rule_alignment_lot_ratio_summary.csv")
    export_csv(summaries["numeric"], OUT_DIR / "stage_exit_rule_alignment_numeric_summary.csv")
    export_csv(top_rows, OUT_DIR / "stage_exit_rule_alignment_top_stage_diffs.csv")
    write_text(OUT_DIR / "stage_exit_rule_alignment_report.md", render_report(stage_rows, summaries, top_rows))

    print(summaries["exit_relation"].to_string(index=False))
    print()
    print(summaries["sign_pair"].to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
