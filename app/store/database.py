"""SQLite 持久化。"""

from __future__ import annotations

import json
import sqlite3
import logging
from pathlib import Path
from typing import Any

from app.core.app_types import ConversationState, utc_now_text


class BotStore:
    def __init__(self, db_path: Path) -> None:
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._init_db()
        except sqlite3.OperationalError:
            fallback_path = self.db_path.with_name(f"{self.db_path.stem}-local{self.db_path.suffix}")
            self.logger.warning("默认数据库文件不可用，改用备用库文件: %s", fallback_path)
            self.db_path = fallback_path
            self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # 当前工作区下 SQLite 默认磁盘日志模式会报 I/O 错误，这里改成内存日志模式。
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    item_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    chat_id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    manual_mode INTEGER NOT NULL DEFAULT 0,
                    last_message TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS escalations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    slot_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def save_message(
        self,
        chat_id: str,
        item_id: str,
        sender_id: str,
        sender_name: str,
        role: str,
        content: str,
        created_at_ms: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    chat_id, item_id, sender_id, sender_name, role, content, created_at_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    item_id,
                    sender_id,
                    sender_name,
                    role,
                    content,
                    created_at_ms,
                    utc_now_text(),
                ),
            )
            conn.commit()

    def get_recent_messages(self, chat_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT sender_name, role, content, created_at
                FROM messages
                WHERE chat_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (chat_id, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def get_chat_history(self, chat_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if limit is None:
                rows = conn.execute(
                    """
                    SELECT sender_name, role, content, created_at
                    FROM messages
                    WHERE chat_id = ?
                    ORDER BY id ASC
                    """,
                    (chat_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT sender_name, role, content, created_at
                    FROM messages
                    WHERE chat_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (chat_id, limit),
                ).fetchall()
                rows = list(reversed(rows))
        return [dict(row) for row in rows]

    def save_item(self, item_id: str, item_data: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO items (item_id, item_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET item_json = excluded.item_json, updated_at = excluded.updated_at
                """,
                (item_id, json.dumps(item_data, ensure_ascii=False), utc_now_text()),
            )
            conn.commit()

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT item_json FROM items WHERE item_id = ?", (item_id,)).fetchone()
        return json.loads(row["item_json"]) if row else None

    def upsert_conversation(
        self,
        chat_id: str,
        item_id: str,
        customer_id: str,
        customer_name: str,
        status: str,
        manual_mode: bool,
        last_message: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (
                    chat_id, item_id, customer_id, customer_name, status, manual_mode, last_message, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    item_id = excluded.item_id,
                    customer_id = excluded.customer_id,
                    customer_name = excluded.customer_name,
                    status = excluded.status,
                    manual_mode = excluded.manual_mode,
                    last_message = excluded.last_message,
                    updated_at = excluded.updated_at
                """,
                (
                    chat_id,
                    item_id,
                    customer_id,
                    customer_name,
                    status,
                    1 if manual_mode else 0,
                    last_message,
                    utc_now_text(),
                ),
            )
            conn.commit()

    def set_manual_mode(self, chat_id: str, manual_mode: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversations SET manual_mode = ?, status = ?, updated_at = ? WHERE chat_id = ?",
                (1 if manual_mode else 0, "manual" if manual_mode else "auto", utc_now_text(), chat_id),
            )
            conn.commit()

    def touch_conversation_status(self, chat_id: str, status: str, last_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET status = ?, manual_mode = ?, last_message = ?, updated_at = ?
                WHERE chat_id = ?
                """,
                (status, 1 if status == "manual" else 0, last_message, utc_now_text(), chat_id),
            )
            conn.commit()

    def is_manual_mode(self, chat_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT manual_mode FROM conversations WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
        return bool(row["manual_mode"]) if row else False

    def list_conversations(self, limit: int = 50) -> list[ConversationState]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chat_id, item_id, customer_id, customer_name, status, manual_mode, last_message, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            ConversationState(
                chat_id=row["chat_id"],
                item_id=row["item_id"],
                customer_id=row["customer_id"],
                customer_name=row["customer_name"],
                status=row["status"],
                manual_mode=bool(row["manual_mode"]),
                last_message=row["last_message"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def create_escalation(self, chat_id: str, item_id: str, customer_name: str, reason: str, summary: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO escalations (chat_id, item_id, customer_name, reason, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chat_id, item_id, customer_name, reason, summary, utc_now_text()),
            )
            conn.commit()

    def list_escalations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, chat_id, item_id, customer_name, reason, summary, created_at
                FROM escalations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_appointment(self, chat_id: str, item_id: str, customer_name: str, slot_text: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO appointments (chat_id, item_id, customer_name, slot_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chat_id, item_id, customer_name, slot_text, utc_now_text()),
            )
            conn.commit()

    def list_appointments(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, chat_id, item_id, customer_name, slot_text, created_at
                FROM appointments
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
