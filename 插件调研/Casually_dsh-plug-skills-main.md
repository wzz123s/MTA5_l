# dsh-plug-skills

[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的
**Skills 管理器**：在 Web UI 的「设置 → 插件 → Skills」标签页中发现
GitHub 上的 Agent Skills 仓库（`SKILL.md` 技能包），查看详情后一键安装 /
移除。交互模式参考
[`dsh-plug-manager`](https://github.com/Casually/deepseek-harness-plugs-manage)
（插件市场）；MCP 服务管理请见姊妹插件
[`dsh-plug-mcp`](https://github.com/Casually/dsh-plug-mcp)。

## 功能

- **设置 → 插件 → Skills**（Web UI）
  - **发现**：按 GitHub topic 搜索技能仓库——`agent-skills` / `dsh-skill` /
    `claude-skills` / `ai-skills` / `skills` / `skill`，可追加关键词、按最多
    Star / 最近更新排序、翻页。另有两个**模糊匹配**选项：`*skills` 与
    `*skill`——GitHub 搜索不支持通配符限定符，插件会并行搜索一组技能
    相关 topic（`*skills` = agent-skills + ai-skills + claude-skills +
    skills；`*skill` = dsh-skill + skill），合并去重后按 Star 排序展示
    （一次消耗 2-4 个匿名搜索额度，注意限流）。
  - **详情弹窗**：仓库星标 / topics / 许可证 / README（内置安全 Markdown
    渲染，只放行 http(s) 链接，相对图片改写为 raw.githubusercontent.com），
    经 git trees 递归扫描列出仓库内全部 `SKILL.md` 技能包，解析每个技能的
    frontmatter（name / description），勾选后一键安装。
  - **安装**：经 HTTPS 从 codeload.github.com 下载仓库 tarball（自动走
    代理配置），解压后把选中的技能目录复制进 `$DSH_HOME/skills/<目录名>`。
    支持一次装多个、重名检测与可选覆盖。`skill-filesystem` 对技能根目录做
    文件监视——**装完立即生效，无需重启**。
  - **已安装**：列出两个用户技能根目录（`$DSH_HOME/skills`、
    `$DSH_AGENTS_HOME/skills`）中的全部技能（含 frontmatter 摘要、来源、
    是否本插件安装），自定义确认弹窗后一键移除。
  - **GitHub 代理**：直连 GitHub 受限时，可在页面上直接配置代理并测试
    连通性（见下文「代理配置」）。
- **本地 JSON API**（仅回环地址，由运行中的 web 服务器提供）：
  `/plug-skills/search`、`/plug-skills/repo`、`/plug-skills/local`、
  `/plug-skills/install`、`/plug-skills/remove`、`/plug-skills/proxy`、
  `/plug-skills/proxy-test`。

## 代理配置

发现功能访问 `api.github.com` / `raw.githubusercontent.com` /
`codeload.github.com`。出厂部署不挂载平台级 fetch provider，本插件自行
发起请求：默认直连（Node fetch）；**配置代理后经系统 `curl` 发出**，因此
支持 `http` / `https` / `socks5` / `socks5h` / `socks4`（Clash 的混合端口
与 SOCKS 端口都可用）。

代理来源按优先级生效：

1. **持久设置**（UI「GitHub 代理」栏输入后点「应用」）——写入
   `DSH 主目录/plug-skills.json`，立即生效且重启后保留；点「清除」移除；
2. **插件配置**——在 profile 的 `cordis.patch.yml` 中为本插件加
   `config.proxy`（持久生效）：
   ```yaml
   - id: plug-skills
     name: dsh-plug-skills
     config:
       proxy: http://127.0.0.1:7890
   ```
3. **环境变量**——`DSH_PLUG_SKILLS_PROXY`，或标准的 `HTTPS_PROXY` /
   `HTTP_PROXY` / `ALL_PROXY`（大小写均可）。

「测试连接」会请求 `api.github.com/zen` 验证当前生效通道并报告延迟。
特殊值 `direct` 可强制直连（同样会被持久保存）。

## 数据与安全

- 技能装入 `$DSH_HOME/skills/<dir>`，安装登记（来源仓库 / 路径 / 时间）
  记录在 `$DSH_HOME/plug-skills.json`；移除 = 删除技能目录并清理登记。
- **技能是提示词级内容**：加载后进入模型上下文，等价于你亲手写的系统
  指令——只安装你信任的技能仓库。
- 所有安装 / 移除均由你本人在本地界面点击触发，宿主进程直接执行文件
  操作，不经过 agent、不额外审批；操作结果即时反馈。

## 安装

要求宿主有 `curl`（macOS / 主流 Linux 自带）才能使用代理功能；
`dsh plugin` 命令要求 PATH 中有 `pnpm`。

```sh
# npm 安装（推荐）
dsh plugin --profile web add -w dsh-plug-skills

# GitHub 源码（最新 main；也可 #vX.Y.Z 锁 tag）
dsh plugin --profile web add -w github:Casually/dsh-plug-skills

# 本地目录（开发自用，在本目录的父目录下执行）
dsh plugin --profile web add -w ./dsh-plug-skills
```

经 `dsh plugin` 命令安装后**重启 DSH**（`dsh web`）以组合新 bundle。
安装完成后，「Skills」标签页出现在设置 → 插件 下。

## 卸载

```sh
dsh plugin --profile web remove dsh-plug-skills
```

重启 DSH 以移除该层。已安装的技能不受影响（它们是数据，不是插件的
一部分）；如需清理，先在「已安装」页移除。

## 开发说明

- 运行时依赖仅 `js-yaml`（解析 SKILL.md 的 YAML frontmatter）。
- 宿主插件是纯 ESM；GitHub 抓取默认直连，代理经系统 curl；30 秒超时、
  5 MB 响应上限、10 万字符文本上限（递归树扫描单独放宽到 300 万字符）。
- 浏览器端以预构建形式交付（`client.js`，`window.__ModuleLoader__`
  格式），仅依赖平台的 `react` wire 模块。
- 给自己仓库打上 `dsh-skill` 或 `agent-skills` topic 标签，即可出现在
  「发现」中。

## 许可证

MIT
