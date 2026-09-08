# -*- coding: utf-8 -*-
"""解析 rollout JSONL, 提取命令和关键操作."""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

rollout = r"C:\Users\3762\.codex\sessions\2026\08\13\rollout-2026-08-13T20-21-11-019ffb11-bb59-7640-80b6-d60cccaaa79f.jsonl"

lines = open(rollout, 'r', encoding='utf-8').readlines()
print("总行数:", len(lines))

# 提取每条记录的类型和关键字段
types = {}
tool_names = {}
for i, line in enumerate(lines):
    try:
        obj = json.loads(line)
    except Exception:
        continue
    t = obj.get('type', '')
    types[t] = types.get(t, 0) + 1
    # 找 tool call
    if obj.get('type') in ('response_item', 'agent_message', 'tool_call', 'assistant', 'message'):
        pass
    # 尝试多种结构
    tc = obj.get('tool_call') or obj.get('toolCall') or {}
    if tc:
        name = tc.get('name') or tc.get('tool_name') or ''
        if name:
            tool_names[name] = tool_names.get(name, 0) + 1

print("\n=== 记录类型分布 ===")
for k, v in sorted(types.items(), key=lambda x: -x[1]):
    print("  %s: %d" % (k, v))

# 直接搜含 shell/py 命令的行
print("\n=== 含 shell/python/pywinauto/tester 的行 (前 30) ===")
count = 0
for i, line in enumerate(lines):
    if any(k in line for k in ['pywinauto', 'run_shell', 'shell', 'tester', 'run_tester', 'MetaEditor', '.ex5', '.set', 'click_input', 'BM_CLICK']):
        # 截断打印
        print("行%d: %s" % (i, line[:300]))
        count += 1
        if count >= 30:
            break
