# -*- coding: utf-8 -*-
"""数据行情策略监控适配：实时模拟盘 ledger 口径（默认）+ 回测基线兜底。

实时口径数据源（终端 Files 目录，EA 持续写入）：
  {Name}_trade_ledger.csv    已平仓虚拟仓（逐段，含 virtual_balance）
  {Name}_signals_export.csv  逐 bar 信号评估（dir/mode/entry/stop/gate_pass/decision）
  {Name}_gate_state.csv      事件门状态（[CAL] 证据持久化）

标准列（monitor_all_strategies.per_trade_summary 所需）：
  signal_time / dir / stage / mode / entry / stop / stop_distance /
  stage_pnl / stage_exit_time / stage_exit_price / stage_reason
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> 策略根
VALIDATION = ROOT / "data" / "validation"
TERMINAL_FILES = Path(os.environ.get(
    "DATALEVENT_LIVE_DIR",
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Files",
))

STAGE_UNITS_GOLD = {1: 0.5, 2: 1.0, 3: 1.5}
USD_PER_POINT_GOLD = 10.0   # XAUUSDm 1 lot 1 point = $10
UNITS_TOTAL_GOLD = 3.0
# EA pnl_points 为价格单位；监控点数口径：黄金 1 价格单位=100 点，原油=1000 点
PTS_PER_PRICE = {"gold": 100.0, "oil": 1000.0}

_ST_COLS = ["signal_time", "dir", "stage", "mode", "entry", "stop", "stop_distance",
            "stage_pnl", "stage_exit_time", "stage_exit_price", "stage_reason"]


def _read_live_csv(kind: str):
    f = TERMINAL_FILES / kind
    if not f.exists():
        return None
    df = None
    # EA 用 FILE_ANSI 写 CSV：事件名可能为 GBK 中文 → utf-8 解码失败时回退 gbk/latin-1
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            df = pd.read_csv(f, encoding=enc, on_bad_lines="skip")
            break
        except Exception:
            continue
    if df is None or df.empty or df.shape[1] < 2:
        return None
    return df


def _live_active(name: str) -> bool:
    """实时可用：ledger 有数据行，或 signals_export 有数据行。"""
    led = _read_live_csv(f"{name}_trade_ledger.csv")
    if led is not None and len(led) > 0:
        return True
    sig = _read_live_csv(f"{name}_signals_export.csv")
    return sig is not None and len(sig) > 0


def _st_from_live_ledger(led, name: str):
    """实时 ledger（逐段）→ 标准 st 列。"""
    if led is None or led.empty:
        return pd.DataFrame(columns=_ST_COLS)
    mult = PTS_PER_PRICE[name]
    st = led.copy()
    st["signal_time"] = pd.to_datetime(st["signal_time"], errors="coerce")
    st["stage_exit_time"] = pd.to_datetime(st["exit_time"], errors="coerce")
    st["dir"] = st["dir"].astype(str).str.upper().map({"BUY": "L", "SELL": "S"})
    st["entry"] = pd.to_numeric(st["entry"], errors="coerce")
    st["stop"] = pd.to_numeric(st["stop"], errors="coerce")
    st["stop_distance"] = (st["entry"] - st["stop"]).abs() * mult
    st["stage_pnl"] = pd.to_numeric(st["pnl_points"], errors="coerce") * mult
    st["stage_exit_price"] = pd.to_numeric(st["exit_price"], errors="coerce")
    st["stage_reason"] = st["reason"].astype(str)
    if name == "gold":
        st["stage"] = pd.to_numeric(st["stage"], errors="coerce").fillna(1).astype(int)
        st["mode"] = st["mode"].astype(str)
    else:
        st["stage"] = 1
        st["mode"] = "data_event"
    out = st[_ST_COLS].dropna(subset=["signal_time", "dir"])
    return out


def _live_tf_frame(name: str):
    """实时 bar 收盘参考：signals_export 最新 bar_time（EA 服务器时间=UTC）；
    无信号行时回退 gate_state check_time；再无则用当前时间。"""
    sig = _read_live_csv(f"{name}_signals_export.csv")
    if sig is not None and "bar_time" in sig.columns:
        ts = pd.to_datetime(sig["bar_time"], errors="coerce").dropna()
        if len(ts):
            return pd.DataFrame({"bar_close_time": ts})
    gate = _read_live_csv(f"{name}_gate_state.csv")
    if gate is not None and "check_time" in gate.columns:
        ts = pd.to_datetime(gate["check_time"], errors="coerce").dropna()
        if len(ts):
            return pd.DataFrame({"bar_close_time": ts})
    return pd.DataFrame({"bar_close_time": pd.to_datetime([pd.Timestamp.now().normalize()])})


def live_snapshot(name: str) -> str:
    """实时模拟盘快照 markdown：事件门 + 最近信号 + 已平仓/未平仓 + 虚拟余额。"""
    lines = []
    gold = name == "Gold_DataEvent"
    pending_tag = "ENTRY_PENDING" if gold else "ENTRY"

    live = _live_active(name)
    lines.append(f"- 口径: **{'实时模拟盘 ledger（EA Files 导出）' if live else '回测基线兜底（实时 ledger 暂无数据行）'}**")

    gate = _read_live_csv(f"{name}_gate_state.csv")
    if gate is not None and len(gate):
        last = gate.iloc[-1]
        blk = "🔒 拦截" if str(last.get("blackout", "")).strip() == "1" else "放行"
        lines.append(
            f"- 事件门（gate_state）: **{blk}**｜{last.get('event_name', '-')} "
            f"@ {last.get('event_time', '-')} imp={last.get('importance', '-')} "
            f"{last.get('currency', '-')}（累计 {len(gate)} 次检查）"
        )

    sig = _read_live_csv(f"{name}_signals_export.csv")
    if sig is not None and len(sig):
        s_all = sig.copy()
        s = sig.copy()
        if "dir" in s.columns:
            s = s[s["dir"].astype(str).str.upper().isin(["BUY", "SELL"])]
        if len(s):
            blocked = 0
            if "gate_pass" in s.columns and "decision" in s.columns:
                cand = s[s["gate_pass"].astype(str).str.upper() == "PASS"]
                cand = cand[cand["decision"].astype(str).str.upper() == "SKIP"]
                if len(cand) and gate is not None and len(gate):
                    gts = pd.to_datetime(gate["check_time"], errors="coerce")
                    gblk = gate["blackout"].astype(str).str.strip() == "1"
                    bt = pd.to_datetime(cand["bar_time"], errors="coerce")
                    for t in bt.dropna():
                        before = gts[gts <= t]
                        state = False
                        if len(before):
                            m = before.max()
                            idx = gts[gts == m].index
                            if len(idx) and gblk.loc[idx[0]]:
                                state = True
                        else:
                            after = gts[gts > t]
                            if len(after):
                                m = after.min()
                                idx = gts[gts == m].index
                                if len(idx) and gblk.loc[idx[0]]:
                                    state = True
                        if state:
                            blocked += 1
            lines.append(
                f"- 实时信号（signals_export）: 累计 **{len(s)}** 个，"
                f"其中事件拦截候选 **{blocked}** 个；最近 {min(5, len(s))} 个信号："
            )
            show = s.tail(5)
        else:
            lines.append(
                f"- 逐 bar 评估（signals_export）: 共 {len(s_all)} 行（尚无 BUY/SELL 信号，"
                f"事件门拦截窗口内评估中）；最近 {min(5, len(s_all))} 行："
            )
            show = s_all.tail(5)
            rows = ["| bar_time | dir | mode | entry | stop | gate | decision |",
                    "|---|---|---|---|---|---|---|"]
            for _, r in show.iterrows():
                try:
                    en = float(r.get("entry") or 0)
                    sp = float(r.get("stop") or 0)
                except (TypeError, ValueError):
                    en, sp = 0.0, 0.0
                rows.append(
                    f"| {r.get('bar_time')} | {r.get('dir')} | {r.get('mode')} | "
                    f"{en:.2f} | {sp:.2f} | {r.get('gate_pass')} | {r.get('decision')} |"
                )
            lines.append("\n".join(rows))

    led = _read_live_csv(f"{name}_trade_ledger.csv")
    if led is not None and len(led):
        n_sig = led["signal_time"].nunique()
        try:
            bal = float(led["virtual_balance"].iloc[-1])
        except (TypeError, ValueError):
            bal = 0.0
        lines.append(f"- 已平仓虚拟仓（ledger）: {len(led)} 段 / {n_sig} 信号，虚拟余额 **${bal:,.2f}**")
        if sig is not None and "decision" in sig.columns:
            closed = set(pd.to_datetime(led["signal_time"], errors="coerce").dropna().astype(str))
            pend = sig[sig["decision"].astype(str).str.upper() == pending_tag]
            open_sigs = []
            for _, r in pend.iterrows():
                bt = pd.to_datetime(r.get("bar_time"), errors="coerce")
                if pd.isna(bt) or str(bt) not in closed:
                    open_sigs.append(r)
            if open_sigs:
                last_o = open_sigs[-1]
                lines.append(
                    f"- 未平仓（pending 未入账）: {len(open_sigs)} 个｜最近: "
                    f"bar {last_o.get('bar_time')} {last_o.get('dir')} {last_o.get('mode')} "
                    f"@ {last_o.get('entry')}"
                )
    if not lines:
        lines.append("- 实时数据未就绪（EA 未挂载或尚无输出，请确认终端运行中）")
    return "\n".join(lines)


# ---------------- 回测兜底（实时不可用时的原口径） ----------------


def _standardize(trades, name: str):
    """把基线/变体 trades CSV 标准化为 st 格式（三列：L/S 方向、三点数口径）。"""
    if trades.empty:
        return pd.DataFrame(columns=_ST_COLS)
    st = trades.copy()
    st["signal_time"] = pd.to_datetime(st["entry_time"], utc=True)
    st["dir"] = st["dir"].map({"L": "L", "S": "S"})
    st["stage"] = 1
    st["mode"] = st.get("sig", "data_event")
    st["entry"] = pd.to_numeric(st["entry"], errors="coerce")
    st["stop"] = pd.to_numeric(st["stop"], errors="coerce")
    st["stop_distance"] = (st["entry"] - st["stop"]).abs()
    if "stop_dist" in st.columns:
        st["stop_distance"] = pd.to_numeric(st["stop_dist"], errors="coerce").fillna(st["stop_distance"])
    if name == "gold":
        dir_sign = st["dir"].map({"L": 1.0, "S": -1.0}).fillna(0.0)
        total = pd.Series(0.0, index=st.index)
        for col in ("exit_s1", "exit_s2", "exit_s3"):
            px = pd.to_numeric(st[col].astype(str).str.split("@").str[-1], errors="coerce")
            total += (px - st["entry"]) * dir_sign * 100.0
        st["stage_pnl"] = total
    else:
        st["stage_pnl"] = pd.to_numeric(st["pnl_pts"], errors="coerce")
    st["stage_exit_time"] = pd.to_datetime(st["exit_time"], utc=True)
    if "exit_price" in st.columns:
        st["stage_exit_price"] = pd.to_numeric(st["exit_price"], errors="coerce")
    else:
        st["stage_exit_price"] = (
            pd.to_numeric(st["exit_s1"].astype(str).str.split("@").str[-1], errors="coerce")
            if "exit_s1" in st.columns else 0.0
        )
    st["stage_reason"] = (
        st["exit_reason"] if "exit_reason" in st.columns
        else (st["exit_s3"].astype(str).str.split("@").str[0] if "exit_s3" in st.columns else "sim")
    )
    st["signal_time"] = st["signal_time"].dt.tz_localize(None)
    st["stage_exit_time"] = st["stage_exit_time"].dt.tz_localize(None)
    return st[_ST_COLS]


def _backtest_tf(path_rel: str):
    ctx = pd.read_csv(ROOT / "data" / "processed" / path_rel, parse_dates=["time"])
    ctx["time"] = pd.to_datetime(ctx["time"], utc=True)
    tf = ctx.rename(columns={"time": "bar_close_time"})[["bar_close_time"]]
    tf["bar_close_time"] = pd.to_datetime(tf["bar_close_time"], utc=True).dt.tz_localize(None)
    return tf


def _build_backtest_gold():
    trades_f = VALIDATION / "baseline_gold_trades.csv"
    trades = pd.read_csv(trades_f, parse_dates=["entry_time"]) if trades_f.exists() else pd.DataFrame()
    st = _standardize(trades, "gold")
    try:
        tf = _backtest_tf("gold_context.csv")
    except Exception:
        tf = pd.DataFrame({"bar_close_time": pd.to_datetime([])})
    return st, trades, tf


def _build_backtest_oil():
    trades_f = VALIDATION / "baseline_oil_trades.csv"
    trades = pd.read_csv(trades_f, parse_dates=["entry_time"]) if trades_f.exists() else pd.DataFrame()
    st = _standardize(trades, "oil")
    try:
        tf = _backtest_tf("oil_context_h2.csv")
    except Exception:
        tf = pd.DataFrame({"bar_close_time": pd.to_datetime([])})
    return st, trades, tf


def build_gold():
    """实时模拟盘口径（仅当 trade_ledger 已有平仓数据行时启用）；否则回测基线兜底。

    BUGFIX(2026-09-02): 原逻辑用 _live_active() 判定——只要 signals_export 有逐 bar 行
    （EA 已挂载、正在评估信号）就切到"实时口径"，而 trade_ledger 尚未有任何已平仓虚拟仓时
    会返回 0 笔，导致 dashboard 的 Gold_DataEvent 从基线 405 笔骤变为 0（看起来策略"归零"）。
    修复：只有 ledger 真实积累平仓记录后才切实时口径；EA 在跑但无平仓记录期间继续显示回测基线。
    """
    led = _read_live_csv("Gold_DataEvent_trade_ledger.csv")
    if led is not None and len(led) > 0:
        st = _st_from_live_ledger(led, "gold")
        return st, led, _live_tf_frame("Gold_DataEvent")
    return _build_backtest_gold()


def build_oil():
    """实时模拟盘口径（仅当 trade_ledger 已有平仓数据行时启用）；否则回测基线兜底。
    与 build_gold 同口径修复（2026-09-02）。"""
    led = _read_live_csv("Oil_DataEvent_trade_ledger.csv")
    if led is not None and len(led) > 0:
        st = _st_from_live_ledger(led, "oil")
        return st, led, _live_tf_frame("Oil_DataEvent")
    return _build_backtest_oil()
