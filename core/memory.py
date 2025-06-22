# File: core/memory.py

import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, List, Dict, Optional

class MemoryManager:
    """
    Kalıcı, thread-safe hafıza ve görev yöneticisi.
    - Kısa ve uzun vadeli etkileşimleri kaydeder
    - Kod/sohbet geçmişi çıkarır, özetler
    - Zamanlanmış görevleri yönetir
    """

    def __init__(self, db_path: str = "memory.db"):
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execute_at INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0
                )
            """)

    def store_interaction(self, prompt: str, response: str):
        """Persist a prompt/response pair in the database."""

        ts = int(datetime.now(timezone.utc).timestamp())
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO interactions (timestamp, prompt, response) VALUES (?, ?, ?)",
                (ts, prompt, response),
            )

    def retrieve_context(self, limit_tokens: Optional[int] = None, max_interactions: int = 10) -> str:
        """
        Son konuşma/kod geçmişini döndürür.
        """
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT prompt, response FROM interactions ORDER BY timestamp DESC LIMIT ?",
                (max_interactions,)
            )
            rows = cur.fetchall()
        # kronolojik sıraya çevir
        parts = []
        for row in reversed(rows):
            parts.append(f"User: {row['prompt']}")
            parts.append(f"AI: {row['response']}")
        return "\n".join(parts)

    def add_task(self, execute_at: datetime, payload: Dict[str, Any]):
        """Schedule a task to be executed in the future."""

        ts = int(execute_at.replace(tzinfo=timezone.utc).timestamp())
        import json
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO tasks (execute_at, payload, done) VALUES (?, ?, 0)",
                (ts, json.dumps(payload)),
            )

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        Zamanı gelmiş görevleri döndürür ve 'done' olarak işaretler.
        """
        now_ts = int(datetime.now(timezone.utc).timestamp())
        import json
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT id, payload FROM tasks WHERE done = 0 AND execute_at <= ?",
                (now_ts,)
            )
            rows = cur.fetchall()
            task_ids = [row["id"] for row in rows]
            payloads = [json.loads(row["payload"]) for row in rows]
            if task_ids:
                q = ",".join("?" for _ in task_ids)
                self._conn.execute(f"UPDATE tasks SET done = 1 WHERE id IN ({q})", task_ids)
        return payloads

    def prune(self, max_age_seconds: int = 86400):
        """
        Eski konuşmaları/görevleri temizler.
        """
        cutoff_ts = int((datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)).timestamp())
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM interactions WHERE timestamp < ?",
                (cutoff_ts,)
            )
            self._conn.execute(
                "DELETE FROM tasks WHERE done = 1 AND execute_at < ?",
                (cutoff_ts,)
            )

    def get_all_interactions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Son N etkileşimi kronolojik sırayla döndürür."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT prompt, response FROM interactions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        return list(reversed([dict(row) for row in rows]))

    def close(self):
        """Close the underlying database connection."""

        with self._lock:
            self._conn.close()
