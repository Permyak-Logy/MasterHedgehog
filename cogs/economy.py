import datetime
import json
import math
import random
import re
from typing import Optional, Union

import discord
import sqlalchemy
from discord.ext import commands
from discord.ext.commands import BucketType

import db_session
from PLyBot import Bot, Cog, join_string, HRF, Context, BotEmbed
from PLyBot.const import EMOJI_NUMBERS
from db_session import BaseConfigMix, SqlAlchemyBase, bigint, Session


# TODO: Роли бустеры

# TODO: Команда для снятия роли
# TODO: Сделать подробные ошибки при отсутствии класса
# TODO: Pymorphy

class EconomyConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "economy_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    shop = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{"shop": []}')
    currency_icon = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='💎')
    currency_name = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='алм.')

    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)

    def get_shop(self, ctx: commands.Context):
        shop = json.loads(self.shop)
        for item in shop['shop']:
            item["role"] = ctx.guild.get_role(item['role'])
        return {"shop": list(filter(lambda x: bool(x["role"]), shop['shop']))}

    def set_shop(self, data: dict):
        for item in data['shop']:
            item["role"] = item["role"].id
        self.shop = json.dumps(data)


class LuckBox(SqlAlchemyBase):
    __tablename__ = "luck_boxes_economy"
    config_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('economy_configs.guild_id'),
                                  primary_key=True)
    ctrl_msg = sqlalchemy.Column(sqlalchemy.Integer, unique=True, primary_key=True)

    data_boxes = sqlalchemy.Column(sqlalchemy.String)

    def set_data_boxes(self, data: dict):
        self.data_boxes = json.dumps(data, ensure_ascii=False)

    def get_data_boxes(self):
        return json.loads(self.data_boxes)


class FeatureMember(SqlAlchemyBase):
    __tablename__ = "features_economy"

    member_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('members.id'), primary_key=True)
    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('members.id'), primary_key=True)

    crime_success = sqlalchemy.Column(sqlalchemy.BIGINT, default=0, nullable=False)
    crime_fail = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)

    steal_success = sqlalchemy.Column(sqlalchemy.BIGINT, default=0, nullable=False)
    steal_fail = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)

    casino_success = sqlalchemy.Column(sqlalchemy.BigInteger, default=0, nullable=False)

    # member = orm.relationship("Member", back_populates="feature")


class Balance(SqlAlchemyBase):
    __tablename__ = "balances_economy"

    member_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('members.id'), primary_key=True)
    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('members.guild_id'), primary_key=True)

    cash = sqlalchemy.Column(sqlalchemy.BigInteger, default=0, nullable=False)
    dep = sqlalchemy.Column(sqlalchemy.BigInteger, default=0, nullable=False)

    # member = orm.relationship("Member", back_populates="balance")

    @staticmethod
    def get(session: Session, member: discord.Member):
        return session.query(Balance).filter(Balance.member_id == member.id,
                                             Balance.guild_id == member.guild.id).first()

    def get_total(self) -> int:
        return self.cash + self.dep

    def set_cash(self, cash: int):
        self.cash = bigint(cash)

    def set_dep(self, dep: int):
        self.dep = bigint(dep)

    def add_cash(self, cash: int):
        self.set_cash(self.cash + cash)

    def add_dep(self, dep: int):
        self.set_dep(self.dep + dep)


class PromoCode(SqlAlchemyBase):
    __tablename__ = "promo_codes"
    config_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("economy_configs.guild_id"),
                                  primary_key=True)
    code = sqlalchemy.Column(sqlalchemy.String, unique=True, primary_key=True)
    moneys = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False)
    activated = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    by = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))


# Ошибка при подключении к новому серваку
class EconomyCog(Cog, name='Экономика'):
    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=EconomyConfig, emoji_icon='💎')
        self.bot.add_models(LuckBox, FeatureMember, PromoCode, Balance)

    def get_config(self, session: db_session.Session, guild: Union[discord.Guild, int]) -> Optional[EconomyConfig]:
        return super().get_config(session, guild)

    @staticmethod
    def random(chance: float) -> bool:
        assert 0 <= chance <= 1, "Шанс в пределах [0; 1]"
        return (chance or -1) >= random.random()

    @commands.Cog.listener('on_ready')
    async def _listener_update_members(self):
        with db_session.create_session() as session:
            for member in self.bot.get_all_members():
                DBEconomyTools.update_features_member(session, member)
                DBEconomyTools.update_balance_member(session, member)
            session.commit()

    @commands.Cog.listener('on_guild_join')
    async def _listener_first_update_guild_on_join(self, guild: discord.Guild):
        with db_session.create_session() as session:
            for member in guild.members:
                DBEconomyTools.update_features_member(session, member)
            session.commit()

    # =======================================================================================================
    async def do_work(self, ctx: commands.Context, data: dict, chance=1., title="Работа окончена"):
        with db_session.create_session() as session:
            config: EconomyConfig = self.get_config(session, guild=ctx.guild)
            phrase, money, color = data[self.random(chance)]

            embed = BotEmbed(ctx=ctx,
                             title=title,
                             description=phrase + f" {'+' if money > 0 else ''}{money} {config.currency_name}",
                             colour=color
                             )

            member = DBEconomyTools.get_balance_member(session, ctx.author)
            member.add_cash(money)
            session.commit()
            await ctx.send(embed=embed)

    @commands.group('work', aliases=['работа'])
    @commands.guild_only()
    async def _group_work(self, ctx: Context):
        """Команда для работы"""
        await ctx.just_send_help()

    @_group_work.command('off')
    @commands.guild_only()
    @commands.cooldown(1, 1 * 60 * 60, type=commands.BucketType.user)
    async def _cmd_work_official(self, ctx: Context):
        """
        -Простая работа без всяких рисков, зарабатываете и не бойтесь за свои деньги.
        -Минимальный заработок: 100 ; Максимальный  заработок 2000 ; Отдых от работы 6 часов
        """
        d = {
            True: (random.choice([
                "Гуляя по парку, ты натыкаешься на кошелёк",

                "Подстригая газон, поливая кустики, ты заработал",

                "Помыв машину, ты получил",

                "Сегодня ты вышел на ночную смену в клубе, она прошла удачно",

                "Сегодня твои навыки впервые в жизни пригодились",

                "Ты сегодня славно поработал на",

                "Твоя зарплата",

                "Ты получаешь",

                "Поработав барменом, ты получил неплохой опыт"
            ]), random.randint(100, 2000), discord.colour.Color.from_rgb(0, 255, 0))
        }
        await self.do_work(ctx, d)

    @_group_work.command('slut')
    @commands.guild_only()
    @commands.cooldown(1, 1 * 60 * 60, type=commands.BucketType.user)
    async def _cmd_work_slut(self, ctx: Context):
        """
        -Работа, отчасти связана с криминалом. Вы - ночная бабочка, работаете, чтобы удовлетворять
        людей и получать за это деньги. Учтите, что у этой работы есть свои риски;

        Риск: 55%, вы рискуете потерять часть денег.
        -Минимальный риск: -300 ; Максимальный: -600
        -Минимальный заработок: 1000 ; Максимальный 3000 ; Отдых от работы 12 часов
        """
        d = {
            True: (random.choice([
                "Сегодня нашелся новый папик, тебе удалось развести его на деньги",

                "В жизни нужны знакомые, сегодня тебе удалось завести несколько полезных людей",

                "Ты получаешь",

                "Ты стащил зарплату у мороженщика "
            ]), random.randint(4000, 10000), discord.colour.Color.from_rgb(0, 255, 0)),

            False: (random.choice([
                "Сегодня тебе пришлось убегать от охраны местного клуба, по дороге твой телефон упал в воду, "
                "придется с ним расстаться",

                "Во время ночной работы начался пожар в здании, "
                "к сожалению, папик оставил тебя без наличных",

                "Что то пошло не так..."
            ]), -random.randint(500, 1000), discord.colour.Color.from_rgb(255, 0, 0))
        }
        await self.do_work(ctx, d, chance=0.45, title="Вылазка окончена!")

    @_group_work.command('crime')
    @commands.guild_only()
    @commands.cooldown(1, 1 * 60 * 60, type=commands.BucketType.user)
    async def _cmd_work_crime(self, ctx: Context):
        """
        -Работа полностью связана с криминалом, вы погружаетесь в азартный и рискованный мир,
        где очень большой шанс потерять все деньги, но не менее плохой шанс сорвать куш.
        На тёмные дела выходят только смелые люди, может быть, ты один из них.
        Риск: 80%, вы рискуете потерять часть денег.
        Минимальный риск: -500 ; Максимальный -1000
        -Минимальный заработок: 4000 ; Максимальный 10000 ; Отдых от работы 1 день
        """

        d = {
            True: (random.choice([
                "Сегодня состоялась стрелка между Русской Мафией и Мексиканской Мафией\n"
                "Из за недостатка людей, Мексиканская Мафия решила нанять тебя",

                "Сегодня состоялся выезд на ВЗХ, из за навала работы, тебе предложили подменить Босса Украинской Мафии",

                "Ограбление успешно! Твоя доля",

                "Хорошая сегодня была вылазка! Держи",

                "Ты получаешь",

                "Ты стащил зарплату у мороженщика и выручил"
            ]), random.randint(4000, 10000), discord.colour.Color.from_rgb(0, 255, 0)),

            False: (random.choice([
                "После очередного грязного дела, скрыв пистолет за поясом, вас встретила Американская Мафия, старые"
                "знакомые, по пути вы увидели, что вторая машина, в которой сидел ваш друг поехала в другую сторону, на"
                "что вам ответили\n"
                "Босс Мафии: \"Прости, Джо в сделку не входил\"\n"
                "На поиски вы потратили немалую сумму денег, но все оказалось зря",

                "После очередной развозки контрабанды, вас повязала полиция\n"
                "К счастью, вам попался подкупной коп и вам удалось договориться",

                "До вас уже кто то ограбил!",

                "Твой товарищ был ранен на перестрелке!",

                "Вас накрыли! Ты единственный кто сбежал!"

            ]), -random.randint(500, 1000), discord.colour.Color.from_rgb(255, 0, 0))
        }

        await self.do_work(ctx, d, chance=0.2, title="Вылазка окончена!")

    @_group_work.command('business')
    @commands.guild_only()
    @commands.cooldown(1, 12 * 60 * 60, type=BucketType.user)
    async def _cmd_work_business(self, ctx: Context):
        """
        -Работа полностью связана с Бизнесом, Тебе придется покупать акции, придумывать новое,
        терять деньги, входить в банкротство. Тебе придется столкнутся с
        проблемами каждых бизнесменов, терять деньги и зарабатывать миллионы.
        Риск: 80%, вы рискуете потерять часть денег.
        Минимальный риск: -10к ; Максимальный -1 млн
        -Минимальный заработок: 10к ; Максимальный 1 млрд ; Отдых от работы 12 ч
        """

        d = {
            False: (random.choice([
                "Ты решил купить акции Tesla, но обвал рынка привел вас к банкротству и вы потеряли",

                "Ты создал умные ведра для мусора, но ведра начали ломается от попадания в них воды",

                "Ты решил создать Кафе, но из - за рабочих оно было закрыто",

                "Ты начал скупать продукты в магазине чтобы их продать, но они пропали"
            ]), -int(10000 + ((1000000 - 10000) * ((random.random() / 100) ** 1.8))),
                    discord.colour.Color.from_rgb(255, 0, 0)),

            True: (random.choice([
                "Ты придумал носки с GPS и идея Выстрелила! Тысячи мужиков их купило, ты получаешь",

                "Ты начал мыслить масштабно, создал ларек и начал торговать. "
                "Акции росли, Деньги пошли верх, ты начал получать больше, появилось больше филиалов"
                " и ты стал самым богатым человеком в твоём роду за всю историю!",

                "Ты купил самолет и продал его дороже потом еще, потом еще больше, и у тебя авиакомпания",

                "Вы со своими друзьями решили стать брокерами, торговали акциями, ваши кошельки росли,"
                " в итоге вы на-продали акций и заработали на этом"
            ]), int(10000 + ((1000000000 - 10000) * ((random.random() / 100) ** 1.8))),
                   discord.colour.Color.from_rgb(0, 255, 0))
        }

        await self.do_work(ctx, d, chance=0.2, title="Создание бизнеса окончено!")

    @commands.command('steal')
    @commands.guild_only()
    async def _cmd_steal(self, ctx: Context, member: discord.Member = None):
        """
        Попытаться ограбить кошелёк у другого участника.
        Если провал то вы заплатите компенсацию (0-100% Денег оппонента)
        Шанс кражи 10%
        """
        assert ctx.author != member, "Ты не можешь себя обкрадывать"
        with db_session.create_session() as session:
            me_data = DBEconomyTools.get_balance_member(session, ctx.author)
            op_data = DBEconomyTools.get_balance_member(session, member)
            config = self.get_config(session, ctx.guild)

            assert op_data.cash > 0, f"У {member.mention} нет денег в кошельке. Нечего красть!"

            done, money = self.random(0.1), round(random.random() * op_data.cash)
            if done:
                embed_data = {
                    "title": random.choice(["Уря, Удача!", "Хорошо сработано!", "Молодец", "Успех"]),
                    "description": random.choice([f"Вы получили {HRF.number(money)} {config.currency_name}"]),
                    "colour": discord.colour.Color.from_rgb(0, 255, 0)
                }
                me_data.add_cash(money)
                op_data.add_cash(-money)
            else:
                embed_data = {
                    "title": random.choice(["Неудача", "Облом", "Идём на дно", "Провал"]),
                    "description": random.choice([f"Вы заплатили {HRF.number(money)} {config.currency_name}"]),
                    "colour": discord.colour.Color.from_rgb(255, 0, 0)
                }
                me_data.add_dep(-money)
                op_data.add_dep(money)

            session.commit()
            await ctx.send(embed=BotEmbed(ctx=ctx, **embed_data))

    @commands.command('casino')
    @commands.guild_only()
    async def _cmd_casino(self, ctx: Context, rate: str, money: int):
        """
        Казино, ставте ваши деньги и ставку. Размер выигрыша обратно пропорционален ставке
        (чем меньше шанс выигрыша, тем больше сам выигрыш)

        Ставка (rate) указывается например так: "1к10" или "2/5" или "7:20" (без кавычек)
        """
        assert re.match(r'\d+[к/:]\d+', rate), "Неверный формат ставки"
        rate: list = list(map(int, rate.replace('к', '/').replace('/', ':').split(':')))
        assert all(map(lambda x: x > 0, rate)), "Числа в ставке должны быть больше 0"
        rate: int = rate[0] / rate[1]
        assert money > 0, "Сумма денег должна быть больше 0"
        assert rate <= 0.5, "Шанс выигрыша должен быть не более 50%"

        with db_session.create_session() as session:
            member_data = DBEconomyTools.get_balance_member(session, ctx.author)
            assert member_data.cash >= money, "Ты не можешь ставить те деньги которых нет у тебя"
            casino_data = DBEconomyTools.get_balance_member(session, ctx.guild.get_member(self.bot.user.id))
            member_data.add_cash(-money)
            if casino_data:
                casino_data.add_cash(money)

            win = self.random(rate)

            if win:
                win_money = int(money * rate ** -1)
                member_data.add_cash(win_money)
                if casino_data:
                    casino_data.add_cash(-win_money)

                config = self.get_config(session, ctx.guild)

                big_wins = [(1 / 2, 1000, "Большой куш!",
                             "https://cdn.discordapp.com/attachments/617713919464833054/831873297411080283/2Q.png"),
                            (1 / 3, 10000, "Денежный дождь!",
                             "https://cdn.discordapp.com/attachments/617713919464833054/831873218003730462/Z.png"),
                            (1 / 4, 100000, "Повезло повезло.",
                             "https://memepedia.ru/wp-content/uploads/2021/02/povezlo-povezlo-mem-5.jpg"),
                            (1 / 5, 1000000, "Море золота!",
                             "https://klike.net/uploads/posts/2018-10/1539761596_1.jpg"),
                            (1 / 10, 10000000, "Калифорний!",
                             "https://cdn.discordapp.com/attachments/617713919464833054/831873183110922250/"
                             "Desktop_210414_1846.jpg")][::-1]
                embed = None
                for chance, sum_money, name, image_url in big_wins:
                    if rate <= chance and win_money >= sum_money:
                        embed = BotEmbed(ctx=ctx,
                                         description=f'Ты получил {name} {win_money} {config.currency_icon} '
                                                     f'(+ {win_money - money})',
                                         colour=discord.Colour.from_rgb(0, 250, 0))
                        embed.set_image(url=image_url)
                        break

                if not embed:
                    embed = BotEmbed(ctx=ctx,
                                     title=random.choice(['Ура, удача!', 'Ты победил!', 'Пополнение счёта успешно!']),
                                     description=f'Ты получаешь {win_money} '
                                                 f'{config.currency_name} (+ {win_money - money})',
                                     colour=discord.Colour.from_rgb(0, 200, 0))
            else:
                embed = BotEmbed(ctx=ctx,
                                 title=random.choice(['Понимаю', 'Повезёт в другой раз...', 'Неудача', 'Fail']),
                                 description=f"ты ничего не получил ({-money})",
                                 colour=discord.Colour.from_rgb(255, 0, 0))
            session.commit()

        await ctx.reply(embed=embed)

    # =======================================================================================================
    @staticmethod
    def get_chance_steal_bank(total: int, count: int) -> float:
        if count == 0 or total <= 0 or total / count <= 1:
            return 0
        return math.log10(total / count) ** -1

    @commands.group('bank')
    @commands.guild_only()
    async def _group_bank(self, ctx: Context):
        """
        Показывает сколько денег в банке.
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            balances = map(lambda m: DBEconomyTools.get_balance_member(session, m).dep, ctx.guild.members)
            balances = list(filter(lambda x: x > 0, balances))
            total = sum(balances)
            count = len(balances)

            embed = BotEmbed(ctx=ctx, title="Данные о банке")
            embed.add_field(name="Всего в банке", value=f'{HRF.number(total)} {config.currency_icon}')
            embed.add_field(name='Непустых ячеек', value=str(count))
            embed.add_field(name='В среднем',
                            value=f'{HRF.number(round(total / count)) if count > 0 else 0} '
                                  f'{config.currency_icon}')
            embed.add_field(name='Шанс успеха',
                            value=str(round(math.log10((total or 2) / (count or 1)) ** -1 * 100, 2)) + "%")
            await ctx.send(embed=embed)

    @_group_bank.command('rob')
    @commands.guild_only()
    @commands.is_owner()
    async def _cmd_bank_rob(self, ctx: Context, count: int):
        """
        Позволяет ограбить банк ограбив указанное кол-во ячеек (чем больше ячеек тем меньше шанс на успех).
        Чем больше средний показатель денег в непустых ячейках тем больше шанс ограбления.
        Если не удача то вы выплачиваете долг банку в размере 1% от всей суммы в банке.
        Необходимо не иметь долгов в банке!

        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            balances = map(lambda m: DBEconomyTools.get_balance_member(session, m).dep, ctx.guild.members)
            balances = list(filter(lambda x: x > 0, balances))
            total_dep = sum(balances)
            count_dep = len(balances)
            assert count <= count_dep, "Слишком много ячеек!"
            chance = (1 - (count - 1) / count_dep) * self.get_chance_steal_bank(total_dep, count_dep)
            success = (chance or -1) >= random.random()
            member = DBEconomyTools.get_balance_member(session, ctx.author)
            if success:
                member.add_cash(1000)
                embed = BotEmbed(ctx=ctx,
                                 title="Успех",
                                 description=f"Ты молодец. Сколько-то награбил, но нечаянно посеял всё на улице. "
                                             f"Жди обновы, но пока держи 1000 {config.currency_icon}!",
                                 colour=discord.Colour.from_rgb(0, 255, 0)
                                 )
            else:

                member.set_dep(int(- total_dep * 0.1))

                embed = BotEmbed(ctx=ctx,
                                 title="Провал",
                                 description=f"К сожалению вам не удалось ограбить банк.\n"
                                             f"Вы теперь должны заплатить: {member.dep} {config.currency_icon}",
                                 colour=discord.Colour.from_rgb(255, 0, 0)
                                 )
            session.commit()
            await ctx.reply(embed=embed)

    # =======================================================================================================
    async def change_bal(self, ctx: Context, member: discord.Member, value: int, a: int, where) -> BotEmbed:
        assert value >= 0, "Value должно быть >= 0"
        assert where in ["dep", "cash"], "where принимает значения только 'dep' и 'cash'"
        with db_session.create_session() as session:
            a //= abs(a)

            config = self.get_config(session, member.guild)
            member_data = DBEconomyTools.get_balance_member(session, member)

            embed = BotEmbed(ctx=ctx,
                             title="Изменение баланса",
                             description=f"{'Зачислено' if a > 0 else 'Снято'} "
                                         f"{HRF.number(value)} {config.currency_name}"
                             )
            embed.set_author(name=member.display_name, icon_url=member.avatar_url)
            embed.add_field(name="Было", value=f"{HRF.number(member_data.get_total())} "
                                               f"{config.currency_icon}")
            if where == 'dep':
                member_data.add_dep(value * a)
            else:
                member_data.add_cash(value * a)

            embed.add_field(name="Стало",
                            value=f"{HRF.number(member_data.get_total())} {config.currency_icon}")
            session.commit()
            return embed

    @commands.group('bal')
    @commands.guild_only()
    async def _group_balance(self, ctx: Context, member: discord.Member = None):
        """
        Показывает свой баланс (участника если указан member)
        """

        with db_session.create_session() as session:
            member = ctx.author if member is None else member
            data = DBEconomyTools.get_balance_member(session, member)
            config = self.get_config(session, ctx.guild)

            embed = BotEmbed(ctx=ctx, title=f"Баланс на сервере", description=f"Счёт {member.mention}")
            embed.set_thumbnail(url=member.avatar_url)
            embed.add_field(name="Кошелёк", value=f"{HRF.number(data.cash)} {config.currency_icon}")
            embed.add_field(name="Банк", value=f"{HRF.number(data.dep)} {config.currency_icon}")
            embed.add_field(name="Всего", value=f"{HRF.number(data.get_total())} {config.currency_icon}")
            await ctx.send(embed=embed)

    # Взаимодействие со счётом
    @_group_balance.command('dep')
    @commands.guild_only()
    async def _cmd_bal_dep(self, ctx: Context, value: int = None):
        """
        Кладёт деньги в банк (Если value не указан, то вся сумма)
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            me_data = DBEconomyTools.get_balance_member(session, ctx.author)

            if value is None:
                value = me_data.cash
                assert value > 0, "У вас нет наличных"
            else:
                assert value > 0, "value должен быть > 0"

            assert value <= me_data.cash, "У вас недостаточно денег для взноса"

            me_data.add_cash(-value)
            me_data.add_dep(value)

            embed = BotEmbed(ctx=ctx,
                             title="Перевод",
                             description=f"В банк зачислено {HRF.number(value)} {config.currency_name}"
                             )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            embed.add_field(name="Осталось налички",
                            value=f"{HRF.number(me_data.cash)} {config.currency_icon}")
            session.commit()
            await ctx.send(embed=embed)

    @_group_balance.command('cash')
    @commands.guild_only()
    async def _cmd_bal_cash(self, ctx: Context, value: int = None):
        """
        Снимает деньги с банка (Если value не указан, то вся сумма)
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            me_data = DBEconomyTools.get_balance_member(session, ctx.author)

            if value is None:
                value = me_data.dep
                assert value > 0, "У вас нет денег в банке"
            else:
                assert value > 0, "value должен быть > 0"

            assert value <= me_data.dep, "У вас недостаточно денег для снятия"

            me_data.add_dep(-value)
            me_data.add_cash(value)

            embed = BotEmbed(ctx=ctx,
                             title="Перевод",
                             description=f"В банке снято {HRF.number(value)} {config.currency_name}"
                             )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
            embed.add_field(name="Осталось в банке",
                            value=f"{HRF.number(me_data.dep)} {config.currency_icon}")
            session.commit()
        await ctx.send(embed=embed)

    @_group_balance.command('add')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_bal_add(self, ctx: Context, member: discord.Member, value: int, where: str = None):
        """
        Кладёт указанное кол-во денег на счёт участника (по умолчанию в dep)
        """
        await ctx.send(embed=await self.change_bal(ctx, member, value, 1, where or "dep"))

    @_group_balance.command('remove')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_bal_remove(self, ctx: Context, member: discord.Member, value: int, where: str = None):
        """
        Снимает указанное кол-во денег со счёта участника (по умолчанию в dep)
        """
        await ctx.send(embed=await self.change_bal(ctx, member, value, -1, where or "dep"))

    @_group_balance.command('set')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_bal_set(self, ctx: Context, member: discord.Member, value: int, where: str = None):
        """
        Устанавливает указанное кол-во денег на счету участника (по умолчанию в dep)
        """
        where = where or "dep"
        assert where in ["dep", "cash"], "where принимает значения только 'dep' и 'cash'"
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            member_data = DBEconomyTools.get_balance_member(session, member)

            if where == 'dep':
                member_data.set_dep(value)
            else:
                member_data.set_cash(value)
            embed = BotEmbed(ctx=ctx,
                             title="Изменение баланса",
                             description=f"Установлен баланс в {where} "
                                         f"{HRF.number(member_data.cash if where == 'cash' else member_data.dep)} "
                                         f"{config.currency_name}"
                             )
            embed.set_author(name=member.display_name, icon_url=member.avatar_url)
            session.commit()
            await ctx.send(embed=embed)

    @_group_balance.command('visa')
    @commands.guild_only()
    async def _cmd_bal_visa(self, ctx: Context, member: discord.Member, value: int):
        """
        Переводит деньги из банка другому участнику в банк с комиссией в 5%
        """
        assert value > 0, "Сумма средств должна быть больше 0"

        with db_session.create_session() as session:
            member_a = DBEconomyTools.get_balance_member(session, ctx.author)
            member_b = DBEconomyTools.get_balance_member(session, member)
            bank = DBEconomyTools.get_balance_member(session, ctx.me)
            config = self.get_config(session, ctx.guild)

            assert member_a.dep >= value, "Недостаточно денег в банке для перевода"
            commission = int(value * 0.02)
            member_a.add_dep(-value)
            member_b.add_dep(value - commission)
            bank.add_cash(commission)
            session.commit()

            embed = BotEmbed(ctx=ctx, title="Транзакция на перевод",
                             timestamp=datetime.datetime.now())
            embed.add_field(name="Отправитель", value=ctx.author.mention)
            embed.add_field(name="Получатель", value=member.mention)
            embed.add_field(name="Переведено", value=str(HRF.number(value)) + " " + config.currency_icon,
                            inline=False)
            embed.add_field(name="Комиссия", value=str(HRF.number(commission)) + " " + config.currency_icon,
                            inline=False)
            embed.add_field(name="Итого",
                            value=str(HRF.number(value - commission)) + " " + config.currency_icon,
                            inline=False)
            await ctx.reply(embed=embed)

    @commands.Cog.listener('on_member_join')
    async def _listener_auto_add_member_data(self, member: discord.Member):
        with db_session.create_session() as session:
            DBEconomyTools.update_balance_member(session, member)
            DBEconomyTools.update_features_member(session, member)
            session.commit()

    @commands.Cog.listener('on_member_remove')
    async def _listener_auto_remove_member_data(self, member: discord.Member):
        with db_session.create_session() as session:
            if DBEconomyTools.get_balance_member(session, member):
                DBEconomyTools.delete_balance_member(session, member)
                DBEconomyTools.delete_features_member(session, member)
                session.commit()

    # =======================================================================================================
    @commands.command()
    @commands.guild_only()
    async def leader_board(self, ctx: Context):
        """
        Выводит таблицу с топ богачами
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            members = list(
                sorted(filter(lambda x: bool(x[0]),
                              map(lambda m: (m, DBEconomyTools.get_balance_member(session, m).get_total()),
                                  ctx.guild.members)),
                       key=lambda m: (m[1], m[0].name), reverse=True)
            )

            embed = BotEmbed(ctx=ctx,
                             title="Самые богатые люди",
                             description="\n".join(
                                 f"{i + 1}. {member.mention} : {HRF.number(money)} {config.currency_icon}"
                                 for i, (member, money) in enumerate(members[:10]))
                             )
            embed.set_author(name=str(ctx.guild), icon_url=ctx.guild.icon_url)

            for i in range(len(members)):
                if members[i][0] == ctx.author:
                    embed.set_footer(text=f"Ваше место {i + 1}-е", icon_url=ctx.author.avatar_url)
                    break
            await ctx.reply(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def poor_board(self, ctx: Context):
        """
        Выводит таблицу с топ бедняками
        """

        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            members = list(
                sorted(filter(lambda x: bool(x[0]),
                              map(lambda m: (m, DBEconomyTools.get_balance_member(session, m).get_total()),
                                  ctx.guild.members)),
                       key=lambda m: (m[1], m[0].name), reverse=False)
            )

            embed = BotEmbed(ctx=ctx,
                             title="Самые бедные люди",
                             description="\n".join(
                                 f"{i + 1}. {member.mention} : {HRF.number(money)} {config.currency_icon}"
                                 for i, (member, money) in enumerate(members[:10]))
                             ).set_author(name=str(ctx.guild), icon_url=ctx.guild.icon_url)

            for i in range(len(members)):
                if members[i][0] == ctx.author:
                    embed.set_footer(text=f"Ваше место {i + 1}-е", icon_url=ctx.author.avatar_url)
                    break

            await ctx.send(embed=embed)

    # =======================================================================================================
    @commands.group('shop')
    @commands.guild_only()
    async def _group_shop(self, ctx: Context, page=1):
        """
        Показывает магазин сервера (Page - страница магазина)
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)

            items = config.get_shop(ctx)['shop']  # , [{"role": 733753399102668831, "price": 10000000}])

            max_items_on_page = 5
            max_page = len(items) // max_items_on_page + (1 if len(items) % max_items_on_page else 0)
            assert max_page >= page >= 1, "Нет такой страницы"

            embed = BotEmbed(ctx=ctx,
                             title=f"Магазин сервера",
                             description=f"Чтобы купить предмет используйте `{ctx.prefix}buy`\n"
                                         f"Чтобы просматривать магазин используйте "
                                         f"`{ctx.prefix}shop page`\n"
                                         f"где `page` - номер страницы"
                             )
            embed.set_author(name=str(ctx.guild), icon_url=ctx.guild.icon_url)
            embed.set_footer(text=f"Страница {page}/{max_page}")
            try:
                for i in range(max_items_on_page):
                    item = items[i + (page - 1) * max_items_on_page]
                    name = (
                            f"{i + (page - 1) * max_items_on_page + 1} - "
                            + item['role'].name +
                            f" {HRF.number(item['price'])} {config.currency_icon}"
                    )
                    embed.add_field(name=name, value=item.get('description', 'Без описания'), inline=False)
            except IndexError:
                pass
            await ctx.send(embed=embed)

    @_group_shop.command(name='buy')
    @commands.guild_only()
    async def _cmd_shop_buy(self, ctx: Context, item_id: int):
        """
        Покупает предмет из магазина с указанным id
        """

        assert item_id >= 1, "item_id должен быть >= 1"

        with db_session.create_session() as session:
            config = self.get_config(session, guild=ctx.guild)

            try:
                item = config.get_shop(ctx)['shop'][item_id - 1]
            except (IndexError, KeyError):
                assert False, f"В магазине нет предмета с id {item_id}"
            else:
                role = item['role']
                price = item['price']
                member_data = DBEconomyTools.get_balance_member(session, ctx.author)
                assert member_data.cash >= price, "У вас не хватает наличных средств для покупки"
                await ctx.author.add_roles(role)
                member_data.add_cash(-price)
                session.commit()
                session.close()
                await ctx.send(embed=BotEmbed(ctx=ctx, title="Успешно!", description="Роль добавлена в ваш инвентарь",
                                              colour=discord.colour.Color.from_rgb(0, 255, 0)))

    @_group_shop.command(name='add')
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _cmd_shop_add(self, ctx: Context, role: discord.Role, price: int, *description):
        """
        Добавляет предмет в магазин
        """

        assert price >= 1, "Цена должна быть >= 1"

        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            items = config.get_shop(ctx)['shop']
            items.append(
                {"role": role, "price": price, "description": join_string(description, "Нет описания")})
            config.set_shop({'shop': items})
            session.commit()
            await ctx.send(embed=BotEmbed(ctx=ctx, title="Успешно!", description="Предмет добавлен в магазин",
                                          colour=discord.colour.Color.from_rgb(0, 255, 0)))

    @_group_shop.command(name='remove')
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _cmd_shop_remove(self, ctx: Context, item_id: int):
        """
        Убирает предмет из магазина
        """

        assert item_id >= 1, "item_id должен быть >= 1"
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            shop = config.get_shop(ctx)
            try:
                item = shop['shop'].pop(item_id - 1)
                config.set_shop(shop)
                session.commit()
                session.close()
            except (IndexError, KeyError):
                assert False, f"В магазине нет предмета с id {item_id}"
            else:
                await ctx.send(embed=BotEmbed(ctx=ctx, title="Успешно!", description=f"Предмет {item['role']} убран "
                                                                                     f"из магазина",
                                              colour=discord.colour.Color.from_rgb(0, 255, 0)))

    # =======================================================================================================
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_currency(self, ctx: Context, icon: str, name: str):
        """
        Устанавливает изображение и название ходовой валюты на сервере
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            config.currency_icon = icon
            config.currency_name = name
            session.commit()
            await ctx.send(
                embed=BotEmbed(ctx=ctx, title="Изменена валюта", description=f"Изменена валюта на {icon} {name}"))

    # =======================================================================================================
    @commands.group('luck_box')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _group_luck_box(self, ctx: Context):
        """Коробки удачи"""
        # TODO: Заглушка
        await ctx.just_send_help()

    @_group_luck_box.command('set')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_luck_box_set(self, ctx: Context, name: str, desc: str, prices: str, image: str, *lots: str):
        class Lot:
            def __init__(self, data):
                _name, _role_id, _chance = data.split(';')
                self.name = _name
                self.role: discord.Role = ctx.guild.get_role(int(_role_id))
                self.chance = float(_chance)

        lots = list(map(Lot, lots))

        with db_session.create_session() as session:
            session: db_session.Session

            config: EconomyConfig = self.get_config(session, ctx.guild)

            f = "{}: {} " + config.currency_icon
            embed = BotEmbed(ctx=ctx, title=name, description=desc + "\nЦены за коробки\n" + "\n".join(
                f.format(i + 1, p) for i, p in enumerate(list(map(int, prices.split(" "))))))
            embed.set_thumbnail(url=image)
            embed.set_author(name=name, icon_url=ctx.guild.icon_url)
            for i, lot in enumerate(lots):
                embed.add_field(name=f"#{i + 1}: {lot.name}", value=lot.role.mention, inline=i != 0)

            msg: discord.Message = await ctx.send(embed=embed)
            # TODO: Цены на коробки

            data_box = {
                "lots": [{"name": lot.name, "role_id": lot.role.id, "chance": lot.chance} for lot in lots],
                "prices": list(map(int, prices.split(" ")))
            }
            for i in range(5):
                await msg.add_reaction(EMOJI_NUMBERS[i + 1])

            box = LuckBox()
            box.config_id = self.get_config(session, ctx.guild).guild_id
            box.ctrl_msg = msg.id
            box.set_data_boxes(data_box)
            session.add(box)

            session.commit()
            await ctx.message.delete()

    @commands.Cog.listener('on_raw_reaction_add')
    async def _listener_buy_luck_box(self, payload: discord.RawReactionActionEvent):
        if payload.emoji.name not in EMOJI_NUMBERS.values():
            return
        if payload.member == self.bot.user:
            return

        with db_session.create_session() as session:
            session: db_session.Session

            luck_box: LuckBox = session.query(LuckBox).filter(LuckBox.ctrl_msg == payload.message_id).first()
            if not luck_box:
                return

            data = luck_box.get_data_boxes()
            lots = data["lots"]
            prices = data["prices"]

            count = None
            for key, val in EMOJI_NUMBERS.items():
                if val == payload.emoji.name:
                    count = key
            if count is None:
                return

            member = payload.member
            member_data = DBEconomyTools.get_balance_member(session, member)

            price = sum(prices[:count])
            channel: discord.TextChannel = self.bot.get_channel(831087870843682846)
            if member_data.cash < price:
                await channel.send(
                    embed=BotEmbed(
                        title="Ошибка покупки",
                        description=f"{member.mention} У тебя не достаточно "
                                    f"средств для покупки этого количества коробок. ({self.bot.command_prefix}bal)"),
                    delete_after=10)
            else:
                member_data.add_cash(- price)
                session.commit()

                async with channel.typing():

                    prizes = list()
                    while len(prizes) < count:
                        for lot in lots:
                            if lot['chance'] >= random.random():
                                prizes.append(lot)
                                break

                    embed = BotEmbed(title="Твой выигрыш", description=f"{member.mention} твои призы уже у тебя!")
                    for i, lot in enumerate(prizes):
                        embed.add_field(name=f"#{i + 1}: {lot['name']}",
                                        value=channel.guild.get_role(lot['role_id']).mention, inline=False)
                roles = list(map(lambda x: channel.guild.get_role(x['role_id']), prizes))
                await member.add_roles(*roles)

                # TODO: Сделать вывод в отдельный канал
                await channel.send(embed=embed)

    @commands.Cog.listener('on_raw_message_delete')
    async def _listener_delete_luck_box(self, payload: discord.RawMessageDeleteEvent):
        with db_session.create_session() as session:
            box = session.query(LuckBox).filter(LuckBox.ctrl_msg == payload.message_id).first()
            if box:
                session.delete(box)
                session.commit()

    # =======================================================================================================
    @commands.group('promo')
    @commands.guild_only()
    async def _group_promo(self, ctx: Context, code: str):
        """
        Активирует промокод
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)

            code = session.query(PromoCode).filter(PromoCode.code == code,
                                                   PromoCode.config_id == config.guild_id).first()
            assert isinstance(code, PromoCode), "Недействительный код"
            assert not code.activated, "Код уже активирован"

            balance = DBEconomyTools.get_balance_member(session, ctx.author)
            balance.add_dep(code.moneys)
            code.activated = True
            code.by = ctx.author.id
            session.commit()

            await ctx.reply(embed=BotEmbed(ctx=ctx, title="Активирован промокод").add_field(
                name="Начислено", value=HRF.number(code.moneys) + " " + config.currency_icon))

    @_group_promo.command('create')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_promo_create(self, ctx: Context, moneys: int):
        """
        Создаёт промокод на указанную сумму денег
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            code = PromoCode()
            code.config_id = config.guild_id
            code.code = "".join(chr(random.randint(ord("A"), ord("Z"))) for _ in range(10))
            code.moneys = bigint(moneys)
            session.add(code)
            session.commit()
            await ctx.send(embed=BotEmbed(ctx=ctx, title="Промокод").add_field(
                name="Код", value=f"`{code.code}`").add_field(
                name="Сумма", value=HRF.number(code.moneys) + ' ' + config.currency_icon
            ))

    @_group_promo.command('list')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_promo_list(self, ctx: Context):
        """
        Показывает промокоды сервера
        """

        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            codes = session.query(PromoCode).filter(PromoCode.config_id == config.guild_id,
                                                    PromoCode.activated == False).all()
            await ctx.send(embed=BotEmbed(ctx=ctx,
                                          title=f"Промокоды {ctx.guild.name}",
                                          description="\n".join(
                                              f"`{code.code}` - {HRF.number(code.moneys)} {config.currency_icon}"
                                              for code in codes)))

    # =======================================================================================================
    @commands.command('help_economy')
    @commands.guild_only()
    async def _cmd_help_economy(self, ctx: Context):
        """
        Показывает информацию о работах на сервере
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)

            embed = BotEmbed(ctx=ctx, )
            embed.title = "Экономическая система \"Г.Р.И.Б\""
            embed.description = (
                "```python\n"
                "   Мы находимся в криминальном городе, вокруг воровство, обман, насилие. "

                "Никому нельзя доверять, рассчитывай только на себя.\n"
                "Работай, воруй, грабь банки, делай все, чтобы выйти победителем и получить славу. "
                "Этому городу нужна новая легенда, возможно, это будешь ты!\n\n"
                f"Город: {ctx.guild.name}\n"
                f"Валюта города: {config.currency_name}\n\n"
                f"Мэр - {ctx.guild.owner.display_name}\n"
                "Ваша роль - Гражданин```"
            )
            embed.add_field(name=ctx.prefix + self.bot.get_command('work').name,
                            value="Узнать о способах заработка")
            await ctx.send(embed=embed)


class DBEconomyTools:
    @staticmethod
    def get_features_member(session: db_session.Session, member: discord.Member) -> Optional[FeatureMember]:
        return session.query(FeatureMember).filter(FeatureMember.member_id == member.id,
                                                   FeatureMember.guild_id == member.guild.id).first()

    @staticmethod
    def add_features_member(session: db_session.Session, member: discord.Member) -> FeatureMember:
        if DBEconomyTools.get_features_member(session, member):
            raise ValueError("Такая характеристика уже есть")

        fm = FeatureMember()
        fm.member_id = member.id
        fm.guild_id = member.guild.id
        session.add(fm)
        return fm

    @staticmethod
    def update_features_member(session: db_session.Session, member: discord.Member) -> FeatureMember:
        fm = DBEconomyTools.get_features_member(session, member)
        if not fm:
            fm = DBEconomyTools.add_features_member(session, member)
        else:
            fm.member_id = member.id
            fm.guild_id = member.guild.id
        return fm

    @staticmethod
    def delete_features_member(session: db_session.Session, member: discord.Member):
        fm = DBEconomyTools.get_features_member(session, member)
        if not fm:
            raise ValueError("Такой характеристики нет в базе")
        session.delete(fm)
        return fm

    @staticmethod
    def get_balance_member(session: db_session.Session, member: discord.Member) -> Optional[Balance]:
        return session.query(Balance).filter(Balance.member_id == member.id,
                                             Balance.guild_id == member.guild.id).first()

    @staticmethod
    def add_balance_member(session: db_session.Session, member: discord.Member):
        if DBEconomyTools.get_balance_member(session, member):
            raise ValueError("Такой счёт уже есть")

        bal = Balance()
        bal.member_id = member.id
        bal.guild_id = member.guild.id
        session.add(bal)
        return bal

    @staticmethod
    def update_balance_member(session: db_session.Session, member: discord.Member) -> Balance:
        bal = DBEconomyTools.get_balance_member(session, member)
        if not bal:
            bal = DBEconomyTools.add_balance_member(session, member)
        else:
            bal.member_id = member.id
            bal.guild_id = member.guild.id
        return bal

    @staticmethod
    def delete_balance_member(session: db_session.Session, member: discord.Member):
        bal = DBEconomyTools.get_balance_member(session, member)
        if not bal:
            raise ValueError("Такого счёта нет в базе")
        session.delete(bal)
        return bal


async def setup(bot: Bot):
    await bot.add_cog(EconomyCog(bot))
