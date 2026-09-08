# -*- coding: utf-8 -*-
"""monitor_magic_302025 - Watch MT5 for 30m2H EA activity, notify on new deals.

Runs forever in a loop:
  1. Scan open positions for magic 302026/27/28 (Stage 1/2/3 of 30m2H EA)
  2. Scan deal history since last scan for new entries/exits
  3. Print + log + beep on new deals or signal
  4. Sleep 30 min (configurable), repeat

State persists in monitor_state.json so restarts don't double-notify.

Usage:
    python auto_trade/monitor_magic_302025.py
    python auto_trade/monitor_magic_302025.py --interval 60   # 60-min scans
    python auto_trade/monitor_magic_302025.py --once          # single scan, exit

Notification methods:
  - Console (always)
  - Log file: auto_trade/monitor.log
  - Windows beep (3 short beeps on signal/close)
  - Server 酱 push to personal WeChat (if SendKey configured)

Credentials are read from environment variables (or a `.env` file next to this
script). See `.env.example` for the full list. Required: MT5_ACCOUNT + MT5_PASSWORD.
"""
import sys
import os
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import MetaTrader5 as mt5
import urllib.request
import urllib.parse
import ssl


def _load_dotenv():
    """Load KEY=VALUE pairs from a .env file next to this script into os.environ.

    Does NOT overwrite variables that are already set in the shell — env vars win.
    Lines starting with `#` and blank lines are ignored. Quotes are stripped.
    No external dependency (avoids `pip install python-dotenv`).
    """
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    try:
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
    except Exception as e:
        print(f"[WARN] failed to parse .env: {e}")


_load_dotenv()

CONFIG = {
    # MT5_PATH and MT5_SERVER are not secrets — defaults provided for convenience.
    "mt5_path": os.environ.get(
        "MT5_PATH",
        r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
    ),
    "server": os.environ.get("MT5_SERVER", "Exness-MT5Trial5"),
    "symbol": os.environ.get("MT5_SYMBOL", "XAUUSDm"),
    # Required credentials — must come from env / .env (no defaults).
    "account": int(os.environ.get("MT5_ACCOUNT", "0")),
    "password": os.environ.get("MT5_PASSWORD", ""),
    # Strategy magic base (InpMagic in EA). Stage suffixes derived below.
    "magic_base": int(os.environ.get("MT5_MAGIC_BASE", "302025")),
    # Push notification. Get SendKey from https://sct.ftqq.com (scan QR with
    # personal WeChat). Free tier: 5 pushes/day. Leave empty to disable.
    "server_chan_sendkey": os.environ.get("SERVER_CHAN_SENDKEY", ""),
    # Enterprise WeChat (企业微信) via wecom-cli subprocess.
    # Requires: `npm install -g @wecom/cli` + `wecom-cli init` (QR scan).
    # Set to the recipient's userid (run `wecom-cli contact get_userlist '{}'`
    # to look up userids). Leave empty to disable.
    "wecom_target_userid": os.environ.get("WECOM_TARGET_USERID", ""),
}
CONFIG["magic_min"] = CONFIG["magic_base"] + 1   # Stage 1
CONFIG["magic_max"] = CONFIG["magic_base"] + 3   # Stage 3

STATE_FILE = Path(__file__).resolve().parent / "monitor_state.json"
LOG_FILE   = Path(__file__).resolve().parent / "monitor.log"


def _log(msg, also_print=True):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    if also_print:
        print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _beep(pattern=(800, 200, 800, 200, 800, 200)):
    """Cross-platform beep. Falls back silently if no audio."""
    try:
        import winsound
        for f, d in zip(pattern[::2], pattern[1::2]):
            winsound.Beep(f, d)
    except Exception:
        pass  # non-Windows or no audio


def notify_server_chan(title, content, mention_all=False):
    """Push to personal WeChat via Server 酱 (Server Chan).

    Setup (one-time):
      1. Open https://sct.ftqq.com/login in any browser
      2. Scan the QR with your personal WeChat (NOT 企业微信 — regular WeChat works)
      3. Copy the SendKey from the dashboard (format: SCT2...)
      4. Paste into CONFIG["server_chan_sendkey"]

    Free tier: 5 pushes/day. For higher volume, subscribe ¥9/month via WeChat pay.

    Server 酱 markdown in `desp` field: `**bold**`, `\\n` for line break.
    `mention_all` is accepted for signature compatibility but ignored —
    Server 酱 always pushes to the binding WeChat account.
    """
    sendkey = CONFIG.get("server_chan_sendkey", "")
    if not sendkey:
        return  # not configured, skip silently
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = urllib.parse.urlencode({
        "title": title,
        "desp": content,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            try:
                result = json.loads(body)
                if result.get("code") == 0:
                    _log(f"[OK] server_chan push: {title}")
                else:
                    _log(f"[WARN] server_chan push: {result}")
            except Exception:
                _log(f"[WARN] server_chan push response: {body[:200]}")
    except Exception as e:
        _log(f"[WARN] server_chan push failed: {e}")


def _strip_markdown(s):
    """Strip Server 酱 markdown so it renders cleanly in plain-text wecom.

    Server 酱 supports **bold**, code blocks, etc. 企业微信 send_message text
    type is plain text — keep `**` would show literal asterisks.
    """
    return s.replace("**", "").replace("  \n", "\n")


def notify_wecom(title, content, mention_all=False):
    """Push to Enterprise WeChat via wecom-cli subprocess.

    Requires:
      - `npm install -g @wecom/cli` (binary in PATH)
      - `wecom-cli init` (QR scan to bind an enterprise member account)
      - WECOM_TARGET_USERID env var set to the recipient's userid

    The `mention_all` parameter is accepted for signature parity with the
    other notifiers but ignored — wecom-cli send_message text type has no
    @mention feature (use chat_type=2 group send for that).
    """
    target = CONFIG.get("wecom_target_userid", "")
    if not target:
        return  # not configured, skip silently
    text = f"{title}\n\n{_strip_markdown(content)}"
    if len(text.encode("utf-8")) > 2000:
        text = text[:1990] + "...(截断)"
    payload = {
        "chat_type": 1,            # single chat
        "chatid": target,
        "msgtype": "text",
        "text": {"content": text},
    }
    try:
        # shutil.which on Windows respects PATHEXT (finds .cmd/.bat/.exe).
        # Avoids shell=True brittleness (colon in JSON looking like CLI flag).
        import shutil
        binary = shutil.which("wecom-cli")
        if not binary:
            _log("[WARN] wecom-cli not found in PATH. Install: npm install -g @wecom/cli")
            return
        proc = subprocess.run(
            [binary, "msg", "send_message", "--json", json.dumps(payload, ensure_ascii=False)],
            capture_output=True,
            timeout=15,
            text=True,
        )
        if proc.returncode != 0:
            _log(f"[WARN] wecom push failed (exit {proc.returncode}): {proc.stderr.strip()[:200]}")
        else:
            # wecom-cli wraps API response in MCP/JSON-RPC envelope. Parse it
            # and drill into result.content[0].text to read the real errcode.
            try:
                envelope = json.loads(proc.stdout)
                inner_text = envelope["result"]["content"][0]["text"]
                inner = json.loads(inner_text)
                if inner.get("errcode") == 0:
                    _log(f"[OK] wecom push: {title}")
                else:
                    _log(f"[WARN] wecom push: {inner}")
            except Exception:
                _log(f"[WARN] wecom push unparseable response: {proc.stdout.strip()[:200]}")
    except FileNotFoundError:
        _log("[WARN] wecom-cli not found in PATH. Install: npm install -g @wecom/cli")
    except subprocess.TimeoutExpired:
        _log("[WARN] wecom push timed out after 15s")
    except Exception as e:
        _log(f"[WARN] wecom push failed: {e}")


def connect():
    if not mt5.initialize(path=CONFIG["mt5_path"]):
        _log(f"[FAIL] MT5 init: {mt5.last_error()}", also_print=True)
        return False
    if not mt5.login(
        login=CONFIG["account"],
        password=CONFIG["password"],
        server=CONFIG["server"],
    ):
        _log(f"[FAIL] MT5 login: {mt5.last_error()}", also_print=True)
        mt5.shutdown()
        return False
    info = mt5.account_info()
    _log(f"[OK] Connected: account={info.login}, balance=${info.balance:.2f}, "
         f"equity=${info.equity:.2f}, leverage=1:{info.leverage}")
    return True


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_scan_time": (datetime.now() - timedelta(hours=2)).isoformat(),
        "seen_deal_tickets": [],
    }


def save_state(state):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        _log(f"[WARN] save_state: {e}")


def stage_label(magic):
    suffix = magic - CONFIG["magic_base"]
    return {1: "Stage1", 2: "Stage2", 3: "Stage3"}.get(suffix, f"raw({magic})")


def reason_str(reason):
    reasons = {
        mt5.DEAL_REASON_CLIENT: "CLIENT",
        mt5.DEAL_REASON_EXPERT: "EA",
        mt5.DEAL_REASON_SL: "SL",
        mt5.DEAL_REASON_TP: "TP",
    }
    return reasons.get(reason, f"?{reason}")


def scan_positions():
    positions = mt5.positions_get(symbol=CONFIG["symbol"])
    if positions is None:
        return []
    out = []
    for p in positions:
        out.append({
            "ticket": p.ticket,
            "magic": p.magic,
            "stage": stage_label(p.magic),
            "type": "LONG" if p.type == mt5.ORDER_TYPE_BUY else "SHORT",
            "volume": p.volume,
            "price_open": p.price_open,
            "sl": p.sl,
            "profit": p.profit,
        })
    return out


def scan_new_deals(since_dt):
    deals = mt5.history_deals_get(since_dt, datetime.now(), symbol=CONFIG["symbol"])
    if deals is None:
        return []
    out = []
    for d in deals:
        if not (CONFIG["magic_min"] <= d.magic <= CONFIG["magic_max"]):
            continue
        out.append({
            "ticket": d.ticket,
            "order": d.order,
            "magic": d.magic,
            "stage": stage_label(d.magic),
            "type": "LONG" if d.type == mt5.DEAL_TYPE_BUY else "SHORT",
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "time": datetime.fromtimestamp(d.time),
            "entry": "IN" if d.entry == mt5.DEAL_ENTRY_IN else "OUT",
            "reason": reason_str(d.reason),
            "comment": d.comment,
        })
    return out


def notify_new_deal(deal):
    direction_arrow = "LONG" if deal["type"] == "LONG" else "SHORT"
    icon = "[OPEN]" if deal["entry"] == "IN" else "[CLOSE]"
    msg = (f"{icon} {deal['stage']:<7} {direction_arrow:<5} "
           f"vol={deal['volume']:.2f} price={deal['price']:.2f} "
           f"PnL=${deal['profit']:+.2f} reason={deal['reason']}")
    print("\n" + "=" * 60)
    _log(f"NEW DEAL: {msg}", also_print=False)
    print(f"  >>> {msg}")
    print(f"      ticket={deal['ticket']} time={deal['time']} magic={deal['magic']}")
    print("=" * 60 + "\n")
    _beep()
    # Push to Enterprise WeChat (if configured)
    title = f"EA 30m2H {icon} {deal['stage']}"
    content = (
        f"**方向**: {direction_arrow}  \n"
        f"**手数**: {deal['volume']:.2f}  \n"
        f"**价格**: {deal['price']:.2f}  \n"
        f"**盈亏**: {deal['profit']:+.2f} USD  \n"
        f"**原因**: {deal['reason']}  \n"
        f"**时间**: {deal['time'].strftime('%Y-%m-%d %H:%M:%S')}  \n"
        f"**Ticket**: {deal['ticket']}"
    )
    notify_server_chan(title, content, mention_all=False)
    notify_wecom(title, content, mention_all=False)


def notify_position_change(prev, curr):
    prev_t = {p["ticket"] for p in prev}
    curr_t = {p["ticket"] for p in curr}
    new_t = curr_t - prev_t
    closed_t = prev_t - curr_t
    if not new_t and not closed_t:
        return
    lines = []
    for t in new_t:
        p = next(x for x in curr if x["ticket"] == t)
        line = (f"NEW {p['stage']:<7} {p['type']:<5} vol={p['volume']:.2f} "
                f"entry={p['price_open']:.2f} SL={p['sl']:.2f} "
                f"PnL=${p['profit']:+.2f} (ticket={t})")
        print(f"  >>> {line}")
        lines.append(line)
    for t in closed_t:
        p = next(x for x in prev if x["ticket"] == t)
        line = (f"CLOSED {p['stage']:<7} {p['type']:<5} vol={p['volume']:.2f} "
                f"entry={p['price_open']:.2f} (ticket={t})")
        print(f"  <<< {line}")
        lines.append(line)
    _beep()
    title = "EA 30m2H 仓位变化"
    content = "  \n".join(lines)
    notify_server_chan(title, content, mention_all=False)
    notify_wecom(title, content, mention_all=False)


def once_scan(state):
    print()
    print("=" * 60)
    print(f"  Scan @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Current positions
    positions = scan_positions()
    ours = [p for p in positions if CONFIG["magic_min"] <= p["magic"] <= CONFIG["magic_max"]]
    if ours:
        total_pnl = sum(p["profit"] for p in ours)
        total_vol = sum(p["volume"] for p in ours)
        print(f"  Open: {len(ours)} positions, {total_vol:.2f} lots, PnL ${total_pnl:+.2f}")
        for p in ours:
            print(f"    {p['stage']:<7} {p['type']:<5} vol={p['volume']:.2f} "
                  f"entry={p['price_open']:.2f} SL={p['sl']:.2f} PnL=${p['profit']:+.2f}")
        # Detect new positions since last scan
        prev_positions = state.get("last_positions", [])
        notify_position_change(prev_positions, ours)
        state["last_positions"] = ours
    else:
        print(f"  Open: 0 30m2H EA positions")

    # New deals since last scan
    last_scan_dt = datetime.fromisoformat(state["last_scan_time"])
    new_deals = scan_new_deals(last_scan_dt)
    seen = set(state.get("seen_deal_tickets", []))
    fresh = [d for d in new_deals if d["ticket"] not in seen]

    if fresh:
        print(f"\n  NEW DEALS since {last_scan_dt.strftime('%H:%M:%S')}:")
        for d in fresh:
            notify_new_deal(d)
            seen.add(d["ticket"])
    else:
        print(f"\n  No new deals since {last_scan_dt.strftime('%H:%M:%S')}")

    # Update state
    state["last_scan_time"] = datetime.now().isoformat()
    state["seen_deal_tickets"] = sorted(seen)[-1000:]  # keep last 1000
    save_state(state)

    print(f"  Next scan in {args.interval} min (Ctrl+C to stop)")
    return len(fresh) > 0 or len(ours) != len(state.get("last_positions_at_check", [])) if False else len(fresh) > 0


def main():
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=30,
                        help="Minutes between scans (default 30)")
    parser.add_argument("--once", action="store_true",
                        help="Single scan and exit")
    parser.add_argument("--test-push", action="store_true",
                        help="Send a test message via Server 酱 and exit")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  30m2H EA Monitor (magic {CONFIG['magic_min']}-{CONFIG['magic_max']})")
    print(f"  Interval: {args.interval} min  |  Log: {LOG_FILE}")
    print(f"  State:   {STATE_FILE}")
    print("=" * 60)

    if not CONFIG["account"] or not CONFIG["password"]:
        print()
        print("[FAIL] MT5 credentials missing.")
        print("       Required env vars: MT5_ACCOUNT, MT5_PASSWORD")
        print("       Optional: MT5_PATH, MT5_SERVER, MT5_SYMBOL, MT5_MAGIC_BASE, SERVER_CHAN_SENDKEY")
        print("       Set them in your shell, or create `auto_trade/.env` (see .env.example).")
        sys.exit(1)

    if not connect():
        sys.exit(1)

    state = load_state()
    _log(f"State loaded: last_scan={state['last_scan_time']}, "
         f"seen_deals={len(state.get('seen_deal_tickets', []))}")

    try:
        if args.test_push:
            print("\n[TEST] Sending test push via Server 酱 and wecom-cli...")
            test_title = "[TEST] EA 30m2H 监控已上线"
            test_content = (
                f"如果你看到这条消息，Server 酱 + 企业微信 推送都通了！  \n"
                f"**账号**: {CONFIG['account']}  \n"
                f"**品种**: {CONFIG['symbol']}  \n"
                f"**Magic**: {CONFIG['magic_min']}-{CONFIG['magic_max']}  \n"
                f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            notify_server_chan(test_title, test_content, mention_all=False)
            notify_wecom(test_title, test_content, mention_all=False)
        elif args.once:
            once_scan(state)
        else:
            while True:
                once_scan(state)
                time.sleep(args.interval * 60)
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user.")
    finally:
        mt5.shutdown()
        print("[OK] MT5 disconnected.")


if __name__ == "__main__":
    main()
