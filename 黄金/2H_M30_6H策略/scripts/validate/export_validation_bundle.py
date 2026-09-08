# -*- coding: utf-8 -*-
"""Export local validation outputs for 2H_M30_6H."""
from __future__ import annotations


from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_workspace_common import (  # noqa: E402
    COMBO,
    PERIOD_LABEL,
    SIGNALS_DIR,
    VALIDATION_DIR,
    build_gate_scan,
    build_yearly_performance,
    ensure_dirs,
    export_csv,
    pick_primary_variant,
)


def main() -> None:
    ensure_dirs()
    summary = pd.read_csv(SIGNALS_DIR / "strategy_variant_summary.csv", encoding="utf-8-sig")
    candidates = pd.read_csv(SIGNALS_DIR / "strategy_candidate_trades.csv", encoding="utf-8-sig")
    primary = pick_primary_variant(summary)
    primary_variant = str(primary["variant"])
    primary_trades = candidates.loc[candidates["variant"].astype(str) == primary_variant].copy()

    strategy_summary = pd.DataFrame(
        [
            {
                "combo": COMBO,
                "frames": PERIOD_LABEL,
                "primary_variant": primary_variant,
                "primary_desc": primary["desc"],
                "trades": int(primary["n"]),
                "wr": float(primary["wr"]),
                "pf": float(primary["pf"]),
                "ev": float(primary["ev"]),
                "pnl": float(primary["pnl"]),
                "test_n": int(primary["test_n"]),
                "test_pf": float(primary["test_pf"]),
                "test_ev": float(primary["test_ev"]),
            }
        ]
    )
    export_csv(strategy_summary, VALIDATION_DIR / "strategy_summary.csv")
    export_csv(build_gate_scan(summary, primary_variant), VALIDATION_DIR / "combo_gate_range_scan.csv")
    export_csv(build_yearly_performance(primary_trades), VALIDATION_DIR / "yearly_performance.csv")

    readme = """# 2H_M30_6H 验证数据

## 本地验证输出

- `strategy_summary.csv`
- `combo_gate_range_scan.csv`
- `yearly_performance.csv`

## 说明

- 本策略是新增组合，参考工程现有矩阵里没有同名历史认证包。
- 当前验证先覆盖候选门表现、主推荐门和按年表现。
- Stage 参数、止损范围、仓位档位和 EA 对齐需要在后续认证脚本中继续补齐。
"""
    (VALIDATION_DIR / "README.md").write_bytes(readme.encode("utf-8-sig"))
    print(f"Exported validation bundle for {COMBO}.")


if __name__ == "__main__":
    main()
