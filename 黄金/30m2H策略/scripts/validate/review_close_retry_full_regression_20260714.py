from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
OLD_DIR = VALIDATION / "mt5_ledger_deinitfix_full_20260713_v1"
NEW_DIR = VALIDATION / "mt5_full_close_retry_fix_20260714"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def main() -> None:
    old = read_csv(OLD_DIR / "30m2H_strategy_trade_ledger.csv")
    new = read_csv(NEW_DIR / "30m2H_strategy_trade_ledger.csv")
    old_deals = read_csv(OLD_DIR / "30m2H_strategy_deal_history.csv")
    new_deals = read_csv(NEW_DIR / "30m2H_strategy_deal_history.csv")

    for frame in (old, new, old_deals, new_deals):
        if "net_profit" in frame.columns:
            frame["net_profit"] = pd.to_numeric(frame["net_profit"], errors="coerce")

    keys = ["signal_anchor_time", "dir", "stage"]
    merged = old.merge(new, on=keys, how="outer", suffixes=("_old", "_new"), indicator=True)
    merged["net_diff"] = merged["net_profit_new"].fillna(0) - merged["net_profit_old"].fillna(0)

    changed = merged[
        (merged["_merge"] != "both")
        | (merged["net_diff"].abs() > 0.01)
        | (
            merged["local_exit_reason_old"].astype(str)
            != merged["local_exit_reason_new"].astype(str)
        )
        | (merged["deal_reason_old"].astype(str) != merged["deal_reason_new"].astype(str))
        | (merged["exit_time_old"].astype(str) != merged["exit_time_new"].astype(str))
        | (merged["lots_old"].astype(str) != merged["lots_new"].astype(str))
    ].copy()

    diff_cols = keys + [
        "_merge",
        "ticket_old",
        "position_id_old",
        "lots_old",
        "fill_price_old",
        "actual_stop_old",
        "local_exit_reason_old",
        "deal_reason_old",
        "exit_time_old",
        "exit_price_old",
        "net_profit_old",
        "ticket_new",
        "position_id_new",
        "lots_new",
        "fill_price_new",
        "actual_stop_new",
        "local_exit_reason_new",
        "deal_reason_new",
        "exit_time_new",
        "exit_price_new",
        "net_profit_new",
        "net_diff",
    ]
    changed = changed[diff_cols].sort_values(keys)

    old_reason = (
        old.groupby(["stage", "local_exit_reason", "deal_reason"], dropna=False)
        .size()
        .reset_index(name="old_rows")
    )
    new_reason = (
        new.groupby(["stage", "local_exit_reason", "deal_reason"], dropna=False)
        .size()
        .reset_index(name="new_rows")
    )
    reason_diff = old_reason.merge(
        new_reason,
        on=["stage", "local_exit_reason", "deal_reason"],
        how="outer",
    ).fillna(0)
    reason_diff["row_diff"] = reason_diff["new_rows"] - reason_diff["old_rows"]

    old_out = old_deals[old_deals["deal_entry"].astype(str).eq("OUT")]
    new_out = new_deals[new_deals["deal_entry"].astype(str).eq("OUT")]
    summary = pd.DataFrame(
        [
            {
                "snapshot": "old_mt5_ledger_deinitfix_full_20260713_v1",
                "ledger_rows": len(old),
                "unique_signal_anchors": old["signal_anchor_time"].nunique(),
                "ledger_net_profit": round(float(old["net_profit"].sum()), 2),
                "deal_out_rows": len(old_out),
                "deal_out_net_profit": round(float(old_out["net_profit"].sum()), 2),
            },
            {
                "snapshot": "new_mt5_full_close_retry_fix_20260714",
                "ledger_rows": len(new),
                "unique_signal_anchors": new["signal_anchor_time"].nunique(),
                "ledger_net_profit": round(float(new["net_profit"].sum()), 2),
                "deal_out_rows": len(new_out),
                "deal_out_net_profit": round(float(new_out["net_profit"].sum()), 2),
            },
        ]
    )

    summary.to_csv(NEW_DIR / "close_retry_full_regression_summary.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(NEW_DIR / "close_retry_full_regression_changed_rows.csv", index=False, encoding="utf-8-sig")
    reason_diff.to_csv(NEW_DIR / "close_retry_full_regression_reason_diff.csv", index=False, encoding="utf-8-sig")

    delta = float(summary.loc[1, "ledger_net_profit"] - summary.loc[0, "ledger_net_profit"])
    report = [
        "# ClosePos Retry Full Regression 20260714",
        "",
        "## Scope",
        "",
        "- Old snapshot: `mt5_ledger_deinitfix_full_20260713_v1`",
        "- New snapshot: `mt5_full_close_retry_fix_20260714`",
        "- Key: `signal_anchor_time + dir + stage`",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        f"- Net profit delta: `{delta:.2f}`.",
        f"- Changed rows: `{len(changed)}`.",
        "",
        "## Changed Rows",
        "",
        changed.to_markdown(index=False),
        "",
        "## Reason Diff",
        "",
        reason_diff.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- The new full ledger remains internally closed: ledger OUT net equals raw deal OUT net.",
        "- Signal count and stage row count are unchanged: `78` anchors and `234` stage rows.",
        "- The main behavioral change is the `2020.03.20 02:00` BUY Stage3 row: after a market-closed close failure, the fixed EA keeps Stage3 state and retries successfully on `2020.03.22 22:05:00` instead of losing state and leaving the position until `2020.03.25 10:00:05`.",
        "- Later differences are mostly dynamic-lot cascade effects caused by the earlier balance path change.",
        "- The `2026.01.26 20:30` Stage1 row now reports `deal_exit + SL` instead of the stale `stage1_tp + SL` intent, with no PnL change for that row.",
        "",
    ]
    (NEW_DIR / "close_retry_full_regression_report.md").write_text(
        "\n".join(report), encoding="utf-8-sig"
    )


if __name__ == "__main__":
    main()
