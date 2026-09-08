# -*- coding: utf-8 -*-
"""定时总览推送: 刷新 qq_snapshot 并推送人类摘要到 QQ (受 qq_push_config.json 控制)。"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from qq_snapshot import build_snapshot, build_text  # noqa: E402


def main() -> int:
    snap = build_snapshot()
    mt5 = snap.get('mt5_live') or {}
    positions = mt5.get('open_positions') or []
    deals = (mt5.get('deal_summary') or {}).get('deals_count', 0)
    # 空仓静默: 无持仓且无近期成交则不推送 (仅打印摘要)
    if not positions and not deals:
        print('[qq_digest] 空仓且无近期成交, 跳过 QQ 推送')
        return 0
    text = build_text(snap)
    print(text)
    cfgp = ROOT / 'scripts' / 'qq_push_config.json'
    try:
        cfg = json.loads(cfgp.read_text(encoding='utf-8'))
    except Exception:
        cfg = {}
    if not (cfg.get('enabled') and cfg.get('targetId')):
        print('[qq_digest] 未启用 QQ 推送 (enabled/targetId)，仅输出摘要')
        return 0
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as tf:
            tf.write(text)
            tmp = tf.name
        node = str(cfg.get('node_path') or 'node')
        subprocess.run([node, str(ROOT / 'scripts' / 'notify_qq.mjs'), '--file', tmp], check=False)
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
