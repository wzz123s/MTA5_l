# 2H_M30_6H Auto Trade

## 当前可部署内容

- `2H_M30_6H_Strategy_EA.mq5`：新策略专用 EA 源码，基于 30m2H 成熟 EA 框架迁移。
- `2H_M30_6H_Strategy_EA.set`：MT5 测试器参数，固定当前验证 profile。
- `deploy_ea.ps1`：复制 EA 源码和 `.set` 到 MT5 目录。
- `compare_python_vs_ea.py`：Python 预期逐笔账单与 EA 导出账单对齐工具。

## 默认参数

- Magic：`322025`
- Symbol：`XAUUSDm`
- Stage：`1.0 / 1.5 / 3.0`
- 手数：`0.02 / 0.01 / 0.03`
- StopSpec：`14-70pt`
- 导出账单：`2H_M30_6H_strategy_trade_ledger.csv`

## MT5 流程

1. 运行 `deploy_ea.ps1`，或手动复制 `.mq5` 到 MT5 的 `MQL5/Experts`。
2. 用 MetaEditor 编译 `2H_M30_6H_Strategy_EA.mq5`，生成 `.ex5`。
3. 在 MT5 Strategy Tester 里加载 `2H_M30_6H_Strategy_EA.set`。
4. 跑完测试后，把 `2H_M30_6H_strategy_trade_ledger.csv` 放到本目录或传给对账脚本。

## 对账命令

```powershell
python .\auto_trade\compare_python_vs_ea.py
python .\auto_trade\compare_python_vs_ea.py "C:\path\to\2H_M30_6H_strategy_trade_ledger.csv"
```

无 EA ledger 时，脚本会先生成 `data/validation/ea_alignment/python_expected_stage_ledger.csv`。有 ledger 时，会输出 `alignment_summary.csv`、`alignment_detail.csv` 和 `alignment_report.md`。

## 边界说明

当前 EA 对齐的是 `2H_M30_6H__baseline` 部署 profile。高 PF 但样本较少的窄门候选，例如 `2H_M30_6H__2h_bias5_top30`，没有作为默认 EA profile 启用。
