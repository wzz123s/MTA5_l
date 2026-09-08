# 1H_M30_4H 策略

这是按 `30m2H策略` 标准目录新建的策略工程。

## 策略定位

- 组合周期：`30M / 1H / 4H`
- 聚焦周期：`30M`
- 当前策略编码：`1H_M30_4H`
- 对齐母版：`30m2H策略`
- 参考验证：已从 `H1_M30_H4` 历史认证包导入并统一到 `1H_M30_4H` 命名。

## 推荐阅读顺序

1. `说明文档/01_总览说明/策略说明.md`
2. `说明文档/01_总览说明/一次性执行计划.md`
3. `说明文档/02_策略流程/流程说明.md`
4. `scripts/README.md`
5. `data/validation/README.md`

## 一键构建

```powershell
python 黄金/1H_M30_4H策略/scripts/bundle/build_strategy_bundle.py
```
