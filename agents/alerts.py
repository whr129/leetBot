"""Personal alert/reminder specialist agent with isolated tools and memory."""

from typing import Any, Optional

from openai import AsyncOpenAI

from agents.base import BaseAgent
from services.alerts import AlertService
from services.memory import AgentMemory

SYSTEM_PROMPT = """\
You are a personal alert and reminder assistant in a Discord server.

You can create stock price alerts and due-date reminders, list active alerts, \
and delete alerts using the tools provided.

Guidelines:
- Be concise. Discord messages have a 2000-char limit.
- When creating a price alert, confirm the symbol, direction (above/below), and target price.
- When creating a reminder, confirm the message and due date/time.
- Parse natural language dates (e.g. "next Friday", "in 3 days") into ISO format.
- Always show the alert ID so the user can delete it later.
- Use Markdown formatting for readability in Discord.
"""

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "create_price_alert",
            "description": "Create a stock price alert that triggers when a stock goes above or below a target price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "Discord user ID"},
                    "symbol": {"type": "string", "description": "Stock ticker symbol, e.g. 'AAPL'"},
                    "direction": {"type": "string", "enum": ["above", "below"], "description": "Trigger when price goes above or below target"},
                    "target": {"type": "number", "description": "Target price"},
                },
                "required": ["user_id", "symbol", "direction", "target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a due-date reminder that triggers at a specific date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "Discord user ID"},
                    "message": {"type": "string", "description": "Reminder message"},
                    "due_date": {"type": "string", "description": "Due date in ISO format (YYYY-MM-DDTHH:MM:SS)"},
                },
                "required": ["user_id", "message", "due_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_alerts",
            "description": "List all active (non-triggered) alerts for a user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "Discord user ID"},
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_alert",
            "description": "Delete an alert by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "Discord user ID"},
                    "alert_id": {"type": "string", "description": "The alert ID to delete"},
                },
                "required": ["user_id", "alert_id"],
            },
        },
    },
]


class AlertAgent(BaseAgent):
    name = "alerts"
    system_prompt = SYSTEM_PROMPT
    tool_definitions = TOOL_DEFINITIONS

    def __init__(
        self,
        client: Optional[AsyncOpenAI],
        alert_service: AlertService,
        model: str = "gpt-4o-mini",
        max_iterations: int = 8,
        memory_ttl_days: int = 7,
        memory_max_conversations: int = 50,
    ):
        memory = AgentMemory("alerts", ttl_days=memory_ttl_days, max_conversations=memory_max_conversations)
        super().__init__(client=client, memory=memory, model=model, max_iterations=max_iterations)
        self.alerts = alert_service

    async def execute_tool(self, name: str, args: dict) -> Any:
        if name == "create_price_alert":
            alert = self.alerts.create_alert(
                user_id=args["user_id"],
                alert_type="price",
                config={
                    "symbol": args["symbol"].upper(),
                    "direction": args["direction"],
                    "target": args["target"],
                },
            )
            return {
                "status": "created",
                "id": alert.id,
                "symbol": args["symbol"].upper(),
                "direction": args["direction"],
                "target": args["target"],
            }

        if name == "create_reminder":
            alert = self.alerts.create_alert(
                user_id=args["user_id"],
                alert_type="reminder",
                config={
                    "message": args["message"],
                    "due_date": args["due_date"],
                },
            )
            return {
                "status": "created",
                "id": alert.id,
                "message": args["message"],
                "due_date": args["due_date"],
            }

        if name == "list_alerts":
            alerts = self.alerts.list_alerts(args["user_id"])
            if not alerts:
                return {"alerts": [], "message": "No active alerts."}
            return {"alerts": alerts}

        if name == "delete_alert":
            deleted = self.alerts.delete_alert(args["user_id"], args["alert_id"])
            if deleted:
                return {"status": "deleted", "id": args["alert_id"]}
            return {"status": "not_found", "id": args["alert_id"]}

        return {"error": f"Unknown tool: {name}"}
