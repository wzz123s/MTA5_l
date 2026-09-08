# -*- coding: utf-8 -*-
"""搜所有 rollout 的 portable/Tester/部署命令."""
import sys, json, glob
sys.stdout.reconfigure(encoding='utf-8')

files = glob.glob(r"C:\Users\3762\.codex\sessions\2026\08\**\rollout-*.jsonl", recursive=True)
files += glob.glob(r"C:\Users\3762\.codex\archived_sessions\rollout-*.jsonl")

print("rollout 文件数:", len(files))
cmds = []
for f in files:
    for line in open(f, 'r', encoding='utf-8', errors='ignore'):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        p = obj.get('payload', {})
        if p.get('type') == 'function_call':
            try:
                args = json.loads(p.get('arguments', '{}'))
            except Exception:
                continue
            cmd = args.get('command') or args.get('file_path') or ''
            if cmd:
                cmds.append((f.split('rollout-')[-1][:20], cmd))

print("总命令数:", len(cmds))
print("\n=== portable/Tester 运行/参数设置 相关 ===")
n = 0
for fname, c in cmds:
    cl = c.lower()
    if any(k in cl for k in ['portable', 'mt5_portable', 'terminal64', 'tester', '/config', 'optimization', 'copy-item.*ex5', 'set.*inp', 'parameter', 'pywinauto', 'BM_CLICK', 'click_input', 'run_shell.*tester']):
        print("\n[%s]" % fname)
        print(c[:700])
        n += 1
        if n >= 40:
            break
