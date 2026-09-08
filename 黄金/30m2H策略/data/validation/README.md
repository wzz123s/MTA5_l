# validation 数据层总览

这个目录存放 `scripts/validate` 的输出结果。

## 对应关系

- 日常验证脚本
  - 对应看：`../../scripts/validate/01_日常验证说明.md`
- MT5 对齐脚本
  - 对应看：`../../scripts/validate/02_MT5对齐说明.md`
- 实盘证据脚本
  - 对应看：`../../scripts/validate/03_实盘证据说明.md`
- 历史专题脚本
  - 对应看：`../../scripts/validate/04_历史专题说明.md`

## 目录命名规则

- 推荐格式：
  - `主题_日期`
- 例如：
  - `dynamic_risk_alignment_20260712`
  - `stage_state_final_live_gate_review_20260721`
  - `unmatched_signal_cause_20260713`

## 最低结构建议

每个子目录尽量至少包含：

- 一份说明文档
  - `README.md` 或 `*_review.md` 或 `*_report.md`
- 若干关键 CSV
- 必要时附带证据子目录

## 使用建议

- 先从脚本分组说明找到主题。
- 再回到这里看同主题的输出目录。
- 不把这里当作原始数据层使用。
