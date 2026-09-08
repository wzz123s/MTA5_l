
from pathlib import Path
rep = Path(r"F:\use_code\MTA5_l\宏观日历研究\报告\宏观日历影响分析报告.md")
sec = Path(r"F:\use_code\MTA5_l\宏观日历研究\scripts\_sec6.md").read_text(encoding="utf-8")
text = rep.read_text(encoding="utf-8")
marker = "---\n*数据：MT5 终端内置财经日历"
assert marker in text, "marker not found"
text = text.replace(marker, sec + marker)
rep.write_text(text, encoding="utf-8")
print("report updated, size:", len(text))
