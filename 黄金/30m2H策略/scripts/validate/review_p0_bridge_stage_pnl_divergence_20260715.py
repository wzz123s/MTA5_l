from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

P0_DIR = VALIDATION_DIR / "p0_subset_full_chain_bridge_20260715"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_p0_subset_bridge_20260715"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_p0_subset_bridge_20260715"
MT5_LEDGER_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
OUT_DIR = VALIDATION_DIR / "p0_bridge_stage_pnl_divergence_20260715"

TARGET_MT5_IDS = ["mt5_0005", "mt5_0019"]
PY_VALUE_PER_SPEC_POINT_PER_LOT = 10.0


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")


def to_dt(value: object) -> pd.Timestamp:
    text = str(value).strip()
    if not text:
        return pd.NaT
    text = text.replace(".", "-")
    return pd.to_datetime(text, errors="coerce")


def num(value: object, default: float = 0.0) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(out):
        return default
    return float(out)


def direction_points(direction: str, entry: float, exit_price: float) -> float:
    text = str(direction).upper()
    if text in {"BUY", "L", "LONG"}:
        return exit_price - entry
    return entry - exit_price


def implied_exit_price(direction: str, entry: float, points: float) -> float:
    text = str(direction).upper()
    if text in {"BUY", "L", "LONG"}:
        return entry + points
    return entry - points


def safe_div(numerator: float, denominator: float) -> float | None:
    if abs(denominator) < 1e-12:
        return None
    return numerator / denominator


def fmt(value: object, digits: int = 6) -> object:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def build_stage_rows(
    matches: pd.DataFrame,
    dynamic: pd.DataFrame,
    bridge_stage: pd.DataFrame,
    ledger: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stage_rows: list[dict[str, object]] = []
    trade_rows: list[dict[str, object]] = []
    scenario_rows: list[dict[str, object]] = []

    for mt5_id in TARGET_MT5_IDS:
        match = matches.loc[matches["mt5_trade_id"] == mt5_id].iloc[0]
        py_date = to_dt(match["py_date"])
        anchor_dt = to_dt(match["mt5_signal_anchor_time"])
        signal_src = str(match["mt5_signal_src"])
        direction = str(match["dir_norm"])

        dyn_row = dynamic.loc[pd.to_datetime(dynamic["date"], errors="coerce") == py_date].iloc[0]
        bridge_row = bridge_stage.loc[bridge_stage["bridge_mt5_trade_id"] == mt5_id].iloc[0]

        led = ledger.loc[
            (ledger["_anchor_dt"] == anchor_dt)
            & (ledger["signal_src"].astype(str) == signal_src)
            & (ledger["dir"].astype(str).str.upper() == direction.upper())
        ].copy()
        led["stage_num"] = pd.to_numeric(led["stage"], errors="coerce").astype("Int64")
        led = led.sort_values("stage_num")
        if len(led) != 3:
            raise RuntimeError(f"{mt5_id}: expected 3 MT5 stage rows, got {len(led)}")

        py_weighted_points_lot = 0.0
        mt5_weighted_points_lot = 0.0
        py_dynamic_total = 0.0
        mt5_gross_total = 0.0
        mt5_net_total = 0.0
        swap_total = 0.0
        commission_total = 0.0
        py_points_py_lots_mt5_value = 0.0
        py_points_mt5_lots_mt5_value = 0.0
        mt5_points_mt5_lots_mt5_value = 0.0

        mt5_stage_values: list[float] = []
        py_stage_values: list[float] = []

        for stage in [1, 2, 3]:
            mt5_row = led.loc[led["stage_num"] == stage].iloc[0]
            py_points = num(bridge_row[f"stage{stage}_pnl"])
            py_lot = num(dyn_row[f"stage{stage}_lot"])
            py_dynamic = num(dyn_row[f"stage{stage}_dynamic_$"])
            py_exit_reason = str(dyn_row[f"stage{stage}_exit"])

            mt5_entry = num(mt5_row["fill_price"])
            mt5_exit = num(mt5_row["exit_price"])
            mt5_lot = num(mt5_row["lots"])
            mt5_gross = num(mt5_row["profit"])
            mt5_swap = num(mt5_row["swap"])
            mt5_commission = num(mt5_row["commission"])
            mt5_net = num(mt5_row["net_profit"])
            mt5_points = direction_points(direction, mt5_entry, mt5_exit)

            py_exit = implied_exit_price(direction, num(dyn_row["entry"]), py_points)
            py_contract = safe_div(py_dynamic, py_points * py_lot)
            mt5_contract = safe_div(mt5_gross, mt5_points * mt5_lot)
            if py_contract is not None:
                py_stage_values.append(py_contract)
            if mt5_contract is not None:
                mt5_stage_values.append(mt5_contract)

            py_weighted_points_lot += py_points * py_lot
            mt5_weighted_points_lot += mt5_points * mt5_lot
            py_dynamic_total += py_dynamic
            mt5_gross_total += mt5_gross
            mt5_net_total += mt5_net
            swap_total += mt5_swap
            commission_total += mt5_commission

            # Use the MT5-inferred value at trade level after it is available.
            stage_rows.append(
                {
                    "mt5_trade_id": mt5_id,
                    "stage": stage,
                    "py_date": py_date,
                    "mt5_signal_anchor_time": anchor_dt,
                    "py_entry": num(dyn_row["entry"]),
                    "mt5_fill_price": mt5_entry,
                    "py_points": py_points,
                    "mt5_price_points": mt5_points,
                    "points_diff_mt5_minus_py": mt5_points - py_points,
                    "py_implied_exit_price": py_exit,
                    "mt5_exit_price": mt5_exit,
                    "exit_price_gap_mt5_minus_py": mt5_exit - py_exit,
                    "py_stage_lot": py_lot,
                    "mt5_lot": mt5_lot,
                    "lot_diff_mt5_minus_py": mt5_lot - py_lot,
                    "py_dynamic_$": py_dynamic,
                    "mt5_profit": mt5_gross,
                    "mt5_swap": mt5_swap,
                    "mt5_commission": mt5_commission,
                    "mt5_net_profit": mt5_net,
                    "net_gap_mt5_minus_py_dynamic": mt5_net - py_dynamic,
                    "py_exit_reason": py_exit_reason,
                    "mt5_local_exit_reason": mt5_row["local_exit_reason"],
                    "mt5_deal_reason": mt5_row["deal_reason"],
                    "mt5_exit_time": to_dt(mt5_row["exit_time"]),
                    "py_stage3_time": to_dt(bridge_row.get("stage3_time", "")) if stage == 3 else pd.NaT,
                    "py_contract_value_per_spec_point_per_lot": py_contract,
                    "mt5_contract_value_per_spec_point_per_lot": mt5_contract,
                    "contract_value_factor_mt5_over_py": safe_div(mt5_contract or 0.0, py_contract or 0.0),
                }
            )

        mt5_value = safe_div(mt5_gross_total, mt5_weighted_points_lot)
        if mt5_value is None:
            mt5_value = 100.0

        for row in stage_rows:
            if row["mt5_trade_id"] != mt5_id:
                continue
            py_points = float(row["py_points"])
            py_lot = float(row["py_stage_lot"])
            mt5_lot = float(row["mt5_lot"])
            mt5_points = float(row["mt5_price_points"])
            row["py_points_py_lots_at_mt5_value"] = py_points * py_lot * mt5_value
            row["py_points_mt5_lots_at_mt5_value"] = py_points * mt5_lot * mt5_value
            row["mt5_points_mt5_lots_at_mt5_value"] = mt5_points * mt5_lot * mt5_value

        py_points_py_lots_mt5_value = sum(
            float(r["py_points"]) * float(r["py_stage_lot"]) * mt5_value
            for r in stage_rows
            if r["mt5_trade_id"] == mt5_id
        )
        py_points_mt5_lots_mt5_value = sum(
            float(r["py_points"]) * float(r["mt5_lot"]) * mt5_value
            for r in stage_rows
            if r["mt5_trade_id"] == mt5_id
        )
        mt5_points_mt5_lots_mt5_value = sum(
            float(r["mt5_price_points"]) * float(r["mt5_lot"]) * mt5_value
            for r in stage_rows
            if r["mt5_trade_id"] == mt5_id
        )

        contract_value_effect = py_points_py_lots_mt5_value - py_dynamic_total
        lot_sizing_effect = py_points_mt5_lots_mt5_value - py_points_py_lots_mt5_value
        exit_price_effect = mt5_points_mt5_lots_mt5_value - py_points_mt5_lots_mt5_value
        cost_effect = mt5_net_total - mt5_points_mt5_lots_mt5_value
        reconstructed_gap = contract_value_effect + lot_sizing_effect + exit_price_effect + cost_effect

        bridge_entry_time = to_dt(bridge_row.get("entry_time", ""))
        mt5_first_open = to_dt(led["open_time"].iloc[0])
        py_date_minus_open = (py_date - mt5_first_open).total_seconds() / 60.0
        bridge_entry_minus_open = (bridge_entry_time - mt5_first_open).total_seconds() / 60.0
        py_date_minus_anchor = (py_date - anchor_dt).total_seconds() / 60.0
        mt5_open_minus_anchor = (mt5_first_open - anchor_dt).total_seconds() / 60.0

        trade_rows.append(
            {
                "mt5_trade_id": mt5_id,
                "py_trade_id": match["py_trade_id"],
                "py_date": py_date,
                "mt5_signal_anchor_time": anchor_dt,
                "mt5_signal_src": signal_src,
                "direction": direction,
                "py_variant": match["py_variant"],
                "py_balance_before": num(dyn_row["balance_before"]),
                "py_dynamic_total_lot": num(dyn_row["dynamic_total_lot"]),
                "py_stage_lot_sum": num(dyn_row["stage1_lot"]) + num(dyn_row["stage2_lot"]) + num(dyn_row["stage3_lot"]),
                "mt5_stage_lot_sum": float(led["lots"].astype(float).sum()),
                "py_stage_lots": f"{num(dyn_row['stage1_lot']):.2f}/{num(dyn_row['stage2_lot']):.2f}/{num(dyn_row['stage3_lot']):.2f}",
                "mt5_stage_lots": "/".join(f"{num(v):.2f}" for v in led["lots"].tolist()),
                "python_dynamic_total_$": py_dynamic_total,
                "python_stage_fixed_total_$": num(bridge_row["total_$"]),
                "mt5_gross_profit": mt5_gross_total,
                "mt5_swap": swap_total,
                "mt5_commission": commission_total,
                "mt5_net_profit": mt5_net_total,
                "net_gap_mt5_minus_python_dynamic": mt5_net_total - py_dynamic_total,
                "net_gap_mt5_minus_python_stage_fixed": mt5_net_total - num(bridge_row["total_$"]),
                "py_value_per_spec_point_per_lot": PY_VALUE_PER_SPEC_POINT_PER_LOT,
                "mt5_inferred_value_per_spec_point_per_lot": mt5_value,
                "contract_value_factor_mt5_over_py": mt5_value / PY_VALUE_PER_SPEC_POINT_PER_LOT,
                "contract_value_effect": contract_value_effect,
                "lot_sizing_effect": lot_sizing_effect,
                "exit_price_effect": exit_price_effect,
                "cost_effect": cost_effect,
                "reconstructed_gap": reconstructed_gap,
                "gap_reconstruction_error": (mt5_net_total - py_dynamic_total) - reconstructed_gap,
                "py_aligned_date_minus_mt5_open_min": py_date_minus_open,
                "bridge_entry_time_minus_mt5_open_min": bridge_entry_minus_open,
                "py_aligned_date_minus_mt5_anchor_min": py_date_minus_anchor,
                "mt5_open_minus_anchor_min": mt5_open_minus_anchor,
                "bridge_entry_time": bridge_entry_time,
                "mt5_first_open_time": mt5_first_open,
                "py_stage3_time": to_dt(bridge_row.get("stage3_time", "")),
                "mt5_stage3_exit_time": to_dt(led.loc[led["stage_num"] == 3, "exit_time"].iloc[0]),
                "stage3_exit_time_delta_min_mt5_minus_py": (
                    to_dt(led.loc[led["stage_num"] == 3, "exit_time"].iloc[0])
                    - to_dt(bridge_row.get("stage3_time", ""))
                ).total_seconds()
                / 60.0,
            }
        )

        scenarios = [
            ("current_python_dynamic", py_dynamic_total),
            ("py_points_py_lots_at_mt5_value", py_points_py_lots_mt5_value),
            ("py_points_mt5_lots_at_mt5_value", py_points_mt5_lots_mt5_value),
            ("mt5_points_mt5_lots_at_mt5_value", mt5_points_mt5_lots_mt5_value),
            ("mt5_net_profit_after_costs", mt5_net_total),
        ]
        previous_value = None
        for name, value in scenarios:
            scenario_rows.append(
                {
                    "mt5_trade_id": mt5_id,
                    "scenario": name,
                    "profit_$": value,
                    "delta_from_previous": "" if previous_value is None else value - previous_value,
                    "gap_to_mt5_net": mt5_net_total - value,
                }
            )
            previous_value = value

    stage_df = pd.DataFrame(stage_rows)
    trade_df = pd.DataFrame(trade_rows)
    scenario_df = pd.DataFrame(scenario_rows)

    numeric_cols = stage_df.select_dtypes(include=["number"]).columns.tolist()
    stage_df[numeric_cols] = stage_df[numeric_cols].round(6)
    numeric_cols = trade_df.select_dtypes(include=["number"]).columns.tolist()
    trade_df[numeric_cols] = trade_df[numeric_cols].round(6)
    numeric_cols = scenario_df.select_dtypes(include=["number"]).columns.tolist()
    scenario_df[numeric_cols] = scenario_df[numeric_cols].round(6)

    return stage_df, trade_df, scenario_df


def write_report(stage_df: pd.DataFrame, trade_df: pd.DataFrame, scenario_df: pd.DataFrame) -> None:
    key_cols = [
        "mt5_trade_id",
        "python_dynamic_total_$",
        "mt5_net_profit",
        "net_gap_mt5_minus_python_dynamic",
        "contract_value_effect",
        "lot_sizing_effect",
        "exit_price_effect",
        "cost_effect",
        "contract_value_factor_mt5_over_py",
        "py_stage_lots",
        "mt5_stage_lots",
        "stage3_exit_time_delta_min_mt5_minus_py",
    ]
    stage_key_cols = [
        "mt5_trade_id",
        "stage",
        "py_points",
        "mt5_price_points",
        "points_diff_mt5_minus_py",
        "py_stage_lot",
        "mt5_lot",
        "py_dynamic_$",
        "mt5_net_profit",
        "net_gap_mt5_minus_py_dynamic",
        "py_exit_reason",
        "mt5_local_exit_reason",
        "mt5_deal_reason",
    ]
    time_cols = [
        "mt5_trade_id",
        "mt5_signal_anchor_time",
        "mt5_first_open_time",
        "bridge_entry_time",
        "py_date",
        "mt5_open_minus_anchor_min",
        "bridge_entry_time_minus_mt5_open_min",
        "py_aligned_date_minus_mt5_open_min",
    ]

    lines = [
        "# P0 bridge Stage/PnL divergence audit",
        "",
        "## Scope",
        "",
        "- Targets: `mt5_0005`, `mt5_0019`.",
        "- This audit compares Python Stage replay / dynamic-risk valuation with MT5 close-retry trade ledger.",
        "- MT5 net profit is used only as comparison evidence; no Python PnL is overwritten by ledger profit.",
        "",
        "## Decision",
        "",
        "- Signal recovery remains valid, but merge remains blocked.",
        "- Primary reason: PnL is not on the same execution model.",
        f"- Python dynamic uses `VALUE_PER_SPEC_PT_PER_LOT={PY_VALUE_PER_SPEC_POINT_PER_LOT}` and dynamic stage lots.",
        "- The two MT5 rows infer about `100` value per 1.0 price point per 1.00 lot and both execute `0.01/0.01/0.01` lots.",
        "- The bridge rows also preserve a +90 aligned signal date, while MT5 actual opens are 90 minutes earlier than the bridge entry_time.",
        "",
        "## Trade-Level Attribution",
        "",
        trade_df[key_cols].to_markdown(index=False),
        "",
        "## Stage-Level Comparison",
        "",
        stage_df[stage_key_cols].to_markdown(index=False),
        "",
        "## Time/Lot Model Summary",
        "",
        trade_df[time_cols].to_markdown(index=False),
        "",
        "## Scenario Matrix",
        "",
        scenario_df.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- `contract_value_effect` shows what happens if Python's stage points and Python lots are revalued using MT5-inferred value per lot.",
        "- `lot_sizing_effect` then changes Python dynamic lots to MT5 actual lots while keeping Python exit points.",
        "- `exit_price_effect` then changes Python exit points to MT5 actual exit points while keeping MT5 lots.",
        "- `cost_effect` is the remaining swap/commission/net-vs-gross difference.",
        "- Therefore the next executable repair should not be another signal filter. It should be an execution-model gate: either align Python-MT5 valuation to MT5 tick/contract/lots for EA equivalence, or keep this subset as signal-only diagnostic under Python dynamic risk.",
        "",
        "## Output Files",
        "",
        "- `p0_bridge_stage_pnl_divergence.csv`",
        "- `p0_bridge_trade_pnl_gap_attribution.csv`",
        "- `p0_bridge_execution_scenario_matrix.csv`",
        "- `p0_bridge_stage_pnl_divergence_review.md`",
    ]
    write_text(OUT_DIR / "p0_bridge_stage_pnl_divergence_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    matches = read_csv(MAPPING_DIR / "python_mt5_mt5_unique_matches.csv")
    matches = matches.loc[matches["mt5_trade_id"].isin(TARGET_MT5_IDS)].copy()
    if set(matches["mt5_trade_id"]) != set(TARGET_MT5_IDS):
        raise RuntimeError("Missing target matches")

    dynamic = read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv")
    dynamic["date"] = pd.to_datetime(dynamic["date"], errors="coerce")

    bridge_stage = read_csv(P0_DIR / "bridge_stage_replay_rows.csv")
    bridge_entries = read_csv(P0_DIR / "bridge_layer3_rows.csv")[
        ["bridge_mt5_trade_id", "entry_time"]
    ].copy()
    bridge_stage = bridge_stage.merge(
        bridge_entries,
        on="bridge_mt5_trade_id",
        how="left",
        suffixes=("", "_signal"),
    )

    ledger = read_csv(MT5_LEDGER_DIR / "30m2H_strategy_trade_ledger.csv")
    ledger["_anchor_dt"] = ledger["signal_anchor_time"].map(to_dt)
    for col in [
        "stage",
        "fill_price",
        "exit_price",
        "lots",
        "profit",
        "swap",
        "commission",
        "net_profit",
    ]:
        ledger[col] = pd.to_numeric(ledger[col], errors="coerce")

    stage_df, trade_df, scenario_df = build_stage_rows(matches, dynamic, bridge_stage, ledger)

    export_csv(stage_df, OUT_DIR / "p0_bridge_stage_pnl_divergence.csv")
    export_csv(trade_df, OUT_DIR / "p0_bridge_trade_pnl_gap_attribution.csv")
    export_csv(scenario_df, OUT_DIR / "p0_bridge_execution_scenario_matrix.csv")
    write_report(stage_df, trade_df, scenario_df)

    print(trade_df[
        [
            "mt5_trade_id",
            "python_dynamic_total_$",
            "mt5_net_profit",
            "net_gap_mt5_minus_python_dynamic",
            "contract_value_effect",
            "lot_sizing_effect",
            "exit_price_effect",
            "cost_effect",
        ]
    ].to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
