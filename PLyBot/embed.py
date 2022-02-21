from discord.ext import commands
import discord


class BotEmbed(discord.Embed):
    def __init__(self, ctx: commands.Context = None, colour=discord.embeds.EmptyEmbed, **kwargs):
        super().__init__(colour=ctx.bot.colour if colour is discord.embeds.EmptyEmbed else colour, **kwargs)
        if ctx is not None:
            self.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            self.set_footer(**ctx.bot.footer)
