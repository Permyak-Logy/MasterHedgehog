from typing import Union, Optional

import discord
import sqlalchemy
from discord.errors import NotFound
from discord.ext import commands

import db_session
from PLyBot import Bot, Cog, BotEmbed
from db_session import SqlAlchemyBase, BaseConfigMix


class TicketsConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "tickets_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)


class TicketsSection(SqlAlchemyBase):
    __tablename__ = "tickets_sections"
    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True, primary_key=True)
    config_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('tickets_configs.guild_id'))
    name = sqlalchemy.Column(sqlalchemy.String)
    ctrl_msg = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, unique=True)
    category = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, unique=True)


class TicketSession(SqlAlchemyBase):
    __tablename__ = "ticket_sessions"
    id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True, primary_key=True)
    ticket_section = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('tickets_sections.id'))
    ctrl_msg = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, unique=True)
    channel = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, unique=True)
    author = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)


class TicketsCog(Cog, name='Билеты'):
    """
    Модуль для реализации запросов в техподдержку сервера.
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=TicketsConfig, emoji_icon='📨')
        self.bot.add_models(TicketsSection, TicketSession)

    def get_config(self, session: db_session.Session, guild: Union[discord.Guild, int]) -> Optional[TicketsConfig]:
        return super().get_config(session, guild)

    @commands.command(name='создать_категорию_билетов', aliases=['create_section_tickets'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.has_permissions(manage_roles=True, manage_channels=True)
    async def create_section(self, ctx: commands.Context, name: str):
        """
        Создаёт новую категорию для билетов.
        """
        with db_session.create_session() as session:
            config: TicketsConfig = self.get_config(session, ctx.guild)

            # Псевдонимы
            guild: discord.Guild = ctx.guild
            author: discord.Member = ctx.author

            # Новая запись
            ts = TicketsSection()

            ts.config_id = config.guild_id

            ts.name = name

            # Создание категории
            category: discord.CategoryChannel = await guild.create_category(f'✉️ - "{name}"')
            role_everyone: discord.Role = discord.utils.find(lambda r: r.name == '@everyone', guild.roles)
            await category.set_permissions(role_everyone, read_messages=False, send_messages=False, add_reactions=False)
            await category.set_permissions(author, read_messages=True, send_messages=True, add_reactions=True)
            ts.category = category.id

            # Создание контролирующей реакции
            message = await ctx.send(embed=BotEmbed(ctx=ctx,
                                                    title=f"**{name}**",
                                                    description='Для создания билета нажмите 📩',
                                                    colour=self.bot.colour
                                                    ))
            await message.add_reaction('📩')
            ts.ctrl_msg = message.id

            # Удаление команды
            await ctx.message.delete()

            session.add(ts)
            session.commit()

    @commands.Cog.listener('on_raw_message_delete')
    async def on_delete_section(self, payload: discord.RawMessageDeleteEvent):
        with db_session.create_session() as session:
            session: db_session.Session

            config = self.get_config(session, payload.guild_id)
            if not config:
                return
            # noinspection PyUnresolvedReferences
            section: TicketsSection = session.query(TicketsSection).filter(TicketsSection.config_id == config.guild_id,
                                                                           TicketsSection.ctrl_msg == payload.message_id
                                                                           ).first()
            if section:
                guild: discord.Guild = self.bot.get_guild(payload.guild_id)
                category: discord.CategoryChannel = discord.utils.find(lambda cat: cat.id == section.category,
                                                                       guild.categories)
                if category:
                    for cnl in category.channels:
                        cnl: Union[discord.TextChannel, discord.VoiceChannel]
                        await cnl.delete()
                    await category.delete()

                for ses in session.query(TicketSession).filter(TicketSession.ticket_section == section.id).all():
                    session.delete(ses)
                session.delete(section)
                session.commit()

    @commands.Cog.listener('on_raw_reaction_add')
    async def on_create_session(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.name != '📩' or payload.user_id == self.bot.user.id:
            return
        with db_session.create_session() as session:
            session: db_session.Session

            guild: discord.Guild = self.bot.get_guild(payload.guild_id)
            author: discord.Member = payload.member

            config: TicketsConfig = self.get_config(session, guild=guild)
            section: TicketsSection = session.query(TicketsSection).filter(
                TicketsSection.config_id == config.guild_id, TicketsSection.ctrl_msg == payload.message_id
            ).first()

            if section:

                category: discord.CategoryChannel = discord.utils.find(
                    lambda cat: cat.id == section.category, guild.categories)

                ts = session.query(TicketSession).filter(TicketSession.ticket_section == section.id,
                                                         TicketSession.author == author.id).first()
                if not category:
                    await (await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)).delete()
                elif not ts:

                    ts = TicketSession()

                    ts.ticket_section = section.id

                    channel: discord.TextChannel = await category.create_text_channel(f"ts-{ts.id}")
                    await channel.set_permissions(target=author, read_messages=True, send_messages=True,
                                                  add_reactions=True)
                    ts.channel = channel.id

                    message = await channel.send(f"{author.mention} Здравствуй!",
                                                 embed=BotEmbed(description="Какова причина твоего визита?\n"
                                                                            "Чтобы закрыть билет - 🔒",
                                                                colour=self.bot.colour))
                    await message.add_reaction('🔒')

                    ts.author = author.id

                    ts.ctrl_msg = message.id
                    session.add(ts)
                    session.commit()

                    number = session.query(TicketSession).filter(TicketSession.ticket_section == section.id,
                                                                 TicketSession.author == author.id).first().id
                    await channel.edit(name=f'ts-{number}')

    @commands.Cog.listener('on_raw_reaction_add')
    async def on_close_session_by_reaction(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.name != '🔒' or payload.user_id == self.bot.user.id:
            return
        await self.close_session(channel=payload.channel_id)

    @commands.Cog.listener('on_raw_message_delete')
    async def on_close_session_by_del_msg(self, payload: discord.RawMessageDeleteEvent):
        await self.close_session(channel=payload.channel_id)

    @commands.Cog.listener('on_guild_channel_delete')
    async def on_close_session_by_del_cnl(self, channel: Union[discord.TextChannel, discord.VoiceChannel]):
        await self.close_session(channel=channel)

    async def close_session(self, *, channel: Union[discord.TextChannel, discord.VoiceChannel, int]):
        with db_session.create_session() as session:
            session: db_session.Session
            if not isinstance(channel, discord.TextChannel):
                channel = self.bot.get_channel(channel)
                if not isinstance(channel, discord.TextChannel):
                    return
            config: TicketsConfig = self.get_config(session, guild=channel.guild)
            section: TicketsSection = session.query(TicketsSection).filter(
                TicketsSection.category == channel.category_id, TicketsSection.config_id == config.guild_id).first()
            if section:
                ticket_session: TicketSession = session.query(TicketSession).filter(
                    TicketSession.ticket_section == section.id, TicketSession.channel == channel.id
                ).first()

                if ticket_session:
                    session.delete(ticket_session)
                    session.commit()
                    try:
                        await channel.delete()
                    except NotFound:
                        pass


async def setup(bot: Bot):
    await bot.add_cog(TicketsCog(bot))
