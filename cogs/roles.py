from typing import Union, Optional

import discord
import sqlalchemy
from discord.errors import NotFound, Forbidden
from discord.ext import commands

import db_session
from PLyBot import Bot
from PLyBot import Cog, Context
from PLyBot.const import EMOJI_NUMBERS
from db_session import SqlAlchemyBase, BaseConfigMix, NONE, MIN_DATETIME
from db_session.base import Member


class RolesConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "roles_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)

    auto_roles = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    return_old_roles = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)

    roles = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')

    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=MIN_DATETIME)

    def __str__(self):
        return f'{self.__class__.__name__}(id={self.guild_id} roles={self.active_until})'

    def __repr__(self):
        return self.__class__.__name__

    def get_roles(self, bot: Bot) -> list:
        guild = self.get_guild(bot)
        if self.roles != NONE and isinstance(guild, discord.Guild):
            roles = self.roles
            roles = list(filter(bool, map(guild.get_role, list(map(int, roles.split(","))))))
            return roles
        return []

    def set_roles(self, *roles: discord.Role):
        self.roles = ",".join(filter(bool, [str(role.id) for role in roles])) or None

    def get_autoroles(self, bot: Bot):
        guild = self.get_guild(bot)
        if self.auto_roles != NONE and isinstance(guild, discord.Guild):
            roles = self.auto_roles
            roles = list(filter(bool, map(guild.get_role, list(map(int, roles.split(","))))))
            return roles
        return []

    def set_autoroles(self, *roles: discord.Role):
        self.auto_roles = ",".join(filter(bool, [str(role.id) for role in roles])) or None


class RoleForReaction(SqlAlchemyBase):
    __tablename__ = "role_for_reaction"
    config_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('roles_configs.guild_id'),
                                  primary_key=True)
    channel_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    message_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, primary_key=True)
    roles = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    def get_roles(self, bot: Bot) -> list:
        guild = bot.get_guild(self.config_id)
        if self.roles != NONE and isinstance(guild, discord.Guild):
            roles = self.roles
            roles = list(map(guild.get_role, list(map(int, roles.split(",")))))
            return roles
        return []

    def set_roles(self, *roles: discord.Role):
        self.roles = ",".join(filter(bool, [str(role.id) for role in roles])) or None


class RolesMembers:  # (SqlAlchemyBase):
    __tablename__ = "roles_members"
    config_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('role'))

    member_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('role'))

    roles_id = sqlalchemy.Column(sqlalchemy.String)


class RolesCog(Cog, name='Роли'):
    """
    Модуль для выдачи ролей по реакции или команде. Для их работы необходимо предварительно
    установить роли которые возможно выдать с помощью `!!=роли`

    ||По тех. причинам по реакции роли пока не выдаются||
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=RolesConfig)

    def get_config(self, session: db_session.Session, guild: Union[discord.Guild, int]) -> Optional[RolesConfig]:
        return super().get_config(session, guild)

    @commands.Cog.listener('on_ready')
    async def clear_unavailable_rfr(self):
        session = db_session.create_session()
        all_rfr = session.query(RoleForReaction).all()
        for rfr in all_rfr:
            channel = self.bot.get_channel(rfr.channel_id)
            try:
                await channel.fetch_message(rfr.message_id)
            except (AttributeError, NotFound):
                session.delete(rfr)
        session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        session = db_session.create_session()
        all_rfr = session.query(RoleForReaction).filter(RoleForReaction.message_id.in_(payload.message_ids)).all()
        for rfr in all_rfr:
            session.delete(rfr)
        session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        session = db_session.create_session()
        rfr = session.query(RoleForReaction).filter(RoleForReaction.message_id == payload.message_id).first()
        if rfr:
            session.delete(rfr)
        session.commit()
        session.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        session = db_session.create_session()
        config = self.get_config(session, guild)
        if not config:
            session.close()
            return
        for i, reaction in EMOJI_NUMBERS.items():
            if payload.emoji.name == reaction:
                rfr: RoleForReaction = session.query(RoleForReaction).filter(
                    RoleForReaction.message_id == payload.message_id).first()
                if rfr:
                    roles = rfr.get_roles(self.bot)
                    try:
                        member = guild.get_member(payload.user_id)
                        await member.add_roles(roles[i - 1])
                    except (IndexError, Forbidden, AttributeError):
                        pass
                break

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        session = db_session.create_session()
        config = self.get_config(session, guild)
        if not config:
            session.close()
            return
        for i, reaction in EMOJI_NUMBERS.items():
            if payload.emoji.name == reaction:
                rfr: RoleForReaction = session.query(RoleForReaction).filter(
                    RoleForReaction.message_id == payload.message_id).first()
                if rfr:
                    roles = rfr.get_roles(self.bot)
                    try:
                        member = guild.get_member(payload.user_id)
                        await member.remove_roles(roles[i - 1])
                    except (IndexError, Forbidden, AttributeError):
                        pass
                break

    @commands.command(name='автороли', aliases=['autoroles'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def auto_old_roles(self, ctx: Context):
        """
        Переключатель автоматического востановления ролей на сервере при перезаходе
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            config.return_old_roles = not config.return_old_roles
            if not config.return_old_roles:
                # Очищаем весь кэш людей
                for member in session.query(Member).filter(Member.guild_id == ctx.guild.id,
                                                           Member.joined.is_(False)).all():
                    session.delete(member)
            session.commit()
            await ctx.send(embed=discord.Embed(title="Успешно", colour=self.bot.colour_embeds,
                                               description="Статус автоматической выдачи").add_field(
                name="Статус автовыдачи",
                value="Вкл" if config.return_old_roles else "Выкл"))

    @commands.command(name='рольпореакции', aliases=['role_for_reaction', 'rfr', 'рпр'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, manage_messages=True)
    async def role_for_reaction(self, ctx: commands.Context, title: str, description: str, *roles: discord.Role):
        """
        Создаёт сообщение через которое можно получать роли по реакции
        """
        assert 0 < len(roles) <= 10, "Кол-во ролей дожно быть от 1 до 10"
        assert all(map(lambda r: ctx.author.top_role > r, roles)) or ctx.guild.owner == ctx.author, \
            "Указанные роли должны быть ниже вашей"
        me = ctx.guild.get_member(self.bot.user.id)
        assert all(map(lambda r: me.top_role > r and not r.managed, roles)), "Я не могу выдать одну из указанных ролей"
        description += "\nНажмите на реакцию для получения\n\n" + "\n".join(
            f"{EMOJI_NUMBERS[i + 1]} - {role.mention}" for i, role in enumerate(roles)
        )
        embed = discord.Embed(
            title=title,
            description=description,
            colour=self.bot.colour_embeds
        )
        message = await ctx.send(embed=embed)
        session = db_session.create_session()
        config = self.get_config(session, ctx.guild)
        rfr = RoleForReaction()
        rfr.config_id = config.guild_id
        rfr.channel_id = message.channel.id
        rfr.message_id = message.id
        rfr.set_roles(*roles)
        for i, role in enumerate(roles):
            await message.add_reaction(EMOJI_NUMBERS[i + 1])
        session.add(rfr)
        session.commit()
        session.close()
        await ctx.message.delete()

    @commands.command(name='роли', aliases=['roles'])
    @commands.guild_only()
    @commands.cooldown(1, 5)
    @commands.bot_has_permissions(manage_roles=True)
    async def roles(self, ctx: commands.Context):
        """
        Показывает доступные роли для выдачи
        """
        session = db_session.create_session()
        config = self.get_config(session, ctx.guild)
        roles = config.get_roles(ctx.bot)
        if not roles:
            embed = discord.Embed(title="Нет доступных ролей",
                                  description=f'Чтобы установить список ролей воспользуйтесь '
                                              f'командой `{self.bot.command_prefix}'
                                              f'{self.bot.get_command("set_roles")}`',
                                  colour=self.bot.colour_embeds)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Список выдаваемых ролей",
                                  description="\n".join(role.mention for role in roles),
                                  colour=self.bot.colour_embeds)
            await ctx.send(embed=embed)

    @commands.command(name='=роли', aliases=['=roles', 'setroles', 'set_roles'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def set_roles(self, ctx: commands.Context, *roles: discord.Role):
        """
        Устанавливает выдаваемые роли
        """
        session = db_session.create_session()
        config = self.get_config(session, ctx.guild)
        config.set_roles(*roles)
        session.commit()
        session.close()

        embed = discord.Embed(
            title="Список ролей обновлён!",
            description=f"Для получения списка доступных ролей введите "
                        f"`{self.bot.command_prefix}{self.bot.get_command('roles')}`",
            colour=self.bot.colour_embeds
        )
        await ctx.send(embed=embed)

    @commands.command(name='+роли', aliases=['+roles', 'addroles', 'add_roles'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def add_roles(self, ctx: commands.Context, *roles: discord.Role):
        """
        Добавляет указанные роли если это возможно
        """
        session = db_session.create_session()
        config = self.get_config(session, ctx.guild)
        acc_roles = config.get_roles(ctx.bot)
        session.close()

        for role in roles:
            assert role not in ctx.author.roles, \
                f"У вас уже есть роль '{role}'"
            assert role in acc_roles, f"Роль '{role}' не может быть выдана"
            assert role < ctx.guild.get_member(self.bot.user.id).top_role, \
                f"Я не могу выдать роль '{role}', т.к. она выше чем я"
        await ctx.author.add_roles(*roles)
        await ctx.send(embed=discord.Embed(title="Успешно", description=f"Вам успешно выдано {len(set(roles))} ролей",
                                           colour=self.bot.colour_embeds))

    @commands.command(name='-роли', aliases=['-roles', 'rmroles', 'rm_roles'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def remove_role(self, ctx: commands.Context, *roles: discord.Role):
        """
        Убирает указаные роли если это возможно
        """
        session = db_session.create_session()
        config = self.get_config(session, ctx.guild)
        acc_roles = config.get_roles(ctx.bot)
        session.close()

        for role in roles:
            assert role in ctx.author.roles, \
                f"Роли {role} нет у вас"
            assert role in acc_roles, f"Роль '{role}' не может быть снята"
            assert role < ctx.guild.get_member(self.bot.user.id).top_role, \
                f"Я не могу снять роль {role}, т.к. она выше чем я"
        await ctx.author.remove_roles(*roles)
        await ctx.send(embed=discord.Embed(title="Успешно",
                                           description=f"У вас успешно убрано {len(set(roles))} ролей",
                                           colour=self.bot.colour_embeds))

    @commands.command(name='+роли_всем', aliases=['+roles_all'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def add_roles_for_everyone(self, ctx: commands.Context, *roles: discord.Role):
        """
        Выдаёт указанные роли для каждого участника сервера
        """
        for role in roles:
            assert role < ctx.guild.get_member(self.bot.user.id).top_role, \
                f"Я не могу дать роль {role}, т.к. она выше чем я"
        async with ctx.typing():
            for member in ctx.guild.members:
                member: discord.Member
                await member.add_roles(*roles)
        await ctx.send(embed=discord.Embed(title="Успешно",
                                           description=f"Всем участникам были выданы роли",
                                           colour=self.bot.colour_embeds))

    @commands.command(name='-роли_всем', aliases=['-roles_all'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def remove_roles_for_everyone(self, ctx: commands.Context, *roles: discord.Role):
        """
        Убирает указанные роли у каждого участника сервера
        """
        for role in roles:
            assert role < ctx.guild.get_member(self.bot.user.id).top_role, \
                f"Я не могу снять роль {role}, т.к. она выше чем я"
        async with ctx.typing():
            for member in ctx.guild.members:
                member: discord.Member
                await member.remove_roles(*roles)
        await ctx.send(embed=discord.Embed(title="Успешно",
                                           description=f"У всех участников были сняты роли",
                                           colour=self.bot.colour_embeds))

    @commands.command(name='-роли_всем_искл', aliases=['-roles_all_exc'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def remove_roles_for_everyone(self, ctx: commands.Context, *roles: discord.Role):
        """
        Убирает указанные роли у каждого участника сервера, если он имеет только эти роли и никакие другие
        """
        for role in roles:
            assert role < ctx.guild.get_member(self.bot.user.id).top_role, \
                f"Я не могу снять роль {role}, т.к. она выше чем я"
        async with ctx.typing():
            for member in ctx.guild.members:
                member: discord.Member

                get_id = lambda x: x.id
                result = set(map(get_id, filter(lambda x: x.name != '@everyone', member.roles))) - set(
                    map(get_id, roles))
                if not result:
                    await member.remove_roles(*roles)
        await ctx.send(embed=discord.Embed(title="Успешно",
                                           description=f"У всех участников были сняты роли",
                                           colour=self.bot.colour_embeds))

    @commands.group(name='auto_roles')
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def auto_roles(self):
        pass

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def set_auto_roles(self):
        pass


def setup(bot: Bot):
    bot.add_cog(RolesCog(bot))
