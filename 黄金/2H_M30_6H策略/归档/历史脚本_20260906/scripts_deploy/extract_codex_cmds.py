# -*- coding: utf-8 -*-
"""提取 rollout 所有 shell 命令 + Python 脚本, 筛 Tester 相关."""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

rollout = r"C:\Users\3762\.codex\sessions\2026\08\13\rollout-2026-08-13T20-21-11-019ffb11-bb59-7640-80b6-d60cccaaa79f.jsonl"

cmds = []
for line in open(rollout, 'r', encoding='utf-8'):
    try:
        obj = json.loads(line)
    except Exception:
        continue
    p = obj.get('payload', {})
    if p.get('type') == 'function_call':
        name = p.get('name', '')
        try:
            args = json.loads(p.get('arguments', '{}'))
        except Exception:
            args = {}
        cmd = args.get('command') or args.get('cmd') or args.get('file_path') or ''
        if cmd:
            cmds.append(cmd)

print("总命令数:", len(cmds))

# 筛 Tester/EA/参数/部署相关
kw = ['pywinauto', 'click_input', '.set', '.mq5', '.ex5', 'terminal', 'MetaEditor', 'Tester', 'tester', 'parameter', 'copy', 'Copy-Item', 'Inp', 'EA', 'Expert']
print("\n=== Tester/部署相关命令 ===")
n = 0
for c in cmds:
    if any(k.lower() in c.lower() for k in ['pywinauto', 'click_input', '.set', '.ex5', 'terminal', 'tester', 'parameter', 'copy-item', 'metaeditor']):
        print("---")
        print(c[:600])
        n += 1
        if n >= 25:
            break
