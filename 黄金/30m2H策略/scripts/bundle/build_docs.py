# -*- coding: utf-8 -*-
"""Build package-level markdown docs for the 30m2H strategy workspace."""
from __future__ import annotations


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_30m2h_common import SIGNALS_DIR, START_CAPITAL, STRATEGY_DIR, write_text


def _build_index() -> str:
    return "\n".join(
        [
            "# 30m2H 主线策略包清单",
            "",
            "## 目录结构",
            "",
            "- `data/raw`：原始行情与上游原始说明",
            "- `data/processed`：标准化后的 M30 / H2 / M15 上下文数据",
            "- `data/signals`：候选信号、Layer3 入选信号、执行交易、年度表现",
            "- `data/validation`：Layer / Stage / StopSpec / EA 对齐等验证结果",
            "- `scripts/data_source`：同步原始数据脚本",
            "- `scripts/prepare`：处理行情与上下文脚本",
            "- `scripts/signals`：导出信号与收益统计脚本",
            "- `scripts/validate`：整理验证结果脚本",
            "- `scripts/bundle`：一键构建脚本",
            "",
            "## 固定规则",
            "",
            "- Markdown 文档统一使用 `utf-8-sig` 编码。",
            "- 中文 CSV 统一优先导出 `utf-8-sig`，避免 Excel 打开乱码。",
            f"- 主线统计默认原始资金为 `${START_CAPITAL:.2f}`。",
        ]
    )


def _build_runbook() -> str:
    return "\n".join(
        [
            "# 30m2H 主线执行说明",
            "",
            "## 一键执行",
            "",
            "```powershell",
            "python 黄金/30m2H策略/scripts/bundle/build_strategy_bundle.py",
            "```",
            "",
            "## 执行顺序",
            "",
            "1. 同步 `base_data` 到 `data/raw`。",
            "2. 生成标准化后的 M30 / H2 / M15 上下文数据。",
            "3. 导出候选信号、Layer3 入选信号、Stage 执行交易和中文汇总。",
            "4. 收集历史验证结果与 EA/Python 对齐结果。",
            "5. 重写策略包说明文档。",
            "",
            "## 关键输出",
            "",
            "- `data/signals/信号汇总_中文.csv`",
            "- `data/signals/年度表现_中文.csv`",
            "- `data/signals/执行交易_Stage结果.csv`",
            "- `data/validation/ea_python_diff/*`",
        ]
    )


def _build_signal_readme() -> str:
    files = sorted(path.name for path in SIGNALS_DIR.glob("*") if path.is_file())
    lines = [
        "# 30m2H 主线信号数据",
        "",
        "## 当前包含",
        "",
    ]
    lines.extend(f"- `{name}`" for name in files)
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- `候选信号_Layer1_Layer2通过.csv`：通过 Layer1 和 Layer2 的候选机会。",
            "- `最终信号_Layer3入选.csv`：再经 Layer3 强度筛选后保留的信号。",
            "- `执行交易_Stage结果.csv`：套用 Stage 出场逻辑后的最终交易结果。",
            "- `信号汇总_中文.csv`：原始资金、总盈利、最终资金额、胜率、止损占比等主表。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    write_text(STRATEGY_DIR / "策略包清单.md", _build_index())
    write_text(STRATEGY_DIR / "策略执行说明.md", _build_runbook())
    write_text(SIGNALS_DIR / "README.md", _build_signal_readme())
    print("Built docs for 30m2H strategy package.")


if __name__ == "__main__":
    main()
