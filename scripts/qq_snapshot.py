# -*- coding: utf-8 -*-
"""
qq_snapshot.py - QQ 监控快照生成器 (MTA5_l)

产出 observation_dashboard/qq_snapshot.json，两层:
  1) mt5_live   : 实盘 MT5 账户余额/净值/持仓每单(开仓/现价/止盈/止损/浮盈)/最近成交
  2) strategies : dashboard.csv 各策略总览 + watch_state 最新信号 + 警戒摘要 + 最新监测报告

用法:
  python scripts/qq_snapshot.py            # 生成快照 json
  python scripts/qq_snapshot.py --text     # 生成 json 并打印人类摘要
  python scripts/qq_snapshot.py --console  # 只打印摘要不写文件
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "observation_dashboard"
ALERTS_DIR = ROOT / "scripts" / "alerts"
CONFIG = ROOT / "scripts" / "alerts_config.json"
OUT_JSON = DASHBOARD / "qq_snapshot.json"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config() -> dict:
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


# ---------------- MT5 live ----------------
def read_mt5(cfg: dict) -> dict:
    out: dict = {
        "ok": False,
        "terminal": None,
        "error": None,
        "account": None,
        "open_positions": [],
        "recent_deals": [],
        "deal_summary": None,
    }
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        out["error"] = "MetaTrader5 模块不可用: " + str(e)
        return out

    candidates = []
    t = (cfg.get("main_terminal") or "").strip()
    if t:
        candidates.append(t)
    candidates += [
        "F:/Program Files/MetaTrader 5/terminal64.exe",
        "F:/Program Files/MetaTrader 5 EXNESS/terminal64.exe",
    ]
    inited = None
    for path in candidates:
        try:
            if mt5.initialize(path):
                inited = path
                break
        except Exception:
            continue
    if inited is None:
        out["error"] = "MT5 initialize 失败 (终端未运行或路径不可用)"
        return out
    out["terminal"] = inited

    acc = mt5.account_info()
    if acc is None:
        out["error"] = "account_info 失败: " + str(mt5.last_error())
        mt5.shutdown()
        return out
    out["account"] = {
        "login": acc.login,
        "server": acc.server,
        "name": acc.name,
        "currency": acc.currency,
        "balance": round(float(acc.balance), 2),
        "equity": round(float(acc.equity), 2),
        "margin_free": round(float(acc.margin_free), 2),
        "margin": round(float(acc.margin), 2),
        "floating_profit": round(float(acc.profit), 2),
    }

    pos = mt5.positions_get() or []
    for d in pos:
        out["open_positions"].append({
            "ticket": d.ticket,
            "symbol": d.symbol,
            "side": "BUY" if d.type == 0 else "SELL",
            "volume": float(d.volume),
            "price_open": round(float(d.price_open), 3),
            "sl": round(float(d.sl), 3) if d.sl else None,
            "tp": round(float(d.tp), 3) if d.tp else None,
            "price_current": round(float(d.price_current), 3),
            "profit": round(float(d.profit), 2),
            "swap": round(float(d.swap), 2) if hasattr(d, "swap") else None,
            "magic": d.magic,
            "comment": (d.comment or "")[:40],
        })

    try:
        since = datetime.now(timezone.utc) - timedelta(hours=72)
        deals = mt5.history_deals_get(since) or []
        deals.sort(key=lambda x: x.time, reverse=True)
        recent = []
        for d in deals[:40]:
            t_utc = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            entry = {0: "in", 1: "out", 2: "inout", 3: "out_by"}.get(d.entry, str(d.entry))
            side = "BUY" if d.type == 0 else ("SELL" if d.type == 1 else ("type" + str(d.type)))
            recent.append({
                "ticket": d.ticket,
                "position_id": d.position_id,
                "time_utc": t_utc,
                "symbol": d.symbol,
                "side": side,
                "entry": entry,
                "volume": float(d.volume),
                "price": round(float(d.price), 3),
                "profit": round(float(d.profit), 2),
                "commission": round(float(d.commission), 2) if hasattr(d, "commission") else None,
                "swap": round(float(d.swap), 2) if hasattr(d, "swap") else None,
                "magic": d.magic,
            })
        out["recent_deals"] = recent
        closed = [d for d in recent if d["entry"] == "out" and d["profit"] is not None]
        net = 0.0
        for d in recent:
            net += (d["profit"] or 0) + (d["swap"] or 0)
        out["deal_summary"] = {
            "window_hours": 72,
            "deals_count": len(recent),
            "closed_count": len(closed),
            "net_pnl": round(net, 2),
        }
    except Exception as e:
        out["deal_error"] = str(e)
    finally:
        mt5.shutdown()
    out["ok"] = True
    return out


# ---------------- Strategy overview ----------------
def read_dashboard() -> dict:
    res: dict = {"overview": [], "warnings": [], "report": None}
    csv_path = DASHBOARD / "dashboard.csv"
    if csv_path.exists():
        try:
            with csv_path.open(encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                reader.fieldnames = [((h or "").strip()) for h in (reader.fieldnames or [])]
                rows = list(reader)
            for r in rows:
                item = {k: (v if v is not None else "") for k, v in r.items()}
                warn = (item.get("warnings") or "").strip()
                item["_has_warning"] = bool(warn and warn != "无")
                if item["_has_warning"]:
                    res["warnings"].append((item.get("strategy", "?") + ": " + warn))
                res["overview"].append(item)
        except Exception as e:
            res["overview_error"] = str(e)
    rep_dir = DASHBOARD / "监测报告"
    if rep_dir.exists():
        mds = sorted(rep_dir.glob("监测报告_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mds:
            p = mds[0]
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
                head = chr(10).join(l for l in lines[:12] if l.strip())[:900]
            except Exception:
                head = ""
            res["report"] = {
                "file": str(p.relative_to(ROOT)),
                "generated": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "head": head,
            }
    return res


def read_signals() -> dict:
    f = ALERTS_DIR / "watch_state.json"
    if not f.exists():
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        sig = data.get("signals") or {}
        out = {}
        for k in sorted(sig.keys()):
            v = sig[k]
            out[k] = {"time": v.get("last_signal_time"), "dir": v.get("dir"), "mode": v.get("mode")}
        return out
    except Exception:
        return {}


# ---------------- human summary ----------------
def build_text(snap: dict) -> str:
    lines = []
    mt5 = snap.get("mt5_live", {})
    if mt5.get("ok") and mt5.get("account"):
        a = mt5["account"]
        lines.append("【MT5 实盘账户】 " + str(a.get("login")) + " @ " + str(a.get("server")) + " (" + str(a.get("currency")) + ")")
        lines.append(
            "余额 " + fmt_money(a.get("balance")) + " | 净值 " + fmt_money(a.get("equity"))
            + " | 可用保证金 " + fmt_money(a.get("margin_free")) + " | 浮动盈亏 " + fmt_signed(a.get("floating_profit"))
        )
        pos = mt5.get("open_positions") or []
        if not pos:
            lines.append("当前持仓: 无")
        else:
            lines.append("当前持仓 " + str(len(pos)) + " 单:")
            for p in pos:
                lines.append(
                    "  #" + str(p["ticket"]) + " " + p["symbol"] + " " + p["side"] + " " + str(p["volume"])
                    + "手 | 开仓 " + fmt_p(p["price_open"]) + " | 现价 " + fmt_p(p["price_current"])
                    + " | 止损 " + fmt_p(p["sl"]) + " | 止盈 " + fmt_p(p["tp"]) + " | 浮盈 " + fmt_signed(p["profit"])
                )
        ds = mt5.get("deal_summary")
        rd = mt5.get("recent_deals")
        if ds is not None:
            lines.append("近72h成交 " + str(ds["deals_count"]) + " 笔 (平仓 " + str(ds["closed_count"]) + ") | 净盈亏 " + fmt_signed(ds["net_pnl"]))
            if rd:
                outs = [d for d in rd if d["entry"] == "out"][:5]
                for d in reversed(outs):
                    lines.append(
                        "  平仓 " + str(d["time_utc"]) + " " + d["symbol"] + " " + d["side"] + " " + str(d["volume"])
                        + "手 @" + fmt_p(d["price"]) + " | 盈亏 " + fmt_signed(d["profit"])
                    )
    else:
        lines.append("【MT5】读取失败: " + (mt5.get("error") or "未知"))

    ov = snap.get("strategies", {}).get("overview") or []
    if ov:
        lines.append("")
        lines.append("【策略监测总览】")
        for r in ov:
            w = "!" if r.get("_has_warning") else " "
            lines.append(
                w + " " + (r.get("strategy", "?") or "?")[:16].ljust(16)
                + " 交易 " + str(r.get("total_trades", "?"))
                + " | 累计 " + fmt_pts(r.get("total_weighted_pts")) + " pts"
                + " | 0.5/1pct 净值 " + fmt_money(r.get("equity_0_5pct")) + "/" + fmt_money(r.get("equity_1pct"))
                + " | 数据至 " + str(r.get("data_last_bar", "-"))
            )
        warns = snap.get("strategies", {}).get("warnings") or []
        if warns:
            lines.append("警戒 " + str(len(warns)) + " 项: " + "; ".join(warns))
    sig = snap.get("strategies", {}).get("signals") or {}
    if sig:
        lines.append("")
        lines.append("【最新策略信号】")
        for k, v in sig.items():
            if v.get("time"):
                lines.append("  " + k + ": " + str(v["dir"]) + " @ " + str(v["time"]) + " (" + str(v.get("mode") or "") + ")")
    rep = snap.get("strategies", {}).get("report")
    if rep:
        lines.append("")
        lines.append("最新监测报告: " + str(rep["file"]) + " (" + str(rep["generated"]) + ")")
    lines.append("")
    lines.append("快照时间: " + str(snap.get("generated_utc")))
    return chr(10).join(lines)


def fmt_money(v) -> str:
    if v is None or v == "":
        return "-"
    try:
        return "{:,.0f}".format(float(v))
    except Exception:
        return str(v)


def fmt_signed(v) -> str:
    if v is None or v == "":
        return "-"
    try:
        return "{:+,.2f}".format(float(v))
    except Exception:
        return str(v)


def fmt_pts(v) -> str:
    if v is None or v == "":
        return "-"
    try:
        return "{:,.0f}".format(float(v))
    except Exception:
        return str(v)


def fmt_p(v) -> str:
    if v is None or v == "":
        return "-"
    try:
        return "{:,.3f}".format(float(v))
    except Exception:
        return str(v)


def build_snapshot() -> dict:
    cfg = load_config()
    mt5 = read_mt5(cfg)
    dash = read_dashboard()
    sig = read_signals()
    return {
        "generated_utc": now_utc(),
        "mt5_live": mt5,
        "strategies": dict(dash, signals=sig),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", action="store_true", help="写 json 并打印摘要")
    ap.add_argument("--console", action="store_true", help="只打印摘要不写文件")
    a = ap.parse_args()

    snap = build_snapshot()
    text = build_text(snap)

    if a.console:
        print(text)
        return 0
    try:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUT_JSON.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(OUT_JSON)
        print("[qq_snapshot] OK -> " + str(OUT_JSON) + "  (" + datetime.now(timezone.utc).strftime("%H:%M:%S") + " UTC)")
    except Exception as e:
        print("[qq_snapshot] write failed: " + str(e))
    if a.text:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
