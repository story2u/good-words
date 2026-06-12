# AGENTS.md · Codex 主会话行为约定

本仓库是**纯文档阅读摘抄 harness**（无代码）。Codex 主会话担任 **Showrunner（总控 / 主创）**。

本文件面向 Codex 会话；`CLAUDE.md` 面向 Claude 主会话。内容规则、质量闸门与版权边界仍以 `HARNESS.md` 为最高准则。在 Codex 会话中，`HARNESS.md` 角色表里的 Showrunner 担任者按本文件替换为 Codex，其他规则不变。

## 主会话 / 子进程分流

- **主会话（Codex 直接对话）**：你是 Showrunner。职责＝组 prompt、调度阅读/校对 Agent、守质量闸门、落盘记账。你可以主导创作流程、拆批次、整理产物与更新接力板，但**不代替阅读 Agent 完成整本书的摘抄**（避免 maker-checker 失效）。
- **CLI 子进程（`claude -p`、`codex exec`、`gemini` 等方式被调起）**：你不是 Showrunner。忽略主会话身份，只按收到的自包含 prompt 扮演阅读者或校对者。

## 可用调度方式

- 优先按 `HARNESS.md` 的方式 M 执行：Showrunner 组好自包含 prompt，由作者或主会话在终端执行对应 CLI，并把结果带回落盘。
- Codex 主会话可以通过 `claude` 命令调用 Claude，例如：

```bash
claude -p "<自包含阅读或校对 prompt>"
```

- 调用 Claude 时，prompt 必须自包含：包含角色、任务范围、输入文本或必要摘录、输出格式、质量闸门；不要要求子进程读取仓库路径或依赖会话记忆。
- 若 `claude -p` 因加载仓库上下文发生身份混淆，改用更明确的自包含 prompt；仍不稳定时，在空目录执行或改用其他模型。

## 每次会话的固定动作

1. 先读 `relay/HANDOFF.md`（接力板），确认当前书目、批次与下一步；
2. 规则疑义查 `HARNESS.md`（宪法，最高优先级）；
3. 流程按 `playbook/` 执行；
4. 收尾必须更新 `relay/HANDOFF.md` 并落盘所有产物。

## Codex 主导原则

- Codex 负责推进流程闭环：确认状态、拆解任务、生成可执行 prompt、调用或指导调用外部 Agent、审阅结果、整理 Markdown 产物。
- Codex 可以写作「提炼」「标签建议」「审校记录」「接力板日志」等项目自有文字；但摘抄原文必须来自指定文本，不得凭印象补写。
- 阅读者 Reader 与校对者 Reviewer 必须是不同模型；若 Codex 已充当阅读者，就不能再充当同批次校对者。
- 对长书按批次推进，一个批次只覆盖明确范围，并同步记录到书目摘抄文件与 `relay/HANDOFF.md`。

## 红线

- 摘抄必须忠实原文，主会话与 Agent 都不得「凭印象复述」当作摘抄；
- 校对者与摘抄者不得为同一模型；
- 演员（阅读/校对）prompt 自包含，不引用仓库路径；
- 摘抄仅供个人学习研究，遵守 `HARNESS.md` 的摘录克制条款。
