# -*- coding: utf-8 -*-
"""Rebuild core markdown docs for H1_M30_H4 from local validation data."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h1_m30_h4_common import (
    load_capital_metrics,
    load_combined_summary,
    load_final_summary,
    load_gate_scan,
    load_stop_scan,
    load_top3_position,
    load_top3_stage,
    write_text,
)


TODAY = "2026-07-02"


def fmt_money(value: float) -> str:
    return f"${value:.2f}"


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def build_strategy_doc() -> str:
    final_row = load_final_summary()
    combo_row = load_combined_summary()
    cap_row = load_capital_metrics()
    gate_scan = load_gate_scan()
    win_rate = float(gate_scan.iloc[0]["wr"]) if not gate_scan.empty else 0.0

    year_rows = []
    for year in range(2020, 2027):
        year_rows.append(
            [
                year,
                int(cap_row[f"y{year}_trades"]),
                fmt_money(float(cap_row[f"y{year}_profit"])),
                int(cap_row[f"y{year}_stops"]),
            ]
        )

    result_rows = [
        ["总交易次数", int(cap_row["total_trades"])],
        ["胜率", f"{win_rate:.2f}%"],
        ["最终 PF", f"{float(final_row['final_pf']):.4f}"],
        ["最终 EV", f"+{float(final_row['final_ev']):.4f}pt"],
        ["总盈利", fmt_money(float(cap_row["total_profit"]))],
        ["最终资金额", fmt_money(float(cap_row["final_capital"]))],
        ["止损次数", int(cap_row["stop_count"])],
        ["止损次数占比", f"{float(cap_row['stop_ratio']) * 100:.2f}%"],
    ]

    return f"""# H1_M30_H4 策略说明

> 生成时间：{TODAY}
> 策略定位：多周期矩阵中的 `H1_M30_H4`
> 对齐对象：`30m2H策略` 文件夹的文档组织方式

## 1. 当前方案

- 组合周期：`30M / 1H / 4H`
- 当前组合门：`{final_row["picked_variant"]}`
- 组合门说明：`{final_row["picked_desc"]}`
- 当前 Stage 参数：`{combo_row["stage_params"]}`
- 当前仓位单位：`{combo_row["units"]}`
- 当前手数：`{combo_row["lots"]}`
- 聚焦周期：`{combo_row["focus_tf"]}`
- 当前主推荐止损范围：`{combo_row["stop_main"]}`
- 当前次优止损范围：`{combo_row["stop_second"]}`
- 当前可接受止损区间：`{combo_row["stop_ok"]}`

## 2. 当前结果

{md_table(["项目", "当前结果"], result_rows)}

按年份拆分：

{md_table(["年份", "交易次数", "年度盈利", "年度止损次数"], year_rows)}

## 3. 当前认证结论

- 当前主门仍保留 `baseline`，没有被更强的单门约束稳定替代。
- `Stage 1 / Stage 2 / Stage 3` 组合里，`{combo_row["stage_params"]}` 是当前综合采用值。
- 仓位分配上，收益峰值方案为 `{combo_row["units"]}`。
- 止损不再沿用主线 `30m2H` 的统一扫描口径，而是按 `30M` 聚焦周期重算 `sd` 后单独扫描。
"""


def build_panel_doc() -> str:
    combo_row = load_combined_summary()
    gate = load_gate_scan().head(6)
    stage = load_top3_stage()
    pos = load_top3_position()
    stop = load_stop_scan().sort_values(["score", "test_ev"], ascending=[False, False]).head(5)

    gate_rows = [
        [
            row["gate_param"],
            int(row["trades"]),
            f"{float(row['wr']):.2f}%",
            f"{float(row['pf']):.4f}",
            f"+{float(row['ev']):.4f}pt",
            f"{float(row['test_pf']):.4f}",
        ]
        for _, row in gate.iterrows()
    ]
    stage_rows = [
        [
            f"{row['stage1_r']:.1f} / {row['stage2_trail_r']:.1f} / {row['stage2_force_r']:.1f}",
            int(row["n"]),
            f"{float(row['wr']):.2f}%",
            f"{float(row['pf']):.4f}",
            f"+{float(row['ev']):.4f}pt",
            f"{float(row['test_pf']):.4f}",
        ]
        for _, row in stage.iterrows()
    ]
    pos_rows = [
        [
            row["units"],
            row["lots"],
            f"{float(row['pf']):.4f}",
            f"+{float(row['ev']):.4f}pt",
            fmt_money(float(row["pnl_$"])),
        ]
        for _, row in pos.iterrows()
    ]
    stop_rows = [
        [
            row["stop_range"],
            int(row["trades"]),
            f"{float(row['wr']):.2f}%",
            f"{float(row['pf']):.4f}",
            f"+{float(row['ev']):.4f}pt",
            fmt_money(float(row["profit"])),
        ]
        for _, row in stop.iterrows()
    ]

    current_rows = [
        ["策略组合", "H1_M30_H4"],
        ["当前组合门", combo_row["current_variant"]],
        ["Stage 参数", combo_row["stage_params"]],
        ["仓位单位", combo_row["units"]],
        ["手数", combo_row["lots"]],
        ["聚焦周期", combo_row["focus_tf"]],
        ["主推荐止损范围", combo_row["stop_main"]],
        ["次优止损范围", combo_row["stop_second"]],
        ["可接受止损区间", combo_row["stop_ok"]],
    ]

    return f"""# H1_M30_H4 参数范围测试面板

> 生成时间：{TODAY}

## 当前基准口径

{md_table(["项目", "当前值"], current_rows)}

## 组合门范围细扫

{md_table(["门参数", "交易数", "胜率", "PF", "EV", "验证PF"], gate_rows)}

## Stage 参数扫描

{md_table(["参数组合", "交易数", "胜率", "PF", "EV", "验证PF"], stage_rows)}

## 仓位档位

{md_table(["仓位单位", "手数", "PF", "EV", "总盈利"], pos_rows)}

## 止损范围

{md_table(["止损范围", "交易数", "胜率", "PF", "EV", "总盈利"], stop_rows)}
"""


def build_stage_doc() -> str:
    stage = load_top3_stage()
    rows = [
        [
            f"{row['stage1_r']:.1f} / {row['stage2_trail_r']:.1f} / {row['stage2_force_r']:.1f}",
            int(row["n"]),
            f"{float(row['wr']):.2f}%",
            f"{float(row['pf']):.4f}",
            f"+{float(row['ev']):.4f}pt",
            f"{float(row['test_pf']):.4f}",
        ]
        for _, row in stage.iterrows()
    ]
    return f"""# H1_M30_H4 Stage1 / Stage2 测试结果

> 生成时间：{TODAY}

## 当前 Top 3

{md_table(["Stage 参数", "交易数", "胜率", "PF", "EV", "验证PF"], rows)}

## 当前采用值

- 当前采用：`1.5 / 1.5 / 4.0`
"""


def build_stop_doc() -> str:
    combo_row = load_combined_summary()
    stop = load_stop_scan().sort_values(["score", "test_ev"], ascending=[False, False]).head(5)
    rows = [
        [
            row["stop_range"],
            int(row["trades"]),
            f"{float(row['wr']):.2f}%",
            f"{float(row['pf']):.4f}",
            f"+{float(row['ev']):.4f}pt",
            fmt_money(float(row["profit"])),
            f"{float(row['test_pf']):.4f}",
        ]
        for _, row in stop.iterrows()
    ]
    return f"""# H1_M30_H4 StopSpec 严格认证结果

> 生成时间：{TODAY}

## 当前扫描网格

- 下限集：`{combo_row["stop_grid_lo"]}`
- 上限集：`{combo_row["stop_grid_hi"]}`

## Top 结果

{md_table(["止损范围", "交易数", "胜率", "PF", "EV", "总盈利", "验证PF"], rows)}

## 当前结论

- 主推荐止损范围：`{combo_row["stop_main"]}`
- 次优止损范围：`{combo_row["stop_second"]}`
- 可接受止损区间：`{combo_row["stop_ok"]}`
"""


def build_position_doc() -> str:
    pos = load_top3_position()
    rows = [
        [
            row["units"],
            row["lots"],
            f"{float(row['pf']):.4f}",
            f"+{float(row['ev']):.4f}pt",
            fmt_money(float(row["pnl_$"])),
            f"{float(row['test_pf']):.4f}",
        ]
        for _, row in pos.iterrows()
    ]
    return f"""# H1_M30_H4 仓位档位严格认证结果

> 生成时间：{TODAY}

## 当前 Top 3

{md_table(["仓位单位", "手数", "PF", "EV", "总盈利", "验证PF"], rows)}

## 当前采用值

- 仓位单位：`0.5 / 0.5 / 2.0`
- 手数：`0.01 / 0.01 / 0.04`
"""


def build_index_doc() -> str:
    names = [
        "策略说明.md",
        "参数范围测试面板.md",
        "Layer1严格认证结果.md",
        "Layer2验证过程.md",
        "Layer3严格认证结果.md",
        "Layer3动态阈值测试结果.md",
        "Stage1_Stage2测试结果.md",
        "StopSpec严格认证结果.md",
        "仓位档位严格认证结果.md",
        "仓位档位详细分析.md",
        "仓位档位差异交易分析.md",
        "仓位档位关键交易图形复盘.md",
        "M15_H2提前触发测试计划.md",
        "M15_H2提前触发测试结果.md",
        "M15第二轮激进测试结果.md",
        "多周期后续测试计划_20260702.md",
        "技能安装清单.md",
        "项目文件归类清单.md",
        "data/raw/README.md",
        "data/processed/README.md",
        "data/validation/README.md",
    ]
    file_lines = "\n".join(f"- `{name}`" for name in names)
    return f"""# H1_M30_H4 全项目清单

> 生成时间：{TODAY}

## 文档清单

{file_lines}

## 脚本目录

- `scripts/data_source/sync_raw_data.py`
- `scripts/prepare/build_processed_data.py`
- `scripts/signals/export_signal_candidates.py`
- `scripts/validate/export_validation_bundle.py`
- `scripts/bundle/build_docs.py`
- `scripts/bundle/build_strategy_bundle.py`
"""


def build_script_readme() -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""# H1_M30_H4 Scripts

> 更新时间：{ts}

## 目录说明

- `data_source`
  - 负责同步策略所需原始数据。
- `prepare`
  - 负责生成 30M / 1H / 4H 标准化 K 线和上下文交易数据。
- `signals`
  - 负责导出单因子、多因子候选门和候选交易机会。
- `validate`
  - 负责把全局认证结果按 `H1_M30_H4` 过滤并落到本策略目录。
- `bundle`
  - 负责文档生成与整包构建。

## 使用方式

```powershell
python H1_M30_H4策略/scripts/bundle/build_strategy_bundle.py
```
"""


def build_processed_readme() -> str:
    return """# H1_M30_H4 处理后数据

## 当前包含

- `raw_m30_standardized.csv`
- `30m_bars.csv`
- `1h_bars.csv`
- `4h_bars.csv`
- `h1_m30_h4_context_trades.csv`

## 说明

- 原始 30 分钟数据会先做字段标准化和时间修正。
- 再按策略周期重采样，生成本策略独立使用的 1H / 4H 数据。
- `h1_m30_h4_context_trades.csv` 是后续门测试、止损验证、信号复核的主表。
"""


def main() -> None:
    write_text("策略说明.md", build_strategy_doc())
    write_text("参数范围测试面板.md", build_panel_doc())
    write_text("Stage1_Stage2测试结果.md", build_stage_doc())
    write_text("StopSpec严格认证结果.md", build_stop_doc())
    write_text("仓位档位严格认证结果.md", build_position_doc())
    write_text("全项目清单_20260702.md", build_index_doc())
    write_text("scripts/README.md", build_script_readme())
    write_text("data/processed/README.md", build_processed_readme())
    print("Rebuilt core H1_M30_H4 docs.")


if __name__ == "__main__":
    main()
