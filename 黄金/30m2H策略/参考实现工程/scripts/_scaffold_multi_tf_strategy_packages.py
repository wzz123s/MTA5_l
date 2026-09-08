# -*- coding: utf-8 -*-
"""Scaffold local multi-timeframe strategy packages from the H1_M30_H4 layout."""
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STRATEGIES = [
    {"combo": "H2_H6_H8", "frames": ["2H", "6H", "8H"]},
    {"combo": "H3_H10_H12", "frames": ["3H", "10H", "12H"]},
    {"combo": "H4_H16", "frames": ["4H", "16H"]},
    {"combo": "H5_H20", "frames": ["5H", "20H"]},
    {"combo": "H6_H24", "frames": ["6H", "24H"]},
]


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def write_py(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def combo_slug(combo: str) -> str:
    return combo.lower()


def strategy_dir_name(combo: str) -> str:
    return f"{combo}策略"


def common_module_name(combo: str) -> str:
    return combo_slug(combo) + "_common"


def context_file_name(combo: str) -> str:
    return combo_slug(combo) + "_context_trades.csv"


def current_strategy_doc(combo: str, frames: list[str]) -> str:
    focus = frames[0]
    return f"""# {combo} 策略说明

> 生成时间：2026-07-05
> 策略定位：多周期矩阵中的 `{combo}`
> 对齐对象：`H1_M30_H4策略` 的目录结构与 `30m2H策略` 的文档规则
> 当前状态：已建立本地策略工作区骨架，验证文档待按 H1 模板逐项补齐

## 0. 文档与编码规则

- 本策略目录的主文档是 `{strategy_dir_name(combo)}/策略说明.md`，负责保存当前采用参数、当前结果和当前认证结论。
- `findings.md`：只放研究结论、判断依据、风险。
- `progress.md`：只放时间顺序的工作过程。
- `task_plan.md`：只放当前待办和完成状态。
- `CONTEXT.md`：只放接手时必须知道的固定背景。
- 本策略目录下新生成或重写的 Markdown 文档统一使用 `utf-8-sig`。
- 本策略目录下结果类 CSV 主版本优先使用 `utf-8-sig`；如需兼容旧工具链，再额外输出 `gbk` 版本。

## 1. 当前方案

- 组合周期：`{" / ".join(frames)}`
- 当前组合门：`{combo}__baseline`
- 组合门说明：`待补：按 H1 模板从组合门细扫结果回填`
- 当前 Stage 参数：`待补`
- 当前仓位单位：`待补`
- 当前手数：`待补`
- 聚焦周期：`{focus}`
- 当前主推荐止损范围：`待补`
- 当前次优止损范围：`待补`
- 当前可接受止损区间：`待补`

## 2. 当前结果

| 项目 | 当前结果 |
| --- | --- |
| 总交易次数 | 待补 |
| 胜率 | 待补 |
| 最终 PF | 待补 |
| 最终 EV | 待补 |
| 总盈利 | 待补 |
| 最终资金额 | 待补 |
| 止损次数 | 待补 |
| 止损次数占比 | 待补 |

## 3. 当前认证结论

- 当前目录骨架、数据分层、分类脚本已经建立。
- Layer 1 / Layer 2 / Layer 3 / Stage1 / Stage2 / StopSpec / 门参数区间 / 止损区间，待按 `H1_M30_H4策略` 模板逐项补齐。
- 本策略不作为当前主线任务，主线优先级低于 `30m2H策略` 和 `auto_trade/30m2H_Strategy_EA.mq5`。
"""


def pending_doc(title: str, combo: str, extra_lines: list[str]) -> str:
    lines = "\n".join(f"- {line}" for line in extra_lines)
    return f"""# {combo} {title}

> 生成时间：2026-07-05
> 当前状态：已建立文档骨架，待补正式验证过程与结果

## 当前说明

{lines}

## 待补内容

- 待从全局验证结果和本策略本地复跑结果中补齐正式表格。
- 待补每一步扫描范围、筛选逻辑、当前采用值和放弃原因。
"""


def raw_readme(combo: str, frames: list[str]) -> str:
    return f"""# {combo} 原始数据

## 当前包含

- `XAUUSDm30.csv` <- `F:\\use_code\\MTA5\\base_data\\XAUUSDm30.csv`
- `README.md` <- `F:\\use_code\\MTA5\\base_data\\README.md`

## 说明

- `XAUUSDm30.csv` 是本策略重建 `{" / ".join(frames)}` 上下文的基础原始 K 线。
- `README.md` 保留上游 `base_data` 目录的口径说明，便于后续复核来源。
"""


def processed_readme(combo: str, frames: list[str]) -> str:
    files = ["`raw_m30_standardized.csv`"] + [f"`{frame.lower()}_bars.csv`" for frame in frames] + [f"`{context_file_name(combo)}`"]
    file_lines = "\n".join(f"- {item}" for item in files)
    return f"""# {combo} 处理后数据

## 当前包含

{file_lines}

## 说明

- 原始 30 分钟数据会先做字段标准化和时间修正。
- 再按策略周期重采样，生成本策略独立使用的 `{" / ".join(frames)}` 数据。
- `{context_file_name(combo)}` 是后续门测试、止损验证、信号复核的主表。
"""


def validation_readme(combo: str) -> str:
    return f"""# {combo} 验证数据

## 当前状态

- 本目录用于存放组合门扫描、Layer/Stage/StopSpec、仓位与最终资金指标结果。
- 初次脚手架阶段只建立目录和 README。
- 执行 `scripts/bundle/build_strategy_bundle.py` 后，会按 `{combo}` 自动回填本地 CSV 清单。
"""


def signals_readme(combo: str) -> str:
    return f"""# {combo} 信号数据

## 当前状态

- 本目录用于单独存放候选门汇总、候选交易明细、Top 3 组合门结果。
- 初次脚手架阶段会先创建空目录与说明文档。
- 执行 `scripts/signals/export_signal_candidates.py` 后，会自动生成本策略的信号层 CSV。
"""


def scripts_readme(combo: str, frames: list[str]) -> str:
    return f"""# {combo} Scripts

> 更新时间：2026-07-05

## 目录说明

- `data_source`
  - 负责同步策略所需原始数据。
- `prepare`
  - 负责生成 `{" / ".join(frames)}` 标准化 K 线和上下文交易数据。
- `signals`
  - 负责导出单因子、多因子候选门和候选交易机会。
- `validate`
  - 负责把全局认证结果按 `{combo}` 过滤并落到本策略目录。
- `bundle`
  - 负责文档生成与整包构建。

## 使用方式

```powershell
python {strategy_dir_name(combo)}/scripts/bundle/build_strategy_bundle.py
```
"""


def common_py(combo: str, frames: list[str]) -> str:
    module_name = common_module_name(combo)
    dir_name = strategy_dir_name(combo)
    ctx_file = context_file_name(combo)
    return f'''# -*- coding: utf-8 -*-
"""Shared helpers for the {combo} strategy workspace."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
STRATEGY_DIR = ROOT / "{dir_name}"
SCRIPTS_DIR = STRATEGY_DIR / "scripts"
DATA_DIR = STRATEGY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SIGNALS_DIR = DATA_DIR / "signals"
VALIDATION_DIR = DATA_DIR / "validation"
GLOBAL_VALIDATION_DIR = ROOT / "shadow_tests" / "multi_tf_matrix" / "data" / "validation_20260701"
COMBO = "{combo}"
FRAMES = {frames!r}
CONTEXT_FILE = "{ctx_file}"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shadow_tests" / "multi_tf_matrix" / "scripts"))

from _multi_tf_matrix_common import TIMEFRAME_MATRIX  # type: ignore  # noqa: E402


FINAL_SUMMARY_COLS = [
    "combo", "picked_variant", "picked_desc", "picked_n", "picked_pf", "picked_ev",
    "picked_test_pf", "picked_test_ev", "stage1_r", "stage2_trail_r", "stage2_force_r",
    "stage_pf", "stage_ev", "stage_test_pf", "stage_test_ev", "units", "lots",
    "final_pf", "final_ev", "final_pnl_$", "final_test_pf", "final_test_ev",
]

COMBINED_SUMMARY_COLS = [
    "combo", "current_variant", "variant_desc", "gate_range", "stage_params",
    "units", "lots", "focus_tf", "stop_main", "stop_second", "stop_ok",
    "stop_grid_lo", "stop_grid_hi", "stop_desc", "stop_pf", "stop_test_pf",
    "stop_ev", "stop_profit",
]

CAPITAL_BASE_COLS = [
    "combo", "final_variant", "variant_desc", "stage_params", "units", "lots",
    "start_capital", "total_trades", "final_capital", "total_profit",
    "avg_stop_pt", "median_stop_pt", "max_r", "min_r", "avg_r", "median_r",
    "stop_count", "stop_ratio",
]

STOP_SCAN_COLS = [
    "combo", "current_variant", "focus_tf", "stop_range", "stop_lo", "stop_hi",
    "grid_lo", "grid_hi", "trades", "wr", "pf", "ev", "profit", "test_pf",
    "test_ev", "avg_stop", "median_stop", "sample_ok", "score",
]

GATE_SCAN_COLS = [
    "combo", "current_variant", "focus_tf", "gate_family", "gate_param", "desc",
    "trades", "wr", "pf", "ev", "test_pf", "test_ev",
]


def ensure_dirs() -> None:
    for path in [
        RAW_DIR, PROCESSED_DIR, SIGNALS_DIR, VALIDATION_DIR,
        SCRIPTS_DIR / "data_source", SCRIPTS_DIR / "prepare",
        SCRIPTS_DIR / "signals", SCRIPTS_DIR / "validate", SCRIPTS_DIR / "bundle",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def strategy_spec() -> dict:
    for item in TIMEFRAME_MATRIX:
        if item["name"] == COMBO:
            return item
    raise KeyError("Strategy combo not found: " + COMBO)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def read_csv_with_fallback(path: Path, encodings: list[str] | None = None) -> pd.DataFrame:
    attempts = encodings or ["utf-8-sig", "utf-8", "gbk"]
    last_error: Exception | None = None
    for encoding in attempts:
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise RuntimeError("Unable to read CSV: " + str(path)) from last_error


def rename_by_position(frame: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    out = frame.copy()
    out.columns = names + list(out.columns[len(names):])
    return out


def filter_combo(frame: pd.DataFrame, combo_col: str = "combo") -> pd.DataFrame:
    return frame.loc[frame[combo_col] == COMBO].copy().reset_index(drop=True)


def load_final_summary(local_first: bool = True) -> pd.Series:
    path = VALIDATION_DIR / "combo_final_best_summary.csv" if local_first else GLOBAL_VALIDATION_DIR / "combo_final_best_summary.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "combo_final_best_summary.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, FINAL_SUMMARY_COLS)
    return filter_combo(df).iloc[0]


def load_combined_summary(local_first: bool = True) -> pd.Series:
    path = VALIDATION_DIR / "combo_combined_summary.csv" if local_first else GLOBAL_VALIDATION_DIR / "缁勫悎鍙傛暟鎬昏〃_闂ㄥ尯闂確姝㈡崯鍖洪棿_涓枃.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "缁勫悎鍙傛暟鎬昏〃_闂ㄥ尯闂確姝㈡崯鍖洪棿_涓枃.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, COMBINED_SUMMARY_COLS)
    return filter_combo(df).iloc[0]


def load_capital_metrics(local_first: bool = True) -> pd.Series:
    path = VALIDATION_DIR / "combo_final_capital_metrics.csv" if local_first else GLOBAL_VALIDATION_DIR / "缁勫悎鏈€缁堣祫閲戞寚鏍嘷涓枃_utf8.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "缁勫悎鏈€缁堣祫閲戞寚鏍嘷涓枃_utf8.csv"
    df = read_csv_with_fallback(path)
    year_cols: list[str] = []
    for year in range(2020, 2027):
        year_cols.extend([f"y{{year}}_trades", f"y{{year}}_profit", f"y{{year}}_stops"])
    df = rename_by_position(df, CAPITAL_BASE_COLS + year_cols)
    return filter_combo(df).iloc[0]


def load_stop_scan(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_stop_range_scan.csv" if local_first else GLOBAL_VALIDATION_DIR / "缁勫悎姝㈡崯鑼冨洿娴嬭瘯_涓枃.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "缁勫悎姝㈡崯鑼冨洿娴嬭瘯_涓枃.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, STOP_SCAN_COLS)
    return filter_combo(df)


def load_gate_scan(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_gate_range_scan.csv" if local_first else GLOBAL_VALIDATION_DIR / "缁勫悎闂ㄨ寖鍥寸粏鎵玙涓枃.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "缁勫悎闂ㄨ寖鍥寸粏鎵玙涓枃.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, GATE_SCAN_COLS)
    return filter_combo(df)


def load_top3_stage(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_top3_stage12.csv" if local_first else GLOBAL_VALIDATION_DIR / "combo_top3_stage12.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "combo_top3_stage12.csv"
    df = read_csv_with_fallback(path)
    return filter_combo(df)


def load_top3_position(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_top3_position.csv" if local_first else GLOBAL_VALIDATION_DIR / "combo_top3_position.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "combo_top3_position.csv"
    df = read_csv_with_fallback(path)
    return filter_combo(df)


def write_text(name: str, text: str) -> None:
    path = STRATEGY_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\\n").encode("utf-8-sig"))


def copy_source_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
'''


def sync_raw_py(combo: str) -> str:
    module = common_module_name(combo)
    return f'''# -*- coding: utf-8 -*-
"""Copy required raw inputs into the local {combo} strategy folder."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from {module} import RAW_DIR, ROOT, copy_source_file, ensure_dirs, write_text


def main() -> None:
    ensure_dirs()
    sources = [
        ROOT / "base_data" / "XAUUSDm30.csv",
        ROOT / "base_data" / "README.md",
    ]
    copied = []
    for src in sources:
        dst = RAW_DIR / src.name
        copy_source_file(src, dst)
        copied.append("- `" + src.name + "` <- `" + str(src) + "`")
    manifest = "\\n".join(copied)
    write_text(
        "data/raw/README.md",
        """# {combo} 原始数据

## 当前包含

""" + manifest + """

## 说明

- `XAUUSDm30.csv` 是本策略重建上下文的基础原始 K 线。
- `README.md` 保留上游 `base_data` 目录的口径说明，便于后续复核来源。""",
    )
    print("Synced raw data into {combo} strategy folder.")


if __name__ == "__main__":
    main()
'''


def build_processed_py(combo: str) -> str:
    module = common_module_name(combo)
    return f'''# -*- coding: utf-8 -*-
"""Build processed timeframe and context datasets for {combo}."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from {module} import COMBO, CONTEXT_FILE, PROCESSED_DIR, RAW_DIR, ensure_dirs, export_csv, strategy_spec
from _multi_tf_matrix_common import attach_all_context, build_tf, load_m30_raw, load_mainline_bundle


def main() -> None:
    ensure_dirs()
    spec = strategy_spec()
    raw_path = RAW_DIR / "XAUUSDm30.csv"
    raw_m30 = load_m30_raw(str(raw_path))

    export_csv(raw_m30, PROCESSED_DIR / "raw_m30_standardized.csv")
    for label in spec["frames"]:
        frame = build_tf(raw_m30, label)
        export_csv(frame, PROCESSED_DIR / (label.lower() + "_bars.csv"))

    bundle = load_mainline_bundle()
    ctx = attach_all_context(bundle["signals"], spec["frames"]).sort_values("date").reset_index(drop=True)
    export_csv(ctx, PROCESSED_DIR / CONTEXT_FILE)

    print("Built processed data for " + COMBO + ".")


if __name__ == "__main__":
    main()
'''


def signals_py(combo: str) -> str:
    module = common_module_name(combo)
    return f'''# -*- coding: utf-8 -*-
"""Export strategy signal candidates and per-variant trade sets."""
from __future__ import annotations

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from {module} import COMBO, CONTEXT_FILE, PROCESSED_DIR, SIGNALS_DIR, ensure_dirs, export_csv, strategy_spec
from _multi_tf_matrix_common import build_combo_variant_frames, summarize_variant_item


def main() -> None:
    ensure_dirs()
    ctx = pd.read_csv(PROCESSED_DIR / CONTEXT_FILE, encoding="utf-8-sig")
    ctx["date"] = pd.to_datetime(ctx["date"])
    combo = strategy_spec()

    variants = build_combo_variant_frames(combo, ctx)
    summary = pd.DataFrame([summarize_variant_item(item) for item in variants]).sort_values(
        ["pf", "test_pf", "n"], ascending=[False, False, False]
    )
    export_csv(summary, SIGNALS_DIR / "strategy_variant_summary.csv")

    trade_frames = []
    for item in variants:
        frame = item["frame"].copy()
        if "variant" in frame.columns:
            frame = frame.rename(columns={{"variant": "source_variant"}})
        frame.insert(0, "combo", COMBO)
        frame.insert(1, "variant", item["variant"])
        frame.insert(2, "variant_desc", item["desc"])
        trade_frames.append(frame)
    export_csv(pd.concat(trade_frames, ignore_index=True), SIGNALS_DIR / "strategy_candidate_trades.csv")
    export_csv(summary.head(3).copy(), SIGNALS_DIR / "strategy_variant_top3.csv")
    print("Exported signal candidates for " + COMBO + ".")


if __name__ == "__main__":
    main()
'''


def validate_py(combo: str) -> str:
    module = common_module_name(combo)
    return f'''# -*- coding: utf-8 -*-
"""Copy combo-specific validation outputs into the local strategy folder."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from {module} import COMBO, GLOBAL_VALIDATION_DIR, VALIDATION_DIR, ensure_dirs, export_csv
from {module} import load_capital_metrics, load_combined_summary, load_final_summary, load_gate_scan
from {module} import load_stop_scan, load_top3_position, load_top3_stage, read_csv_with_fallback


def _filter_and_export(src_name: str, dst_name: str) -> None:
    path = GLOBAL_VALIDATION_DIR / src_name
    frame = read_csv_with_fallback(path)
    combo_col = frame.columns[0]
    frame = frame.loc[frame[combo_col] == COMBO].copy().reset_index(drop=True)
    export_csv(frame, VALIDATION_DIR / dst_name)


def main() -> None:
    ensure_dirs()
    _filter_and_export("combo_best_stage12_trades.csv", "combo_best_stage12_trades.csv")
    _filter_and_export("combo_candidate_pick.csv", "combo_candidate_pick.csv")
    _filter_and_export("combo_final_best_summary.csv", "combo_final_best_summary.csv")
    _filter_and_export("combo_final_capital_metrics.csv", "combo_final_capital_metrics_raw.csv")
    _filter_and_export("combo_gate_strength_top3.csv", "combo_gate_strength_top3.csv")
    _filter_and_export("combo_position_sizing.csv", "combo_position_sizing.csv")
    _filter_and_export("combo_stage12_sweep.csv", "combo_stage12_sweep.csv")
    _filter_and_export("combo_top3_position.csv", "combo_top3_position.csv")
    _filter_and_export("combo_top3_stage12.csv", "combo_top3_stage12.csv")
    _filter_and_export("缁勫悎闂ㄨ寖鍥寸粏鎵玙涓枃.csv", "combo_gate_range_scan_raw.csv")
    _filter_and_export("缁勫悎姝㈡崯鑼冨洿娴嬭瘯_涓枃.csv", "combo_stop_range_scan_raw.csv")
    _filter_and_export("缁勫悎姝㈡崯鑼冨洿鎺ㄨ崘_涓枃.csv", "combo_stop_range_pick_raw.csv")
    _filter_and_export("缁勫悎鍙傛暟鎬昏〃_闂ㄥ尯闂確姝㈡崯鍖洪棿_涓枃.csv", "combo_combined_summary_raw.csv")
    _filter_and_export("缁勫悎鏈€缁堣祫閲戞寚鏍嘷涓枃_utf8.csv", "combo_final_capital_metrics_raw_utf8.csv")

    export_csv(load_final_summary(local_first=False).to_frame().T, VALIDATION_DIR / "combo_final_best_summary_clean.csv")
    export_csv(load_combined_summary(local_first=False).to_frame().T, VALIDATION_DIR / "combo_combined_summary.csv")
    export_csv(load_capital_metrics(local_first=False).to_frame().T, VALIDATION_DIR / "combo_final_capital_metrics.csv")
    export_csv(load_gate_scan(local_first=False), VALIDATION_DIR / "combo_gate_range_scan.csv")
    export_csv(load_stop_scan(local_first=False), VALIDATION_DIR / "combo_stop_range_scan.csv")
    export_csv(load_top3_stage(local_first=False), VALIDATION_DIR / "combo_top3_stage12.csv")
    export_csv(load_top3_position(local_first=False), VALIDATION_DIR / "combo_top3_position.csv")

    manifest_lines = []
    for path in sorted(VALIDATION_DIR.glob("*.csv")):
        manifest_lines.append("- `" + path.name + "`")
    (VALIDATION_DIR / "README.md").write_bytes(
        ("# {combo} 验证数据\\n\\n## 当前文件\\n\\n" + "\\n".join(manifest_lines) + "\\n").encode("utf-8-sig")
    )
    print("Exported validation bundle for " + COMBO + ".")


if __name__ == "__main__":
    main()
'''


def build_docs_py(combo: str, frames: list[str]) -> str:
    module = common_module_name(combo)
    focus = frames[0]
    return f'''# -*- coding: utf-8 -*-
"""Rebuild core markdown docs for {combo} from local validation data when available."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from {module} import (
    CONTEXT_FILE,
    FRAMES,
    PROCESSED_DIR,
    VALIDATION_DIR,
    load_capital_metrics,
    load_combined_summary,
    load_final_summary,
    load_gate_scan,
    load_stop_scan,
    load_top3_position,
    load_top3_stage,
    write_text,
)


TODAY = "2026-07-05"


def fmt_money(value: float) -> str:
    return f"${{value:.2f}}"


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\\n".join(lines)


def safe_series(loader):
    try:
        return loader()
    except Exception:
        return None


def safe_frame(loader):
    try:
        return loader()
    except Exception:
        return None


def build_strategy_doc() -> str:
    final_row = safe_series(load_final_summary)
    combo_row = safe_series(load_combined_summary)
    cap_row = safe_series(load_capital_metrics)
    gate_scan = safe_frame(load_gate_scan)
    if final_row is None or combo_row is None or cap_row is None or gate_scan is None or gate_scan.empty:
        return """# {combo} 策略说明

> 生成时间：""" + TODAY + """
> 当前状态：已建立本地策略工作区骨架，正式认证结果待补

## 当前方案

- 组合周期：`{" / ".join(frames)}`
- 当前组合门：`{combo}__baseline`
- 当前 Stage 参数：`待补`
- 当前仓位单位：`待补`
- 当前手数：`待补`
- 聚焦周期：`{focus}`

## 当前结果

- 待执行本地 `validate` 和后续复跑后回填。
"""

    win_rate = float(gate_scan.iloc[0]["wr"])
    result_rows = [
        ["总交易次数", int(cap_row["total_trades"])],
        ["胜率", f"{{win_rate:.2f}}%"],
        ["最终 PF", f"{{float(final_row['final_pf']):.4f}}"],
        ["最终 EV", f"+{{float(final_row['final_ev']):.4f}}pt"],
        ["总盈利", fmt_money(float(cap_row["total_profit"]))],
        ["最终资金额", fmt_money(float(cap_row["final_capital"]))],
        ["止损次数", int(cap_row["stop_count"])],
        ["止损次数占比", f"{{float(cap_row['stop_ratio']) * 100:.2f}}%"],
    ]
    year_rows = []
    for year in range(2020, 2027):
        key = f"y{{year}}_trades"
        if key not in cap_row.index:
            continue
        year_rows.append([year, int(cap_row[key]), fmt_money(float(cap_row[f"y{{year}}_profit"])), int(cap_row[f"y{{year}}_stops"])])

    return """# {combo} 策略说明

> 生成时间：""" + TODAY + """
> 策略定位：多周期矩阵中的 `{combo}`
> 当前状态：目录、数据分层和分类脚本已就位；正式验证过程文档仍待补全过程说明

## 1. 当前方案

- 组合周期：`{" / ".join(frames)}`
- 当前组合门：`""" + str(final_row["picked_variant"]) + """`
- 组合门说明：`""" + str(final_row["picked_desc"]) + """`
- 当前 Stage 参数：`""" + str(combo_row["stage_params"]) + """`
- 当前仓位单位：`""" + str(combo_row["units"]) + """`
- 当前手数：`""" + str(combo_row["lots"]) + """`
- 聚焦周期：`""" + str(combo_row["focus_tf"]) + """`
- 当前主推荐止损范围：`""" + str(combo_row["stop_main"]) + """`
- 当前次优止损范围：`""" + str(combo_row["stop_second"]) + """`
- 当前可接受止损区间：`""" + str(combo_row["stop_ok"]) + """`

## 2. 当前结果

""" + md_table(["项目", "当前结果"], result_rows) + """

按年份拆分：

""" + md_table(["年份", "交易次数", "年度盈利", "年度止损次数"], year_rows) + """
"""


def build_stage_doc() -> str:
    frame = safe_frame(load_top3_stage)
    if frame is None or frame.empty:
        return """# {combo} Stage1 / Stage2 测试结果

> 生成时间：""" + TODAY + """
> 当前状态：已建立文档骨架，待回填正式扫描结果
"""
    rows = []
    for _, row in frame.iterrows():
        rows.append([
            f"{{row['stage1_r']:.1f}} / {{row['stage2_trail_r']:.1f}} / {{row['stage2_force_r']:.1f}}",
            int(row["n"]),
            f"{{float(row['wr']):.2f}}%",
            f"{{float(row['pf']):.4f}}",
            f"+{{float(row['ev']):.4f}}pt",
            f"{{float(row['test_pf']):.4f}}",
        ])
    return """# {combo} Stage1 / Stage2 测试结果

> 生成时间：""" + TODAY + """

## 当前 Top 结果

""" + md_table(["Stage 参数", "交易数", "胜率", "PF", "EV", "验证PF"], rows) + """
"""


def build_stop_doc() -> str:
    frame = safe_frame(load_stop_scan)
    combo_row = safe_series(load_combined_summary)
    if frame is None or frame.empty or combo_row is None:
        return """# {combo} StopSpec 严格认证结果

> 生成时间：""" + TODAY + """
> 当前状态：已建立文档骨架，待回填正式止损扫描结果
"""
    top = frame.sort_values(["score", "test_ev"], ascending=[False, False]).head(5)
    rows = []
    for _, row in top.iterrows():
        rows.append([
            row["stop_range"],
            int(row["trades"]),
            f"{{float(row['wr']):.2f}}%",
            f"{{float(row['pf']):.4f}}",
            f"+{{float(row['ev']):.4f}}pt",
            fmt_money(float(row["profit"])),
            f"{{float(row['test_pf']):.4f}}",
        ])
    return """# {combo} StopSpec 严格认证结果

> 生成时间：""" + TODAY + """

## 当前扫描网格

- 下限集：`""" + str(combo_row["stop_grid_lo"]) + """`
- 上限集：`""" + str(combo_row["stop_grid_hi"]) + """`

## Top 结果

""" + md_table(["止损范围", "交易数", "胜率", "PF", "EV", "总盈利", "验证PF"], rows) + """
"""


def build_panel_doc() -> str:
    combo_row = safe_series(load_combined_summary)
    gate = safe_frame(load_gate_scan)
    pos = safe_frame(load_top3_position)
    if combo_row is None or gate is None or gate.empty:
        return """# {combo} 参数范围测试面板

> 生成时间：""" + TODAY + """
> 当前状态：已建立文档骨架，待回填门区间、Stage、仓位和止损扫描结果
"""
    current_rows = [
        ["策略组合", "{combo}"],
        ["当前组合门", combo_row["current_variant"]],
        ["Stage 参数", combo_row["stage_params"]],
        ["仓位单位", combo_row["units"]],
        ["手数", combo_row["lots"]],
        ["聚焦周期", combo_row["focus_tf"]],
        ["主推荐止损范围", combo_row["stop_main"]],
        ["次优止损范围", combo_row["stop_second"]],
    ]
    gate_rows = []
    for _, row in gate.head(6).iterrows():
        gate_rows.append([
            row["gate_param"], int(row["trades"]), f"{{float(row['wr']):.2f}}%",
            f"{{float(row['pf']):.4f}}", f"+{{float(row['ev']):.4f}}pt", f"{{float(row['test_pf']):.4f}}",
        ])
    pos_rows = []
    if pos is not None:
        for _, row in pos.iterrows():
            pos_rows.append([row["units"], row["lots"], f"{{float(row['pf']):.4f}}", f"+{{float(row['ev']):.4f}}pt"])
    return """# {combo} 参数范围测试面板

> 生成时间：""" + TODAY + """

## 当前基准口径

""" + md_table(["项目", "当前值"], current_rows) + """

## 组合门范围细扫

""" + md_table(["门参数", "交易数", "胜率", "PF", "EV", "验证PF"], gate_rows) + """

## 仓位档位

""" + md_table(["仓位单位", "手数", "PF", "EV"], pos_rows or [["待补", "待补", "待补", "待补"]]) + """
"""


def build_validation_readme() -> str:
    files = sorted(path.name for path in VALIDATION_DIR.glob("*.csv"))
    if not files:
        return """# {combo} 验证数据

## 当前状态

- 本地尚未写入 CSV。
- 执行 `scripts/validate/export_validation_bundle.py` 后会自动回填。
"""
    return "# {combo} 验证数据\\n\\n## 当前文件\\n\\n" + "\\n".join("- `" + item + "`" for item in files)


def build_processed_readme() -> str:
    files = ["raw_m30_standardized.csv"] + [frame.lower() + "_bars.csv" for frame in FRAMES] + [CONTEXT_FILE]
    return "# {combo} 处理后数据\\n\\n## 当前包含\\n\\n" + "\\n".join("- `" + item + "`" for item in files)


def main() -> None:
    write_text("策略说明.md", build_strategy_doc())
    write_text("参数范围测试面板.md", build_panel_doc())
    write_text("Stage1_Stage2测试结果.md", build_stage_doc())
    write_text("StopSpec严格认证结果.md", build_stop_doc())
    write_text("Layer1严格认证结果.md", """# {combo} Layer1 严格认证结果

> 生成时间：""" + TODAY + """

## 当前状态

- 目录骨架已建立。
- 待按 H1 模板补完整扫描范围、候选阈值、采用值和放弃原因。
""")
    write_text("Layer2验证过程.md", """# {combo} Layer2 验证过程

> 生成时间：""" + TODAY + """

## 当前状态

- 目录骨架已建立。
- 待补 `pre_cross / cross / post_n` 的测试过程、参数范围和最终采用值。
""")
    write_text("Layer3严格认证结果.md", """# {combo} Layer3 严格认证结果

> 生成时间：""" + TODAY + """

## 当前状态

- 目录骨架已建立。
- 待补 Bias_5 阈值测试、验证集表现和当前采用值。
""")
    write_text("data/validation/README.md", build_validation_readme())
    write_text("data/processed/README.md", build_processed_readme())
    print("Rebuilt core docs for {combo}.")


if __name__ == "__main__":
    main()
'''


def build_bundle_py(combo: str) -> str:
    return '''# -*- coding: utf-8 -*-
"""Build the complete local strategy package."""
from __future__ import annotations

import runpy
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]


def run_script(*parts: str) -> None:
    runpy.run_path(str(SCRIPT_DIR.joinpath(*parts)), run_name="__main__")


def main() -> None:
    run_script("data_source", "sync_raw_data.py")
    run_script("prepare", "build_processed_data.py")
    run_script("signals", "export_signal_candidates.py")
    run_script("validate", "export_validation_bundle.py")
    run_script("bundle", "build_docs.py")
    print("Built full strategy bundle.")


if __name__ == "__main__":
    main()
'''


def project_manifest(combo: str) -> str:
    dir_name = strategy_dir_name(combo)
    return f"""# {combo} 项目文件归类清单

> 生成时间：2026-07-05

## 文档

- `策略说明.md`
- `参数范围测试面板.md`
- `Layer1严格认证结果.md`
- `Layer2验证过程.md`
- `Layer3严格认证结果.md`
- `Stage1_Stage2测试结果.md`
- `StopSpec严格认证结果.md`

## 数据目录

- `data/raw`
- `data/processed`
- `data/signals`
- `data/validation`

## 脚本目录

- `scripts/data_source`
- `scripts/prepare`
- `scripts/signals`
- `scripts/validate`
- `scripts/bundle`

## 当前说明

- 该目录由批量脚手架生成器建立。
- 后续按 `H1_M30_H4策略` 模板补齐正式过程文档与复跑结果。
- 当前主线仍以 `30m2H策略` 和 `auto_trade/30m2H_Strategy_EA.mq5` 为最高优先级。
"""


def scaffold_strategy(item: dict[str, object]) -> None:
    combo = str(item["combo"])
    frames = list(item["frames"])  # type: ignore[arg-type]
    dir_name = strategy_dir_name(combo)
    strategy_dir = ROOT / dir_name
    scripts_dir = strategy_dir / "scripts"

    for sub in [
        strategy_dir / "data" / "raw",
        strategy_dir / "data" / "processed",
        strategy_dir / "data" / "signals",
        strategy_dir / "data" / "validation",
        scripts_dir / "data_source",
        scripts_dir / "prepare",
        scripts_dir / "signals",
        scripts_dir / "validate",
        scripts_dir / "bundle",
    ]:
        sub.mkdir(parents=True, exist_ok=True)

    raw_src = ROOT / "base_data" / "XAUUSDm30.csv"
    readme_src = ROOT / "base_data" / "README.md"
    if raw_src.exists():
        shutil.copy2(raw_src, strategy_dir / "data" / "raw" / raw_src.name)
    if readme_src.exists():
        shutil.copy2(readme_src, strategy_dir / "data" / "raw" / readme_src.name)

    write_md(strategy_dir / "策略说明.md", current_strategy_doc(combo, frames))
    write_md(strategy_dir / "Layer1严格认证结果.md", pending_doc("Layer1 严格认证结果", combo, [
        "当前仅完成策略工作区骨架建立。",
        "待补 Layer 1 阈值扫描、采用值、验证表现和放弃方案。",
    ]))
    write_md(strategy_dir / "Layer2验证过程.md", pending_doc("Layer2 验证过程", combo, [
        "当前仅完成策略工作区骨架建立。",
        "待补 pre_cross / cross / post_n 的参数测试和最终采用值。",
    ]))
    write_md(strategy_dir / "Layer3严格认证结果.md", pending_doc("Layer3 严格认证结果", combo, [
        "当前仅完成策略工作区骨架建立。",
        "待补 Bias_5 阈值扫描、验证集表现和当前采用值。",
    ]))
    write_md(strategy_dir / "Stage1_Stage2测试结果.md", pending_doc("Stage1 / Stage2 测试结果", combo, [
        "当前仅完成策略工作区骨架建立。",
        "待补 Stage 参数扫描结果和当前采用值。",
    ]))
    write_md(strategy_dir / "StopSpec严格认证结果.md", pending_doc("StopSpec 严格认证结果", combo, [
        "当前仅完成策略工作区骨架建立。",
        "待补止损扫描网格、推荐区间和次优区间。",
    ]))
    write_md(strategy_dir / "参数范围测试面板.md", pending_doc("参数范围测试面板", combo, [
        "当前仅完成策略工作区骨架建立。",
        "待补组合门区间、Stage、仓位和止损区间总表。",
    ]))
    write_md(strategy_dir / "项目文件归类清单.md", project_manifest(combo))
    write_md(strategy_dir / "data" / "raw" / "README.md", raw_readme(combo, frames))
    write_md(strategy_dir / "data" / "processed" / "README.md", processed_readme(combo, frames))
    write_md(strategy_dir / "data" / "signals" / "README.md", signals_readme(combo))
    write_md(strategy_dir / "data" / "validation" / "README.md", validation_readme(combo))
    write_md(strategy_dir / "scripts" / "README.md", scripts_readme(combo, frames))

    write_py(scripts_dir / (common_module_name(combo) + ".py"), common_py(combo, frames))
    write_py(scripts_dir / "data_source" / "sync_raw_data.py", sync_raw_py(combo))
    write_py(scripts_dir / "prepare" / "build_processed_data.py", build_processed_py(combo))
    write_py(scripts_dir / "signals" / "export_signal_candidates.py", signals_py(combo))
    write_py(scripts_dir / "validate" / "export_validation_bundle.py", validate_py(combo))
    write_py(scripts_dir / "bundle" / "build_docs.py", build_docs_py(combo, frames))
    write_py(scripts_dir / "bundle" / "build_strategy_bundle.py", build_bundle_py(combo))


def main() -> None:
    for item in STRATEGIES:
        scaffold_strategy(item)
        print("Scaffolded " + strategy_dir_name(str(item["combo"])))


if __name__ == "__main__":
    main()
