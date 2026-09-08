# -*- coding: utf-8 -*-
"""Copy combo-specific validation outputs into the local strategy folder."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h1_m30_h4_common import COMBO, GLOBAL_VALIDATION_DIR, VALIDATION_DIR, ensure_dirs, export_csv
from h1_m30_h4_common import load_capital_metrics, load_combined_summary, load_final_summary, load_gate_scan
from h1_m30_h4_common import load_stop_scan, load_top3_position, load_top3_stage, read_csv_with_fallback


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
    _filter_and_export("组合门范围细扫_中文.csv", "combo_gate_range_scan_raw.csv")
    _filter_and_export("组合止损范围测试_中文.csv", "combo_stop_range_scan_raw.csv")
    _filter_and_export("组合止损范围推荐_中文.csv", "combo_stop_range_pick_raw.csv")
    _filter_and_export("组合参数总表_门区间_止损区间_中文.csv", "combo_combined_summary_raw.csv")
    _filter_and_export("组合最终资金指标_中文_utf8.csv", "combo_final_capital_metrics_raw_utf8.csv")

    export_csv(load_final_summary(local_first=False).to_frame().T, VALIDATION_DIR / "combo_final_best_summary_clean.csv")
    export_csv(load_combined_summary(local_first=False).to_frame().T, VALIDATION_DIR / "combo_combined_summary.csv")
    export_csv(load_capital_metrics(local_first=False).to_frame().T, VALIDATION_DIR / "combo_final_capital_metrics.csv")
    export_csv(load_gate_scan(local_first=False), VALIDATION_DIR / "combo_gate_range_scan.csv")
    export_csv(load_stop_scan(local_first=False), VALIDATION_DIR / "combo_stop_range_scan.csv")
    export_csv(load_top3_stage(local_first=False), VALIDATION_DIR / "combo_top3_stage12.csv")
    export_csv(load_top3_position(local_first=False), VALIDATION_DIR / "combo_top3_position.csv")

    manifest_lines = []
    for path in sorted(VALIDATION_DIR.glob("*.csv")):
        manifest_lines.append(f"- `{path.name}`")
    (VALIDATION_DIR / "README.md").write_bytes(
        ("# H1_M30_H4 验证数据\n\n## 当前文件\n\n" + "\n".join(manifest_lines) + "\n").encode("utf-8-sig")
    )
    print(f"Exported validation bundle for {COMBO}.")


if __name__ == "__main__":
    main()
