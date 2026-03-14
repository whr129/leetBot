# SWE Bot - Multi-Agent Discord Assistant

A Discord bot with an LLM-powered orchestrator that coordinates specialist AI agents for LeetCode, stock market, news, and personal alerts. Features RAG-based memory with ChromaDB for semantic recall across short-term, long-term, and cross-agent knowledge.

## Features

- **LeetCode** (`/leetcode`): daily challenge, problem lookup, random problem, user stats
- **Stocks** (`/stock`): real-time quotes, daily summaries via yfinance
- **News** (`/news`): latest headlines from RSS feeds (general, tech, market)
- **Alerts** (`/alert`): stock price alerts and due-date reminders with DM notifications
- **AI** (`/ask`): natural-language queries orchestrated across multiple specialist agents
- **Scheduling** (`/schedule`): automated daily LeetCode challenge and news briefing posts
- **RAG Memory**: ChromaDB-backed short-term, long-term, and shared memory with semantic retrieval

## Architecture

An orchestrator decomposes queries and coordinates specialist agents. Multiple agents can collaborate on a single query (e.g. stock + news for a market briefing).

```
User ──▶ /ask ──▶ Orchestrator
                      │
              ┌───────┼───────┐
         1. Plan   2. Execute  3. Synthesize
              │       │              │
              ▼       ▼              ▼
         LLM picks   Agents run    LLM merges
         agents      (parallel     multi-agent
         + subtasks   or sequential) results
```

### Agents

| Agent | Domain | Playbook |
|-------|--------|----------|
| LeetCode | Coding problems, algorithms | `agents/playbooks/leetcode.md` |
| Stock | Market data, prices, tickers | `agents/playbooks/stock.md` |
| News | Headlines, articles, briefings | `agents/playbooks/news.md` |
| Alerts | Price alerts, reminders | `agents/playbooks/alerts.md` |

### Memory System

ChromaDB-backed RAG memory with three layers:

| Layer | Purpose | Expiry |
|-------|---------|--------|
| **Short-term** | Recent conversations, embedded for semantic search | TTL-based (default 7 days) |
| **Long-term** | User preferences, curated facts and insights | Never expires |
| **Shared** | Cross-agent knowledge (e.g. stock agent saves a price milestone that news agent can reference) | Never expires |

Memory recall is semantic: when an agent runs, only memories relevant to the current query are retrieved (not all history), saving context window tokens.

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
pip install -r requirements.txt
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
AI_MODEL=gpt-4o-mini
CHROMA_PERSIST_DIR=data/chromadb
MEMORY_SHORT_TERM_TTL_DAYS=7
MEMORY_RECALL_LIMIT=5
EMBEDDING_MODEL=text-embedding-3-small
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
| `/ask <question>` | AI-powered query (orchestrated across agents) |
| `/schedule leetcode <channel> [hour] [minute]` | Enable daily LeetCode notifications |
| `/schedule news <channel> [hour] [minute]` | Enable daily news briefing |
| `/schedule stop <notification>` | Disable a scheduled notification |
| `/schedule status` | Check notification settings |

## Project Structure

```
agents/
  base.py              # BaseAgent - ReAct loop with playbook loading and RAG memory
  orchestrator.py       # Orchestrator - plan/execute/synthesize multi-agent pipeline
  leetcode.py           # LeetCode agent tools and executor
  stock.py              # Stock agent tools and executor
  news.py               # News agent tools and executor
  alerts.py             # Alerts agent tools and executor
  playbooks/            # Markdown files defining agent behavior
    _base.md            # Shared rules for all agents
    orchestrator.md     # How the orchestrator plans and coordinates
    leetcode.md         # LeetCode agent role, memory guidelines, collaboration rules
    stock.md            # Stock agent role, memory guidelines, collaboration rules
    news.md             # News agent role, memory guidelines, collaboration rules
    alerts.md           # Alerts agent role, memory guidelines, collaboration rules

services/
  memory/               # RAG memory system
    __init__.py         # MemoryManager facade
    chroma_store.py     # ChromaDB wrapper (3 collections)
    short_term.py       # TTL-based conversation memory
    long_term.py        # Persistent facts and preferences
    shared.py           # Cross-agent knowledge base
    migration.py        # Legacy JSON-to-ChromaDB migration
  leetcode.py           # LeetCode API client
  stock.py              # yfinance wrapper
  news.py               # RSS feed parser
  alerts.py             # Alert CRUD + checking

bot/
  main.py               # Bot creation and cog loading
  cogs/
    ai.py               # /ask command with orchestrator wiring
    leetcode.py         # /leetcode commands
    stock.py            # /stock commands
    news.py             # /news commands
    alerts.py           # /alert commands
    scheduler.py        # Scheduled tasks (daily posts, alert checks)
  utils/
    embeds.py           # Discord embed helpers

data/
  chromadb/             # ChromaDB vector store (auto-created)
  alerts.json           # Active user alerts
  schedule_config.json  # Per-guild schedule settings
```
