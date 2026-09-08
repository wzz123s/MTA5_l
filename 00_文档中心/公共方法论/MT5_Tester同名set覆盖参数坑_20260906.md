# MT5 Tester「同名 .set 自动加载」覆盖 EA 参数坑（踩坑记录）

> 记录时间：2026-09-06
> 场景：2H_M30_6H 策略难论改进（reg55 gate）Tester 实测
> 严重度：高 —— 改 EA 默认值 + 改 .ini 都无效，白白多轮调试；且会影响**所有**策略的 Tester 部署

---

## 一、现象

给 EA 新增参数 `InpNanRegOn`（bool，默认 `true`）并重新编译部署后，MT5 策略测试器回测时 **EA 收到的值仍是 `false`**：

- EA `OnInit` 打印 `[NANREG] On=false`（EA 源码默认明明是 `true`）
- Tester 日志 `started with inputs:` 显示 `InpNanRegOn=false`
- 交易数 518 笔（= 没开 gate 的基线），预期 187 笔（开 gate）

---

## 二、排查过程（走了弯路，供后人避开）

| 步骤 | 尝试 | 结果 |
|---|---|---|
| 1 | 改 EA 默认 `InpNanRegOn=true` + 重编译 + 部署 .ex5 | ❌ 仍 false |
| 2 | 改 `.ini` 缓存（`Profiles\\Tester\\*.ini`）加 `InpNanRegOn=true` | ❌ 仍 false（Tester 跑完又把 .ini 覆盖回 false） |
| 3 | `.ini` 里 bool 值试 `true` / `1` | ❌ 都被读回 false（int/double 参数能读对，唯独 bool 不认） |
| 4 | 删除 `.ini` 缓存 | ❌ 仍 false（Tester 跑完重新生成 .ini） |
| 5 | 删除与 EA 同名的 `.set` | ✅ **成功了**（InpNanRegOn=true，交易 518→187） |

> 弯路原因：一直以为参数来自 .ex5 默认值或 .ini 缓存，**忽略了 Tester 会自动加载与 EA 同名的 .set**。

---

## 三、根因

**MT5 策略测试器会自动加载与 EA 文件名同名的 .set 文件**，且该 .set 里的参数**优先于 .ex5 的 input 默认值**。

具体到本坑：

- EA 名：`2H_M30_6H_ABC_EA`（`Experts\\Advisors\\2H_M30_6H_ABC_EA.ex5`）
- Tester 自动加载：`MQL5\\Profiles\\Tester\\2H_M30_6H_ABC_EA.set`（**同名** .set）
- 该 .set 是我们部署的**基线参数包**，内容含 `InpNanRegOn=false`
- 于是每次回测，Tester 用 .set 里的 `InpNanRegOn=false` 覆盖了 .ex5 默认 `true`

同理，.ini 缓存（`*.ini`）也会被 Tester 覆盖/重新生成，所以改 .ini 无效。

---

## 四、解决办法

1. **跑基线**：保持同名 `.set`（`2H_M30_6H_ABC_EA.set`）内容为基线参数（含 `InpNanRegOn=false`）。
2. **跑改进/变体**：把同名 `.set` 里的参数改成目标值（如 `InpNanRegOn=true`），或**直接删除同名 .set**（此时 Tester 退回 .ex5 的 input 默认值）。

⚠️ 注意：删除同名 .set 后，其他参数也退回 .ex5 默认（如 `InpMaxOpenVirtual` 从 10 变 100），若这些参数重要，应在 .set 里显式写全，而不是只改目标参数。

---

## 五、验证证据（2026-09-06）

删除 `2H_M30_6H_ABC_EA.set` 后：

- Tester 日志：`InpNanRegOn=true`
- EA OnInit：`[NANREG] On=true Pct=0.500 SMA55=55`
- 回测结果：交易 **187 笔**（基线 518），EA↔Python 对齐 **533/552 = 96.6%**（高于基线 93.5%），最终余额 3024 USD（1% 复利）

---

## 六、预防建议（对所有策略）

1. **部署 .set 时命名别和 EA 撞名**：若要保留多个参数包，用 `<EA>_<variant>.set` 命名（如 `2H_M30_6H_ABC_NanRegOn_EA.set`），**不要把基线参数写成与 EA 完全同名的 `.set`**——因为 Tester 会自动加载它，改 EA 默认值后极难排查。
2. **改 EA input 默认值验证时**，同时检查/删除同名 .set，否则默认值改动会被静默覆盖。
3. **排查参数不生效**的顺序建议：① 同名 .set → ② .ini 缓存 → ③ .ex5 是否真的重新编译部署 → ④ EA OnInit 打印实际值确认。
4. **确认参数最可靠的手段**：在 EA `OnInit` 里 `Print` 关键 input 实际值（本次就是靠 `[NANREG] On=true/false` 定位的）。

---

## 七、影响范围

该机制影响**所有 MT5 策略**的 Tester 部署（30m2H / 1H_M30_4H / 2H_M30_6H / 原油系列 / 乖离反转等）。部署新参数或改默认值时，务必先查同名 .set。
