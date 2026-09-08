# -*- coding: utf-8 -*-
from pathlib import Path

# 1) EA接入方案：标记已实施 + 插入实现章节
p = Path(r"F:\use_code\MTA5_l\宏观日历研究\报告\EA接入方案.md")
text = p.read_text(encoding="utf-8")

old_status = "\uff5c \u72b6\u6001\uff1a\u65b9\u6848\u8bbe\u8ba1\uff08\u672a\u5b9e\u65bd\uff09"
new_status = "\uff5c \u72b6\u6001\uff1a**\u5df2\u5b9e\u65bd\uff082026-08-26\uff0c\u9ed8\u8ba4\u5173\u95ed\uff0c\u5f85\u6a21\u62df\u76d8\u9a8c\u8bc1\uff09**"
assert text.count(old_status) == 1
text = text.replace(old_status, new_status)

old_h3 = "## 3. EA \u6539\u9020\u8bbe\u8ba1\uff08USOIL4H \u4e8b\u4ef6\u8fc7\u6ee4\u4e3a\u4f8b\uff09"
new_h3 = ("## 3. EA \u6539\u9020\u5b9e\u73b0\uff082026-08-26 \u5df2\u90e8\u7f72\uff09\n\n"
          "\u4e09\u4e2a EA \u5df2\u6ce8\u5165\u4e8b\u4ef6\u95e8\uff08\u9ed8\u8ba4 InpEventFilterOn=false\uff0c\u884c\u4e3a\u4e0d\u53d8\uff09\uff1a\n\n"
          "| EA | InpEventFilterHrs | \u6ce8\u5165\u4f4d\u7f6e |\n|---|---|---|\n"
          "| 30m2H_ABC_EA | 2 | \u4fe1\u53f7\u63a5\u53d7\u5904\uff08cd_ok \u6761\u4ef6\u65c1\uff09 |\n"
          "| 2H_M30_6H_ABC_EA | 1 | \u4fe1\u53f7\u63a5\u53d7\u5904 |\n"
          "| USOIL4H_Gate_On2H_EA | 8 | \u5f00\u4ed3 ok \u6761\u4ef6 |\n\n"
          "\u5b9e\u73b0\u8981\u70b9\uff1aOnTimer(60s) \u5f02\u6b65\u5237\u65b0\uff08**\u4e0d\u5728 OnInit \u8c03\u65e5\u5386 API**\u2014\u2014\u9996\u6b21\u8c03\u7528\u4f1a\u963b\u585e\u540c\u6b65\u5bfc\u81f4 5 \u5206\u949f\u521d\u59cb\u5316\u8d85\u65f6\uff09\uff1b\n"
          "CalendarValueHistory(now, now+N*3600) \u53d6\u672a\u6765 N \u5c0f\u65f6\u4e8b\u4ef6\uff0cCalendarEventById \u5224 importance>=3 \u5373\u7f6e\u9ed1\u540d\u5355\uff1b\n"
          "300s \u7f13\u5b58\uff1b\u5f00\u5173\u5173\u95ed\u65f6\u96f6\u65e5\u5386\u8c03\u7528\u3001\u96f6\u884c\u4e3a\u53d8\u5316\u3002\u8865\u4e01\u811a\u672c\uff1ascripts/patch_ea_event_gate.py\u3002\n\n### 3.1 \u53c2\u6570\uff08\u4ee5 30m2H \u4e3a\u4f8b\uff09")
assert text.count(old_h3) == 1
text = text.replace(old_h3, new_h3)

text += "\n\n---\n\n## 5. \u90e8\u7f72\u8bb0\u5f55\uff082026-08-26 00:32\uff09\n\n" \
        "- \u4e09\u4e2a EA \u7f16\u8bd1 0 errors\uff08warning 39 \u4e3a\u65e7\u4ee3\u7801\u539f\u6709\uff1atickets ulong \u5f53\u5e03\u5c14\uff09\uff0cex5 \u5df2\u90e8\u7f72\u5230\u7ec8\u7aef Experts\\Advisors\n" \
        "- \u7ec8\u7aef\u91cd\u542f\u540e 8 \u4e2a EA \u5168\u90e8\u52a0\u8f7d\u6210\u529f\uff08\u542b\u6539\u7248\u7684 30m2H_ABC / 2H_M30_6H_ABC / USOIL4H_Gate_On2H\uff09\n" \
        "- \u9ed8\u8ba4\u53c2\u6570\u5168\u90e8\u5173\u95ed \u2192 \u5b9e\u76d8\u884c\u4e3a\u4e0e\u90e8\u7f72\u524d\u5b8c\u5168\u4e00\u81f4\uff1b\u5f00\u542f\u65b9\u5f0f\uff1a\u56fe\u8868\u5c5e\u6027 \u2192 \u8f93\u5165 \u2192 Macro Calendar Filter \u7ec4 \u2192 InpEventFilterOn=true\uff08\u5efa\u8bae\u5148\u5728\u6a21\u62df\u76d8\u9a8c\u8bc1 2-4 \u5468\uff09\n" \
        "- \u9a8c\u8bc1\u8981\u70b9\uff1a\u5f00\u542f\u540e\u65e5\u5fd7\u51fa\u73b0 [CAL] event blackout: ... \u8868\u793a\u4e8b\u4ef6\u95e8\u751f\u6548\uff1b[CAL] signal blocked... \u8868\u793a\u4fe1\u53f7\u88ab\u62e6\u622a"
p.write_text(text, encoding="utf-8")
print("EA doc updated")

# 2) 计划文档状态
p2 = Path(r"F:\use_code\MTA5_l\宏观日历研究\计划_宏观数据影响测试.md")
t2 = p2.read_text(encoding="utf-8")
old_line = "- \u2b1c \u540e\u7eed\uff1aUSOIL4H \u4e8b\u4ef6\u8fc7\u6ee4\u6a21\u62df\u76d8\u524d\u5411\u9a8c\u8bc1\uff082-4 \u5468\uff09\uff1bsurprise \u65b9\u5411\u4e00\u81f4\u6027\u7814\u7a76\uff1b2H_M30_6H \u975e\u519c\u4e13\u9879\u8fc7\u6ee4\u8bd5\u9a8c\uff1b30m2H/2H \u53e0\u52a0\u201c\u4e8b\u4ef6\u524d1-2h\u4e0d\u5f00\u4ed3\u201d\u7684\u5b9e\u76d8\u8bd5\u70b9"
new_line = ("- \u2705 **EA \u843d\u5730\uff082026-08-26\uff09**\uff1a30m2H(T=2h)/2H_M30_6H(T=1h)/USOIL4H(T=8h) \u4e09\u4e2a EA \u5df2\u6ce8\u5165\u201c\u9ad8\u5f71\u54cd\u4e8b\u4ef6\u524dN\u5c0f\u65f6\u4e0d\u5f00\u4ed3\u201d\u53ef\u9009\u95e8\uff08\u9ed8\u8ba4\u5173\uff0cOnTimer \u5f02\u6b65\u5237\u65b0\uff0c\u7f16\u8bd1\u90e8\u7f72\u5b8c\u6210\uff0c8 EA \u6b63\u5e38\u52a0\u8f7d\uff09\n"
            "- \u2b1c \u540e\u7eed\uff1a\u4e8b\u4ef6\u8fc7\u6ee4\u6a21\u62df\u76d8\u524d\u5411\u9a8c\u8bc1\uff082-4 \u5468\uff09\uff1bsurprise \u65b9\u5411\u4e00\u81f4\u6027\u7814\u7a76\uff1b2H_M30_6H \u975e\u519c\u4e13\u9879\u8fc7\u6ee4\u8bd5\u9a8c")
if old_line not in t2:
    # 可能引号不同，逐行找
    for ln in t2.splitlines():
        if "\u540e\u7eed\uff1aUSOIL4H" in ln:
            t2 = t2.replace(ln, new_line)
            print("plan line replaced (fuzzy)")
            break
    else:
        raise SystemExit("plan line not found")
else:
    t2 = t2.replace(old_line, new_line)
    print("plan line replaced (exact)")
p2.write_text(t2, encoding="utf-8")
