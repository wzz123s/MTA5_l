# -*- coding: utf-8 -*-
"""Compare USOIL2H_CrossConfirm_EA Tester ledger vs Python expected (40 trades).

Usage:
  python "原油/原油2H策略/scripts/validate/compare_usoil2h_tester_vs_python.py" [ea_ledger_csv]

Default EA ledger path = DAD3B8CC tester Agent Files.
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

# 权威参考 = 因果口径(2021-2026, long-only 53笔); 2020-2026 旧文件(40笔)已弃用(曾致误判 FAIL)
EXPECTED = (
    Path(r"F:\use_code\MTA5_l\原油\原油2H策略\auto_trade\python_expected_2020_2026")
    / "python_expected_usoil2h_crossconfirm_causal_2021_2026.csv"
)
DEFAULT_EA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65"
    r"\Agent-127.0.0.1-3000\MQL5\Files\USOIL2H_crossconfirm_trade_ledger.csv"
)
OUT_DIR = EXPECTED.parent
PNL_TOL = 0.01


def norm_time(value) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(parsed) else parsed.strftime("%Y-%m-%d %H:%M:%S")


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
        print("请在 Strategy Tester 跑完 USOIL2H_CrossConfirm_EA 后再运行本脚本。")
        return
    ea = read_csv_any(ea_path)
    if ea.empty:
        print("EA ledger empty (0 rows) - tester may not have written trades")
        return

    exp = exp.rename(columns={"pnl_points": "exp_pnl"}).copy()
    exp["signal_time"] = exp["signal_time"].map(norm_time)
    exp["dir"] = exp["dir"].astype(str).str.upper()
    exp["key"] = exp["signal_time"] + "|" + exp["dir"]

    ea = ea.copy()
    ea["signal_time"] = ea["signal_time"].map(norm_time)
    ea["dir"] = ea["dir"].map(lambda d: "L" if str(d).upper() in ("L", "BUY", "1", "LONG") else
                              ("S" if str(d).upper() in ("S", "SELL", "-1", "SHORT") else str(d).upper()))
    ea["key"] = ea["signal_time"] + "|" + ea["dir"]

    matched = exp.merge(ea, on="key", how="inner", suffixes=("_exp", "_ea"))
    missing = exp[~exp["key"].isin(ea["key"])]
    extra = ea[~ea["key"].isin(exp["key"])]

    diffs = []
    if not matched.empty:
        matched["pnl_diff"] = (matched["exp_pnl"] - matched["pnl_points"].astype(float)).abs()
        diffs = matched.loc[matched["pnl_diff"] > PNL_TOL, ["key", "exp_pnl", "pnl_points", "pnl_diff"]]
        sign_agree = (matched["exp_pnl"] > 0) == (matched["pnl_points"].astype(float) > 0)
    else:
        sign_agree = pd.Series(dtype=bool)

    print("=" * 78)
    print(f"expected trades : {len(exp)}")
    print(f"EA trades       : {len(ea)}")
    print(f"matched         : {len(matched)}")
    print(f"missing_in_ea   : {len(missing)}")
    print(f"extra_in_ea     : {len(extra)}")
    if not matched.empty:
        print(f"pnl sign agree  : {int(sign_agree.sum())}/{len(matched)}")
        print(f"pnl diff > {PNL_TOL} : {len(diffs)}")
    print("=" * 78)

    missing.to_csv(OUT_DIR / "tester_vs_python_missing.csv", index=False, encoding="utf-8-sig")
    extra.to_csv(OUT_DIR / "tester_vs_python_extra.csv", index=False, encoding="utf-8-sig")
    if not matched.empty:
        matched.to_csv(OUT_DIR / "tester_vs_python_detail.csv", index=False, encoding="utf-8-sig")

    ok = (len(missing) == 0 and len(extra) == 0 and len(diffs) == 0 and len(matched) == len(exp))
    print("RESULT:", "PASS - EA 与 Python 完全一致" if ok else "FAIL - 需排查 missing/extra/diff")


if __name__ == "__main__":
    main()
