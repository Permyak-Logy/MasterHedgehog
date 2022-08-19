import asyncio
from typing import List

import discord
import sqlalchemy
from discord.ext import commands
from discord_components import Interaction, Select, SelectOption

import db_session
from PLyBot import Bot, Cog, atimer, Context, BotEmbed
from db_session import BaseConfigMix, SqlAlchemyBase


# TODO: Роли бустеры

# TODO: Команда для снятия роли
# TODO: Сделать подробные ошибки при отсутствии класса
# TODO: Pymorphy

class BodyguardConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "bodyguard_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)

    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)


class BodyguardMember(SqlAlchemyBase):
    __tablename__ = "bodyguards_members"

    config_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('bodyguard_configs.guild_id'),
                                  primary_key=True, nullable=False)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'),
                                primary_key=True, nullable=False)

    enable_save_roles = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    enable_deny_roles = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    save_roles = sqlalchemy.Column(sqlalchemy.String, nullable=False, default="")
    deny_roles = sqlalchemy.Column(sqlalchemy.String, nullable=False, default="")

    delay_add_role = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)
    delay_deny_role = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)

    @staticmethod
    def query(session: db_session.Session, member: discord.Member):
        return session.query(BodyguardMember).filter(BodyguardMember.config_id == member.guild.id,
                                                     BodyguardMember.user_id == member.id).first()

    def get_save_roles(self, bot: Bot):
        roles = self.save_roles

        # noinspection PyTypeChecker
        guild: discord.Guild = bot.get_guild(self.config_id)
        return list(filter(bool, map(lambda x: guild.get_role(int(x)), filter(bool, roles.split(",")))))

    def set_save_roles(self, roles: List[discord.Role]):
        self.save_roles = ",".join(map(lambda x: str(x.id), roles))

    def get_deny_roles(self, bot: Bot):
        roles = self.deny_roles

        # noinspection PyTypeChecker
        guild: discord.Guild = bot.get_guild(self.config_id)
        return list(filter(bool, map(lambda x: guild.get_role(int(x)), filter(bool, roles.split(",")))))

    def set_deny_roles(self, roles: List[discord.Role]):
        self.deny_roles = ",".join(map(lambda x: str(x.id), roles))


class BodyguardCog(Cog, name='Телохранитель'):
    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=BodyguardConfig, emoji_icon='💎')

    @commands.Cog.listener('on_ready')
    async def _listener_update_members(self):
        with db_session.create_session() as session:
            for member in self.bot.get_all_members():
                member_bodyguard: BodyguardMember = BodyguardMember.query(session, member)
                if not member_bodyguard:
                    member_bodyguard = BodyguardMember()
                    member_bodyguard.config_id = member.guild.id
                    member_bodyguard.user_id = member.id
                    session.add(member_bodyguard)
                else:
                    await self.full_safe(member)
            session.commit()

    @commands.Cog.listener('on_member_join')
    async def _listener_auto_add_member_data(self, member: discord.Member):
        with db_session.create_session() as session:
            session.add(BodyguardMember(config_id=member.guild.id, user_id=member.id))
            session.commit()

    @commands.Cog.listener('on_member_remove')
    async def _listener_auto_remove_member_data(self, member: discord.Member):
        with db_session.create_session() as session:
            session: db_session.Session
            session.delete(BodyguardMember.query(session, member))  # TODO: больше нет session.remove
            session.commit()

    @commands.Cog.listener('on_member_update')
    async def _listener_save_member_roles(self, before: discord.Member, after: discord.Member):
        await self.bot.wait_until_ready()
        with db_session.create_session() as session:
            config = self.get_config(session, before.guild)
            if not config.check_active_until():
                return

            bodyguard_member: BodyguardMember = BodyguardMember.query(session, before)
            if not bodyguard_member:
                return

            if bodyguard_member.enable_save_roles and bodyguard_member.save_roles:
                removed = set(before.roles) - set(after.roles)
                to_add = list(filter(lambda x: x < before.guild.me.top_role,
                                     removed & set(bodyguard_member.get_save_roles(self.bot))))
                # noinspection PyTypeChecker
                asyncio.ensure_future(atimer(bodyguard_member.delay_add_role, after.add_roles(*to_add)))

            if bodyguard_member.enable_deny_roles and bodyguard_member.deny_roles:
                added = set(after.roles) - set(before.roles)
                to_remove = list(filter(lambda x: x < before.guild.me.top_role,
                                        added & set(bodyguard_member.get_deny_roles(self.bot))))
                # noinspection PyTypeChecker
                asyncio.ensure_future(atimer(bodyguard_member.delay_deny_role, after.remove_roles(*to_remove)))

    @commands.group("safer")
    # @commands.has_permissions(manage_roles=True)  # TODO: Включить потом
    @commands.bot_has_permissions(manage_roles=True)
    # @commands.is_owner()
    async def _group_safer(self, ctx: Context, member: discord.Member = None):
        """Вызывает настройщика Телохранителя для участника"""

        member: discord.Member = member or ctx.author
        guild: discord.Guild = member.guild

        with db_session.create_session() as session:
            bodyguard_member: BodyguardMember = BodyguardMember.query(session, member)
            save_roles = bodyguard_member.get_save_roles(self.bot)
            deny_roles = bodyguard_member.get_deny_roles(self.bot)

        custom_id_role_save = "_cmd_safer_role_save:"
        custom_id_role_deny = "_cmd_safer_role_deny:"

        # noinspection PyTypeChecker
        allow_roles_to_save: List[discord.Role] = list(sorted(filter(
            lambda x: x < guild.me.top_role and x != guild.default_role and not x.is_bot_managed(), set(member.roles)),
            reverse=True))
        # noinspection PyTypeChecker
        allow_roles_to_deny: List[discord.Role] = list(sorted(filter(
            lambda x: x < guild.me.top_role and x not in member.roles and not x.is_bot_managed(), guild.roles),
            reverse=True))

        embed = BotEmbed(
            ctx=ctx,
            title=f"Настройка Телохранителя для {member.display_name}",
            description="Выберите какие роли нужно сохранить, а какие исключать.\n"
                        "||Первый пункт для сохранений, второй для исключений||",
            colour=self.bot.colour).set_author(name=ctx.guild.name,
                                               icon_url=ctx.guild.icon_url).set_thumbnail(url=member.avatar_url)

        custom_ids_role_save = []
        custom_ids_role_deny = []

        components = []
        r = []
        data = [
            (
                allow_roles_to_save,
                save_roles,
                "Сохраняемые роли",
                "✅",
                custom_id_role_save,
                custom_ids_role_save
            ),
            (
                allow_roles_to_deny,
                deny_roles,
                "Исключаемые роли",
                "⛔",
                custom_id_role_deny,
                custom_ids_role_deny
            )
        ]
        for allow_roles, roles, placeholder, emoji, custom_id, custom_ids in data:
            a = []
            r.append(a)
            if allow_roles:
                for i in range(0, len(allow_roles), 20):
                    part_allow_roles = allow_roles[i:i + 20]
                    a.append(list(filter(lambda x: x in roles, part_allow_roles)))
                    custom_id = custom_id + str(i) + ":" + str(ctx.message.id)
                    components.append(Select(
                        placeholder=placeholder,
                        options=[SelectOption(
                            label=role.name,
                            value=role.id,
                            emoji=emoji,
                            description=f"id: {role.id}",
                            default=role in roles)
                            for role in part_allow_roles],
                        min_values=0, max_values=len(part_allow_roles),
                        custom_id=custom_id))
                    custom_ids.append(custom_id)
        if components:
            msg: discord.Message = await ctx.reply(embed=embed, components=components)
        else:
            await ctx.reply(embed=BotEmbed(ctx=ctx, description="Нет доступных ролей для телохранителя"),
                            delete_after=10)
            return
        try:
            interaction: Interaction = await self.bot.wait_for(
                "select_option",
                check=lambda inter:
                inter.custom_id in custom_ids_role_save + custom_ids_role_deny and inter.user == ctx.author,
                timeout=5 * 60
            )
        except asyncio.TimeoutError:
            pass
        else:
            changed_roles: List[discord.Role] = list(map(guild.get_role, map(int, interaction.values)))
            with db_session.create_session() as session:
                bodyguard_member: BodyguardMember = BodyguardMember.query(session, member)
                if interaction.custom_id in custom_ids_role_save:
                    for custom_id, roles in zip(custom_ids_role_save, r[0]):
                        if custom_id != interaction.custom_id:
                            changed_roles += roles
                    bodyguard_member.set_save_roles(changed_roles)
                else:
                    for custom_id, roles in zip(custom_ids_role_deny, r[1]):
                        if custom_id != interaction.custom_id:
                            changed_roles += roles
                    bodyguard_member.set_deny_roles(changed_roles)
                session.commit()

            for_ = "сохранения" if interaction.custom_id in custom_ids_role_save else "исключения"
            embed = BotEmbed(ctx=ctx,
                             title="Успешно!",
                             description=(
                                 (f'Установлены новые роли для {for_}:\n' + "\n".join(
                                     f"\\{role.name}" for role in changed_roles)
                                  if len(changed_roles) <= 10 else f"Установлены {len(changed_roles)} ролей для {for_}")
                                 if changed_roles else "Убраны все роли для " + for_)
                             )

            await interaction.send(embed=embed, ephemeral=True, delete_after=60)
        finally:
            try:
                await msg.delete()
            except discord.NotFound:
                pass

    async def full_safe(self, member: discord.Member):
        with db_session.create_session() as session:
            config = self.get_config(session, member.guild)
            if not config.check_active_until():
                return
            bodyguard_member: BodyguardMember = BodyguardMember.query(session, member)
            save_roles = bodyguard_member.get_save_roles(self.bot)
            deny_roles = bodyguard_member.get_deny_roles(self.bot)

            to_add = list(filter(lambda x: x < member.guild.me.top_role, set(save_roles) - set(member.roles)))
            to_remove = list(filter(lambda x: x < member.guild.me.top_role, set(deny_roles) & set(member.roles)))

            if save_roles and to_add:
                await member.add_roles(*to_add)
            if deny_roles and to_remove:
                await member.remove_roles(*to_remove)


def setup(bot: Bot):
    bot.add_cog(BodyguardCog(bot))
