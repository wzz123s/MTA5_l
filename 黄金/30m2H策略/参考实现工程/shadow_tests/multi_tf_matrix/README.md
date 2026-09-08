# 多周期影子测试

本目录用于继续扩展当前主线之外的“其他周期”验证，不直接改主策略，也不直接改 EA。

当前首轮测试矩阵：

- `1H/30M-4H`
- `2H-6H/8H`
- `3H-10H/12H`
- `4H-16H`
- `5H-29H`
- `6H-24H`

运行方式：

```powershell
python shadow_tests\multi_tf_matrix\scripts\_multi_tf_matrix_test.py
```

输出位置：

- `results\multi_tf_matrix_test_results.md`
- `data\multi_tf_matrix_trade_context.csv`
- `data\multi_tf_matrix_summary.csv`
