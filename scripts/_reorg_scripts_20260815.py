# -*- coding: utf-8 -*-
"""Move scripts/ into per-strategy purpose folders and patch sys.path bootstrap."""
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(r"F:\use_code\MTA5_l")
SRC = ROOT / "scripts"

# strategy scripts dir -> (purpose subfolder, [files])
PLAN = {
    ROOT / "1H_M30_4H策略" / "scripts": {
        "signals": [
            "replay_1h_bias55_h1_stop_optimization.py",
            "replay_1h_delayed_entry_sma13_stop.py",
            "replay_1h_h4_bias_opportunity_pool.py",
            "replay_1h_h4_bias_stop_range_scan.py",
            "replay_1h_h4_high_bias55_opportunity.py",
            "replay_1h_hybrid_entry_stop.py",
            "replay_1h_way_momentum_filter_scan.py",
        ],
        "validate": [
            "validate_1h_way_momentum_candidates.py",
            "validate_1h_abc_2020_2026.py",
            "validate_1h_improved_20260815.py",
            "export_1h_current_candidate_ea_alignment.py",
            "walkforward_and_weak_analysis_1h_abc.py",
            "optimize_1h_abc_20260815.py",
            "optimize_1h_guard_20260815.py",
            "optimize_1h_short_side_filters.py",
        ],
        "research": [
            "experiment_1h_m30_4h_variants_20260813.py",
            "experiment_1h_m30_4h_combined_20260813.py",
            "analyze_1h_4h_bias55_threshold_2_6.py",
            "analyze_bias_threshold_grid.py",
            "analyze_signed_bias.py",
            "analyze_strategy_direction.py",
        ],
        "monitor": ["monitor_1h_abc_paper.py"],
        "deploy": ["deploy_1h_abc_chart.py"],
    },
    ROOT / "2H_M30_6H策略" / "scripts": {
        "validate": [
            "gate_variant_2h_bias5_magnitude.py",
            "generate_2h_abc_expected_ledger.py",
            "compare_2h_abc_tester_vs_python.py",
        ],
        "deploy": ["deploy_2h_abc_chart.py", "run_2h_abc_tester_smoke.py"],
    },
    ROOT / "30m2H策略" / "scripts": {
        "signals": ["combined_abc_30m2h_2h_20260814.py"],
        "deploy": ["deploy_30m2h_abc_chart.py"],
    },
    ROOT / "原油" / "原油2H策略" / "scripts": {
        "data_source": [
            "pull_usoil_strategies.py",
            "pull_usoil_gate_strategies.py",
            "pull_usoil_2h_standalone.py",
        ],
        "signals": [
            "usoil_golden_cross_20260815.py",
            "usoil_large_tf_golden_cross_20260815.py",
            "usoil_2h_execute_other_tf_20260815.py",
            "usoil_2h_with_6h8h_gate_20260815.py",
            "usoil_2h_cross_postn_gate_20260815.py",
            "usoil_segment_len_extreme_way_20260815.py",
            "usoil_1h_prev_segment_filter_20260815.py",
            "usoil_1h_prev_seg_sma13_20260815.py",
            "usoil_1h_golden_cross_validate_20260815.py",
            "usoil_4h_opt_6h8h_diag_20260815.py",
            "usoil_4h6h8h_strategies_20260815.py",
            "combined_abc_usoil_20260815.py",
        ],
        "validate": [
            "validate_usoil_2h_standalone.py",
            "validate_usoil_gate_strategy.py",
            "usoil_2h_confirm_oos_20260815.py",
        ],
        "research": ["optimize_usoil_20260815.py"],
    },
}

BOOTSTRAP = '''
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\\use_code\\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)
'''


def _find_insert_index(lines: list[str]) -> int:
    """Index where the bootstrap block is inserted without breaking syntax.

    Prefer after any `from __future__` import (it must stay near the top of
    the file); fall back to right after the coding line or the file start.
    """
    for idx, line in enumerate(lines):
        if line.strip().startswith("from __future__"):
            return idx + 1
    for idx, line in enumerate(lines[:4]):
        if line.strip().startswith("# -*- coding"):
            return idx + 1
    return 0


def _bootstrap_span(lines: list[str]) -> tuple[int, int] | None:
    """(start, end) line indices of an existing bootstrap block, else None."""
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == "import sys as _sys":
            start = idx
            break
    if start is None:
        return None
    end = start
    while end < len(lines):
        if "_sys.path.insert(0, _s)" in lines[end]:
            return start, end
        end += 1
    return None


def patch_bootstrap(path: Path) -> bool:
    """Insert (or repair) the sys.path bootstrap block in a moved script."""
    lines = path.read_text(encoding="utf-8").split("\n")
    span = _bootstrap_span(lines)
    if span:
        start, end = span
        if start > 0 and lines[start - 1].strip() == "":
            start -= 1
        del lines[start : end + 1]
    insert_at = _find_insert_index(lines)
    lines.insert(insert_at, BOOTSTRAP)
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> None:
    moved = 0
    for strategy_scripts, purposes in PLAN.items():
        for purpose, files in purposes.items():
            dst_dir = strategy_scripts / purpose
            dst_dir.mkdir(parents=True, exist_ok=True)
            for name in files:
                src = SRC / name
                if not src.exists():
                    print("MISSING:", name)
                    continue
                dst = dst_dir / name
                shutil.move(str(src), str(dst))
                if name.endswith(".py"):
                    patched = patch_bootstrap(dst)
                    print(f"{strategy_scripts.name}/scripts/{purpose}/{name}" + (" [bootstrap]" if patched else ""))
                moved += 1
    print("moved:", moved)


if __name__ == "__main__":
    main()
