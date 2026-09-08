# 1H_M30_4H 验证结果摘要

## 主推荐结果

| combo | frames | primary_variant | primary_desc | trades | wr | pf | ev | pnl | test_n | test_pf | test_ev |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1H_M30_4H | 30M / 1H / 4H | 1H_M30_4H__1h_dir_align | 1H 方向同向 | 648 | 29.32098765432099 | 1.383391787248608 | 1.2480077160493832 | 808.7090000000003 | 195 | 1.2864976520503184 | 0.8300512820512815 |

## Top 候选门

| variant | desc | n | wr | pf | ev | test_pf | test_ev |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1H_M30_4H__1h_dir_align | 1H 方向同向 | 648 | 29.32098765432099 | 1.383391787248608 | 1.2480077160493832 | 1.2864976520503184 | 0.8300512820512815 |
| 1H_M30_4H__1h_recent2_any | 1H 最近2根至少1根同向_对照 | 652 | 29.4478527607362 | 1.3763451815736885 | 1.2293696319018397 | 1.3085752821876202 | 0.8894540816326535 |
| 1H_M30_4H__4h_bias55_signed_top30 | 4H Bias_55 signed top30% | 576 | 29.166666666666668 | 1.3108859118706289 | 1.1009322916666666 | 1.2677706233991144 | 0.8526358381502889 |

## 门扫描预览

| gate_family | gate_param | desc | trades | wr | pf | ev | test_pf |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 方向族 | 1H_M30_4H__1h_dir_align | 1H 方向同向 | 648 | 29.3210 | 1.3834 | 1.2480 | 1.2865 |
| 对照实验 | 1H_M30_4H__1h_recent2_any | 1H 最近2根至少1根同向_对照 | 652 | 29.4479 | 1.3763 | 1.2294 | 1.3086 |
| 带方向强度族 | 1H_M30_4H__4h_bias55_signed_top30 | 4H Bias_55 signed top30% | 576 | 29.1667 | 1.3109 | 1.1009 | 1.2678 |
| 位置族 | 1H_M30_4H__4h_close_side | 4H close位于SMA13交易方向一侧 | 764 | 27.7487 | 1.3033 | 1.0375 | 1.4546 |
| 带方向强度族 | 1H_M30_4H__4h_bias13_signed_pos | 4H Bias_13 signed > 0 | 764 | 27.7487 | 1.3033 | 1.0375 | 1.4546 |
| 带方向强度族 | 1H_M30_4H__30m_bias55_signed_pos | 30M Bias_55 signed > 0 | 1170 | 29.4872 | 1.2857 | 1.0073 | 1.2593 |
| 带方向强度族 | 1H_M30_4H__30m_bias5_13_55_signed_pos | 30M Bias_5+13+55 signed > 0 | 1170 | 29.4872 | 1.2857 | 1.0073 | 1.2593 |
| 带方向强度族 | 1H_M30_4H__4h_bias5_signed_top30 | 4H Bias_5 signed top30% | 580 | 29.3103 | 1.2825 | 0.9592 | 1.3491 |
| 带方向强度族 | 1H_M30_4H__4h_bias5_13_signed_pos | 4H Bias_5+13 signed > 0 | 547 | 28.3364 | 1.2709 | 0.9305 | 1.1918 |
| 带方向强度族 | 1H_M30_4H__4h_bias5_signed_pos | 4H Bias_5 signed > 0 | 691 | 28.2200 | 1.2477 | 0.8483 | 1.2906 |

## Stage Top 3

| combo | variant | stage1_r | stage2_trail_r | stage2_force_r | n | wr | pf | ev | pnl | maxcl | test_pf | test_ev | sample_ok | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1H_M30_4H | 1H_M30_4H__1h_dir_align | 2.0 | 2.5 | 4.0 | 648 | 29.32098765432099 | 0.7572142150313952 | -2.370931327160493 | -1536.3634999999997 | 13 | 0.7895474200874042 | -1.829192307692308 | True | 1009.1038183639456 |
| 1H_M30_4H | 1H_M30_4H__1h_dir_align | 2.0 | 2.5 | 3.0 | 648 | 29.32098765432099 | 0.7520541834135 | -2.421321759259259 | -1569.0164999999995 | 13 | 0.7849972534977342 | -1.868741025641025 | True | 1009.0421099059452 |
| 1H_M30_4H | 1H_M30_4H__1h_dir_align | 2.0 | 2.0 | 4.0 | 648 | 29.32098765432099 | 0.742167981287162 | -2.51786574074074 | -1631.576999999999 | 13 | 0.773153073102981 | -1.9716871794871809 | True | 1008.9176286442628 |

## 仓位 Top 3

| units | lots | n | wr | pf | ev | pnl_$ | maxcl | test_pf | test_ev | combo | variant | stage1_r | stage2_trail_r | stage2_force_r | balanced_bonus | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5/0.5/2.0 | 0.01/0.01/0.04 | 648 | 29.32098765432099 | 1.0703030011400017 | 0.6865459104938278 | 88.97634999999998 | 13 | 1.0380225360688615 | 0.3304807692307699 | 1H_M30_4H | 1H_M30_4H__1h_dir_align | 2.0 | 2.5 | 4.0 | 0 | 12.792806001747618 |
| 0.5/1.0/1.5 | 0.01/0.02/0.03 | 648 | 29.32098765432099 | 0.9204159978205018 | -0.7771797839506176 | -100.72249999999995 | 13 | 0.9207588370406689 | -0.6887410256410255 | 1H_M30_4H | 1H_M30_4H__1h_dir_align | 2.0 | 2.5 | 4.0 | 1 | 11.330134056607344 |
| 1.0/0.5/1.5 | 0.02/0.01/0.03 | 648 | 29.32098765432099 | 0.9071012183508947 | -0.9072056327160488 | -117.57385 | 13 | 0.9068111191155966 | -0.809970512820514 | 1H_M30_4H | 1H_M30_4H__1h_dir_align | 2.0 | 2.5 | 4.0 | 0 | 10.86649030908582 |

## StopSpec 推荐

| combo | current_variant | focus_tf | stage_params | units | lots | grid_lo | grid_hi | primary_stop_range | secondary_stop_range | acceptable_stop_range | stopspec_source | primary_trades | primary_pf | primary_test_pf | primary_ev | primary_profit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1H_M30_4H | 1H_M30_4H__1h_dir_align | 1H | 2.0/2.5/4.0 | 0.5/0.5/2.0 | 0.01/0.01/0.04 | 2 | 4/6/8/20 | 2-8pt | 2-6pt | 2-20pt | stop_distance | 310 | 1.089416810401293 | 1.0918708297428108 | 0.9512056451612924 | 58.97474999999999 |

## EA 对齐状态

| item | status | note |
| --- | --- | --- |
| MT5 raw data | done | History manifest and live smoke output exist for this strategy. |
| Research parameters | done | Stage / StopSpec / position profile exported to ea_parameter_pack.json. |
| Feature rules | done | Bias uses directional signed fields; StopSpec uses structural stop_distance. |
| EA source file | partial | Dedicated mq5 exists, but it still inherits the old EA structure. |
| Research .set | done | 1H_M30_4H_Strategy_EA.mt5_raw_research_20260725.set generated for backtest only. |
| EA compile | pending | Compile in MetaEditor and keep the compiler log before deployment. |
| Python vs EA alignment | pending | Current alignment is not refreshed for the MT5-raw profile; EA ledger is required. |
| Live deployment | blocked | Use only for MT5 Strategy Tester or demo until alignment passes. |
