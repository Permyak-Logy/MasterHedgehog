from discord.ext import commands
import discord


class BotEmbed(discord.Embed):
    def __init__(self, ctx: commands.Context = None, colour=None, **kwargs):
        colour = ctx.bot.colour if colour is None and ctx else colour
        if ctx and ctx.bot.root_active and ctx.bot.root_id == ctx.author.id:
            colour = discord.Colour.from_rgb(255, 0, 0)
        super().__init__(colour=colour, **kwargs)
        if ctx is not None:
            if ctx.guild:
                self.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)
            self.set_footer(**ctx.bot.footer)
