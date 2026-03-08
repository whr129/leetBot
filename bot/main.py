"""Discord bot main setup and cog loading."""

import logging
from pathlib import Path

import discord

import config
from services.leetcode import LeetCodeService

# Configure logging - stdout + optional file
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
# Also write to logs/leetbot.log when directory exists
log_dir = Path(__file__).resolve().parent.parent / "logs"
if log_dir.exists():
    fh = logging.FileHandler(log_dir / "leetbot.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(fh)
logger = logging.getLogger("leetbot")


def create_bot() -> discord.Bot:
    """Create and configure the LeetBot."""
    intents = discord.Intents.default()

    bot = discord.Bot(
        intents=intents,
        description="LeetCode AI Assistant for Discord",
    )
    bot.leetcode = LeetCodeService(base_url=config.LEETCODE_API_BASE)

    @bot.event
    async def on_ready() -> None:
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
        logger.info("------")

    @bot.event
    async def on_application_command_error(ctx: discord.ApplicationContext, error: Exception) -> None:
        """Handle slash command errors gracefully."""
        logger.warning(f"Command error: {ctx.command} - {error}")
        try:
            msg = str(error)
            if len(msg) > 500:
                msg = msg[:500] + "..."
            await ctx.respond(embed=discord.Embed(title="Error", description=msg, color=discord.Color.red()))
        except discord.NotFound:
            pass
        except Exception as e:
            logger.exception(f"Failed to send error to user: {e}")

    return bot


def setup_cogs(bot: discord.Bot) -> None:
    """Load all cogs."""
    cogs = ["bot.cogs.leetcode", "bot.cogs.daily_notify", "bot.cogs.ai"]
    for cog in cogs:
        try:
            bot.load_extension(cog)
            logger.info(f"Loaded cog: {cog}")
        except Exception as e:
            logger.warning(f"Failed to load {cog}: {e}")

