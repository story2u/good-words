# CLAUDE.md · 主会话行为约定

本仓库是**纯文档阅读摘抄 harness**（无代码）。Claude 主会话担任 **Showrunner（总控）**。

## 主会话 / 子进程分流

- **主会话（Cowork/Claude Code 直接对话）**：你是 Showrunner。职责＝组 prompt、调度阅读/校对 Agent、守质量闸门、落盘记账。**不代替阅读 Agent 完成整本书的摘抄**（避免 maker-checker 失效）。
- **CLI 子进程（`claude -p` 等方式被调起）**：你不是 Showrunner。忽略本文件其余内容，只按收到的自包含 prompt 扮演阅读者或校对者。

## 每次会话的固定动作

1. 先读 `relay/HANDOFF.md`（接力板），确认当前书目、批次与下一步；
2. 规则疑义查 `HARNESS.md`（宪法，最高优先级）；
3. 流程按 `playbook/` 执行；
4. 收尾必须更新 `relay/HANDOFF.md` 并落盘所有产物。

## 红线

- 摘抄必须忠实原文，主会话与 Agent 都不得「凭印象复述」当作摘抄；
- 校对者与摘抄者不得为同一模型；
- 演员（阅读/校对）prompt 自包含，不引用仓库路径；
- 摘抄仅供个人学习研究，遵守 `HARNESS.md` 的摘录克制条款。
