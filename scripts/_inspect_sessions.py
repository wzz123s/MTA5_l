# -*- coding: utf-8 -*-
"""_inspect_sessions.py - 扫描 ~/.dsh/sessions/<ws> 下最新会话, 找出QQ入站与元数据"""
import json, os, sys, zstandard as zstd
from pathlib import Path

S = Path(os.environ["USERPROFILE"]) / ".dsh" / "sessions" / "--F-use_code-MTA5_l--"
sys.stdout.reconfigure(encoding="utf-8")

def lines_of(p: Path):
    dctx = zstd.ZstdDecompressor()
    with p.open("rb") as fh:
        for chunk in dctx.read_to_iter(fh):
            pass
    # simpler: stream
    data = zstd.ZstdDecompressor().stream_reader(p.open("rb"))
    text = data.read().decode("utf-8", "replace")
    return text.splitlines()

dirs = sorted([d for d in S.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True)
print("session dirs:", len(dirs))
for d in dirs[:6]:
    f = d / "session.jsonl.zstd"
    if not f.exists():
        continue
    mtime = f.stat().st_mtime
    import datetime as dt
    ts = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).strftime("%m-%d %H:%M:%S")
    try:
        lines = lines_of(f)
    except Exception as e:
        print(f.name, ts, "ERR", e)
        continue
    print("---", f.parent.name, "mtime", ts, "lines", len(lines))
    types = {}
    texts = []
    meta_hits = []
    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        t = obj.get("type") or obj.get("kind") or "?"
        types[t] = types.get(t, 0) + 1
        s = json.dumps(obj, ensure_ascii=False)
        if any(k in s.lower() for k in ("openid", "c2c", "qqbot", "peer", "im-qqbot")):
            meta_hits.append(s[:600])
        if t in ("user_message", "assistant_message", "message") or (t == "?") :
            pass
        # capture user/assistant text previews
        for key in ("text", "content"):
            if key in obj and isinstance(obj[key], str) and len(obj[key]) < 300:
                texts.append((t, obj[key][:200]))
    print("   types:", {k: v for k, v in sorted(types.items(), key=lambda x: -x[1])[:12]})
    if meta_hits:
        print("   META HITS:")
        for h in meta_hits[:4]:
            print("    ", h)
    if texts:
        for t, x in texts[-6:]:
            print("   txt:", t, "|", x.replace(chr(10), " "))
