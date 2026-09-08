# -*- coding: utf-8 -*-
"""分析 [GATEDBG] 日志，定位 223 差异"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
lines = open(LOG, encoding='utf-16').read().splitlines()

# 找最近一次回测段
init_idx = -1
passed_idx = -1
for i in range(len(lines)-1, -1, -1):
    if 'Test passed' in lines[i]:
        passed_idx = i
        break
for i in range(passed_idx, -1, -1):
    if 'ABC EA initialized' in lines[i]:
        init_idx = i
        break
print("最近回测段: 行 %d ~ %d" % (init_idx+1, passed_idx+1))

seg = lines[init_idx:passed_idx+1]

# 提取 [GATEDBG]
gatedbg = []
for ln in seg:
    if '[GATEDBG]' in ln:
        m = re.search(r'\[GATEDBG\] (BUY|SELL) (\w+) sig=([\d.]+ \d+:\d+).*?stop_pts=([\d.]+) spec=([\d.]+)\.\.([\d.]+) cd_ok=(\w+) ev=(\w+)', ln)
        if m:
            gatedbg.append({
                'dir': m.group(1), 'mode': m.group(2), 'sig': m.group(3),
                'stop_pts': float(m.group(4)), 'spec_lo': float(m.group(5)), 'spec_hi': float(m.group(6)),
                'cd_ok': m.group(7), 'ev': m.group(8)
            })

print("[GATEDBG] 数量:", len(gatedbg))

# 统计 stop_pts 在 spec 范围内的
in_spec = [g for g in gatedbg if g['spec_lo'] <= g['stop_pts'] <= g['spec_hi']]
out_spec = [g for g in gatedbg if not (g['spec_lo'] <= g['stop_pts'] <= g['spec_hi'])]
print("stop_pts 在 spec 内:", len(in_spec))
print("stop_pts 在 spec 外:", len(out_spec))

# cd_ok=false 或 ev=true 的
cd_false = [g for g in gatedbg if g['cd_ok'] == 'false']
ev_true = [g for g in gatedbg if g['ev'] == 'true']
print("cd_ok=false:", len(cd_false))
print("ev=true:", len(ev_true))

# 应该 [SIGNAL] 的 = in_spec 且 cd_ok=true 且 ev=false
should_signal = [g for g in gatedbg if g['spec_lo'] <= g['stop_pts'] <= g['spec_hi'] and g['cd_ok']=='true' and g['ev']=='false']
print("应该[SIGNAL](spec内+cd_ok+!ev):", len(should_signal))

# [SIGNAL] 实际数
sig_cnt = sum(1 for ln in seg if '[SIGNAL]' in ln)
print("[SIGNAL] 实际数:", sig_cnt)

# 看 out_spec 的样本
print("\n=== stop_pts 在 spec 外的样本(前10) ===")
for g in out_spec[:10]:
    print("  %s %s sig=%s stop_pts=%.1f spec=%.0f..%.0f cd_ok=%s ev=%s" % (g['dir'], g['mode'], g['sig'], g['stop_pts'], g['spec_lo'], g['spec_hi'], g['cd_ok'], g['ev']))
