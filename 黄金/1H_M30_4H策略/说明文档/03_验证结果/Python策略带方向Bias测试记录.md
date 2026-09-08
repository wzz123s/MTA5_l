# Python 带方向 Bias 测试记录

日期：2026-07-25

## 口径

- `bias5/bias13/bias55` 使用带方向偏离。
- 排名基于 Python 候选交易表现，优先看 `test_pf`，再看全样本 `pf/ev`。
- `recent2_any` 和 ATR 不进入本表。

## Top Signed-Bias 候选

| strategy | variant | desc | n | pf | ev | test_pf | test_ev | split_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1H_M30_4H | 1H_M30_4H__4h_bias13_signed_pos | 4H Bias_13 signed > 0 | 764 | 1.3033 | 1.0375 | 1.4546 | 1.3303 | 2022-10-27 |
| 1H_M30_4H | 1H_M30_4H__4h_bias5_signed_top30 | 4H Bias_5 signed top30% | 580 | 1.2825 | 0.9592 | 1.3491 | 1.0232 | 2022-10-18 |
| 1H_M30_4H | 1H_M30_4H__4h_bias5_signed_pos | 4H Bias_5 signed > 0 | 691 | 1.2477 | 0.8483 | 1.2906 | 0.8760 | 2022-10-18 |
| 1H_M30_4H | 1H_M30_4H__4h_bias55_signed_pos | 4H Bias_55 signed > 0 | 847 | 1.1406 | 0.4983 | 1.2681 | 0.8111 | 2022-11-02 |
| 1H_M30_4H | 1H_M30_4H__4h_bias55_signed_top30 | 4H Bias_55 signed top30% | 576 | 1.3109 | 1.1009 | 1.2678 | 0.8526 | 2022-12-07 |
| 1H_M30_4H | 1H_M30_4H__30m_bias55_signed_pos | 30M Bias_55 signed > 0 | 1170 | 1.2857 | 1.0073 | 1.2593 | 0.8459 | 2022-09-26 |
| 1H_M30_4H | 1H_M30_4H__30m_bias5_13_55_signed_pos | 30M Bias_5+13+55 signed > 0 | 1170 | 1.2857 | 1.0073 | 1.2593 | 0.8459 | 2022-09-26 |
| 1H_M30_4H | 1H_M30_4H__1h_bias13_signed_pos | 1H Bias_13 signed > 0 | 1448 | 1.1478 | 0.5180 | 1.2585 | 0.8334 | 2022-09-29 |
| 1H_M30_4H | 1H_M30_4H__1h_bias55_signed_top30 | 1H Bias_55 signed top30% | 580 | 1.0325 | 0.1220 | 1.2577 | 0.8001 | 2022-11-02 |
| 1H_M30_4H | 1H_M30_4H__1h_bias5_13_signed_pos | 1H Bias_5+13 signed > 0 | 1386 | 1.1171 | 0.4151 | 1.2488 | 0.8097 | 2022-10-05 |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_13_55_signed_pos | 6H Bias_5+13+55 signed > 0 | 286 | 2.0399 | 7.6510 | 2.1045 | 14.1314 | 2025-10-09 |
| 2H_M30_6H | 2H_M30_6H__6h_bias55_signed_top30 | 6H Bias_55 signed top30% | 354 | 1.7716 | 6.7269 | 1.9017 | 12.3920 | 2025-12-11 |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_signed_top30 | 6H Bias_5 signed top30% | 359 | 1.7662 | 6.1140 | 1.7712 | 10.7275 | 2025-10-31 |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_signed_pos | 6H Bias_5 signed > 0 | 424 | 1.7527 | 5.7181 | 1.7509 | 10.3976 | 2025-10-09 |
| 2H_M30_6H | 2H_M30_6H__30m_bias55_signed_top30 | 30M Bias_55 signed top30% | 359 | 1.6363 | 6.4249 | 1.6409 | 11.5643 | 2025-12-30 |
| 2H_M30_6H | 2H_M30_6H__6h_bias5_13_signed_pos | 6H Bias_5+13 signed > 0 | 362 | 1.7808 | 6.0121 | 1.6269 | 8.7638 | 2025-10-28 |
| 2H_M30_6H | 2H_M30_6H__30m_bias55_signed_pos | 30M Bias_55 signed > 0 | 729 | 1.5836 | 4.7476 | 1.5398 | 7.9271 | 2025-10-22 |
| 2H_M30_6H | 2H_M30_6H__30m_bias5_13_55_signed_pos | 30M Bias_5+13+55 signed > 0 | 729 | 1.5836 | 4.7476 | 1.5398 | 7.9271 | 2025-10-22 |
| 2H_M30_6H | 2H_M30_6H__2h_bias13_signed_pos | 2H Bias_13 signed > 0 | 560 | 1.5662 | 4.5076 | 1.4584 | 6.5592 | 2025-10-31 |
| 2H_M30_6H | 2H_M30_6H__2h_bias55_signed_top30 | 2H Bias_55 signed top30% | 357 | 1.5671 | 5.1304 | 1.4577 | 7.1343 | 2025-11-28 |

## 输出文件

- `1H_M30_4H`: `黄金/1H_M30_4H策略/data/validation/bias_signed_test/bias_signed_variant_summary.csv`
- `1H_M30_4H`: `黄金/1H_M30_4H策略/data/validation/bias_signed_test/bias_signed_top20.csv`
- `2H_M30_6H`: `黄金/2H_M30_6H策略/data/validation/bias_signed_test/bias_signed_variant_summary.csv`
- `2H_M30_6H`: `黄金/2H_M30_6H策略/data/validation/bias_signed_test/bias_signed_top20.csv`
