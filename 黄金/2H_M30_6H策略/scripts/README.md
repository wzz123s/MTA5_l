# 2H_M30_6H Scripts

## 推荐执行顺序

1. `data_source`
2. `prepare`
3. `signals`
4. `validate`
5. `bundle`

## 一键入口

```powershell
python 黄金/2H_M30_6H策略/scripts/bundle/build_strategy_bundle.py
```

## 验证入口

- `validate/export_validation_bundle.py`：基础候选门与年度表现。
- `validate/export_advanced_validation.py`：Stage / StopSpec / 仓位 / EA 参数包。
