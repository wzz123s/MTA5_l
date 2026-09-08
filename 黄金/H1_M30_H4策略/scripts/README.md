# H1_M30_H4 Scripts

> 更新时间：2026-07-05 20:12:47

## 目录说明

- `data_source`
  - 负责同步策略所需原始数据。
- `prepare`
  - 负责生成 30M / 1H / 4H 标准化 K 线和上下文交易数据。
- `signals`
  - 负责导出单因子、多因子候选门和候选交易机会。
- `validate`
  - 负责把全局认证结果按 `H1_M30_H4` 过滤并落到本策略目录。
- `bundle`
  - 负责文档生成与整包构建。

## 使用方式

```powershell
python H1_M30_H4策略/scripts/bundle/build_strategy_bundle.py
```
