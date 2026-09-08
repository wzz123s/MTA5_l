# -*- coding: utf-8 -*-
"""Copy required raw inputs into the local H1_M30_H4 strategy folder."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h1_m30_h4_common import RAW_DIR, ROOT, copy_source_file, ensure_dirs, write_text


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
        copied.append(f"- `{src.name}` <- `{src}`")
    manifest = "\n".join(copied)
    write_text(
        "data/raw/README.md",
        f"""# H1_M30_H4 原始数据

## 当前包含

{manifest}

## 说明

- `XAUUSDm30.csv` 是本策略重建 30M / 1H / 4H 上下文的基础原始 K 线。
- `README.md` 保留上游 `base_data` 目录的口径说明，便于后续复核来源。
""",
    )
    print("Synced raw data into H1_M30_H4 strategy folder.")


if __name__ == "__main__":
    main()
