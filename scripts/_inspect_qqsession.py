# -*- coding: utf-8 -*-
import json, os, sys, zstandard as zstd
from pathlib import Path
import datetime as dt
S = Path(os.environ["USERPROFILE"]) / ".dsh" / "sessions" / "--F-use_code-MTA5_l--" / "session-757d6ba0-7a87-4652-9cea-9c2d1d233b4d" / "session.jsonl.zstd"
sys.stdout.reconfigure(encoding="utf-8")
data = zstd.ZstdDecompressor().stream_reader(open(S, "rb")).read().decode("utf-8", "replace")
print("bytes:", len(data))
openid_hits = []
shown_src = set()
def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            kl = str(k).lower()
            if any(x in kl for x in ("openid", "peer", "targetid", "sender", "scope", "channel")) and not isinstance(v, (dict, list)):
                openid_hits.append((path + "/" + str(k), str(v)[:160]))
            walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + "/" + str(i))
for ln in data.splitlines():
    try:
        o = json.loads(ln)
    except Exception:
        continue
    walk(o)
    t = o.get("type")
    if t == "user/message":
        ts = dt.datetime.fromtimestamp(o.get("time", 0) / 1000, tz=dt.timezone.utc).strftime("%m-%d %H:%M:%S")
        src = json.dumps(o.get("data", {}).get("source", {}), ensure_ascii=False)
        content = o.get("data", {}).get("content")
        txt = ""
        if isinstance(content, list):
            txt = " ".join((b.get("text") or "") for b in content if isinstance(b, dict))
        print("USER", ts, "|", txt[:300].replace(chr(10), " "))
        print("    SRC:", src[:700])
        key = src[:120]
        if key not in shown_src:
            shown_src.add(key)
    elif t == "assistant/message":
        content = o.get("data", {}).get("content")
        txt = ""
        if isinstance(content, list):
            txt = " ".join((b.get("text") or "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if txt.strip():
            ts = dt.datetime.fromtimestamp(o.get("time", 0) / 1000, tz=dt.timezone.utc).strftime("%m-%d %H:%M:%S")
            print("ASST", ts, "|", txt[:500].replace(chr(10), " "))
print()
print("=== openid-like hits ===")
seen = set()
for p, v in openid_hits:
    if (p, v[:60]) in seen:
        continue
    seen.add((p, v[:60]))
    print(p, "=", v)
