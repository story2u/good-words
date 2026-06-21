# Telegram Digest

把摘抄 Markdown 导入本地 SQLite，并按北京时间定时推送到 Telegram。

当前默认配置：

- 数据源：`../categories/网络文学/excerpts/剑来.md`
- 书名：`剑来`
- 时间：北京时间 `20:00`，可通过 `.env` 配置
- 条数：每次 `5` 条定稿卡，可通过 `.env` 配置
- 数据库：`./data/good_words.sqlite3`

## 1. 配置

复制示例配置：

```bash
cp telegram_digest/config.env.example telegram_digest/.env
```

编辑 `telegram_digest/.env`：

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

`TELEGRAM_CHAT_ID` 可以是个人聊天 ID，也可以是群或频道 ID。频道通常形如 `@channel_name`，群组可能是负数 ID。

## 2. 导入 Markdown 到 SQLite

```bash
python3 telegram_digest/telegram_digest.py sync
```

重复执行是安全的：脚本会按 `markdown_path + card_id` 更新已存在卡片，并把同一 Markdown 中已经不存在的卡标为 inactive。

## 3. 先 dry-run 看推送内容

```bash
python3 telegram_digest/telegram_digest.py send --dry-run
```

dry-run 只打印内容，不调用 Telegram，也不写发送记录。

## 4. 立即推送一批

```bash
python3 telegram_digest/telegram_digest.py send
```

每次会选择发送次数最少、最久未发送的 `定稿` 卡片。默认每天 5 条，80 张《剑来》卡片约 16 天轮完一遍，然后继续循环。

## 5. 常驻定时运行

```bash
python3 telegram_digest/telegram_digest.py run
```

默认每天北京时间 `20:00` 推送 5 条《剑来》定稿卡。可在 `.env` 里调整：

```bash
GOOD_WORDS_SCHEDULE=20:00
GOOD_WORDS_TIMEZONE=Asia/Shanghai
GOOD_WORDS_LIMIT=5
GOOD_WORDS_BOOK=剑来
```

## 6. systemd 示例

仓库内提供了 `good-words-telegram.service.example`。按实际仓库路径和用户复制到 `~/.config/systemd/user/good-words-telegram.service` 后：

```bash
systemctl --user daemon-reload
systemctl --user enable --now good-words-telegram.service
systemctl --user status good-words-telegram.service
```

查看日志：

```bash
journalctl --user -u good-words-telegram.service -f
```
