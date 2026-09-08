# -*- coding: utf-8 -*-
"""Review the two remaining runtime Stage exit blockers with tester journal.

The integrated runtime alignment intentionally left cases unresolved when
bar-level evidence conflicted with MT5 deal reason or session behavior. This
script reads the latest full tester journal and classifies those rows using
actual journal evidence.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
RUNTIME_DIR = VALIDATION_DIR / "python_runtime_stage_exit_prototype_20260714"
INTEGRATED_PATH = RUNTIME_DIR / "runtime_stage_exit_integrated_alignment.csv"

TESTER_LOG = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester"
    r"\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\logs\20260714.log"
)

OUT_CSV = RUNTIME_DIR / "runtime_stage_exit_remaining_blockers.csv"
OUT_SUMMARY = RUNTIME_DIR / "runtime_stage_exit_remaining_blockers_summary.csv"
OUT_SNIPPETS = RUNTIME_DIR / "runtime_stage_exit_remaining_blockers_journal_snippets.txt"
OUT_MD = RUNTIME_DIR / "runtime_stage_exit_remaining_blockers.md"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def sim_time(line: str) -> str:
    marker = ")"
    parts = line.split(marker, 1)
    text = parts[1] if len(parts) == 2 else line
    tokens = text.split()
    for idx, token in enumerate(tokens[:-1]):
        if token.count(".") == 2 and tokens[idx + 1].count(":") == 2:
            return f"{token} {tokens[idx + 1]}"
    return ""


def read_tester_log(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-16", errors="ignore").splitlines()
    if len(lines) <= 1:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return lines


def wall_hour(line: str) -> int | None:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    wall = parts[2]
    if len(wall) < 2 or not wall[:2].isdigit():
        return None
    return int(wall[:2])


def latest_wall_hour_lines(lines: list[str]) -> list[str]:
    hours = [hour for line in lines if (hour := wall_hour(line)) is not None]
    if not hours:
        return lines
    latest = max(hours)
    return [line for line in lines if wall_hour(line) == latest]


def collect_case_lines(lines: list[str], ticket: str, position_id: str) -> list[str]:
    markers = [
        f"ticket={ticket}",
        f"position #{ticket}",
        f"close #{ticket}",
        f"#{ticket} ",
        f"#{ticket}\t",
        f"#{position_id} ",
        f"#{position_id}\t",
    ]
    out: list[str] = []
    for line in lines:
        if any(marker in line for marker in markers):
            out.append(line)
    return out


def first_time(lines: list[str], contains: str) -> str:
    for line in lines:
        if contains in line:
            return sim_time(line)
    return ""


def count_contains(lines: list[str], text: str) -> int:
    return sum(1 for line in lines if text in line)


def classify(row: pd.Series, lines: list[str]) -> dict[str, object]:
    ticket = as_text(row["ticket"])
    stage = as_text(row["stage"])

    stage_cross = count_contains(lines, f"[STAGE{stage} CROSS EXIT] ticket={ticket}")
    closed_ok = count_contains(lines, f"Closed ticket={ticket}")
    failed_close = count_contains(lines, f"close #{ticket}") and count_contains(lines, "[Market closed]")
    close_retry = count_contains(lines, f"[EXIT RETRY] stage {stage} ticket={ticket} close failed")
    stage_tp = count_contains(lines, f"[STAGE{stage} TP] ticket={ticket}")
    sl_triggered = count_contains(lines, f"stop loss triggered #{ticket}")

    if stage == "3" and stage_cross and closed_ok and not sl_triggered:
        return {
            "journal_class": "resolved_stage3_cross_expert_close",
            "remaining_priority1_blocker_after_journal": False,
            "needs_more_journal_or_tick": False,
            "journal_note": "Tester journal confirms EA Stage3 cross close succeeded; M30 broker-SL candidate was coarse open-bar evidence, not the actual close path.",
        }

    if stage == "1" and stage_tp and failed_close and close_retry and sl_triggered:
        return {
            "journal_class": "resolved_stage1_tp_market_closed_retry_then_sl",
            "remaining_priority1_blocker_after_journal": False,
            "needs_more_journal_or_tick": False,
            "journal_note": "Tester journal confirms Stage1 TP close attempts failed with Market closed; state was retained by close retry and the position later closed by broker SL.",
        }

    return {
        "journal_class": "unresolved_by_journal_scan",
        "remaining_priority1_blocker_after_journal": True,
        "needs_more_journal_or_tick": True,
        "journal_note": "Journal scan did not find a decisive close path.",
    }


def compact_snippet(case_id: str, lines: list[str]) -> list[str]:
    interesting = []
    keywords = [
        "[STAGE",
        "[EXIT",
        "Market closed",
        "Close failed",
        "Closed ticket",
        "stop loss triggered",
        "deal #",
        "position modified",
    ]
    for line in lines:
        if any(keyword in line for keyword in keywords):
            interesting.append(line)

    if len(interesting) <= 40:
        selected = interesting
    else:
        selected = interesting[:18] + ["..."] + interesting[-20:]
    return [f"## {case_id}", *selected, ""]


def main() -> None:
    integrated = read_csv(INTEGRATED_PATH)
    blockers = integrated[integrated["remaining_priority1_blocker"].map(bool_value)].copy()
    lines = read_tester_log(TESTER_LOG)

    rows: list[dict[str, object]] = []
    snippet_lines: list[str] = []

    for _, row in blockers.iterrows():
        ticket = as_text(row["ticket"])
        position_id = as_text(row["position_id"])
        case_lines = latest_wall_hour_lines(collect_case_lines(lines, ticket, position_id))
        result = classify(row, case_lines)

        rows.append(
            {
                "case_id": row["case_id"],
                "py_trade_id": row["py_trade_id"],
                "mt5_trade_id": row["mt5_trade_id"],
                "stage": row["stage"],
                "ticket": ticket,
                "position_id": position_id,
                "signal_anchor_time": row["signal_anchor_time"],
                "open_time": row["open_time"],
                "exit_time": row["exit_time"],
                "exit_relation": row["exit_relation"],
                "sign_pair": row["sign_pair"],
                "py_exit": row["py_exit"],
                "mt5_local_exit_reason": row["mt5_local_exit_reason"],
                "mt5_deal_reason": row["mt5_deal_reason"],
                "runtime_residual_class_before": row["runtime_residual_class"],
                "journal_lines_found": len(case_lines),
                "first_stage_tp_time": first_time(case_lines, f"[STAGE{row['stage']} TP] ticket={ticket}"),
                "first_stage_cross_exit_time": first_time(case_lines, f"[STAGE{row['stage']} CROSS EXIT] ticket={ticket}"),
                "first_market_closed_time": first_time(case_lines, "Market closed"),
                "first_exit_retry_time": first_time(case_lines, f"[EXIT RETRY] stage {row['stage']} ticket={ticket}"),
                "first_closed_ticket_time": first_time(case_lines, f"Closed ticket={ticket}"),
                "first_stop_loss_time": first_time(case_lines, f"stop loss triggered #{ticket}"),
                "market_closed_count": count_contains(case_lines, "Market closed"),
                "exit_retry_count": count_contains(case_lines, "[EXIT RETRY]"),
                "stop_loss_trigger_count": count_contains(case_lines, f"stop loss triggered #{ticket}"),
                **result,
            }
        )
        snippet_lines.extend(compact_snippet(as_text(row["case_id"]), case_lines))

    out = pd.DataFrame(rows)
    summary = (
        out.groupby(["journal_class", "remaining_priority1_blocker_after_journal", "needs_more_journal_or_tick"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values("journal_class")
    )

    export_csv(out, OUT_CSV)
    export_csv(summary, OUT_SUMMARY)
    write_text(OUT_SNIPPETS, "\n".join(snippet_lines))

    resolved_count = int((~out["remaining_priority1_blocker_after_journal"].map(bool)).sum()) if not out.empty else 0
    remaining_count = int(out["remaining_priority1_blocker_after_journal"].map(bool).sum()) if not out.empty else 0
    remaining_cases = ", ".join(out.loc[out["remaining_priority1_blocker_after_journal"].map(bool), "case_id"].astype(str).tolist())
    if not remaining_cases:
        remaining_cases = "none"

    md = [
        "# Runtime Stage Exit Remaining Blockers Journal Review",
        "",
        "## Scope",
        "",
        f"- Input: `{INTEGRATED_PATH.relative_to(VALIDATION_DIR)}`",
        f"- Tester journal: `{TESTER_LOG}`",
        "- Journal scan keeps the latest wall-clock hour group for each ticket, which removes earlier same-day smoke snippets from the agent log.",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Case Evidence",
        "",
        out[
            [
                "case_id",
                "stage",
                "ticket",
                "journal_class",
                "first_stage_tp_time",
                "first_stage_cross_exit_time",
                "first_market_closed_time",
                "first_exit_retry_time",
                "first_closed_ticket_time",
                "first_stop_loss_time",
                "market_closed_count",
                "exit_retry_count",
                "remaining_priority1_blocker_after_journal",
            ]
        ].to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        f"- Journal review resolved `{resolved_count}` Priority 1 blocker rows.",
        f"- Remaining Priority 1 blocker rows after journal review: `{remaining_count}`.",
        f"- Remaining case ids: `{remaining_cases}`.",
        "- Resolved journal evidence remains useful for Python runtime-style close-retry and expert-close modeling.",
        "",
        "## Output Files",
        "",
        "- `runtime_stage_exit_remaining_blockers.csv`",
        "- `runtime_stage_exit_remaining_blockers_summary.csv`",
        "- `runtime_stage_exit_remaining_blockers_journal_snippets.txt`",
    ]
    write_text(OUT_MD, "\n".join(md))

    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_SUMMARY}")
    print(f"Wrote {OUT_SNIPPETS}")
    print(f"Wrote {OUT_MD}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
