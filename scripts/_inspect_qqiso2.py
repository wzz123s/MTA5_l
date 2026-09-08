# -*- coding: utf-8 -*-
import json, os, sys, zstandard as zstd
from pathlib import Path
import datetime as dt
S = Path(os.environ["USERPROFILE"]) / ".dsh_qqbot" / "sessions" / "--F-use_code-MTA5_l--" / "cc04bcf2-36ca-fceb-266f-0012eaa83ebd" / "session.jsonl.zstd"
sys.stdout.reconfigure(encoding="utf-8")
data = zstd.ZstdDecompressor().stream_reader(open(S, "rb")).read().decode("utf-8", "replace")
lines = data.splitlines()
print("total lines:", len(lines))
from collections import Counter
types = Counter()
last_seqs = []
texts = []
errs = []
for ln in lines:
    try: o = json.loads(ln)
    except Exception: continue
    types[o.get("type")] += 1
    if o.get("type") in ("assistant/message", "assistant/chunk", "turn/end", "step/end", "error", "agent/error"):
        d = o.get("data", {})
        s = json.dumps(o, ensure_ascii=False)
        if o.get("type") == "assistant/chunk":
            texts.append(s[:200])
        elif o.get("type") == "assistant/message":
            texts.append(s[:600])
        elif o.get("type") == "turn/end":
            texts.append("TURN_END: " + s[:400])
        elif "error" in o.get("type","").lower():
            errs.append(s[:500])
print("type counts:", dict(types.most_common(15)))
print("recent texts:", texts[-6:] if texts else "none")
print("errors:", errs[-3:] if errs else "none")
last = lines[-1]
try:
    lo = json.loads(last)
    ts = dt.datetime.fromtimestamp(lo.get("time",0)/1000,tz=dt.timezone.utc).strftime("%H:%M:%S")
    print("last record:", ts, lo.get("type"), json.dumps(lo.get("data",{}),ensure_ascii=False)[:300])
except Exception as e:
    print("last raw:", lines[-1][:300])
