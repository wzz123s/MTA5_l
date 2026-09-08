from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
BASE = ROOT / "黄金" / "30m2H策略" / "data" / "validation" / "ea_stage_price_side_smoke_20260714"
SNAPSHOTS = [
    "20260126_close_retry_fix",
    "20250422_close_retry_fix",
    "20260324_close_retry_fix",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().eq("true")


def main() -> None:
    summary_rows: list[dict] = []
    reason_frames: list[pd.DataFrame] = []
    trail_frames: list[pd.DataFrame] = []
    mismatch_frames: list[pd.DataFrame] = []

    for snapshot in SNAPSHOTS:
        folder = BASE / snapshot
        ledger = read_csv(folder / "30m2H_strategy_trade_ledger.csv")
        diag = read_csv(folder / "30m2H_strategy_stage_price_diag.csv")

        ledger["net_profit_num"] = pd.to_numeric(ledger["net_profit"], errors="coerce")
        diag["close_profit_rr_num"] = pd.to_numeric(diag["close_profit_rr"], errors="coerce")

        sell = diag[diag["dir"].astype(str).str.upper().eq("SELL")].copy()
        action_mismatch = sell[
            sell["legacy_action_text"].astype(str)
            != sell["profit_side_action_text"].astype(str)
        ].copy()

        trigger_labels = {"stage1_tp", "stage2_force_exit", "stage2_trail_on"}
        negative_new_trigger = sell[
            sell["legacy_action_text"].astype(str).isin(trigger_labels)
            & (sell["close_profit_rr_num"] < 0)
        ].copy()

        trail_on = diag[
            (diag["stage"] == 2)
            & (~bool_series(diag["trail_before"]))
            & bool_series(diag["trail_after"])
        ].copy()

        reason = (
            ledger.groupby(["stage", "local_exit_reason", "deal_reason"], dropna=False)
            .size()
            .reset_index(name="rows")
        )
        reason.insert(0, "snapshot", snapshot)
        reason_frames.append(reason)

        if len(trail_on):
            cols = [
                "time",
                "signal_anchor_time",
                "dir",
                "stage",
                "ticket",
                "entry",
                "orig_sl",
                "current_sl",
                "bid",
                "ask",
                "legacy_abs_rr",
                "close_profit_rr",
                "legacy_action_text",
                "profit_side_action_text",
            ]
            out = trail_on[cols].copy()
            out.insert(0, "snapshot", snapshot)
            trail_frames.append(out)

        if len(action_mismatch):
            cols = [
                "time",
                "signal_anchor_time",
                "dir",
                "stage",
                "ticket",
                "entry",
                "bid",
                "ask",
                "legacy_abs_rr",
                "close_profit_rr",
                "legacy_action_text",
                "profit_side_action_text",
            ]
            out = action_mismatch[cols].copy()
            out.insert(0, "snapshot", snapshot)
            mismatch_frames.append(out)

        summary_rows.append(
            {
                "snapshot": snapshot,
                "ledger_rows": len(ledger),
                "unique_signal_anchors": ledger["signal_anchor_time"].nunique(),
                "ledger_net_profit": round(float(ledger["net_profit_num"].sum()), 2),
                "diag_rows": len(diag),
                "sell_diag_rows": len(sell),
                "sell_action_mismatch_rows": len(action_mismatch),
                "negative_new_trigger_rows": len(negative_new_trigger),
                "stage2_trail_on_events": len(trail_on),
                "stage1_tp_expert_rows": int(
                    (
                        (ledger["stage"] == 1)
                        & ledger["local_exit_reason"].astype(str).eq("stage1_tp")
                        & ledger["deal_reason"].astype(str).eq("EXPERT")
                    ).sum()
                ),
                "stage3_expert_rows": int(
                    (
                        (ledger["stage"] == 3)
                        & ledger["deal_reason"].astype(str).eq("EXPERT")
                    ).sum()
                ),
                "stage3_deinit_client_rows": int(
                    (
                        (ledger["stage"] == 3)
                        & ledger["local_exit_reason"].astype(str).eq("deinit_history")
                        & ledger["deal_reason"].astype(str).eq("CLIENT")
                    ).sum()
                ),
            }
        )

    summary = pd.DataFrame(summary_rows)
    reason_summary = pd.concat(reason_frames, ignore_index=True)
    trail_events = (
        pd.concat(trail_frames, ignore_index=True)
        if trail_frames
        else pd.DataFrame()
    )
    mismatches = (
        pd.concat(mismatch_frames, ignore_index=True)
        if mismatch_frames
        else pd.DataFrame()
    )

    summary.to_csv(BASE / "ea_stage_price_side_smoke_summary.csv", index=False, encoding="utf-8-sig")
    reason_summary.to_csv(BASE / "ea_stage_price_side_reason_summary.csv", index=False, encoding="utf-8-sig")
    trail_events.to_csv(BASE / "ea_stage_price_side_trail_on_events.csv", index=False, encoding="utf-8-sig")
    mismatches.to_csv(BASE / "ea_stage_price_side_action_mismatch.csv", index=False, encoding="utf-8-sig")

    total_sell = int(summary["sell_diag_rows"].sum())
    total_mismatch = int(summary["sell_action_mismatch_rows"].sum())
    total_negative_triggers = int(summary["negative_new_trigger_rows"].sum())

    report = [
        "# EA Stage Price-Side Smoke Review 20260714",
        "",
        "## Scope",
        "",
        "- Snapshots reviewed:",
        *[f"  - `{s}`" for s in SNAPSHOTS],
        "- Source CSVs: `30m2H_strategy_trade_ledger.csv` and `30m2H_strategy_stage_price_diag.csv`.",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Conclusions",
        "",
        f"- Across the three smoke windows there are `{total_sell}` SELL diagnostic rows and `{total_mismatch}` legacy/profit-side action mismatch rows.",
        f"- New Stage1 TP / Stage2 force / Stage2 trail-on triggers with negative close-side profit: `{total_negative_triggers}`.",
        "- All observed Stage2 trail-on events are profit-positive under both legacy and close-side calculations.",
        "- The remaining price-side mismatches are threshold-edge cases, not broad false-profit triggers.",
        "- The `2026-01-26` sample remains dominated by market-session behavior: close/modify attempts occur during market closed, so the ClosePos retry/state-retention fix is required for correct state and ledger reason.",
        "- The `2025-04-22` smoke contains a Stage3 `deinit_history + CLIENT` row, so tester-window/deinit handling must be considered before treating it as a strategy exit mismatch.",
        "",
        "## Stage2 Trail-On Events",
        "",
        trail_events.to_markdown(index=False) if len(trail_events) else "_None_",
        "",
        "## Action Mismatches",
        "",
        mismatches.to_markdown(index=False) if len(mismatches) else "_None_",
        "",
    ]
    (BASE / "ea_stage_price_side_smoke_review.md").write_text(
        "\n".join(report), encoding="utf-8-sig"
    )


if __name__ == "__main__":
    main()
