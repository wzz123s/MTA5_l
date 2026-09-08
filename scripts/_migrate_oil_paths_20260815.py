# -*- coding: utf-8 -*-
"""Migrate USOIL strategy paths after moving root folders into 原油\\.

Handles the 8 oil strategy folders: USOIL_30m2H策略 / USOIL_1H_M30_4H策略 /
USOIL_2H_M30_6H策略 / 原油金叉实验_20260815 / 原油2H策略 / 原油4H门策略 /
原油6H门策略 / 原油8H门策略.
"""
from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(r"F:\use_code\MTA5_l")
OIL = [
    "USOIL_30m2H策略",
    "USOIL_1H_M30_4H策略",
    "USOIL_2H_M30_6H策略",
    "原油金叉实验_20260815",
    "原油2H策略",
    "原油4H门策略",
    "原油6H门策略",
    "原油8H门策略",
]
EXCLUDE_PARTS = ("__pycache__", "参考实现工程", "归档", "\\data\\", "/data/", "_backup", "_待清理")
EXCLUDE_FILES = {"_migrate_oil_paths_20260815.py", "_migrate_gold_paths_20260815.py"}
EXT = {".py", ".ps1", ".bat", ".cmd", ".json", ".set", ".ini", ".md"}

STRATEGY_REL = re.compile(r'ROOT\s*/\s*"(data|auto_trade|说明文档|raw_source_manifest|validation|signals|processed)"')
WS_REL = re.compile(
    r'ROOT\s*/\s*"(USOIL_[A-Za-z0-9_]+策略|原油[234678]H门策略|原油2H策略|原油金叉实验_20260815|scripts|黄金|原油|项目文档)"'
)
ROOT_DEF = re.compile(r'ROOT = Path\(__file__\)\.resolve\(\)\.parents\[\d+\]')
REL_REF = re.compile(
    r"(?<!原油[\\/])(USOIL_30m2H策略|USOIL_1H_M30_4H策略|USOIL_2H_M30_6H策略|"
    r"原油金叉实验_20260815|原油2H策略|原油4H门策略|原油6H门策略|原油8H门策略)([\\/])"
)


def iter_targets() -> list[pathlib.Path]:
    dirs = [ROOT / "原油", ROOT / "scripts", ROOT / "项目文档", ROOT / "observation_dashboard"]
    out: list[pathlib.Path] = []
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


def read_text(path: pathlib.Path) -> tuple[str, str]:
    data = path.read_bytes()
    for enc in ("utf-8", "gbk"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1"), "latin-1"


def classify(text: str) -> str:
    has_sr = bool(STRATEGY_REL.search(text))
    has_ws = bool(WS_REL.search(text))
    if has_sr and has_ws:
        return "mixed"
    if has_sr:
        return "strategy_rel"
    if has_ws:
        return "ws_rel"
    return "none"


def transform(path: pathlib.Path) -> None:
    text, enc = read_text(path)
    orig = text
    kind = classify(text)

    # T2 absolute paths
    for s in OIL:
        text = text.replace(f"F:\\\\use_code\\\\MTA5_l\\\\{s}", f"F:\\\\use_code\\\\MTA5_l\\\\原油\\\\{s}")
        text = text.replace(f"F:\\use_code\\MTA5_l\\{s}", f"F:\\use_code\\MTA5_l\\原油\\{s}")
        text = text.replace(f"F:/use_code/MTA5_l/{s}", f"F:/use_code/MTA5_l/原油/{s}")

    # T3 literal ROOT joins
    for s in OIL:
        text = text.replace(f'ROOT / "{s}"', f'ROOT / "原油" / "{s}"')

    # T3d dynamic joins (oil strategy names flow through variables)
    text = text.replace('ROOT / cfg["name"]', 'ROOT / "原油" / cfg["name"]')
    text = text.replace("ROOT / cfg['name']", "ROOT / '原油' / cfg['name']")
    text = re.sub(r'ROOT / name(?![A-Za-z0-9_])', 'ROOT / "原油" / name', text)

    # T4a ROOT definition
    if kind in ("ws_rel", "mixed"):
        text = ROOT_DEF.sub(r'ROOT = Path(r"F:\\use_code\\MTA5_l")', text)

    # T5 relative refs
    text = REL_REF.sub(lambda m: f"原油/{m.group(1)}{m.group(2)}", text)

    if text != orig:
        path.write_bytes(text.encode(enc))
        print(f"{kind:12s} {path}")


def main() -> None:
    changed = 0
    for p in iter_targets():
        before = p.read_bytes()
        transform(p)
        if p.read_bytes() != before:
            changed += 1
    print("changed:", changed)


if __name__ == "__main__":
    main()
