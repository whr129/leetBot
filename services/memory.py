"""Namespace-scoped agent memory with TTL-based expiration."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("leetbot.memory")

DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "memory"


class AgentMemory:
    """Per-agent, per-user memory store with conversation history and preferences.

    Each instance is scoped to a namespace (e.g. "leetcode", "stock") so agents
    cannot read or write each other's data.
    """

    def __init__(
        self,
        namespace: str,
        ttl_days: int = 7,
        max_conversations: int = 50,
    ):
        self.namespace = namespace
        self.ttl_seconds = ttl_days * 86400
        self.max_conversations = max_conversations
        self._conv_dir = DATA_ROOT / namespace / "conversations"
        self._pref_dir = DATA_ROOT / namespace / "preferences"

    def _ensure_dirs(self) -> None:
        self._conv_dir.mkdir(parents=True, exist_ok=True)
        self._pref_dir.mkdir(parents=True, exist_ok=True)

    def _conv_path(self, user_id: int) -> Path:
        return self._conv_dir / f"{user_id}.json"

    def _pref_path(self, user_id: int) -> Path:
        return self._pref_dir / f"{user_id}.json"

    def _now(self) -> float:
        return time.time()

    def _prune(self, entries: list[dict]) -> list[dict]:
        cutoff = self._now() - self.ttl_seconds
        return [e for e in entries if e.get("ts", 0) > cutoff]

    # -- Conversation history --------------------------------------------------

    def get_conversations(self, user_id: int, limit: int = 10) -> list[dict]:
        path = self._conv_path(user_id)
        if not path.exists():
            return []
        try:
            entries = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []
        entries = self._prune(entries)
        return entries[-limit:]

    def add_conversation(self, user_id: int, question: str, answer: str) -> None:
        self._ensure_dirs()
        path = self._conv_path(user_id)
        try:
            entries = json.loads(path.read_text()) if path.exists() else []
        except (json.JSONDecodeError, OSError):
            entries = []
        entries = self._prune(entries)
        entries.append({"q": question, "a": answer, "ts": self._now()})
        if len(entries) > self.max_conversations:
            entries = entries[-self.max_conversations:]
        path.write_text(json.dumps(entries, ensure_ascii=False))

    # -- User preferences ------------------------------------------------------

    def get_preferences(self, user_id: int) -> dict[str, Any]:
        path = self._pref_path(user_id)
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
        cutoff = self._now() - self.ttl_seconds
        pruned = {k: v for k, v in raw.items() if v.get("ts", 0) > cutoff}
        if len(pruned) != len(raw):
            self._ensure_dirs()
            path.write_text(json.dumps(pruned, ensure_ascii=False))
        return {k: v["val"] for k, v in pruned.items()}

    def save_preference(self, user_id: int, key: str, value: Any) -> None:
        self._ensure_dirs()
        path = self._pref_path(user_id)
        try:
            raw = json.loads(path.read_text()) if path.exists() else {}
        except (json.JSONDecodeError, OSError):
            raw = {}
        raw[key] = {"val": value, "ts": self._now()}
        path.write_text(json.dumps(raw, ensure_ascii=False))

    # -- Recall (combined) -----------------------------------------------------

    def recall(self, user_id: int, conv_limit: int = 5) -> dict:
        return {
            "recent_conversations": self.get_conversations(user_id, limit=conv_limit),
            "preferences": self.get_preferences(user_id),
        }

    # -- Cleanup ---------------------------------------------------------------

    def cleanup_all(self) -> int:
        """Prune stale entries across all users. Returns number of files cleaned."""
        cleaned = 0
        for directory in (self._conv_dir, self._pref_dir):
            if not directory.exists():
                continue
            for path in directory.glob("*.json"):
                try:
                    user_id = int(path.stem)
                except ValueError:
                    continue
                if directory == self._conv_dir:
                    self.get_conversations(user_id)
                else:
                    self.get_preferences(user_id)
                cleaned += 1
        return cleaned
