import gtts

import discord
from discord.ext import commands

from PLyBot import Bot, Cog, Context


# TODO: Роли бустеры

# TODO: Команда для снятия роли
# TODO: Сделать подробные ошибки при отсутствии класса
# TODO: Pymorphy


class AICog(Cog, name='Ёжа Ёжиков'):
    def __init__(self, bot: Bot):
        super().__init__(bot, emoji_icon='👾')
        self.cur_guild: discord.Guild = None

    async def cog_check(self, ctx: Context):
        return await ctx.bot.is_owner(ctx.author)

    @commands.group("ai")
    async def _group_ai(self, ctx: Context):
        pass

    @_group_ai.command("say")
    async def _cmd_ai_say(self, ctx: Context, *, text: str):
        assert self.cur_guild, "Нет активной гильдии"

        tts = gtts.gTTS(text, lang="ru")
        filename = f"tmp\\{ctx.message.id}.mp3"
        tts.save(filename)
        # playsound.playsound(filename)

        self.cur_guild.voice_client.play(discord.FFmpegPCMAudio(filename))
        self.cur_guild.voice_client.source.volume = 50 / 100

    @_group_ai.command("join")
    async def _cmd_ai_join(self, ctx: Context, channel: discord.VoiceChannel = None):
        channel = channel or ctx.author.voice.channel
        assert channel, "Не указан голосовой канал для присоединения"
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()
        self.cur_guild = ctx.guild


    @_group_ai.command("work_guild")
    async def _cmd_ai_work_guild(self, ctx: Context, guild: discord.Guild):
        self.cur_guild = guild

    def make_voice(self, text: str) -> str:
        pass

    def play_voice(self, voice: discord.VoiceClient, file_voice: str):
        pass


async def setup(bot: Bot):
    await bot.add_cog(AICog(bot))
