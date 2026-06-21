#!/usr/bin/env python3
"""Import excerpt Markdown into SQLite and send scheduled Telegram digests."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
DEFAULT_DB = APP_DIR / "data" / "good_words.sqlite3"
DEFAULT_SOURCE = REPO_ROOT / "categories" / "网络文学" / "excerpts" / "剑来.md"
DEFAULT_CATEGORY = "网络文学"
DEFAULT_BOOK = "剑来"
DEFAULT_TZ = "Asia/Shanghai"
DEFAULT_SCHEDULE = "20:00"
DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class Card:
    card_key: str
    book_title: str
    category: str
    status: str
    source: str
    version: str
    tags: str
    reader: str
    batch: str
    card_date: str
    quote: str
    distillation: str
    markdown_path: str
    content_hash: str


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, str(default))).expanduser().resolve()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_key TEXT NOT NULL,
            book_title TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            source TEXT NOT NULL,
            version TEXT NOT NULL,
            tags TEXT NOT NULL,
            reader TEXT NOT NULL,
            batch TEXT NOT NULL,
            card_date TEXT NOT NULL,
            quote TEXT NOT NULL,
            distillation TEXT NOT NULL,
            markdown_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            imported_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(markdown_path, card_key)
        );

        CREATE INDEX IF NOT EXISTS idx_cards_book_status
            ON cards(book_title, status, active);

        CREATE TABLE IF NOT EXISTS delivery_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            chat_id TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            slot_key TEXT NOT NULL,
            status TEXT NOT NULL,
            response_text TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_delivery_card_status
            ON delivery_events(card_id, status, sent_at);

        CREATE TABLE IF NOT EXISTS delivery_runs (
            slot_key TEXT PRIMARY KEY,
            book_title TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        );
        """
    )
    conn.commit()


def infer_book_title(text: str, source_path: Path) -> str:
    match = re.search(r"^#\s+摘抄\s*[·・]\s*(.+?)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return source_path.stem


def parse_reader_line(value: str) -> dict[str, str]:
    result = {"reader": value.strip(), "batch": "", "card_date": ""}
    parts = [part.strip() for part in re.split(r"[｜|]", value) if part.strip()]
    if parts:
        result["reader"] = parts[0].strip()
    for part in parts[1:]:
        if part.startswith("批次"):
            result["batch"] = part.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif part.startswith("日期"):
            result["card_date"] = part.split(":", 1)[-1].split("：", 1)[-1].strip()
    return result


def parse_card_section(
    card_key: str,
    section: str,
    book_title: str,
    category: str,
    source_path: Path,
) -> Card:
    metadata: dict[str, str] = {}
    for line in section.splitlines():
        match = re.match(r"^-\s*([^:：]+)\s*[:：]\s*(.*)$", line)
        if match:
            metadata[match.group(1).strip()] = match.group(2).strip()

    reader_info = parse_reader_line(metadata.get("Reader", ""))
    batch = metadata.get("批次", reader_info["batch"])
    card_date = metadata.get("日期", reader_info["card_date"])

    quote_lines: list[str] = []
    for line in section.splitlines():
        if line.startswith(">"):
            quote_lines.append(re.sub(r"^>\s?", "", line).rstrip())
    quote = "\n".join(quote_lines).strip()

    distillation_match = re.search(r"^\*\*炼\*\*\s*[:：]\s*(.+?)\s*$", section, re.MULTILINE)
    distillation = distillation_match.group(1).strip() if distillation_match else ""

    hash_payload = "\n".join(
        [
            metadata.get("状态", ""),
            metadata.get("出处", ""),
            metadata.get("版本", ""),
            metadata.get("标签", ""),
            quote,
            distillation,
        ]
    )
    content_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

    return Card(
        card_key=card_key,
        book_title=book_title,
        category=category,
        status=metadata.get("状态", ""),
        source=metadata.get("出处", ""),
        version=metadata.get("版本", ""),
        tags=metadata.get("标签", ""),
        reader=reader_info["reader"],
        batch=batch,
        card_date=card_date,
        quote=quote,
        distillation=distillation,
        markdown_path=str(source_path),
        content_hash=content_hash,
    )


def parse_markdown(source_path: Path, category: str) -> list[Card]:
    text = source_path.read_text(encoding="utf-8")
    book_title = infer_book_title(text, source_path)
    matches = list(re.finditer(r"^###\s+(C-\d+)\s*$", text, re.MULTILINE))
    cards: list[Card] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[start:end]
        cards.append(parse_card_section(match.group(1), section, book_title, category, source_path))
    return cards


def import_cards(conn: sqlite3.Connection, cards: Iterable[Card], source_path: Path) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    cards = list(cards)
    with conn:
        conn.execute("UPDATE cards SET active = 0 WHERE markdown_path = ?", (str(source_path),))
        for card in cards:
            conn.execute(
                """
                INSERT INTO cards (
                    card_key, book_title, category, status, source, version, tags,
                    reader, batch, card_date, quote, distillation, markdown_path,
                    content_hash, active, imported_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(markdown_path, card_key) DO UPDATE SET
                    book_title = excluded.book_title,
                    category = excluded.category,
                    status = excluded.status,
                    source = excluded.source,
                    version = excluded.version,
                    tags = excluded.tags,
                    reader = excluded.reader,
                    batch = excluded.batch,
                    card_date = excluded.card_date,
                    quote = excluded.quote,
                    distillation = excluded.distillation,
                    content_hash = excluded.content_hash,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    card.card_key,
                    card.book_title,
                    card.category,
                    card.status,
                    card.source,
                    card.version,
                    card.tags,
                    card.reader,
                    card.batch,
                    card.card_date,
                    card.quote,
                    card.distillation,
                    card.markdown_path,
                    card.content_hash,
                    now,
                    now,
                ),
            )
    return len(cards)


def sync_markdown(conn: sqlite3.Connection, source_path: Path, category: str) -> int:
    if not source_path.exists():
        raise FileNotFoundError(f"Markdown source not found: {source_path}")
    cards = parse_markdown(source_path, category)
    return import_cards(conn, cards, source_path)


def select_cards(conn: sqlite3.Connection, book_title: str, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT c.*,
               COALESCE(sent.sent_count, 0) AS sent_count,
               COALESCE(sent.last_sent_at, '') AS last_sent_at
        FROM cards c
        LEFT JOIN (
            SELECT card_id, COUNT(*) AS sent_count, MAX(sent_at) AS last_sent_at
            FROM delivery_events
            WHERE status = 'sent'
            GROUP BY card_id
        ) sent ON sent.card_id = c.id
        WHERE c.book_title = ?
          AND c.status = '定稿'
          AND c.active = 1
        ORDER BY sent_count ASC, last_sent_at ASC, c.card_key ASC
        LIMIT ?
        """,
        (book_title, limit),
    ).fetchall()


def format_message(card: sqlite3.Row) -> str:
    parts = [
        f"【{card['book_title']}】{card['card_key']}",
        card["quote"],
    ]
    if card["distillation"]:
        parts.append(f"炼：{card['distillation']}")
    if card["source"]:
        parts.append(f"出处：{card['source']}")
    if card["tags"]:
        parts.append(f"标签：{card['tags']}")
    return "\n\n".join(parts)


def send_telegram(token: str, chat_id: str, text: str) -> str:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram request failed: {exc}") from exc


def slot_status(conn: sqlite3.Connection, slot_key: str) -> str:
    row = conn.execute("SELECT status FROM delivery_runs WHERE slot_key = ?", (slot_key,)).fetchone()
    return row["status"] if row else ""


def mark_run(conn: sqlite3.Connection, slot_key: str, book_title: str, status: str, note: str = "") -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with conn:
        conn.execute(
            """
            INSERT INTO delivery_runs(slot_key, book_title, started_at, finished_at, status, note)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(slot_key) DO UPDATE SET
                finished_at = excluded.finished_at,
                status = excluded.status,
                note = excluded.note
            """,
            (slot_key, book_title, now, now if status != "running" else "", status, note),
        )


def record_delivery(
    conn: sqlite3.Connection,
    card_id: int,
    chat_id: str,
    slot_key: str,
    status: str,
    response_text: str,
) -> None:
    with conn:
        conn.execute(
            """
            INSERT INTO delivery_events(card_id, chat_id, sent_at, slot_key, status, response_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                chat_id,
                datetime.now().isoformat(timespec="seconds"),
                slot_key,
                status,
                response_text[:2000],
            ),
        )


def send_batch(
    conn: sqlite3.Connection,
    book_title: str,
    limit: int,
    token: str,
    chat_id: str,
    dry_run: bool,
    slot_key: str,
    force: bool,
) -> int:
    if not dry_run and slot_key and slot_status(conn, slot_key) == "sent" and not force:
        print(f"slot already sent: {slot_key}")
        return 0
    if not dry_run and slot_key:
        mark_run(conn, slot_key, book_title, "running")

    cards = select_cards(conn, book_title, limit)
    if not cards:
        if not dry_run and slot_key:
            mark_run(conn, slot_key, book_title, "skipped", "no cards selected")
        print(f"no active finalized cards found for book: {book_title}")
        return 0

    sent = 0
    try:
        for card in cards:
            message = format_message(card)
            if dry_run:
                print("=" * 72)
                print(message)
            else:
                if not token or not chat_id:
                    raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
                response_text = send_telegram(token, chat_id, message)
                print(f"sent {card['card_key']} to Telegram")
                record_delivery(conn, card["id"], chat_id, slot_key or "manual", "sent", response_text)
            sent += 1
            if not dry_run:
                time.sleep(1)
    except Exception as exc:
        if not dry_run and slot_key:
            mark_run(conn, slot_key, book_title, "failed", str(exc))
        raise

    if not dry_run and slot_key:
        mark_run(conn, slot_key, book_title, "sent", f"sent {sent} cards")
    return sent


def parse_schedule(schedule: str) -> list[tuple[int, int]]:
    times: list[tuple[int, int]] = []
    for item in schedule.split(","):
        item = item.strip()
        if not item:
            continue
        match = re.match(r"^(\d{1,2}):(\d{2})$", item)
        if not match:
            raise ValueError(f"Invalid schedule time: {item}")
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour > 23 or minute > 59:
            raise ValueError(f"Invalid schedule time: {item}")
        times.append((hour, minute))
    if not times:
        raise ValueError("Schedule is empty")
    return sorted(set(times))


def next_run(now: datetime, schedule: list[tuple[int, int]]) -> datetime:
    for day_offset in (0, 1):
        day = now.date() + timedelta(days=day_offset)
        candidates = [
            datetime(day.year, day.month, day.day, hour, minute, tzinfo=now.tzinfo)
            for hour, minute in schedule
        ]
        for candidate in candidates:
            if candidate > now:
                return candidate
    raise RuntimeError("Unable to compute next run")


def sleep_until(target: datetime) -> None:
    while True:
        seconds = (target - datetime.now(target.tzinfo)).total_seconds()
        if seconds <= 0:
            return
        time.sleep(min(seconds, 300))


def make_slot_key(book_title: str, run_at: datetime) -> str:
    return f"{book_title}:{run_at.strftime('%Y-%m-%dT%H:%M%z')}"


def command_init_db(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        init_db(conn)
    print(f"initialized database: {args.db}")
    return 0


def command_sync(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        init_db(conn)
        count = sync_markdown(conn, args.source, args.category)
    print(f"imported {count} cards from {args.source}")
    return 0


def command_send(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        init_db(conn)
        if args.sync:
            count = sync_markdown(conn, args.source, args.category)
            print(f"imported {count} cards from {args.source}")
        sent = send_batch(
            conn=conn,
            book_title=args.book,
            limit=args.limit,
            token=args.token,
            chat_id=args.chat_id,
            dry_run=args.dry_run,
            slot_key=args.slot_key,
            force=args.force,
        )
    print(f"batch complete: {sent} card(s)")
    return 0


def command_run(args: argparse.Namespace) -> int:
    tz = ZoneInfo(args.timezone)
    schedule = parse_schedule(args.schedule)
    with connect(args.db) as conn:
        init_db(conn)
        if args.sync:
            count = sync_markdown(conn, args.source, args.category)
            print(f"imported {count} cards from {args.source}")
        print(
            "scheduler started: "
            f"book={args.book}, schedule={args.schedule}, timezone={args.timezone}, limit={args.limit}"
        )
        while True:
            run_at = next_run(datetime.now(tz), schedule)
            print(f"next run: {run_at.isoformat(timespec='minutes')}")
            sleep_until(run_at)
            if args.sync:
                count = sync_markdown(conn, args.source, args.category)
                print(f"imported {count} cards from {args.source}")
            slot_key = make_slot_key(args.book, run_at)
            send_batch(
                conn=conn,
                book_title=args.book,
                limit=args.limit,
                token=args.token,
                chat_id=args.chat_id,
                dry_run=args.dry_run,
                slot_key=slot_key,
                force=False,
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=APP_DIR / ".env", help="env file path")
    parser.add_argument(
        "--db",
        type=Path,
        default=env_path("GOOD_WORDS_DB", DEFAULT_DB),
        help="SQLite database path",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="create or migrate the SQLite database")
    init_parser.set_defaults(func=command_init_db)

    sync_parser = subparsers.add_parser("sync", help="import Markdown cards into SQLite")
    add_source_args(sync_parser)
    sync_parser.set_defaults(func=command_sync)

    send_parser = subparsers.add_parser("send", help="send one digest batch now")
    add_source_args(send_parser)
    add_send_args(send_parser)
    send_parser.add_argument("--sync", action=argparse.BooleanOptionalAction, default=True)
    send_parser.add_argument("--slot-key", default="")
    send_parser.add_argument("--force", action="store_true", help="ignore an already sent slot key")
    send_parser.set_defaults(func=command_send)

    run_parser = subparsers.add_parser("run", help="run the long-lived scheduler")
    add_source_args(run_parser)
    add_send_args(run_parser)
    run_parser.add_argument("--sync", action=argparse.BooleanOptionalAction, default=True)
    run_parser.add_argument("--schedule", default=os.environ.get("GOOD_WORDS_SCHEDULE", DEFAULT_SCHEDULE))
    run_parser.add_argument("--timezone", default=os.environ.get("GOOD_WORDS_TIMEZONE", DEFAULT_TZ))
    run_parser.set_defaults(func=command_run)

    return parser


def add_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source",
        type=Path,
        default=env_path("GOOD_WORDS_SOURCE", DEFAULT_SOURCE),
        help="excerpt Markdown source",
    )
    parser.add_argument("--category", default=os.environ.get("GOOD_WORDS_CATEGORY", DEFAULT_CATEGORY))


def add_send_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--book", default=os.environ.get("GOOD_WORDS_BOOK", DEFAULT_BOOK))
    parser.add_argument("--limit", type=int, default=int(os.environ.get("GOOD_WORDS_LIMIT", DEFAULT_LIMIT)))
    parser.add_argument("--token", default=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument("--chat-id", default=os.environ.get("TELEGRAM_CHAT_ID", ""))
    parser.add_argument("--dry-run", action="store_true", help="print messages without calling Telegram")


def main(argv: list[str] | None = None) -> int:
    early_parser = argparse.ArgumentParser(add_help=False)
    early_parser.add_argument("--env", type=Path, default=APP_DIR / ".env")
    early_args, _ = early_parser.parse_known_args(argv)
    load_dotenv(early_args.env)

    parser = build_parser()
    args = parser.parse_args(argv)
    args.db = args.db.expanduser().resolve()
    if hasattr(args, "source"):
        args.source = args.source.expanduser().resolve()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("stopped")
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
