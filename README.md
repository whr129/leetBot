# LeetBot - LeetCode Discord AI Assistant

A Discord bot that integrates LeetCode with AI capabilities.

## Features

- **LeetCode commands** (`/leetcode`): daily challenge, problem lookup, random problem, user stats
- **AI commands** (`/ai`): ask questions, natural-language problem search, practice suggestions
- **Daily notifications** (`/notify`): schedule automatic daily challenge posts to a channel

## Setup

### Prerequisites

- Python 3.10+
- [Discord Bot Token](https://discord.com/developers/applications)
- [OpenAI API Key](https://platform.openai.com/api-keys) (for AI features)

### Installation

**Option A – Automatic setup (recommended):**

```bash
cd leetbot
chmod +x setup_venv.sh && ./setup_venv.sh
```

**Option B – Manual setup:**

```bash
cd leetbot
# Use Python 3.12 (3.14+ has compatibility issues with py-cord)
python3.12 -m venv venv
source venv/bin/activate   # or `venv\Scripts\activate` on Windows
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Fill in:

```
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
```

3. Optionally configure the daily notification default time (UTC):

```
DAILY_NOTIFY_HOUR=8
DAILY_NOTIFY_MINUTE=0
```

4. Invite the bot to your server with the `applications.commands` scope.

### Run

```bash
# Use venv's Python directly (avoids conda/system Python conflicts):
./venv/bin/python run.py

# Or use the wrapper:
./run.sh
```

If you see `ModuleNotFoundError: No module named 'discord'`, you're likely using the wrong Python. With conda active, `python` may point to conda. Use `./venv/bin/python run.py` instead.

## Commands

| Command | Description |
|---------|-------------|
| `/leetcode daily` | Today's LeetCode daily challenge |
| `/leetcode problem <query>` | Look up problem by ID or slug |
| `/leetcode random [difficulty] [topic]` | Random problem with optional filters |
| `/leetcode stats [username]` | LeetCode user profile stats |
| `/ai ask <question>` | Ask AI about LeetCode |
| `/ai search <query>` | Search problems with natural language |
| `/ai generate [topic] [difficulty]` | AI-suggested practice problem |
| `/notify setup <channel> [hour] [minute]` | Enable daily challenge notifications |
| `/notify stop` | Disable daily notifications |
| `/notify status` | Check notification settings |
