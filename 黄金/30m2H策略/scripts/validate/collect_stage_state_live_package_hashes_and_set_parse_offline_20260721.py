from __future__ import annotations


import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_live_package_hashes_and_set_parse_offline_20260721"

EX5_PATH = ROOT / "auto_trade" / "30m2H_Strategy_EA.ex5"
SET_PATH = ROOT / "auto_trade" / "30m2H_Strategy_EA.stage_state_frozen_20260718.set"
HASH_APPROVAL = "USER_APPROVES_HASHING_REVIEWED_LIVE_PACKAGE_MANIFEST_ONLY"
SET_APPROVAL = "USER_APPROVES_OFFLINE_PARSE_REVIEWED_SET_TEMPLATE_ONLY"


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_set(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.split("||", 1)[0].strip()
    return values


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")
    missing = [str(path) for path in [EX5_PATH, SET_PATH] if not path.exists()]
    if missing:
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_live_package_hashes_and_set_parse_offline",
            "status": "not_collected_missing_authorized_files",
            "missing_files": ";".join(missing),
            "ready_to_live_trade": False,
        }
        write_json(OUT_DIR / "live_package_hashes_and_set_parse_offline_decision.json", decision)
        write_csv(OUT_DIR / "live_package_hashes_and_set_parse_offline_decision.csv", [decision], list(decision.keys()))
        print("status=not_collected_missing_authorized_files")
        return 1

    hash_rows = []
    for artifact, path in [("live_ea_ex5", EX5_PATH), ("live_set_template", SET_PATH)]:
        hash_rows.append(
            {
                "artifact": artifact,
                "path": rel(path),
                "sha256": sha256(path),
                "verified_by": "codex_offline_hash_after_user_approval",
                "verified_at": collected_at,
                "approval_phrase": HASH_APPROVAL,
                "file_size": path.stat().st_size,
                "last_write_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "collection_mode": "offline_file_hash",
                "mt5_accessed": False,
                "runner_executed": False,
                "orders_placed": False,
                "live_set_switched": False,
                "ready_to_live_trade": False,
            }
        )

    set_values = parse_set(SET_PATH)
    parsed_set = {
        "set_path": rel(SET_PATH),
        "InpSimMode": set_values.get("InpSimMode", ""),
        "InpExportCSV": set_values.get("InpExportCSV", ""),
        "InpExportTradeLedger": set_values.get("InpExportTradeLedger", ""),
        "InpSymbol": set_values.get("InpSymbol", ""),
        "InpRiskPct": set_values.get("InpRiskPct", ""),
        "InpUseDynamicLots": set_values.get("InpUseDynamicLots", ""),
        "InpMinLots": set_values.get("InpMinLots", ""),
        "InpMaxLots": set_values.get("InpMaxLots", ""),
        "InpSimMode_is_false": set_values.get("InpSimMode", "").lower() == "false",
        "approval_phrase": SET_APPROVAL,
        "collection_mode": "offline_set_text_parse",
        "mt5_accessed": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "ready_to_live_trade": False,
        "parsed_at": collected_at,
    }

    decision = {
        "decision_time": collected_at,
        "check_id": "stage_state_live_package_hashes_and_set_parse_offline",
        "status": "live_package_hashes_and_set_parse_collected_offline_live_blocked",
        "hash_rows": len(hash_rows),
        "set_parse_collected": True,
        "ex5_path": rel(EX5_PATH),
        "set_path": rel(SET_PATH),
        "InpSimMode": parsed_set["InpSimMode"],
        "InpExportCSV": parsed_set["InpExportCSV"],
        "InpExportTradeLedger": parsed_set["InpExportTradeLedger"],
        "mt5_accessed": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "ready_to_live_trade": False,
        "recommended_next_action": "review_offline_hash_and_set_parse_then_update_closeout",
    }

    write_csv(
        OUT_DIR / "live_package_hashes.csv",
        hash_rows,
        [
            "artifact",
            "path",
            "sha256",
            "verified_by",
            "verified_at",
            "approval_phrase",
            "file_size",
            "last_write_time",
            "collection_mode",
            "mt5_accessed",
            "runner_executed",
            "orders_placed",
            "live_set_switched",
            "ready_to_live_trade",
        ],
    )
    write_json(OUT_DIR / "parsed_live_set_template.json", parsed_set)
    write_csv(OUT_DIR / "live_package_hashes_and_set_parse_offline_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_package_hashes_and_set_parse_offline_decision.json", decision)
    lines = [
        "# Live Package Hashes And Set Parse Offline Collection",
        "",
        f"- status: `{decision['status']}`",
        f"- hash_rows: `{decision['hash_rows']}`",
        f"- set_path: `{decision['set_path']}`",
        f"- InpSimMode: `{decision['InpSimMode']}`",
        "- collection boundary: offline file hash and offline set text parse only",
        "- mt5_accessed: `False`",
        "- runner_executed: `False`",
        "- orders_placed: `False`",
        "- live_set_switched: `False`",
        "- ready_to_live_trade: `False`",
        "",
    ]
    (OUT_DIR / "live_package_hashes_and_set_parse_offline.md").write_text("\n".join(lines), encoding="utf-8-sig")
    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
