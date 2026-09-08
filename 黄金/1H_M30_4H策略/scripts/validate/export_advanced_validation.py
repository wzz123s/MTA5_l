# -*- coding: utf-8 -*-
"""Export Stage, StopSpec, position sizing, and EA-alignment packs."""
from __future__ import annotations


import itertools
import json
import math
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_workspace_common import (  # noqa: E402
    COMBO,
    FOCUS_TF,
    PERIOD_LABEL,
    SIGNALS_DIR,
    STRATEGY_NAME,
    VALIDATION_DIR,
    build_gate_scan,
    ensure_dirs,
    export_csv,
    focus_from_variant,
    metric,
    pick_primary_variant,
    read_csv_with_fallback,
    strategy_split_metrics,
    write_text,
)


STAGE1_VALUES = [1.0, 1.2, 1.5, 2.0]
STAGE2_TRAIL_VALUES = [1.5, 2.0, 2.5]
STAGE2_FORCE_VALUES = [2.5, 3.0, 4.0]
POSITION_GRID = [0.5, 1.0, 1.5, 2.0]
TOTAL_UNITS = 3.0
UNIT_LOT = 0.02
PT_VALUE_PER_LOT = 10.0
START_CAPITAL = 500.0
MIN_SAMPLE = 50


def _split_metrics(points: pd.Series, dates: pd.Series) -> tuple[dict, dict]:
    train, test, _ = strategy_split_metrics(points, dates)
    return train, test


def _score_stage(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["sample_ok"] = out["n"] >= MIN_SAMPLE
    out["score"] = (
        out["sample_ok"].astype(int) * 1000
        + out["pf"].clip(upper=200) * 10
        + out["test_pf"].clip(upper=50) * 2
        + out["ev"] * 0.02
    )
    return out


def _evaluate_position(out: pd.DataFrame, units: tuple[float, float, float]) -> dict:
    weighted_points = (
        units[0] * out["stage1_pnl"].astype(float)
        + units[1] * out["stage2_pnl"].astype(float)
        + units[2] * out["stage3_pnl"].astype(float)
    )
    dollars = weighted_points * UNIT_LOT * PT_VALUE_PER_LOT
    total_m = metric(weighted_points.values)
    _, test_m = _split_metrics(weighted_points, pd.to_datetime(out["date"]))
    return {
        "units": f"{units[0]:.1f}/{units[1]:.1f}/{units[2]:.1f}",
        "lots": f"{units[0] * UNIT_LOT:.2f}/{units[1] * UNIT_LOT:.2f}/{units[2] * UNIT_LOT:.2f}",
        "n": total_m["n"],
        "wr": total_m["wr"],
        "pf": total_m["pf"],
        "ev": total_m["ev"],
        "pnl_$": float(dollars.sum()),
        "maxcl": total_m["ml"],
        "test_pf": test_m["pf"],
        "test_ev": test_m["ev"],
    }


def _score_position(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["balanced_bonus"] = (out["units"] == "0.5/1.0/1.5").astype(int)
    out["score"] = (
        out["pf"].clip(upper=200) * 10
        + out["test_pf"].clip(upper=50) * 2
        + out["ev"] * 0.02
        + out["balanced_bonus"] * 0.3
    )
    return out


def _choose_step(sd_series: pd.Series) -> int:
    median = float(sd_series.dropna().median())
    if median <= 30:
        return 2
    if median <= 80:
        return 5
    return 10


def _round_down(value: float, step: int) -> int:
    return int(math.floor(float(value) / step) * step)


def _round_up(value: float, step: int) -> int:
    return int(math.ceil(float(value) / step) * step)


def _build_stop_band_grid(sd_series: pd.Series) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    sd = sd_series.dropna().astype(float)
    if sd.empty:
        return [], [], []
    step = _choose_step(sd)
    lo_values = {max(step, _round_down(sd.quantile(q), step)) for q in [0.10, 0.20, 0.30, 0.40]}
    hi_values = {max(step * 2, _round_up(sd.quantile(q), step)) for q in [0.60, 0.70, 0.80, 0.90]}
    lo_values.add(max(step, _round_down(sd.min(), step)))
    hi_values.add(max(step * 2, _round_up(sd.max(), step)))

    lo_sorted = sorted(lo_values)
    hi_sorted = sorted(hi_values)
    bands = []
    for spec_lo in lo_sorted:
        for spec_hi in hi_sorted:
            if spec_hi > spec_lo and spec_hi - spec_lo >= step:
                bands.append((spec_lo, spec_hi))
    return bands, lo_sorted, hi_sorted


def _evaluate_stop_band(frame: pd.DataFrame, units: tuple[float, float, float]) -> dict:
    weighted_points = (
        units[0] * frame["stage1_pnl"].astype(float)
        + units[1] * frame["stage2_pnl"].astype(float)
        + units[2] * frame["stage3_pnl"].astype(float)
    )
    dollars = weighted_points * UNIT_LOT * PT_VALUE_PER_LOT
    total_m = metric(weighted_points.values)
    _, test_m = _split_metrics(weighted_points, pd.to_datetime(frame["date"]))
    return {
        "trades": total_m["n"],
        "wr": total_m["wr"],
        "pf": total_m["pf"],
        "ev": total_m["ev"],
        "profit": float(dollars.sum()),
        "test_pf": test_m["pf"],
        "test_ev": test_m["ev"],
        "avg_stop": float(frame["sd"].mean()) if len(frame) else 0.0,
        "median_stop": float(frame["sd"].median()) if len(frame) else 0.0,
    }


def _score_stop(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["sample_ok"] = out["trades"] >= MIN_SAMPLE
    out["score"] = (
        out["sample_ok"].astype(int) * 1000
        + out["pf"].clip(upper=200) * 10
        + out["test_pf"].clip(upper=50) * 2
        + out["ev"] * 0.02
    )
    return out


def _units_tuple(label: str) -> tuple[float, float, float]:
    values = tuple(float(x) for x in str(label).split("/"))
    if len(values) != 3:
        raise ValueError(f"Expected three position units, got: {label}")
    return values  # type: ignore[return-value]


def _apply_stage_proxy(
    signals: pd.DataFrame,
    stage1_r: float,
    trail_r: float,
    force_r: float,
) -> pd.DataFrame:
    out = signals.copy().sort_values("date").reset_index(drop=True)
    pnl = out["pnl"].astype(float)
    risk_source = "stop_distance" if "stop_distance" in out.columns else "sd"
    risk = out[risk_source].astype(float).abs().replace(0, math.nan)
    out["stop_distance"] = risk
    out["sd"] = risk
    stage1_target = stage1_r * risk
    trail_target = trail_r * risk
    force_target = force_r * risk

    out["stage1_pnl"] = pnl.where(pnl <= stage1_target, stage1_target)
    out["stage2_pnl"] = pnl.where(pnl <= force_target, trail_target)
    out["stage3_pnl"] = pnl
    out["total_points"] = out[["stage1_pnl", "stage2_pnl", "stage3_pnl"]].sum(axis=1)
    out["stage_proxy_note"] = "mt5_raw_proxy_pending_ea_path_replay"
    return out


def _build_stage_and_position(primary_variant: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    candidates = read_csv_with_fallback(SIGNALS_DIR / "strategy_candidate_trades.csv")
    signals = candidates.loc[candidates["variant"].astype(str) == primary_variant].copy().sort_values("date").reset_index(drop=True)
    if signals.empty:
        raise RuntimeError(f"No candidate trades found for primary variant: {primary_variant}")

    stage_rows = []
    trades_by_key: dict[tuple[float, float, float], pd.DataFrame] = {}
    for stage1_r in STAGE1_VALUES:
        for trail_r in STAGE2_TRAIL_VALUES:
            for force_r in STAGE2_FORCE_VALUES:
                if force_r <= trail_r:
                    continue
                out = _apply_stage_proxy(signals, stage1_r, trail_r, force_r)
                total_m = metric(out["total_points"].astype(float).values)
                _, test_m = _split_metrics(out["total_points"], pd.to_datetime(out["date"]))
                row = {
                    "combo": COMBO,
                    "variant": primary_variant,
                    "stage1_r": stage1_r,
                    "stage2_trail_r": trail_r,
                    "stage2_force_r": force_r,
                    "n": total_m["n"],
                    "wr": total_m["wr"],
                    "pf": total_m["pf"],
                    "ev": total_m["ev"],
                    "pnl": total_m["pnl"],
                    "maxcl": total_m["ml"],
                    "test_pf": test_m["pf"],
                    "test_ev": test_m["ev"],
                }
                stage_rows.append(row)
                trades_by_key[(stage1_r, trail_r, force_r)] = out

    stage_df = _score_stage(pd.DataFrame(stage_rows)).sort_values(
        ["score", "test_ev", "pnl"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    best_stage = stage_df.iloc[0]
    best_key = (
        float(best_stage["stage1_r"]),
        float(best_stage["stage2_trail_r"]),
        float(best_stage["stage2_force_r"]),
    )
    best_trades = trades_by_key[best_key].copy()
    best_trades["combo"] = COMBO
    best_trades["variant"] = primary_variant
    best_trades["picked_stage1_r"] = best_key[0]
    best_trades["picked_stage2_trail_r"] = best_key[1]
    best_trades["picked_stage2_force_r"] = best_key[2]

    position_rows = []
    for units in itertools.product(POSITION_GRID, repeat=3):
        if abs(sum(units) - TOTAL_UNITS) > 1e-9:
            continue
        row = _evaluate_position(best_trades, units)
        row.update(
            {
                "combo": COMBO,
                "variant": primary_variant,
                "stage1_r": best_key[0],
                "stage2_trail_r": best_key[1],
                "stage2_force_r": best_key[2],
            }
        )
        position_rows.append(row)
    position_df = _score_position(pd.DataFrame(position_rows)).sort_values(
        ["score", "test_ev", "pnl_$"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    best_position = position_df.iloc[0]
    return stage_df, position_df, best_trades, best_stage, best_position


def _build_stop_scan(primary_variant: str, best_trades: pd.DataFrame, best_position: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    focus_label = focus_from_variant(primary_variant).lower()
    best_trades = best_trades.copy()
    best_trades["date"] = pd.to_datetime(best_trades["date"])
    if "stop_distance" not in best_trades.columns:
        best_trades["stop_distance"] = best_trades["sd"]
    trade_frame = best_trades.copy()
    trade_frame["stop_distance"] = pd.to_numeric(trade_frame["stop_distance"], errors="coerce")
    trade_frame["sd"] = trade_frame["stop_distance"]
    trade_frame = trade_frame.dropna(subset=["stop_distance"]).reset_index(drop=True)

    bands, lo_grid, hi_grid = _build_stop_band_grid(trade_frame["stop_distance"])
    units = _units_tuple(str(best_position["units"]))
    rows = []
    for spec_lo, spec_hi in bands:
        scoped = trade_frame[trade_frame["stop_distance"].between(spec_lo, spec_hi, inclusive="both")].copy()
        metrics = _evaluate_stop_band(scoped, units)
        rows.append(
            {
                "combo": COMBO,
                "current_variant": primary_variant,
                "focus_tf": focus_label.upper(),
                "stopspec_source": "stop_distance",
                "stop_range": f"{spec_lo}-{spec_hi}pt",
                "stop_lo": spec_lo,
                "stop_hi": spec_hi,
                "grid_lo": "/".join(str(x) for x in lo_grid),
                "grid_hi": "/".join(str(x) for x in hi_grid),
                **metrics,
            }
        )
    detail = _score_stop(pd.DataFrame(rows)).sort_values(
        ["score", "test_ev", "profit", "trades"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    viable = detail[detail["trades"] >= MIN_SAMPLE].copy()
    ranked = viable if len(viable) else detail
    primary = ranked.iloc[0]
    secondary = ranked.iloc[1] if len(ranked) > 1 else primary
    top_score = float(ranked["score"].max())
    near_top = ranked[ranked["score"] >= top_score * 0.95].copy()
    if near_top.empty:
        near_top = ranked.head(1).copy()
    summary = pd.DataFrame(
        [
            {
                "combo": COMBO,
                "current_variant": primary_variant,
                "focus_tf": focus_label.upper(),
                "stage_params": f"{best_trades['picked_stage1_r'].iloc[0]:.1f}/{best_trades['picked_stage2_trail_r'].iloc[0]:.1f}/{best_trades['picked_stage2_force_r'].iloc[0]:.1f}",
                "units": best_position["units"],
                "lots": best_position["lots"],
                "grid_lo": "/".join(str(x) for x in lo_grid),
                "grid_hi": "/".join(str(x) for x in hi_grid),
                "primary_stop_range": primary["stop_range"],
                "secondary_stop_range": secondary["stop_range"],
                "acceptable_stop_range": f"{int(near_top['stop_lo'].min())}-{int(near_top['stop_hi'].max())}pt",
                "stopspec_source": "stop_distance",
                "primary_trades": int(primary["trades"]),
                "primary_pf": float(primary["pf"]),
                "primary_test_pf": float(primary["test_pf"]),
                "primary_ev": float(primary["ev"]),
                "primary_profit": float(primary["profit"]),
            }
        ]
    )
    return detail, summary


def _build_final_summary(primary: pd.Series, best_stage: pd.Series, best_position: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "combo": COMBO,
                "picked_variant": primary["variant"],
                "picked_desc": primary["desc"],
                "picked_n": int(primary["n"]),
                "picked_pf": float(primary["pf"]),
                "picked_ev": float(primary["ev"]),
                "picked_test_pf": float(primary["test_pf"]),
                "picked_test_ev": float(primary["test_ev"]),
                "stage1_r": float(best_stage["stage1_r"]),
                "stage2_trail_r": float(best_stage["stage2_trail_r"]),
                "stage2_force_r": float(best_stage["stage2_force_r"]),
                "stage_pf": float(best_stage["pf"]),
                "stage_ev": float(best_stage["ev"]),
                "stage_test_pf": float(best_stage["test_pf"]),
                "stage_test_ev": float(best_stage["test_ev"]),
                "units": best_position["units"],
                "lots": best_position["lots"],
                "final_pf": float(best_position["pf"]),
                "final_ev": float(best_position["ev"]),
                "final_pnl_$": float(best_position["pnl_$"]),
                "final_test_pf": float(best_position["test_pf"]),
                "final_test_ev": float(best_position["test_ev"]),
            }
        ]
    )


def _export_ea_alignment(final_summary: pd.DataFrame, stop_summary: pd.DataFrame) -> None:
    row = final_summary.iloc[0]
    stop = stop_summary.iloc[0]
    params = {
        "strategy": STRATEGY_NAME,
        "combo": COMBO,
        "periods": PERIOD_LABEL,
        "focus_tf": FOCUS_TF,
        "primary_variant": row["picked_variant"],
        "stage": {
            "stage1_r": float(row["stage1_r"]),
            "stage2_trail_r": float(row["stage2_trail_r"]),
            "stage2_force_r": float(row["stage2_force_r"]),
        },
        "position": {
            "units": row["units"],
            "lots": row["lots"],
            "unit_lot": UNIT_LOT,
            "start_capital": START_CAPITAL,
        },
        "stop_spec": {
            "primary": stop["primary_stop_range"],
            "secondary": stop["secondary_stop_range"],
            "acceptable": stop["acceptable_stop_range"],
        },
        "ea_status": "research_parameters_ready__ea_adapter_pending",
        "reference_ea": "黄金/30m2H策略/参考实现工程/auto_trade",
    }
    param_path = VALIDATION_DIR / "ea_parameter_pack.json"
    param_path.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checklist = pd.DataFrame(
        [
            ["研究层参数", "done", "Stage / StopSpec / 仓位参数已落到 ea_parameter_pack.json"],
            ["行情时间语义", "partial", "沿用参考工程 M30 +2h 口径；EA 端仍需实盘日志核对"],
            ["信号门复现", "partial", "Python 候选门已导出；EA 端需新增对应周期上下文门"],
            ["执行阶段复现", "partial", "Python Stage 扫描已导出；EA 端需按本策略参数实现或映射"],
            ["EA 源码", "pending", "尚未新建本策略专用 EA，参考 30m2H auto_trade"],
            ["Python vs EA 对账", "pending", "待 EA 产生日志后再做逐笔映射"],
        ],
        columns=["item", "status", "note"],
    )
    export_csv(checklist, VALIDATION_DIR / "ea_alignment_readiness.csv")
    write_text(
        "说明文档/03_验证结果/EA对齐说明.md",
        f"""# {STRATEGY_NAME} EA 对齐说明

## 当前状态

- 研究层参数包已生成：`data/validation/ea_parameter_pack.json`
- EA 对齐检查表已生成：`data/validation/ea_alignment_readiness.csv`
- 当前没有声明 EA 已完成逐笔对齐；状态是 `research_parameters_ready__ea_adapter_pending`。

## 参数摘要

- 组合门：`{row["picked_variant"]}`
- Stage：`{float(row["stage1_r"]):.1f}/{float(row["stage2_trail_r"]):.1f}/{float(row["stage2_force_r"]):.1f}`
- 仓位单位：`{row["units"]}`
- 手数：`{row["lots"]}`
- 主止损范围：`{stop["primary_stop_range"]}`

## 下一步

1. 从 `黄金/30m2H策略/参考实现工程/auto_trade` 迁移 EA 框架。
2. 增加 `{PERIOD_LABEL}` 上下文门计算。
3. 用 `ea_parameter_pack.json` 固定 Stage / StopSpec / 仓位参数。
4. 导出 EA 日志后再做 Python vs EA 逐笔对账。
""",
    )


def _export_ea_alignment(final_summary: pd.DataFrame, stop_summary: pd.DataFrame) -> None:
    row = final_summary.iloc[0]
    stop = stop_summary.iloc[0]
    params = {
        "strategy": STRATEGY_NAME,
        "combo": COMBO,
        "periods": PERIOD_LABEL,
        "focus_tf": FOCUS_TF,
        "primary_variant": row["picked_variant"],
        "stage": {
            "stage1_r": float(row["stage1_r"]),
            "stage2_trail_r": float(row["stage2_trail_r"]),
            "stage2_force_r": float(row["stage2_force_r"]),
        },
        "position": {
            "units": row["units"],
            "lots": row["lots"],
            "unit_lot": UNIT_LOT,
            "start_capital": START_CAPITAL,
        },
        "stop_spec": {
            "primary": stop["primary_stop_range"],
            "secondary": stop["secondary_stop_range"],
            "acceptable": stop["acceptable_stop_range"],
            "source": "stop_distance",
        },
        "feature_rules": {
            "bias": "directional_signed_bias5_bias13_bias55",
            "stopspec": "structural_stop_distance",
            "recent2_any": "control_only",
            "atr": "risk_filter_only",
        },
        "ea_status": "python_research_rebuilt__ea_pending",
        "reference_ea": "黄金/30m2H策略/参考实现工程/auto_trade",
        "research_set": f"{STRATEGY_NAME}_Strategy_EA.mt5_raw_research_20260725.set",
        "stage_model_status": "proxy_pending_ea_path_replay",
    }
    (VALIDATION_DIR / "ea_parameter_pack.json").write_text(
        json.dumps(params, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    checklist = pd.DataFrame(
        [
            ["MT5 raw data", "done", "History manifest and live smoke output exist for this strategy."],
            ["Research parameters", "done", "Stage / StopSpec / position profile exported to ea_parameter_pack.json."],
            ["Feature rules", "done", "Bias uses directional signed fields; StopSpec uses structural stop_distance."],
            ["EA source file", "partial", "Dedicated mq5 exists, but it still inherits the old EA structure."],
            ["Research .set", "done", f"{STRATEGY_NAME}_Strategy_EA.mt5_raw_research_20260725.set generated for backtest only."],
            ["EA compile", "pending", "Compile in MetaEditor and keep the compiler log before deployment."],
            ["Python vs EA alignment", "pending", "Current alignment is not refreshed for the MT5-raw profile; EA ledger is required."],
            ["Live deployment", "blocked", "Use only for MT5 Strategy Tester or demo until alignment passes."],
        ],
        columns=["item", "status", "note"],
    )
    export_csv(checklist, VALIDATION_DIR / "ea_alignment_readiness.csv")
    write_text(
        "说明文档/03_验证结果/EA对齐说明.md",
        f"""# {STRATEGY_NAME} EA alignment note

## Current status

- Research parameter pack: `data/validation/ea_parameter_pack.json`
- EA readiness checklist: `data/validation/ea_alignment_readiness.csv`
- Status: `python_research_rebuilt__ea_pending`

## Parameter summary

- Variant: `{row["picked_variant"]}`
- Stage: `{float(row["stage1_r"]):.1f}/{float(row["stage2_trail_r"]):.1f}/{float(row["stage2_force_r"]):.1f}`
- Units: `{row["units"]}`
- Lots: `{row["lots"]}`
- Primary StopSpec: `{stop["primary_stop_range"]}`
- StopSpec source: `stop_distance`
- Research set: `{STRATEGY_NAME}_Strategy_EA.mt5_raw_research_20260725.set`

## Required before MT5 deployment

1. Compile the dedicated EA in MetaEditor.
2. Run MT5 Strategy Tester with the MT5-raw research set.
3. Export EA trade ledger.
4. Re-run Python vs EA trade alignment.
5. Promote only after alignment passes.""",
    )


def main() -> None:
    ensure_dirs()
    summary = read_csv_with_fallback(SIGNALS_DIR / "strategy_variant_summary.csv")
    primary = pick_primary_variant(summary)
    primary_variant = str(primary["variant"])

    export_csv(build_gate_scan(summary, primary_variant), VALIDATION_DIR / "combo_gate_range_scan.csv")
    stage_df, position_df, best_trades, best_stage, best_position = _build_stage_and_position(primary_variant)
    final_summary = _build_final_summary(primary, best_stage, best_position)
    stop_detail, stop_summary = _build_stop_scan(primary_variant, best_trades, best_position)

    export_csv(stage_df, VALIDATION_DIR / "combo_stage12_sweep.csv")
    export_csv(stage_df.head(3), VALIDATION_DIR / "combo_top3_stage12.csv")
    export_csv(best_trades, VALIDATION_DIR / "combo_best_stage12_trades.csv")
    export_csv(position_df, VALIDATION_DIR / "combo_position_sizing.csv")
    export_csv(position_df.head(3), VALIDATION_DIR / "combo_top3_position.csv")
    export_csv(final_summary, VALIDATION_DIR / "combo_final_best_summary.csv")
    export_csv(stop_detail, VALIDATION_DIR / "combo_stop_range_scan.csv")
    export_csv(stop_summary, VALIDATION_DIR / "combo_stop_range_pick.csv")
    export_csv(stop_summary, VALIDATION_DIR / "combo_combined_summary.csv")
    _export_ea_alignment(final_summary, stop_summary)

    manifest = [
        "# 高级验证输出",
        "",
        "- `combo_stage12_sweep.csv`",
        "- `combo_top3_stage12.csv`",
        "- `combo_best_stage12_trades.csv`",
        "- `combo_position_sizing.csv`",
        "- `combo_top3_position.csv`",
        "- `combo_final_best_summary.csv`",
        "- `combo_stop_range_scan.csv`",
        "- `combo_stop_range_pick.csv`",
        "- `combo_combined_summary.csv`",
        "- `ea_parameter_pack.json`",
        "- `ea_alignment_readiness.csv`",
    ]
    write_text("说明文档/03_验证结果/高级验证输出.md", "\n".join(manifest))
    write_text(
        "data/validation/README.md",
        f"""# {STRATEGY_NAME} 验证数据

## 本地验证输出

- `strategy_summary.csv`
- `combo_gate_range_scan.csv`
- `yearly_performance.csv`
- `combo_stage12_sweep.csv`
- `combo_top3_stage12.csv`
- `combo_best_stage12_trades.csv`
- `combo_position_sizing.csv`
- `combo_top3_position.csv`
- `combo_final_best_summary.csv`
- `combo_stop_range_scan.csv`
- `combo_stop_range_pick.csv`
- `combo_combined_summary.csv`
- `ea_parameter_pack.json`
- `ea_alignment_readiness.csv`

## 说明

- 当前验证已覆盖候选门表现、主推荐门、按年表现、Stage 扫描、StopSpec 扫描、仓位档位扫描和 EA 参数包。
- EA 侧尚未声明逐笔对齐完成；当前状态是研究参数已就绪，执行端适配待接入。
""",
    )
    print(f"Exported advanced validation bundle for {COMBO}.")


if __name__ == "__main__":
    main()
