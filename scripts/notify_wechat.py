# -*- coding: utf-8 -*-
"""策略提醒发送器：企业微信群机器人 / Server酱 / 纯日志（log_only）。

- 无 key 时 channel=log_only：消息只追加到 alert_log.md（不填 key 也能跑通全流程）。
- 填好 alerts_config.json 后把 channel 切成 wecom_group / serverchan 即生效。

用法：
    python scripts/notify_wechat.py --title "持仓变化" --content "..."
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "scripts" / "alerts_config.json"
sys.stdout.reconfigure(encoding="utf-8")


def load_config() -> dict:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg.setdefault("alert_log", str(ROOT / "scripts" / "alerts" / "alert_log.md"))
    return cfg


def log_only(content: str, log_path: str) -> None:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    Path(log_path).open("a", encoding="utf-8").write(f"### {stamp}\n\n{content}\n\n")


def send_wecom(webhook: str, content: str) -> None:
    payload = json.dumps({"msgtype": "text", "text": {"content": content}}, ensure_ascii=False).encode("utf-8")
    req = Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        if '"errcode":0' not in body:
            raise RuntimeError(f"wecom webhook err: {body[:200]}")


def send_serverchan(key: str, title: str, content: str) -> None:
    import urllib.parse
    url = f"https://sctapi.ftqq.com/{key}.send?" + urllib.parse.urlencode({"title": title, "desp": content})
    with urlopen(url, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        if '"code":0' not in body:
            raise RuntimeError(f"serverchan err: {body[:200]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="策略提醒")
    ap.add_argument("--content", default="")
    ap.add_argument("--dry-run", action="store_true", help="只日志，不真实推送")
    a = ap.parse_args()

    cfg = load_config()
    content = (a.content or "（无正文）").strip()
    full = f"[{a.title}]\n{content}"

    channel = "log_only" if a.dry_run else cfg.get("channel", "log_only")
    if channel == "log_only" or not cfg.get("wecom_webhook") and not cfg.get("serverchan_key"):
        log_only(full, cfg["alert_log"])
        print("[notify] log_only →", cfg["alert_log"])
        return

    if channel == "wecom_group" and cfg.get("wecom_webhook"):
        send_wecom(cfg["wecom_webhook"], full)
    elif channel == "serverchan" and cfg.get("serverchan_key"):
        send_serverchan(cfg["serverchan_key"], a.title, content)
    else:
        log_only(full + "\n（channel=" + channel + " 未配置对应 key，已降级日志）", cfg["alert_log"])
    # 成功推送也留档
    log_only(full + "\n（已推送 " + channel + "）", cfg["alert_log"])
    print("[notify] pushed:", channel)


if __name__ == "__main__":
    main()
