# LeetBot - Multi-Agent Discord Assistant

A Discord bot with isolated AI agents for LeetCode, stock market, news, and personal alerts.

## Features

- **LeetCode** (`/leetcode`): daily challenge, problem lookup, random problem, user stats
- **Stocks** (`/stock`): real-time quotes, daily summaries via yfinance
- **News** (`/news`): latest headlines from RSS feeds (general, tech, market)
- **Alerts** (`/alert`): stock price alerts and due-date reminders with DM notifications
- **AI** (`/ask`): natural-language queries routed to specialist agents with memory
- **Scheduling** (`/schedule`): automated daily LeetCode challenge and news briefing posts

## Architecture

Four isolated AI agents, each with their own system prompt, tools, and memory:

| Agent | Domain | Memory Namespace |
|-------|--------|-----------------|
| LeetCode | Coding problems, algorithms | `data/memory/leetcode/` |
| Stock | Market data, prices, tickers | `data/memory/stock/` |
| News | Headlines, articles, briefings | `data/memory/news/` |
| Alerts | Price alerts, reminders | `data/memory/alerts/` |

The `/ask` command routes queries to the correct agent via keyword matching with LLM fallback.

## Setup

### Prerequisites

- Python 3.10+
- [Discord Bot Token](https://discord.com/developers/applications)
- [OpenAI API Key](https://platform.openai.com/api-keys) (for AI features)

### Installation

**Option A -- Automatic setup:**

```bash
cd leetbot
chmod +x setup_venv.sh && ./setup_venv.sh
```

**Option B -- Manual setup:**

```bash
cd leetbot
python3.12 -m venv venv
source venv/bin/activate
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Fill in:

```
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
```

3. Optionally configure:

```
DAILY_NOTIFY_HOUR=8
DAILY_NOTIFY_MINUTE=0
MEMORY_TTL_DAYS=7
MEMORY_MAX_CONVERSATIONS=50
```

4. Invite the bot to your server with the `applications.commands` scope.

### Run

```bash
./venv/bin/python run.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/leetcode daily` | Today's LeetCode daily challenge |
| `/leetcode problem <query>` | Look up problem by ID or slug |
| `/leetcode random [difficulty] [topic]` | Random problem with optional filters |
| `/leetcode stats <username>` | LeetCode user profile stats |
| `/stock quote <symbol>` | Real-time stock quote |
| `/stock summary <symbol>` | Detailed daily stock summary |
| `/news latest [category]` | Latest news headlines |
| `/news market` | Market/finance news |
| `/alert price <symbol> <above\|below> <price>` | Set stock price alert |
| `/alert remind <message> <date>` | Set a due-date reminder |
| `/alert list` | View your active alerts |
| `/alert delete <id>` | Remove an alert |
| `/ask <question>` | AI-powered query (auto-routed to specialist agent) |
| `/schedule leetcode <channel> [hour] [minute]` | Enable daily LeetCode notifications |
| `/schedule news <channel> [hour] [minute]` | Enable daily news briefing |
| `/schedule stop <notification>` | Disable a scheduled notification |
| `/schedule status` | Check notification settings |
