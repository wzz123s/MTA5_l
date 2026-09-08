# -*- coding: utf-8 -*-
"""Compatibility wrapper for rebuilding H1_M30_H4 docs."""
from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "bundle" / "build_docs.py"), run_name="__main__")
