# -*- coding: utf-8 -*-
import json, os, sys, zstandard as zstd
from pathlib import Path
import datetime as dt
home = os.environ.get("DSH_HOME", "")
S = Path(os.environ["USERPROFILE"]) / ".dsh_qqbot" / "sessions" / "--F-use_code-MTA5_l--" / "cc04bcf2-36ca-fceb-266f-0012eaa83ebd" / "session.jsonl.zstd"
sys.stdout.reconfigure(encoding="utf-8")
if not S.exists():
    print("NOT FOUND", S)
    raise SystemExit(0)
print("file size:", S.stat().st_size)
data = zstd.ZstdDecompressor().stream_reader(open(S, "rb")).read().decode("utf-8", "replace")
print("lines:", data.count(chr(10)))
def txt(o):
    c = o.get("data", {}).get("content") or o.get("content")
    if isinstance(c, list):
        out=[]
        for b in c:
            if isinstance(b, dict) and b.get("type")=="text":
                out.append(b.get("text",""))
        return " ".join(out)
    return ""
n=0
for ln in data.splitlines()[-400:]:
    try: o=json.loads(ln)
    except Exception: continue
    t=o.get("type")
    if t=="user/message":
        ts=dt.datetime.fromtimestamp(o.get("time",0)/1000,tz=dt.timezone.utc).strftime("%m-%d %H:%M:%S")
        print("USER",ts,"|",txt(o)[:200].replace(chr(10)," "))
        n+=1
    elif t=="assistant/message":
        x=txt(o)
        if x.strip():
            ts=dt.datetime.fromtimestamp(o.get("time",0)/1000,tz=dt.timezone.utc).strftime("%m-%d %H:%M:%S")
            print("ASST",ts,"|",x[:400].replace(chr(10)," "))
    elif t in ("turn/end",):
        err=o.get("data",{})
        if err.get("error"):
            print("TURN_ERROR:", json.dumps(err,ensure_ascii=False)[:400])
print("user msgs in tail:",n)
