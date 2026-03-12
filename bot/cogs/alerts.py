"""Alert slash commands for stock price alerts and reminders."""

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from bot.utils.embeds import error_embed


class AlertCog(commands.Cog):
    """Personal alert commands."""

    alert_group = SlashCommandGroup("alert", "Personal alert commands")

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.alerts = bot.alert_service

    @alert_group.command(name="price", description="Set a stock price alert")
    async def price_alert(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, description="Stock ticker symbol (e.g. AAPL)"),
        direction: discord.Option(
            str,
            description="Trigger when price goes...",
            choices=[
                discord.OptionChoice("Above", "above"),
                discord.OptionChoice("Below", "below"),
            ],
        ),
        target: discord.Option(float, description="Target price"),
    ) -> None:
        alert = self.alerts.create_alert(
            user_id=ctx.author.id,
            alert_type="price",
            config={"symbol": symbol.upper(), "direction": direction, "target": target},
        )
        embed = discord.Embed(
            title="Price Alert Created",
            description=(
                f"You'll be notified when **{symbol.upper()}** goes "
                f"**{direction}** **${target:,.2f}**."
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Alert ID: {alert.id}")
        await ctx.respond(embed=embed)

    @alert_group.command(name="remind", description="Set a due-date reminder")
    async def reminder(
        self,
        ctx: discord.ApplicationContext,
        message: discord.Option(str, description="Reminder message"),
        due_date: discord.Option(str, description="Due date (YYYY-MM-DD or YYYY-MM-DDTHH:MM)"),
    ) -> None:
        alert = self.alerts.create_alert(
            user_id=ctx.author.id,
            alert_type="reminder",
            config={"message": message, "due_date": due_date},
        )
        embed = discord.Embed(
            title="Reminder Created",
            description=f"**{message}**\nDue: {due_date}",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Alert ID: {alert.id}")
        await ctx.respond(embed=embed)

    @alert_group.command(name="list", description="List your active alerts")
    async def list_alerts(self, ctx: discord.ApplicationContext) -> None:
        alerts = self.alerts.list_alerts(ctx.author.id)
        if not alerts:
            await ctx.respond(
                embed=discord.Embed(
                    title="Your Alerts",
                    description="No active alerts. Use `/alert price` or `/alert remind` to create one.",
                    color=discord.Color.greyple(),
                )
            )
            return
        lines = []
        for a in alerts:
            cfg = a.get("config", {})
            if a["alert_type"] == "price":
                lines.append(
                    f"`{a['id']}` **{cfg.get('symbol')}** {cfg.get('direction')} "
                    f"${cfg.get('target', 0):,.2f}"
                )
            elif a["alert_type"] == "reminder":
                lines.append(f"`{a['id']}` **{cfg.get('message')}** due {cfg.get('due_date')}")
        embed = discord.Embed(
            title="Your Alerts",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await ctx.respond(embed=embed)

    @alert_group.command(name="delete", description="Delete an alert")
    async def delete_alert(
        self,
        ctx: discord.ApplicationContext,
        alert_id: discord.Option(str, description="Alert ID to delete"),
    ) -> None:
        deleted = self.alerts.delete_alert(ctx.author.id, alert_id)
        if deleted:
            await ctx.respond(
                embed=discord.Embed(
                    title="Alert Deleted",
                    description=f"Alert `{alert_id}` has been removed.",
                    color=discord.Color.green(),
                )
            )
        else:
            await ctx.respond(embed=error_embed(f"Alert `{alert_id}` not found."))


def setup(bot: discord.Bot) -> None:
    from services.alerts import AlertService
    bot.alert_service = AlertService()
    bot.add_cog(AlertCog(bot))
