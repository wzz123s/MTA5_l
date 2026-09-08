# dsh-xingtu-skills · XingTu Skills Plugin for DeepSeek Harness (DSH)

> **26 production-grade AI agent skills, packaged as a standard DeepSeek Harness (DSH) plugin — one command to install.**

[![MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![npm](https://img.shields.io/npm/v/dsh-xingtu-skills)](https://www.npmjs.com/package/dsh-xingtu-skills) [![downloads](https://img.shields.io/npm/dm/dsh-xingtu-skills)](https://www.npmjs.com/package/dsh-xingtu-skills) [![release](https://img.shields.io/github/v/release/xingtu1996/dsh-xingtu-skills)](https://github.com/xingtu1996/dsh-xingtu-skills/releases)

---

## What is this

This plugin packages the **26 production-grade SKILL.md skills** from [xingtu-skills](https://github.com/xingtu1996/xingtu-skills) into a standard DeepSeek Harness plugin bundle. After install, DSH's session skill catalog loads all skills automatically and triggers them on demand (progressive disclosure) — no manual copying.

Each skill follows the cross-tool de-facto standard (`name + description + when_to_use`) and is also compatible with Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI.

## Install

```bash
# From npm (recommended)
dsh plugin add dsh-xingtu-skills

# From the GitHub release tarball
dsh plugin add -w https://github.com/xingtu1996/dsh-xingtu-skills/releases/latest/download/dsh-xingtu-skills-0.1.0.tgz
```

## Skills (26)

| Series | Skills |
|---|---|
| **Caveman · token compression** | `caveman` `caveman-commit` `caveman-compress` `caveman-discover` `caveman-evidence-review` `caveman-explore` `caveman-help` `caveman-learn` `caveman-manage` `caveman-optimize` `caveman-review` `caveman-setup` `caveman-stats` `cavecrew` |
| **Ponytail · minimalism & debt** | `ponytail` `ponytail-audit` `ponytail-debt` `ponytail-gain` `ponytail-help` `ponytail-review` |
| **Engineering practice** | `investigate-first` `lean-build` `migration` `safe-refactor` `surgical-patch` `verify-and-stop` |

## Structure

```
dsh-xingtu-skills/
├── package.json        # dsh.bundle.patch → ./cordis.patch.yml (standard plugin declaration)
├── cordis.patch.yml    # inserts this plugin row (bundle layer)
├── lib/index.js        # entry: apply() registers every SKILL.md under skills/
└── skills/<name>/      # 26 skill directories (SKILL.md + their resources)
```

- **Plugin contract**: exports `name` + `apply(ctx)` (`inject: ['skills']`); every contribution goes through `ctx.effect()` / `ctx.skills.register()` and is auto-disposed on unload.
- **Zero dependencies**: no Cordis copy is bundled; `@deepseek-ai/dsh` is only an optional peerDependency.
- **Validated**: passes `dsh-plugin-dev check` (static checks) + `dsh-plugin-dev verify` (clean-DSH_HOME install / boot / uninstall).

## Related

- [xingtu-skills](https://github.com/xingtu1996/xingtu-skills) — source repo (cross-tool)
- [xingtu-harness](https://github.com/xingtu1996/xingtu-harness) — one-command AI engineering scaffold
- [xingtu-ai-engineering](https://github.com/xingtu1996/xingtu-ai-engineering) — flagship methodology repo

## License

MIT License. Skills distilled from real engineering practice.
