# -*- coding: utf-8 -*-
import json, os, sys, zstandard as zstd
from pathlib import Path
import datetime as dt
S = Path(os.environ["USERPROFILE"]) / ".dsh" / "sessions" / "--F-use_code-MTA5_l--" / "cc04bcf2-36ca-fceb-266f-0012eaa83ebd" / "session.jsonl.zstd"
sys.stdout.reconfigure(encoding="utf-8")
def text_of(obj):
    c = obj.get("data", {}).get("content") or obj.get("content")
    if isinstance(c, list):
        parts = []
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        return " ".join(parts)
    return ""
data = zstd.ZstdDecompressor().stream_reader(open(S, "rb")).read().decode("utf-8", "replace")
seen = 0
for ln in data.splitlines():
    try:
        o = json.loads(ln)
    except Exception:
        continue
    t = o.get("type")
    if t == "user/message":
        txt = text_of(o)
        src = json.dumps(o.get("data", {}).get("source", {}), ensure_ascii=False)
        ts = dt.datetime.fromtimestamp(o.get("time", 0) / 1000, tz=dt.timezone.utc).strftime("%m-%d %H:%M:%S")
        print("USER", ts, "|", txt[:300].replace(chr(10), " "))
        print("    src:", src[:400])
        seen += 1
    elif t in ("assistant/message",):
        # only print messages that look final (with text)
        txt = text_of(o)
        if txt.strip():
            ts = dt.datetime.fromtimestamp(o.get("time", 0) / 1000, tz=dt.timezone.utc).strftime("%m-%d %H:%M:%S")
            print("ASST", ts, "|", txt[:400].replace(chr(10), " "))
print("user messages seen:", seen)
