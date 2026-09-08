# Python-MT5 shift90 重建报告（2026-07-12）

## 口径说明
- MT5 bar export 来源：`F:\use_code\MTA5_l\黄金\30m2H策略\data\validation\mt5_only_bar_export_session5_20260712.csv`
- M30 时间语义：`bar_time + 90min`。
- 输出目录为版本化目录 `黄金/30m2H策略/data/signals_mt5_shift90_20260712`，未覆盖旧 `signals_mt5`。
- 本轮是诊断重建：同时测试 MT5 bar-level H2 与当前 Python decision H2，避免把 H2 时间语义误当成 M30 数据问题。

## 指标摘要
| variant | accepted | picked | trades | final_python_x5 | any_sl | all_sl | win_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mt5_h2_barlevel_direct | 307 | 77 | 77 | 5743.24 | 56 | 16 | 64.94% |
| mt5_h2_barlevel_q2early | 307 | 77 | 77 | 5743.24 | 56 | 16 | 64.94% |
| python_h2_context_q2early | 379 | 98 | 98 | 3188.77 | 80 | 33 | 51.02% |

## 与 MT5 EA 信号集合对比
| variant | Python signals | MT5 signals | shared | Python-only | MT5-only | best offset |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mt5_h2_barlevel_direct | 77 | 78 | 13 | 64 | 65 | 0min |
| mt5_h2_barlevel_q2early | 77 | 78 | 13 | 64 | 65 | 0min |
| python_h2_context_q2early | 98 | 78 | 37 | 61 | 41 | 0min |

## 判断
- `mt5_h2_barlevel_*` 总笔数接近 MT5 EA，但 shared 很低，不能作为对齐成功版本。
- `python_h2_context_q2early` 的 shared 更高，说明 H2 decision context 仍比 bar-level H2 export 更接近当前 EA/Python 对齐口径。
- 本报告只用于第 2 步重建诊断，不代表最终 MT5 EA ledger 对齐完成。
