"""Stock market slash commands."""

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from bot.utils.embeds import error_embed


class StockCog(commands.Cog):
    """Stock market commands."""

    stock_group = SlashCommandGroup("stock", "Stock market commands")

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.stock = bot.stock_service

    @stock_group.command(name="quote", description="Get a real-time stock quote")
    async def quote(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, description="Stock ticker symbol (e.g. AAPL)"),
    ) -> None:
        await ctx.defer()
        try:
            q = await self.stock.get_quote(symbol)
            color = discord.Color.green() if q.change >= 0 else discord.Color.red()
            arrow = "+" if q.change >= 0 else ""
            embed = discord.Embed(
                title=f"{q.symbol} - {q.name}",
                color=color,
            )
            embed.add_field(name="Price", value=f"${q.price:,.2f} {q.currency}", inline=True)
            embed.add_field(name="Change", value=f"{arrow}{q.change:,.2f} ({arrow}{q.change_pct:.2f}%)", inline=True)
            embed.add_field(name="Volume", value=f"{q.volume:,}", inline=True)
            if q.market_cap:
                cap = q.market_cap
                if cap >= 1e12:
                    cap_str = f"${cap / 1e12:.2f}T"
                elif cap >= 1e9:
                    cap_str = f"${cap / 1e9:.2f}B"
                else:
                    cap_str = f"${cap / 1e6:.2f}M"
                embed.add_field(name="Market Cap", value=cap_str, inline=True)
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch quote: {e}"))

    @stock_group.command(name="summary", description="Get a detailed daily summary for a stock")
    async def summary(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, description="Stock ticker symbol (e.g. AAPL)"),
    ) -> None:
        await ctx.defer()
        try:
            s = await self.stock.get_daily_summary(symbol)
            change = s.close - s.prev_close
            change_pct = (change / s.prev_close * 100) if s.prev_close else 0
            color = discord.Color.green() if change >= 0 else discord.Color.red()
            embed = discord.Embed(
                title=f"{s.symbol} - {s.name} Daily Summary",
                color=color,
            )
            embed.add_field(name="Open", value=f"${s.open:,.2f}", inline=True)
            embed.add_field(name="High", value=f"${s.high:,.2f}", inline=True)
            embed.add_field(name="Low", value=f"${s.low:,.2f}", inline=True)
            embed.add_field(name="Close", value=f"${s.close:,.2f}", inline=True)
            arrow = "+" if change >= 0 else ""
            embed.add_field(name="Change", value=f"{arrow}{change:,.2f} ({arrow}{change_pct:.2f}%)", inline=True)
            embed.add_field(name="Volume", value=f"{s.volume:,}", inline=True)
            if s.pe_ratio:
                embed.add_field(name="P/E Ratio", value=f"{s.pe_ratio:.2f}", inline=True)
            if s.fifty_two_week_high and s.fifty_two_week_low:
                embed.add_field(
                    name="52-Week Range",
                    value=f"${s.fifty_two_week_low:,.2f} - ${s.fifty_two_week_high:,.2f}",
                    inline=True,
                )
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch summary: {e}"))


def setup(bot: discord.Bot) -> None:
    from services.stock import StockService
    bot.stock_service = StockService()
    bot.add_cog(StockCog(bot))
