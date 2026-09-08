# -*- coding: utf-8 -*-
"""v39: 等待回测完成（轮询停止->开始）"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

def find_mt5():
    d = Desktop(backend="win32")
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[" in t:
                return w
        except Exception:
            pass
    return None

def btn_status(mt5):
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止", "跳过"):
                return c.window_text(), c
        except Exception:
            pass
    return None, None

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

print("等待回测完成...")
start_t = time.time()
for i in range(40):  # 40 * 15s = 10 分钟上限
    time.sleep(15)
    st, c = btn_status(mt5)
    elapsed = time.time() - start_t
    if st == "开始":
        print("t=%.0fs 回测完成！(按钮变回 开始)" % elapsed)
        break
    else:
        # 读进度信息（如果有）
        print("t=%.0fs 状态=%r" % (elapsed, st))
else:
    print("超时（10分钟）仍未见完成")

# 最终状态
st, c = btn_status(mt5)
print("最终按钮: %r" % st)
