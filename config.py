"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LEETCODE_API_BASE = os.getenv("LEETCODE_API_BASE", "https://leetcode-api-pied.vercel.app")

AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "8"))

DAILY_NOTIFY_HOUR = int(os.getenv("DAILY_NOTIFY_HOUR", "8"))
DAILY_NOTIFY_MINUTE = int(os.getenv("DAILY_NOTIFY_MINUTE", "0"))

ALERT_CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "5"))

MEMORY_TTL_DAYS = int(os.getenv("MEMORY_TTL_DAYS", "7"))
MEMORY_MAX_CONVERSATIONS = int(os.getenv("MEMORY_MAX_CONVERSATIONS", "50"))
