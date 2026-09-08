# -*- coding: utf-8 -*-
"""Rebuild core markdown docs for 1H_M30_4H from local outputs."""
from __future__ import annotations


from datetime import date
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_workspace_common import (  # noqa: E402
    COMBO,
    FOCUS_TF,
    FRAMES,
    PERIOD_LABEL,
    SIGNALS_DIR,
    SOURCE_COMBO,
    STRATEGY_NAME,
    VALIDATION_DIR,
    markdown_table,
    read_csv_with_fallback,
    write_text,
)


TODAY = date.today().isoformat()


def _fmt(value: object, digits: int = 4, suffix: str = "") -> str:
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except Exception:
        return str(value)


def _load(name: str) -> pd.DataFrame:
    return read_csv_with_fallback(VALIDATION_DIR / name)


def _summary_row() -> pd.Series:
    return _load("strategy_summary.csv").iloc[0]


def _top_variants() -> pd.DataFrame:
    path = SIGNALS_DIR / "strategy_variant_top3.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = read_csv_with_fallback(path)
    cols = ["variant", "desc", "n", "wr", "pf", "ev", "test_pf", "test_ev"]
    return frame.loc[:, [col for col in cols if col in frame.columns]].copy()


def _yearly() -> pd.DataFrame:
    frame = _load("yearly_performance.csv")
    if frame.empty:
        return frame
    out = frame.copy()
    out["wr"] = out["wr"].map(lambda value: _fmt(value, 2, "%"))
    out["pf"] = out["pf"].map(lambda value: _fmt(value, 4))
    out["ev"] = out["ev"].map(lambda value: _fmt(value, 4))
    out["pnl"] = out["pnl"].map(lambda value: _fmt(value, 4))
    return out


def _gate_scan() -> pd.DataFrame:
    frame = _load("combo_gate_range_scan.csv")
    if frame.empty:
        return frame
    cols = ["gate_family", "gate_param", "desc", "trades", "wr", "pf", "ev", "test_pf"]
    out = frame.loc[:, cols].head(10).copy()
    for col in ["wr", "pf", "ev", "test_pf"]:
        out[col] = out[col].map(lambda value: _fmt(value, 4))
    return out


def _optional_csv(name: str) -> pd.DataFrame:
    path = VALIDATION_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return read_csv_with_fallback(path)


def _advanced_table() -> pd.DataFrame:
    final = _optional_csv("combo_final_best_summary.csv")
    stop = _optional_csv("combo_stop_range_pick.csv")
    if final.empty:
        return pd.DataFrame(columns=["项目", "当前值"])
    row = final.iloc[0]
    stop_row = stop.iloc[0] if not stop.empty else {}
    return pd.DataFrame(
        [
            ["Stage 参数", f"{float(row['stage1_r']):.1f}/{float(row['stage2_trail_r']):.1f}/{float(row['stage2_force_r']):.1f}"],
            ["Stage PF / EV", f"{_fmt(row['stage_pf'], 4)} / {_fmt(row['stage_ev'], 4)}"],
            ["仓位单位", row["units"]],
            ["手数", row["lots"]],
            ["最终 PF / EV", f"{_fmt(row['final_pf'], 4)} / {_fmt(row['final_ev'], 4)}"],
            ["最终 PnL", f"${float(row['final_pnl_$']):.2f}"],
            ["主止损范围", stop_row.get("primary_stop_range", "")],
            ["次优止损范围", stop_row.get("secondary_stop_range", "")],
            ["可接受止损区间", stop_row.get("acceptable_stop_range", "")],
            ["EA 参数包", "data/validation/ea_parameter_pack.json"],
        ],
        columns=["项目", "当前值"],
    )


def build_root_readme() -> str:
    reference_line = (
        f"- 参考验证：已从 `{SOURCE_COMBO}` 历史认证包导入并统一到 `{COMBO}` 命名。"
        if SOURCE_COMBO
        else "- 参考验证：当前组合暂无同名历史认证包。"
    )
    return f"""# {STRATEGY_NAME} 策略

这是按 `30m2H策略` 标准目录新建的策略工程。

## 策略定位

- 组合周期：`{PERIOD_LABEL}`
- 聚焦周期：`{FOCUS_TF}`
- 当前策略编码：`{COMBO}`
- 对齐母版：`30m2H策略`
{reference_line}

## 推荐阅读顺序

1. `说明文档/01_总览说明/策略说明.md`
2. `说明文档/01_总览说明/一次性执行计划.md`
3. `说明文档/02_策略流程/流程说明.md`
4. `scripts/README.md`
5. `data/validation/README.md`

## 一键构建

```powershell
python {STRATEGY_NAME}策略/scripts/bundle/build_strategy_bundle.py
```
"""


def build_strategy_doc() -> str:
    row = _summary_row()
    results = pd.DataFrame(
        [
            ["主推荐门", row["primary_variant"]],
            ["门说明", row["primary_desc"]],
            ["交易次数", int(row["trades"])],
            ["胜率", _fmt(row["wr"], 2, "%")],
            ["PF", _fmt(row["pf"], 4)],
            ["EV", _fmt(row["ev"], 4)],
            ["样本外交易次数", int(row["test_n"])],
            ["样本外 PF", _fmt(row["test_pf"], 4)],
            ["样本外 EV", _fmt(row["test_ev"], 4)],
        ],
        columns=["项目", "当前结果"],
    )
    return f"""# {STRATEGY_NAME} 策略说明

> 生成时间：{TODAY}
> 对齐对象：`30m2H策略`

## 1. 当前方案

- 组合周期：`{PERIOD_LABEL}`
- 当前组合门：`{row["primary_variant"]}`
- 组合门说明：`{row["primary_desc"]}`
- 聚焦周期：`{FOCUS_TF}`
- 周期文件：`{", ".join(FRAMES)}`

## 2. 当前结果

{markdown_table(results)}

按年份拆分：

{markdown_table(_yearly())}

## 3. 高级认证参数

{markdown_table(_advanced_table())}

## 4. 当前结论

- 本策略已具备从原始 M30 数据到多周期上下文、候选门、基础验证摘要的完整研究链路。
- 当前已补齐 Stage 扫描、StopSpec 扫描、仓位档位扫描和 EA 参数包。
- EA 侧尚未声明逐笔对齐完成；当前状态是研究参数已就绪，执行端适配待接入。
"""


def build_execution_plan() -> str:
    return f"""# {STRATEGY_NAME} 一次性执行计划

## 执行顺序

1. 同步独立 MT5 原始数据：`scripts/data_source/sync_raw_data_from_mt5.py`
2. 构建处理后数据：输出带方向 `bias5/bias13/bias55` 与结构止损 `stop_distance`
3. 导出候选信号：M30 cross + 高周期上下文，不使用旧 `pre_cross/post_n`
4. 导出方向测试：BUY/SELL/高周期同向反向
5. 导出 bias_signed 测试：`bias5_signed`、`bias13_signed`、`bias55_signed`
6. 导出 StopSpec 扫描：只基于 `stop_distance`
7. 导出 Stage/仓位验证：固定信号后再扫描
8. 生成文档：`scripts/bundle/build_docs.py`

## 一键入口

```powershell
python {STRATEGY_NAME}策略/scripts/bundle/build_strategy_bundle.py
```

## 当前边界

- 已覆盖研究层数据链路、基础验证链路和高级参数验证链路。
- 现有结果需要按新规则重跑：带方向 bias，不再用 `abs()`。
- StopSpec 必须改为结构止损 `stop_distance`，不再混用 `focus_sd` 代理口径。
- `recent2_any` 和 ATR 只作为对照实验/风控过滤。
- 暂不直接接入 EA 实盘执行端；Python 验证通过后再重写专用 EA。
"""


def build_flow_doc() -> str:
    return f"""# {STRATEGY_NAME} 策略流程

## 数据链路

`XAUUSDm30.csv` -> 标准化 M30 -> `{PERIOD_LABEL}` 周期 K 线 -> 上下文交易主表。

## 信号链路

M30 SMA5/SMA13 cross -> 带方向 bias 与高周期上下文 -> 候选门汇总 -> 主推荐门。

## 验证链路

候选门表现 -> 主推荐门摘要 -> 年度表现 -> StopSpec(stop_distance) 扫描 -> Stage 扫描 -> 仓位扫描 -> EA 参数包。

## 关键输出

- `data/processed/{STRATEGY_NAME.lower()}_context_trades.csv`
- `data/signals/strategy_variant_summary.csv`
- `data/signals/strategy_candidate_trades.csv`
- `data/validation/strategy_summary.csv`
- `data/validation/combo_gate_range_scan.csv`
- `data/validation/combo_final_best_summary.csv`
- `data/validation/combo_stop_range_pick.csv`
- `data/validation/ea_parameter_pack.json`
"""


def build_validation_doc() -> str:
    return f"""# {STRATEGY_NAME} 验证结果摘要

## 主推荐结果

{markdown_table(pd.DataFrame([_summary_row()]))}

## Top 候选门

{markdown_table(_top_variants())}

## 门扫描预览

{markdown_table(_gate_scan())}

## Stage Top 3

{markdown_table(_optional_csv("combo_top3_stage12.csv"))}

## 仓位 Top 3

{markdown_table(_optional_csv("combo_top3_position.csv"))}

## StopSpec 推荐

{markdown_table(_optional_csv("combo_stop_range_pick.csv"))}

## EA 对齐状态

{markdown_table(_optional_csv("ea_alignment_readiness.csv"))}
"""


def build_inventory_doc() -> str:
    return f"""# {STRATEGY_NAME} 项目文件清单

## 文档入口

- `README.md`
- `说明文档/01_总览说明/策略说明.md`
- `说明文档/01_总览说明/一次性执行计划.md`
- `说明文档/02_策略流程/流程说明.md`
- `说明文档/03_验证结果/README.md`
- `说明文档/04_项目清单/项目文件清单.md`

## 脚本入口

- `scripts/data_source/sync_raw_data.py`
- `scripts/prepare/build_processed_data.py`
- `scripts/signals/export_signal_candidates.py`
- `scripts/validate/export_validation_bundle.py`
- `scripts/validate/export_advanced_validation.py`
- `scripts/bundle/build_docs.py`
- `scripts/bundle/build_strategy_bundle.py`

## 数据入口

- `data/raw`
- `data/processed`
- `data/signals`
- `data/validation`
"""


def build_scripts_readme() -> str:
    return f"""# {STRATEGY_NAME} Scripts

## 推荐执行顺序

1. `data_source`
2. `prepare`
3. `signals`
4. `validate`
5. `bundle`

## 一键入口

```powershell
python {STRATEGY_NAME}策略/scripts/bundle/build_strategy_bundle.py
```

## 验证入口

- `validate/export_validation_bundle.py`：基础候选门与年度表现。
- `validate/export_advanced_validation.py`：Stage / StopSpec / 仓位 / EA 参数包。
"""


def build_raw_data_rule_doc() -> str:
    return f"""# {STRATEGY_NAME} 原始数据独立规则

## 固定规则

- 本策略必须使用自己的原始行情数据生成，不能直接复用 `黄金/30m2H策略/参考实现工程/base_data` 或其他策略目录里的 raw 文件。
- `data/raw/raw_source_manifest.json` 是正式生成前置条件，必须记录来源路径、source id、sha256、大小和策略名。
- 若 manifest 缺失，或与其他策略的 raw source path / sha256 相同，本策略结果只能视为迁移脚手架，不能视为正式认证结果。
- 参考工程只允许提供代码结构、验证方法和 EA 框架；不能作为本策略默认 raw 数据来源。

## 执行入口

```powershell
python {STRATEGY_NAME}策略/scripts/data_source/sync_raw_data.py --source "<{STRATEGY_NAME}专用XAUUSDm30.csv>" --source-id "<来源标识>"
```

完成 raw 安装和 manifest 校验后，再执行 `prepare -> signals -> validate -> bundle`。
"""


def main() -> None:
    write_text("README.md", build_root_readme())
    write_text("说明文档/00_策略生成规则/原始数据独立规则.md", build_raw_data_rule_doc())
    write_text("说明文档/01_总览说明/策略说明.md", build_strategy_doc())
    write_text("说明文档/01_总览说明/一次性执行计划.md", build_execution_plan())
    write_text("说明文档/02_策略流程/流程说明.md", build_flow_doc())
    write_text("说明文档/03_验证结果/README.md", build_validation_doc())
    write_text("说明文档/04_项目清单/项目文件清单.md", build_inventory_doc())
    write_text("scripts/README.md", build_scripts_readme())
    write_text(
        "参考实现工程/README.md",
        "# 参考实现工程\n\n本策略暂不复制完整参考工程，默认引用 `黄金/30m2H策略/参考实现工程` 作为母版。\n",
    )
    write_text("归档/README.md", "# 归档\n\n历史资料和旧版本输出放在这里。\n")
    print(f"Rebuilt core {STRATEGY_NAME} docs.")


if __name__ == "__main__":
    main()
