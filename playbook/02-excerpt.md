# playbook/02 · 阅读摘抄

阅读者（Reader）按批次通读并产出候选摘抄卡。

## 选角

- Reader ＝ claude / ChatGPT / Gemini 任一；在书目档案中登记本书 Reader 与 Reviewer 模型，**两者必须不同模型**。
- 同一本书尽量保持同一 Reader，跨批次风格一致。

## Showrunner 组 prompt（自包含，不含仓库路径）

Prompt 必须包含：

1. 角色设定：你是摘抄员，任务是从指定文本中摘录好词好句；
2. 本批次阅读范围（粘贴文本，或指明作者本地可供 Agent 读取的文件）；
3. 摘抄规则全文（HARNESS.md §4 五条 + 本书侧重点）；
4. 输出格式：摘抄卡模板（粘贴 `templates/excerpt-card.md` 内容）；
5. 数量约束：本批次产出 5–15 张候选卡，宁缺毋滥。

## 执行（方式 M·手动 CLI 接力）

作者在终端执行，例如：

```
claude -p "<自包含 prompt>"
codex exec "<自包含 prompt>"
gemini -p "<自包含 prompt>"
```

结果带回主会话。

## 落盘

1. Showrunner 形式校验（模板字段齐全、出处格式正确）后，把候选卡**追加**到 `categories/<分类>/excerpts/<书名>.md`，标记 `状态: 候选`；
2. 更新该文件头部批次表与 `relay/HANDOFF.md`；
3. `books.md` 状态保持/置为 `摘抄中`；批次全部抄完后进入 03 校对。
