# H1/M15 影子测试

本目录用于存放 H1/M15 小周期确认过滤的旁路研究。

影子测试原则：

- 不直接修改当前主策略。
- 不直接修改 EA。
- 不把脚本放在 `scripts` 主线目录。
- 只有通过样本数、训练/验证稳定性、PF/EV、MaxCL 等检查后，才考虑进入主策略。

## 目录

| 路径 | 作用 |
| --- | --- |
| `scripts\_multi_tf_shadow_test.py` | H1/M15 影子测试脚本 |
| `results\H1_M15影子测试结果.md` | 影子测试结果说明 |
| `data\H1_M15影子测试明细.csv` | 逐笔明细输出 |

## 运行

从项目根目录运行：

```powershell
python shadow_tests\H1_M15\scripts\_multi_tf_shadow_test.py
```
