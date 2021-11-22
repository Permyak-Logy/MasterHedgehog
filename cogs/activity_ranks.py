import math

import discord
from discord.ext import commands

import db_session
from db_session import SqlAlchemyBase, BaseConfigMix, MIN_DATETIME
from sqlalchemy import Column, ForeignKey, Integer, String, Date
from PLyBot import Bot, Cog, Context


class ActivityRanksConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "activity_ranks_configs"

    guild_id = Column(Integer, ForeignKey('guilds.id'),
                      primary_key=True, nullable=False)
    access = Column(String, nullable=False, default='{}')
    active_until = Column(Date, nullable=True, default=MIN_DATETIME)


class RanksMembers(SqlAlchemyBase):
    __tablename__ = "activity_ranks_members"

    config_id = Column(Integer, ForeignKey('activity_ranks_configs.guild_id'), primary_key=True, nullable=False)
    member_id = Column(Integer, ForeignKey('users.id'), primary_key=True, nullable=False)
    experience = Column(Integer, nullable=False, default=0)
    mugs_kvass = Column(Integer, default=0)

    @staticmethod
    def get(session: db_session.Session, member: discord.Member):
        return session.query(RanksMembers).filter(RanksMembers.config_id == member.guild.id,
                                                  RanksMembers.member_id == member.id).first()

    @staticmethod
    def get_position(session: db_session.Session, member: discord.Member):
        all_members_ranks = session.query(RanksMembers).filter(RanksMembers.config_id == member.guild.id)
        mapped_members_ranks = map(lambda m: (m.experience, m.mugs_kvass, m.member_id), all_members_ranks)
        for i, member_data in enumerate(sorted(mapped_members_ranks, reverse=True)):
            if member_data[-1] == member.id:
                return i + 1
        return -1


# TODO: Удалять запись когда человек выходит
class ActivityRanksCog(Cog, name="Ранги Активности"):
    """
    Система Рангов.
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=ActivityRanksConfig, emoji_icon="💬")

        self.tmp_kvass = set()  # { (id_guild, member_a, member_b) }

    @commands.Cog.listener('on_ready')
    async def update_ranks_members(self):
        with db_session.create_session() as session:
            for member in self.bot.get_all_members():
                if not RanksMembers.get(session, member) and not member.bot:
                    rm = RanksMembers()
                    rm.member_id = member.id
                    rm.config_id = member.guild.id
                    session.add(rm)
            session.commit()

    @commands.group('ранг', aliases=['rank'])
    @commands.guild_only()
    async def _group_rank(self, ctx: Context, member: discord.Member = None):
        """Показывает ранг пользователя (или ваш если не указан)"""

        with db_session.create_session() as session:
            member = member or ctx.author
            rank_member: RanksMembers = RanksMembers.get(session, member)

            d = 2.3
            lvl = math.floor(math.pow(rank_member.experience, 1 / d))

            embed = discord.Embed(title=f"Ранг на сервере {ctx.guild}", colour=self.bot.colour_embeds)
            embed.add_field(name="Участник:", value=member.mention)
            embed.add_field(name="Уровень:", value=f"**{lvl}**")
            embed.add_field(name="Опыт:", value=f"**{rank_member.experience}** exp")
            embed.add_field(name="Кружек кваса:", value=f"**{rank_member.mugs_kvass}** \\🍺")
            embed.add_field(name="До повышения", value=f"**{math.ceil((lvl + 1) ** d - rank_member.experience)}** exp")
            embed.set_footer(text=f"Позиция: №{RanksMembers.get_position(session, member)}")
            embed.set_thumbnail(url=member.avatar_url)

        await ctx.reply(embed=embed)

    @commands.command('квас', aliases=['kvass'])
    async def _cmd_kvass(self, ctx: Context, *members: discord.Member):
        """Даёт кружку кваса другом участникам указанным через пробел"""

        assert ctx.author not in members, "Себе нельзя дарить кружку кваса! Дай другим а..."
        with db_session.create_session() as session:
            for member in members:
                if (ctx.guild.id, ctx.author.id, member.id) not in self.tmp_kvass:
                    self.tmp_kvass.add((ctx.guild.id, ctx.author.id, member.id))
                    member_rank: RanksMembers = RanksMembers.get(session, member)
                    member_rank.mugs_kvass += 1
            session.commit()

    @commands.Cog.listener('on_message')
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()

        if message.author.bot or message.guild is None:
            return

        with db_session.create_session() as session:
            config = self.get_config(session, message.guild.id)
            if not config:
                return
            if not config.check_active_until():
                return
            rank_member: RanksMembers = RanksMembers.get(session, message.author)
            if rank_member:
                rank_member.experience = rank_member.experience + 1
            session.commit()


def setup(bot: Bot):
    bot.add_cog(ActivityRanksCog(bot))
