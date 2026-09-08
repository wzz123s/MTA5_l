# Obsidian CLI 项目使用手册

> 这份手册只服务当前 `F:\use_code\MTA5` 这个 vault。
> 目标不是介绍全部 CLI 功能，而是让它尽快接入你的学习、归档、复盘流程；其中 `30m2H策略` 只是历史沿用的目录名，内容重点已经更接近交易学习与实验整理。

## 1. 当前前提

- 当前 vault 根目录：`F:\use_code\MTA5`
- 当前重点整理区：`30m2H策略`（历史沿用名称，内容以交易学习/实验归档为主）
- 当前 Obsidian 配置目录已存在：`.obsidian`
- 使用前提：
  - Obsidian 已升级到支持 CLI 的版本
  - 已在 `Settings -> General` 启用 `Command line interface`
  - 已按官方提示把 `obsidian` 注册到系统 `PATH`
  - Obsidian 桌面程序正在运行

## 2. 先确认 CLI 可用

在新开的终端里先跑：

```powershell
obsidian help
obsidian
```

预期：

- `obsidian help` 能显示帮助
- `obsidian` 能进入官方 TUI 模式

如果这里不通，先不要继续做项目接入。

## 3. 最适合当前项目的命令

### 3.1 查主线和结论

查当前策略主线：

```powershell
obsidian search query="当前方案"
obsidian search query="Layer 1"
obsidian search query="stop spec"
obsidian search query="仓位档位"
```

适用场景：

- 快速找当前主线定义
- 找某个参数结论在什么文件里出现过
- 找历史上某轮认证的记录

### 3.2 记每日研究进度

打开当日笔记：

```powershell
obsidian daily
```

追加一条项目进度：

```powershell
obsidian daily:append content="- [ ] 更新 30m2H 策略主线"
obsidian daily:append content="- [ ] 复核 Layer 1 / Layer 3 结论"
obsidian daily:append content="- [ ] 检查 EA 与 Python 对齐状态"
```

适用场景：

- 每天开始前列清单
- 每轮测试结束后补一句结果摘要
- 把散落的工作记录收进 daily note

### 3.3 建专项页面

给新一轮研究建独立页：

```powershell
obsidian create name="2026-06-28 Layer1二轮复核"
obsidian create name="2026-06-28 MT5对齐检查"
obsidian create name="2026-06-28 仓位档位差异复盘"
```

适用场景：

- 每一轮参数认证单独成页
- 每一轮 EA/MT5 对齐单独成页
- 单独做交易复盘专题

### 3.4 读当前打开文件

```powershell
obsidian read
```

适用场景：

- 先在 Obsidian 里打开 `策略说明.md`
- 再用 CLI 读取当前页面内容
- 适合和脚本化流程、外部工具或 agent 配合

### 3.5 看任务和标签

```powershell
obsidian tasks daily
obsidian tags counts
```

适用场景：

- 看 daily note 里的任务
- 统计 vault 里标签使用频率

### 3.6 看最近文件

```powershell
obsidian files sort=modified limit=10
```

适用场景：

- 快速看最近改过哪些笔记
- 检查今天是不是更新了该更新的文件

### 3.7 看版本差异

```powershell
obsidian diff file="30m2H策略/策略说明.md" from=1 to=2
obsidian diff file="findings.md" from=1 to=2
```

适用场景：

- 对比 `策略说明.md` 的两个版本
- 检查某次结论是怎么改的

注：

- `from` / `to` 的具体版本编号以 CLI 当前可见版本为准
- 这条命令更适合已经纳入 Obsidian 历史或版本体系之后使用

## 4. 项目专用工作流

### 4.1 每天开工

```powershell
obsidian daily
obsidian daily:append content="- [ ] 查看 30m2H 当前待办"
obsidian daily:append content="- [ ] 更新测试结论或复盘摘要"
obsidian files sort=modified limit=5
```

### 4.2 查当前主线

```powershell
obsidian search query="当前候选配置"
obsidian search query="当前待办"
obsidian search query="Layer 1 = 3.0%"
obsidian search query="top34%"
```

### 4.3 做一轮新认证

```powershell
obsidian create name="2026-06-28 StopSpec三轮复核"
obsidian daily:append content="- [ ] 新建 StopSpec 三轮复核页"
obsidian search query="StopSpec严格认证结果"
```

### 4.4 做一轮交易复盘

```powershell
obsidian create name="2026-06-28 K01-K05关键交易复盘"
obsidian search query="关键交易图形复盘"
obsidian search query="仓位档位差异交易分析"
```

### 4.5 做 EA / MT5 对齐

```powershell
obsidian create name="2026-06-28 EA_MT5对齐记录"
obsidian search query="EA 待办"
obsidian search query="MT5 对齐"
obsidian search query="Tester"
```

## 5. 和当前归档结构的接法

当前归档骨架：

- `30m2H策略/Obsidian归档/01_策略总览`
- `30m2H策略/Obsidian归档/02_参数认证`
- `30m2H策略/Obsidian归档/03_复盘图表`
- `30m2H策略/Obsidian归档/04_EA_MT5`
- `30m2H策略/Obsidian归档/05_历史归档`

建议接法：

- 策略主线相关查询，优先落到 `01_策略总览`
- 参数扫描和严格认证，优先落到 `02_参数认证`
- 关键交易图、止损复盘、资金曲线，优先落到 `03_复盘图表`
- 编译、日志、回测对齐，优先落到 `04_EA_MT5`
- 已经淘汰的旧方案，优先落到 `05_历史归档`

### 4.6 学习图片解析后存笔记

```powershell
obsidian create name="2026-06-28 图片解析 - 主题名"
```

新建笔记后，把我解析出来的内容整理成 markdown，套用：

- `99_模板/图片解析模板.md`

适用场景：

- 你上传学习截图、题目图、讲义图
- 我先帮你提炼关键信息
- 再把整理结果写成一篇结构化笔记
- 最后存入 `06_图片解析`

## 6. 当前最推荐的 10 条命令

```powershell
obsidian help
obsidian
obsidian daily
obsidian daily:append content="- [ ] 更新 30m2H 策略主线"
obsidian search query="当前待办"
obsidian search query="仓位档位"
obsidian search query="Layer 1"
obsidian read
obsidian files sort=modified limit=10
obsidian tags counts
```

## 7. 当前限制

- 这份手册基于官方 CLI 页面里已经公开的命令示例。
- 现在还没有把它包装成 Codex 可直接安装的外部 skill。
- 当前最稳的用法，是把它当成你本机 Obsidian 的官方终端入口，而不是等待 skill 安装完成后再开始使用。

## 8. 怎么直接让我调用

你以后可以直接这样跟我说：

- “用 Obsidian CLI 查一下 `仓位档位` 相关笔记”
- “用 Obsidian CLI 打开 today daily，并追加今天的研究摘要”
- “用 Obsidian CLI 新建一个 `Layer1 二轮复核` 页面”
- “用 Obsidian CLI 看最近修改过的 10 个笔记”
- “用 Obsidian CLI 帮我把今天的进度写进 daily note”

如果你这样说，我会理解成：

- 优先调用你本机已经可用的 `obsidian` 命令
- 结合当前项目目录和文档结构来执行
- 执行后把关键结果整理给你，而不是只给你一串命令

最省事的说法就是：

```text
用 Obsidian CLI 帮我……
```
