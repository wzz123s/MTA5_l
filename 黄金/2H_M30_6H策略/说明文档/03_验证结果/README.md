# 2H_M30_6H 验证结果摘要

## 主推荐结果

| combo | frames | primary_variant | primary_desc | trades | wr | pf | ev | pnl | test_n | test_pf | test_ev |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2H_M30_6H | 30M / 2H / 6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 6H Bias_5+13+55 signed > 0 | 286 | 32.16783216783217 | 2.0398915909826427 | 7.651031468531466 | 2188.195 | 86 | 2.1045326314564914 | 14.131441860465117 |

## Top 候选门

| variant | desc | n | wr | pf | ev | test_pf | test_ev |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2H_M30_6H__6h_bias5_13_55_signed_pos | 6H Bias_5+13+55 signed > 0 | 286 | 32.16783216783217 | 2.0398915909826427 | 7.651031468531466 | 2.1045326314564914 | 14.131441860465117 |
| 2H_M30_6H__stack_core | 30M close同侧 + 2H Bias_13 signed > 0 + 6H Bias_55 signed top30% | 243 | 33.744855967078195 | 1.969404490624368 | 8.457423868312759 | 2.0904071289602 | 15.546890410958904 |
| 2H_M30_6H__6h_bias5_13_signed_pos | 6H Bias_5+13 signed > 0 | 362 | 30.662983425414364 | 1.780772808594463 | 6.01209944751381 | 1.6268954482990343 | 8.76377981651376 |

## 门扫描预览

| gate_family | gate_param | desc | trades | wr | pf | ev | test_pf |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 带方向强度族 | 2H_M30_6H__6h_bias5_13_55_signed_pos | 6H Bias_5+13+55 signed > 0 | 286 | 32.1678 | 2.0399 | 7.6510 | 2.1045 |
| 组合族 | 2H_M30_6H__stack_core | 30M close同侧 + 2H Bias_13 signed > 0 + 6H Bias_55 signed top30% | 243 | 33.7449 | 1.9694 | 8.4574 | 2.0904 |
| 带方向强度族 | 2H_M30_6H__6h_bias5_13_signed_pos | 6H Bias_5+13 signed > 0 | 362 | 30.6630 | 1.7808 | 6.0121 | 1.6269 |
| 带方向强度族 | 2H_M30_6H__6h_bias55_signed_top30 | 6H Bias_55 signed top30% | 354 | 34.1808 | 1.7716 | 6.7269 | 1.9017 |
| 带方向强度族 | 2H_M30_6H__6h_bias5_signed_top30 | 6H Bias_5 signed top30% | 359 | 31.1978 | 1.7662 | 6.1140 | 1.7712 |
| 带方向强度族 | 2H_M30_6H__6h_bias5_signed_pos | 6H Bias_5 signed > 0 | 424 | 31.8396 | 1.7527 | 5.7181 | 1.7509 |
| 方向族 | 2H_M30_6H__all_dir_align | 全组合方向同向 | 349 | 31.5186 | 1.7140 | 5.4459 | 1.5925 |
| 方向族 | 2H_M30_6H__2h_dir_align | 2H 方向同向 | 461 | 30.5857 | 1.6402 | 4.9681 | 1.6528 |
| 带方向强度族 | 2H_M30_6H__30m_bias55_signed_top30 | 30M Bias_55 signed top30% | 359 | 33.1476 | 1.6363 | 6.4249 | 1.6409 |
| 位置族 | 2H_M30_6H__6h_close_side | 6H close位于SMA13交易方向一侧 | 506 | 31.8182 | 1.6202 | 5.0126 | 1.3769 |

## Stage Top 3

| combo | variant | stage1_r | stage2_trail_r | stage2_force_r | n | wr | pf | ev | pnl | maxcl | test_pf | test_ev | sample_ok | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 2.0 | 2.5 | 4.0 | 286 | 32.16783216783217 | 1.0533944825075692 | 1.1785541958041954 | 337.0664999999999 | 14 | 1.1061020690340468 | 4.072424418604648 | True | 1012.7697200470598 |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 2.0 | 2.5 | 3.0 | 286 | 32.16783216783217 | 1.0460580706470817 | 1.016620629370632 | 290.7535000000007 | 14 | 1.0951329712463165 | 3.651406976744188 | True | 1012.6711790615508 |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 2.0 | 2.0 | 4.0 | 286 | 32.16783216783217 | 1.0320807431425785 | 0.7081048951048984 | 202.5180000000009 | 14 | 1.085824802233597 | 3.294139534883719 | True | 1012.5066191337952 |

## 仓位 Top 3

| units | lots | n | wr | pf | ev | pnl_$ | maxcl | test_pf | test_ev | combo | variant | stage1_r | stage2_trail_r | stage2_force_r | balanced_bonus | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5/0.5/2.0 | 0.01/0.01/0.04 | 286 | 32.16783216783217 | 1.5466430367451065 | 12.0658243006993 | 690.16515 | 14 | 1.6053173502452691 | 23.233375 | 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 2.0 | 2.5 | 4.0 | 0 | 18.918381553955587 |
| 0.5/1.0/1.5 | 0.01/0.02/0.03 | 286 | 32.16783216783217 | 1.3105539115306004 | 6.854727272727277 | 392.0904 | 14 | 1.3683846108170463 | 14.139389534883716 | 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 2.0 | 2.5 | 4.0 | 1 | 16.279402882394642 |
| 1.0/0.5/1.5 | 0.02/0.01/0.03 | 286 | 32.16783216783217 | 1.2894836077220753 | 6.389651223776226 | 365.48805 | 14 | 1.3430348084622694 | 13.166409883720933 | 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 2.0 | 2.5 | 4.0 | 0 | 15.708698718620814 |

## StopSpec 推荐

| combo | current_variant | focus_tf | stage_params | units | lots | grid_lo | grid_hi | primary_stop_range | secondary_stop_range | acceptable_stop_range | stopspec_source | primary_trades | primary_pf | primary_test_pf | primary_ev | primary_profit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 6H | 2.0/2.5/4.0 | 0.5/0.5/2.0 | 0.01/0.01/0.04 | 2 | 6/8/10/14/56 | 2-10pt | 2-14pt | 2-56pt | stop_distance | 179 | 1.8674402677045503 | 2.708470675044618 | 14.855370111731844 | 531.82225 |

## EA 对齐状态

| item | status | note |
| --- | --- | --- |
| MT5 raw data | done | History manifest and live smoke output exist for this strategy. |
| Research parameters | done | Stage / StopSpec / position profile exported to ea_parameter_pack.json. |
| Feature rules | done | Bias uses directional signed fields; StopSpec uses structural stop_distance. |
| EA source file | partial | Dedicated mq5 exists, but it still inherits the old EA structure. |
| Research .set | done | 2H_M30_6H_Strategy_EA.mt5_raw_research_20260725.set generated for backtest only. |
| EA compile | pending | Compile in MetaEditor and keep the compiler log before deployment. |
| Python vs EA alignment | pending | Current alignment is not refreshed for the MT5-raw profile; EA ledger is required. |
| Live deployment | blocked | Use only for MT5 Strategy Tester or demo until alignment passes. |
