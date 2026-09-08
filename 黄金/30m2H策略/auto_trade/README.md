# 30m2H Auto Trade 最终部署入口

> 创建时间：2026-07-26  
> 目标：按 `黄金/1H_M30_4H策略/auto_trade` 的方式整理最终 EA 证据包。

## 当前定位

历史 EA 和大量调试文件仍保留在：

```text
黄金/30m2H策略/参考实现工程/auto_trade
```

从最终逐笔对齐推进开始，顶层 `黄金/30m2H策略/auto_trade` 只放最终冻结版部署文件。

## 最终应包含

- `30m2H_CurrentCandidate_EA.mq5`
- `30m2H_CurrentCandidate_EA.ex5`
- `30m2H_CurrentCandidate_EA.set`
- `30m2H_CurrentCandidate_EA.compile.log`
- `30m2H_CurrentCandidate_EA.alignment_<date_range>.ini`
- `compare_python_vs_ea.py`

## 当前状态

最终冻结版尚未生成，原因是 Python 基线存在两个口径：

- 顶层快照：102 笔，PF 11.54，PnL `$2200`。
- 参考实现工程复跑：121 笔，PF 2.96，PnL `$913`。

必须先完成 `baseline_freeze`，再生成最终 EA 和逐笔对齐包。

## 安全默认

最终 EA 默认必须保留：

- `InpSimMode=true`
- `InpAllowRealTrading=false`
- `InpMaxOpenPositions=1`
- spread / risk / margin guards

任何真实交易开关都必须在最终历史逐笔 matched 和部署前评审通过后，由操作者显式打开。
