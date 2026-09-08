# -*- coding: utf-8 -*-
"""Compare the EA Strategy-Tester ledger vs the Python expected ledger (2H ABC).

Usage:
  python "黄金/2H_M30_6H策略/scripts/validate/compare_2h_abc_tester_vs_python.py" [ea_ledger_csv]

Default EA ledger path = DAD3B8CC tester Agent-127.0.0.1-3000 Files.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import sys
from pathlib import Path

import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

EXPECTED = (
    Path(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026")
    / "python_expected_2h_abc_2025_2026.csv"
)
DEFAULT_EA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65"
    r"\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
)
OUT_DIR = EXPECTED.parent


def norm_time(value) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(parsed) else parsed.strftime("%Y.%m.%d %H:%M:%S")


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")


def main() -> None:
    ea_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EA
    exp = read_csv_any(EXPECTED)
    if not ea_path.exists():
        print(f"EA ledger not found yet: {ea_path}")
        print("Run the Strategy Tester smoke first (see TESTER_SMOKE_RUNBOOK.md).")
        print(f"Expected stage rows ready: {len(exp)} (trades=477).")
        return
    ea = read_csv_any(ea_path)
    print("expected rows:", len(exp), "| ea rows:", len(ea))

    if "trade_key" not in ea.columns:
        ea["trade_key"] = (
            ea["entry_time"].map(norm_time)
            + "|" + ea["dir"].astype(str).str.upper()
            + "|S" + ea["stage"].astype(str)
        )
    exp["_key"] = exp["trade_key"].astype(str).str.strip()
    ea["_key"] = ea["trade_key"].astype(str).str.strip()

    merged = exp.merge(
        ea.rename(columns={
            "entry": "ea_entry", "stop": "ea_stop", "exit_price": "ea_exit",
            "pnl_points": "ea_pnl", "reason": "ea_reason",
        }),
        on="_key", how="outer", indicator=True,
    )
    matched = merged[merged["_merge"] == "both"]
    missing = merged[merged["_merge"] == "left_only"]
    extra = merged[merged["_merge"] == "right_only"]
    for col in ["entry", "stop", "exit_price", "pnl_points"]:
        merged[f"diff_{col}"] = pd.to_numeric(merged.get(f"ea_{col}"), errors="coerce") - pd.to_numeric(
            merged.get(col), errors="coerce"
        )

    summary = {
        "expected_stage_rows": int(len(exp)),
        "ea_stage_rows": int(len(ea)),
        "matched": int(len(matched)),
        "missing_in_ea": int(len(missing)),
        "extra_in_ea": int(len(extra)),
        "max_abs_entry_diff": float(matched["diff_entry"].abs().max()) if len(matched) else None,
        "max_abs_exit_diff": float(matched["diff_exit_price"].abs().max()) if len(matched) else None,
        "max_abs_pnl_diff": float(matched["diff_pnl_points"].abs().max()) if len(matched) else None,
    }
    print(pd.DataFrame([summary]).to_string(index=False))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_DIR / "tester_vs_python_detail.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(OUT_DIR / "tester_vs_python_summary.csv", index=False, encoding="utf-8-sig")
    if len(missing):
        print("missing keys sample:", missing["_key"].head(5).tolist())
    if len(extra):
        print("extra keys sample:", extra["_key"].head(5).tolist())


if __name__ == "__main__":
    main()
