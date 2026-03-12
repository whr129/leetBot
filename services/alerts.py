"""Alert service with JSON-file persistence."""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("leetbot.alerts")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ALERTS_FILE = DATA_DIR / "alerts.json"


@dataclass
class Alert:
    id: str
    user_id: int
    alert_type: str  # "price" or "reminder"
    config: dict = field(default_factory=dict)
    created_at: str = ""
    triggered: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class AlertService:
    """CRUD and checking for user alerts."""

    def __init__(self):
        self._alerts: list[dict] = []
        self._load()

    def _load(self) -> None:
        if ALERTS_FILE.exists():
            try:
                self._alerts = json.loads(ALERTS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self._alerts = []

    def _save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ALERTS_FILE.write_text(json.dumps(self._alerts, indent=2, ensure_ascii=False))

    def create_alert(
        self,
        user_id: int,
        alert_type: str,
        config: dict,
    ) -> Alert:
        alert = Alert(
            id=uuid.uuid4().hex[:8],
            user_id=user_id,
            alert_type=alert_type,
            config=config,
        )
        self._alerts.append(asdict(alert))
        self._save()
        return alert

    def list_alerts(self, user_id: int) -> list[dict]:
        return [a for a in self._alerts if a["user_id"] == user_id and not a.get("triggered")]

    def delete_alert(self, user_id: int, alert_id: str) -> bool:
        before = len(self._alerts)
        self._alerts = [
            a for a in self._alerts
            if not (a["id"] == alert_id and a["user_id"] == user_id)
        ]
        if len(self._alerts) < before:
            self._save()
            return True
        return False

    def check_price_alerts(self, prices: dict[str, float]) -> list[dict]:
        """Check price alerts against current prices. Returns triggered alerts."""
        triggered = []
        for alert in self._alerts:
            if alert.get("triggered") or alert["alert_type"] != "price":
                continue
            cfg = alert["config"]
            symbol = cfg.get("symbol", "").upper()
            current = prices.get(symbol)
            if current is None:
                continue
            direction = cfg.get("direction", "above")
            target = cfg.get("target", 0)
            if (direction == "above" and current >= target) or \
               (direction == "below" and current <= target):
                alert["triggered"] = True
                triggered.append({**alert, "current_price": current})
        if triggered:
            self._save()
        return triggered

    def check_reminder_alerts(self) -> list[dict]:
        """Check reminder alerts against current time. Returns triggered alerts."""
        now = datetime.now(timezone.utc)
        triggered = []
        for alert in self._alerts:
            if alert.get("triggered") or alert["alert_type"] != "reminder":
                continue
            cfg = alert["config"]
            due = cfg.get("due_date")
            if not due:
                continue
            try:
                due_dt = datetime.fromisoformat(due)
                if due_dt.tzinfo is None:
                    due_dt = due_dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            if now >= due_dt:
                alert["triggered"] = True
                triggered.append(alert)
        if triggered:
            self._save()
        return triggered

    def get_unique_symbols(self) -> set[str]:
        """Get all symbols that have active price alerts."""
        return {
            a["config"]["symbol"].upper()
            for a in self._alerts
            if a["alert_type"] == "price"
            and not a.get("triggered")
            and a["config"].get("symbol")
        }
