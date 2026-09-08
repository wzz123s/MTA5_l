# 阶段0 脚本说明（MCT 大周期拐点策略 · 规则与数据准备）

## 文件清单

| 脚本 | 功能 | 用法 |
|---|---|---|
| segment_analysis.py | 难论段分析核心库（SMMA→方向→v4合并→way→极值→穿越标记） | `import segment_analysis` |
| fetch_mt5_data.py | MT5 历史数据拉取 + raw_source_manifest.json | `python fetch_mt5_data.py --all` |
| validate_segments.py | 断言验证（验收标准） | `python validate_segments.py` |

## 数据流水线

```
python fetch_mt5_data.py --all --timeframes D1,H4,W1 --start 2016-01-01
→ data/raw/<source_id>/<SYMBOL>_<TF>.csv + raw_source_manifest.json

python validate_segments.py
→ 内置用例 + 全部 D1 数据的段分析断言（极值单调/穿越定位/数量守恒/止损方向）
```

## segment_analysis.analyze() 输出列

时间/OHLC + SMA_5/13/55 + 方向(good/up/bad/down) + 方向_合并后(v4) +
way/way_s/way_s_way/vol_way/vol_way_s_way（段内强度）+
up_high_price/up_high_sma13/down_low_price/down_low_sma13（段内极值）+
prev_seg_low_price/prev_seg_low_sma13/prev_seg_high_price/prev_seg_high_sma13（穿越点前段极值）+
long_entry/long_stop/short_entry/short_stop（开仓/止损价）

## 规范来源

- SMA均线参数配置_v3.1.md（F:\\use_code\\MTA5\\交易规则）
- 段的定义与方向标记.md（v4 严格链式吸收）
- 策略生成规则.md（F:\\use_code\\MTA5_l\\项目文档）
