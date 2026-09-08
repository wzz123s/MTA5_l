# -*- coding: utf-8 -*-
"""Install or verify the strategy-dedicated raw input file."""
from __future__ import annotations


import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_workspace_common import (  # noqa: E402
    RAW_M30_FILE,
    RAW_SOURCE_MANIFEST,
    STRATEGY_NAME,
    ensure_dirs,
    ensure_strategy_raw_data_ready,
    install_strategy_raw_source,
    write_text,
)


def write_raw_readme(manifest: dict) -> None:
    write_text(
        "data/raw/README.md",
        f"""# {STRATEGY_NAME} 原始数据

## 固定规则

- 每套策略必须使用自己的原始行情文件生成，不允许直接复用其他策略或 `黄金/30m2H策略/参考实现工程/base_data` 的 raw 文件。
- 本目录必须保留 `raw_source_manifest.json`，记录来源路径、hash、大小和策略名。
- 如果缺少 manifest，后续 `prepare/signals/validate` 结果只能视为旧迁移产物，不能视为正式策略认证结果。

## 当前源

- raw file: `{RAW_M30_FILE.name}`
- manifest: `{RAW_SOURCE_MANIFEST.name}`
- source id: `{manifest.get("source_id", "")}`
- source path: `{manifest.get("source_path", "")}`
- source sha256: `{manifest.get("source_sha256", "")}`
""",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Strategy-dedicated XAUUSDm30.csv source file.")
    parser.add_argument("--source-id", default="", help="Optional stable source label, e.g. broker/date/export id.")
    args = parser.parse_args(argv)

    ensure_dirs()
    if args.source:
        manifest = install_strategy_raw_source(Path(args.source), source_id=args.source_id)
        action = "installed"
    else:
        manifest = ensure_strategy_raw_data_ready()
        action = "verified"

    write_raw_readme(manifest)
    print(f"{STRATEGY_NAME}: raw data {action}; source_id={manifest.get('source_id', '')}")


if __name__ == "__main__":
    main()
