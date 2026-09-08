# 1H_M30_4H_ABC_EA Magic 修复记录（2026-09-02）

> 收尾时间：2026-09-03 08:55（部署完成）
> 关联：`修改记录.md` 追加行；30m2H `EA_v3.35修复与部署记录_20260901.md` Fix 3 同口径修复

## 一、背景：平仓单 magic=0 归因缺口

- 现象：2026-09-02 12:30 UTC，1H_M30_4H SELL（@4567.196，08-28 开）在 M30 金叉/合并方向翻多时被 EA 平仓（+230.58），
  平仓成交单 **magic=0**（`comment=''`，reason=EXPERT）——无法按 magic 归属到 1H_M30_4H 策略，监控归因混乱；
- 同类问题：30m2H 2026-09-01 11:30 的 S2/S3 平仓单也是 magic=0（已在 v3.35 Fix 3 用 SetExpertMagicNumber 修复）；
- 排查确认：`1H_M30_4H_ABC_EA`（magic 312036，chart03 运行）开仓在 Execute 里显式写 `req.magic`，
  但平仓走 `g_trade.PositionClose()`（RecordStageExit），CTrade 从未 `SetExpertMagicNumber` → 平仓单 magic 落为 0。

## 二、修复（1 行）

文件：`auto_trade/1H_M30_4H_ABC_EA.mq5`（OnInit 首部，3 空格缩进风格）：

```mql5
   // BUGFIX(2026-09-02): CTrade had no expert magic, so PositionClose() sent magic=0
   // (observed 2026-09-02 12:30 1H_M30_4H merged-cross close deal magic=0). Same fix as
   // 30m2H_Strategy_EA v3.35 Fix 3. Opens set req.magic explicitly; this makes ALL
   // orders carry InpMagic for clean monitoring attribution.
   g_trade.SetExpertMagicNumber(InpMagic);
```

## 三、编译与验证

- 编译：MetaEditor 命令行 **0 errors, 3 warnings**（warnings 为既有，非本次引入）；新 ex5 59526B（与旧版 59744B 不同，确认改动生效）；
- 备份：项目 `auto_trade/1H_M30_4H_ABC_EA.ex5.bak_v_20260902` + 终端 Advisors 同备份；
- 部署：`DAD3B8CC\MQL5\Experts\Advisors\1H_M30_4H_ABC_EA.ex5`（chart03 引用路径）；
- 加载：主终端重启后 `08:55:24 expert 1H_M30_4H_ABC_EA (XAUUSDm,H4) loaded successfully`，账户 0 持仓同步正常。

## 四、观察项

1. 后续 1H_M30_4H EA 主动平仓（合并叉/移动止损等）成交单应带 magic 312036；
2. 若再出现 magic=0 的 XAUUSDm 平仓单 → 判定为手动/外部操作，而非 EA；
3. `1H_M30_4H_Strategy_EA.mq5`（312025，未部署）存在同样缺口，若启用需同步补丁。