from random import random

import discord
from discord.ext import tasks

from PLyBot import Cog, Bot


class GameActivityCog(Cog, name="Игровая активность"):
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.category_id = 827851596234620948
        self.guild_id = 827497841286840351

    # @commands.Cog.listener('on_ready')
    async def run_handles(self):
        self.handle_activity.start()

    @tasks.loop(minutes=10)
    async def handle_activity(self):
        guild: discord.Guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return
        for channel in guild.voice_channels:
            await self.handle_channel_game_activity(channel)

    async def handle_channel_game_activity(self, channel):
        if channel.category_id != self.category_id:
            return
        if channel.guild.id != self.guild_id:
            return

        game_acts = {}
        custom_acts = {}
        for member in channel.members:
            member: discord.Member
            for act in member.activities:
                if isinstance(act, discord.Game):
                    game_acts.setdefault(act.name, 0)
                    game_acts[act.name] += 1
                elif isinstance(act, discord.CustomActivity):
                    custom_acts.setdefault(act.name, 0)
                    custom_acts[act.name] += 1

        if not game_acts:
            name = 'Нет игр'
            if channel.name != name:
                await channel.edit(name=name)
        else:
            game = max(game_acts.keys(), key=lambda k: (game_acts[k], random()))
            game = f"{game_acts[game]}: {game}"
            if channel.name != game:
                await channel.edit(name=game)


def setup(bot: Bot):
    bot.add_cog(GameActivityCog(bot))
