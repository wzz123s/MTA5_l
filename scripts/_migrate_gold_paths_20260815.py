# -*- coding: utf-8 -*-
"""Migrate gold strategy paths after moving root folders into 黄金\\.

Applied to: scripts/ (shared), 黄金\\{1H_M30_4H策略,2H_M30_6H策略,30m2H策略},
oil strategy scripts, 项目文档. Rewrites:
  T1 bootstrap path list (+黄金/* +原油/* globs)
  T2 absolute F:\\use_code\\MTA5_l\\<gold> -> ...\\黄金\\<gold>
  T3 ROOT / "<gold策略>" joins -> ROOT / "黄金" / "<gold策略>"
  T3b ROOT / f"{X}策略" joins -> ROOT / "黄金" / f"{X}策略"
  T4a ROOT = Path(__file__).resolve().parents[N] -> Path(r"F:\\use_code\\MTA5_l")
  T5 relative "<gold策略>/" refs -> "黄金/<gold策略>/"
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(r"F:\use_code\MTA5_l")
GOLD = ["1H_M30_4H策略", "2H_M30_6H策略", "30m2H策略"]
EXCLUDE_PARTS = ("__pycache__", "参考实现工程", "归档", "\\data\\", "/data/", "_backup")
EXCLUDE_FILES = {"_reorg_scripts_20260815.py", "_migrate_gold_paths_20260815.py"}
EXT = {".py", ".ps1", ".bat", ".cmd", ".json", ".set", ".ini", ".md"}

STRATEGY_REL = re.compile(r'ROOT\s*/\s*"(data|auto_trade|说明文档|raw_source_manifest|validation|signals|processed)"')
WS_REL = re.compile(
    r'ROOT\s*/\s*"(1H_M30_4H策略|2H_M30_6H策略|30m2H策略|黄金|原油|USOIL|项目文档|observation_dashboard|scripts)"'
    r'|ROOT\s*/\s*f"\{(STRATEGY|STRATEGY_NAME|strategy)\}策略"'
)
ROOT_DEF = re.compile(r'ROOT = Path\(__file__\)\.resolve\(\)\.parents\[\d+\]')
REL_REF = re.compile(r"(?<!黄金[\\/])(1H_M30_4H策略|2H_M30_6H策略|30m2H策略)([\\/])")

T1_OLD = '_ROOT / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*")'
T1_NEW = (
    '_ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), '
    '*_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")'
)


def iter_targets() -> list[Path]:
    dirs = [
        ROOT / "scripts",
        ROOT / "黄金" / "1H_M30_4H策略",
        ROOT / "黄金" / "2H_M30_6H策略",
        ROOT / "黄金" / "30m2H策略",
        ROOT / "原油2H策略",
        ROOT / "USOIL_30m2H策略",
        ROOT / "USOIL_1H_M30_4H策略",
        ROOT / "USOIL_2H_M30_6H策略",
        ROOT / "项目文档",
    ]
    out: list[Path] = []
    for d in dirs:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXT:
                continue
            rel = p.as_posix()
            if p.name in EXCLUDE_FILES or any(x in rel for x in EXCLUDE_PARTS):
                continue
            out.append(p)
    return out


def classify(path: Path) -> str:
    text, _ = _read_text(path)
    has_sr = bool(STRATEGY_REL.search(text))
    has_ws = bool(WS_REL.search(text))
    if has_sr and has_ws:
        return "mixed"
    if has_sr:
        return "strategy_rel"
    if has_ws:
        return "ws_rel"
    return "none"


def _read_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            return data.decode(enc), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("latin-1"), "latin-1"


def transform(path: Path, kind: str) -> list[str]:
    changed: list[str] = []
    text, enc = _read_text(path)
    orig = text

    # T2 absolute paths (double-backslash first)
    for s in GOLD:
        text = text.replace(f"F:\\\\use_code\\\\MTA5_l\\\\{s}", f"F:\\\\use_code\\\\MTA5_l\\\\黄金\\\\{s}")
        text = text.replace(f"F:\\use_code\\MTA5_l\\{s}", f"F:\\use_code\\MTA5_l\\黄金\\{s}")
        text = text.replace(f"F:/use_code/MTA5_l/{s}", f"F:/use_code/MTA5_l/黄金/{s}")

    # T3 literal ROOT joins
    for s in GOLD:
        text = text.replace(f'ROOT / "{s}"', f'ROOT / "黄金" / "{s}"')

    # T3b f-string ROOT joins
    for var in ("STRATEGY", "STRATEGY_NAME", "strategy"):
        text = text.replace(f'ROOT / f"{{{var}}}策略"', f'ROOT / "黄金" / f"{{{var}}}策略"')

    # T4a ROOT definition
    if kind in ("ws_rel", "mixed"):
        text = ROOT_DEF.sub(r'ROOT = Path(r"F:\\use_code\\MTA5_l")', text)

    # T1 bootstrap
    text = text.replace(T1_OLD, T1_NEW)

    # T5 relative refs
    text = REL_REF.sub(lambda m: f"黄金/{m.group(1)}{m.group(2)}", text)

    if text != orig:
        path.write_bytes(text.encode(enc))
        changed = ["T1", "T2", "T3", "T3b", "T4a", "T5"]
    return changed


def main() -> None:
    stats: dict[str, int] = {}
    for p in iter_targets():
        kind = classify(p)
        transform(p, kind)
        stats[kind] = stats.get(kind, 0) + 1
        print(f"{kind:14s} {p}")
    print("\nclassified:", stats)


if __name__ == "__main__":
    main()
