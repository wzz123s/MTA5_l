# 30m2H Python Expected Ledger 构建记录

> 生成时间：2026-08-11
> 基线：177 笔冻结口径（Layer3 threshold 0.357236）
> 每笔拆 3 个 stage 子头寸 → 共 279 行

| 指标 | 值 |
| --- | ---: |
| 交易数 | 177 |
| Ledger 行数 | 279 |
| stage1 行数 | 93 |
| stage2 行数 | 93 |
| stage3 行数 | 93 |
| exit 原因 | SL hit / 2.0R TP / trail/SL hit / 4.0R forced / M30 merged cross |

## 参数

- Layer1: `|H2 Bias_55| > 3.0%`
- Layer2: `pre_cross + cross + post_n(2-6)`
- Layer3: `Bias_5 top 34%`
- M15: `replace_any + rescue`
- H2: `Layer1 q2 early-gate`
- Stage1: `2.0R` / Stage2: `1.5R trail / 4.0R force` / Stage3: `M30 merged cross`
- stop spec: `[5, 35] pt`

## 文件

- `..\data\validation\final_ea_alignment_20260811\python_expected_trade_ledger.csv`