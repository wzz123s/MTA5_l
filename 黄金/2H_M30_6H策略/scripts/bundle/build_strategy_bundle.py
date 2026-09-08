# -*- coding: utf-8 -*-
"""Build the complete local 2H_M30_6H strategy package."""
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
    run_script("validate", "export_advanced_validation.py")
    run_script("bundle", "build_docs.py")
    print("Built full 2H_M30_6H strategy bundle.")


if __name__ == "__main__":
    main()
