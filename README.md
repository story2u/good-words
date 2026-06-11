# good-words · 好书阅读 Harness

一套**纯文档、零代码**的多模型阅读摘抄 harness：让 AI Agent（Claude / ChatGPT / Gemini）阅读一本书，按分类摘抄并提炼其中的好词好句，沉淀为可检索、可溯源的摘抄卡片库。

姊妹项目：`../ai-story`（多模型小说创作 harness），本项目沿用其「文档即状态」与 maker-checker 异模型评审的经验。

## 这个项目做什么

- **读**：把一本书交给一个阅读 Agent，按 playbook 流程通读、选段。
- **抄**：忠实摘录原文（中文译本为准），逐条标注出处（版本/章节/节号）。
- **炼**：每条摘抄附一句提炼（为什么好、好在哪），打主题标签。
- **审**：由不同模型的校对 Agent 过质量闸门后才入库。

首个分类为【新时代】，以赛斯资料（Seth Material）为核心圈，外延至赛斯体系周边与新时代经典。

## 目录地图

```
good-words/
├── README.md            ← 你在这里
├── CLAUDE.md            ← 主会话（Showrunner）行为约定
├── HARNESS.md           ← 宪法：摘抄规则、分类标准、质量闸门、协作协议
├── playbook/            ← 工作流
│   ├── 00-overview.md   ← 流程总览与状态机
│   ├── 01-book-intake.md← 选书入库（建书目档案）
│   ├── 02-excerpt.md    ← 阅读摘抄
│   └── 03-review.md     ← 校对闸门与入库
├── templates/           ← 模板
│   ├── book-profile.md  ← 书目档案模板
│   └── excerpt-card.md  ← 摘抄卡模板
├── relay/
│   └── HANDOFF.md       ← 接力板：当前进度与下一步（每次会话先读这里）
└── categories/          ← 分类库（一级分类 = 一个目录）
    └── 新时代/
        ├── README.md    ← 分类定义与圈层说明
        ├── books.md     ← 书单汇总（圈层 A/B/C，含状态与优先级）
        ├── books/       ← 入库书目档案（每书一份）
        └── excerpts/    ← 摘抄卡（每书一个文件）
```

## 快速开始（新会话）

1. 读 `CLAUDE.md` 确认主会话职责；
2. 读 `relay/HANDOFF.md` 了解当前进度；
3. 按 `playbook/00-overview.md` 的状态机续跑。

## 当前状态

- [x] 项目结构搭建完成
- [x] 【新时代】分类建立，书单汇总完成（见 `categories/新时代/books.md`）
- [ ] 尚未开始摘抄（下一步：从书单挑第一本，走 `playbook/01-book-intake.md`）
