# -*- coding: utf-8 -*-
"""策略变化监听：新持仓 / 平仓 / 新信号 / SimMode 虚拟信号 → 通知（可配微信）。

状态化：上次运行结果存 state_file；本次对比差异，仅对"新变化"发提醒，幂等可重复跑。
推荐频率：持仓变化用 1-5 分钟任务；新信号依赖约 30 分钟的 dashboard 快照刷新（快照不刷新则无新信号）。

用法：
    python scripts/watch_signal_alerts.py            # 常规一轮
    python scripts/watch_signal_alerts.py --dry-run  # 只打印/日志不推送
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

CONFIG = ROOT / "scripts" / "alerts_config.json"
STATE = ROOT / "scripts" / "alerts" / "watch_state.json"

# magic → 策略（与 monitor_all_strategies 一致）
MAGIC_STRAT = {
    **{312026: "1H_M30_4H", 312036: "1H_M30_4H"},
    **{302036: "30m2H", 302037: "30m2H", 302038: "30m2H", 302039: "30m2H", 352036: "30m2H"},
    342036: "2H_M30_6H", 362036: "USOIL2H", 362137: "USOIL4H",
    411101: "Gold_DataEvent", 411102: "Oil_DataEvent",
    **{372036: "BiasReversal", 372037: "BiasReversal"},
}


def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_positions(cfg: dict):
    """返回 {ticket: (magic, strat, dir, open_price)}；MT5 不可用返回 None。"""
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize(path=cfg.get("main_terminal")):
            return None
        pos = mt5.positions_get() or []
        out = {}
        for p in pos:
            if p.symbol not in ("XAUUSDm", "USOILm"):
                continue
            out[str(p.ticket)] = {
                "magic": int(p.magic),
                "strat": MAGIC_STRAT.get(int(p.magic), f"other_{p.magic}"),
                "dir": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                "open": float(p.price_open),
                "sl": float(p.sl) if p.sl else 0,
                "profit": float(p.profit),
            }
        mt5.shutdown()
        return out
    except Exception as e:
        print("[watch] MT5 read failed:", e)
        return None


def latest_snapshot_signals(cfg: dict) -> dict:
    """读 dashboard 各策略 trades_snapshot.csv 的最新 signal_time（快照刷新周期内不变）。"""
    dash = Path(cfg.get("dashboard", ROOT / "observation_dashboard"))
    out = {}
    for strat_dir in dash.iterdir():
        if not strat_dir.is_dir():
            continue
        snap = strat_dir / "trades_snapshot.csv"
        if not snap.exists():
            continue
        try:
            import pandas as pd
            df = pd.read_csv(snap, parse_dates=["signal_time"])
            if df.empty:
                continue
            df = df.sort_values("signal_time")
            last = df.iloc[-1]
            out[strat_dir.name] = {
                "last_signal_time": str(last["signal_time"]),
                "dir": str(last.get("dir", "")),
                "mode": str(last.get("mode", "")),
            }
        except Exception:
            continue
    return out


def sim_virtual_signals(cfg: dict) -> list:
    """SimMode（调试终端）signals_export 中 decision=SIGNAL 的行（虚拟信号）。"""
    sim = Path(cfg.get("sim_files", ""))
    sig = sim / "30m2H_strategy_signals_export.csv"
    out = []
    if not sig.exists():
        return out
    try:
        import pandas as pd
        df = pd.read_csv(sig, on_bad_lines="skip")
        if "decision" in df.columns:
            s = df[df["decision"].astype(str).str.upper().eq("SIGNAL")]
            for _, r in s.iterrows():
                out.append(str(r.get("bar_time", "")))
    except Exception:
        pass
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = load_json(CONFIG, {})
    prev = load_json(STATE, {"positions": {}, "signals": {}, "sim_signals": []})
    alerts: list[str] = []

    # 1) 持仓变化
    cur = read_positions(cfg)
    if cur is not None:
        prev_pos = prev.get("positions", {})
        opened = {k: v for k, v in cur.items() if k not in prev_pos}
        closed = [k for k in prev_pos if k not in cur]
        for k, v in opened.items():
            alerts.append(f"🟢 新开仓 [{v['strat']}] magic={v['magic']} {v['dir']} @{v['open']}")
        for k in closed:
            p = prev_pos[k]
            alerts.append(f"🔴 平仓 [{p['strat']}] magic={p['magic']} {p['dir']}（原开仓 @{p['open']}）")
        prev["positions"] = cur

    # 2) dashboard 新信号
    sig = latest_snapshot_signals(cfg)
    prev_sig = prev.get("signals", {})
    for s, info in sig.items():
        old = prev_sig.get(s, {}).get("last_signal_time")
        if old is not None and info["last_signal_time"] != old:
            alerts.append(f"📡 新信号 [{s}] {info['dir']} {info['mode']} @{info['last_signal_time']}")
    prev["signals"] = sig

    # 3) SimMode 虚拟信号
    sims = sim_virtual_signals(cfg)
    prev_sims = set(prev.get("sim_signals", []))
    new_sims = [x for x in sims if x not in prev_sims]
    for x in new_sims:
        alerts.append(f"🧪 SimMode 虚拟信号 @{x}（调试终端）")
    prev["sim_signals"] = sims

    save_json(STATE, prev)

    # 通知
    if alerts:
        content = "\n".join(alerts)
        print("=== ALERTS ===\n" + content)
        if not a.dry_run:
            from notify_wechat import main as _notify  # noqa
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "scripts" / "notify_wechat.py"),
                            "--title", "策略变化提醒", "--content", content], check=False)
            # QQ 推送通道（scripts/qq_push_config.json enabled=true 时生效；未配置则只落盘日志）
            import tempfile, os
            try:
                qc = json.loads((ROOT / "scripts" / "qq_push_config.json").read_text(encoding="utf-8"))
            except Exception:
                qc = {}
            if qc.get("enabled") and qc.get("targetId"):
                # QQ 只推真实交易事件(开仓/平仓)；策略新信号/SimMode 不进 QQ
                trade_lines = [ln for ln in content.split("\n") if ln.startswith(("🟢", "🔴"))]
                if trade_lines:
                    trade_content = "\n".join(trade_lines)
                    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
                        tf.write(trade_content)
                        tmpf = tf.name
                    node = str(cfg.get("node_path") or "node")
                    subprocess.run([node, str(ROOT / "scripts" / "notify_qq.mjs"), "--file", tmpf], check=False)
                    try:
                        os.unlink(tmpf)
                    except Exception:
                        pass
    else:
        print("[watch] 无变化")


if __name__ == "__main__":
    main()
