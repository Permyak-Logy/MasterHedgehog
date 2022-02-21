from PLyBot import Bot, Cog, Context
from discord.ext import commands
import discord


class KeyboardCog(Cog, name='Keyboard'):
    def __init__(self, bot: Bot):
        super().__init__(bot, emoji_icon='⌨️')

        self.sessions = {}

    def add_session(self, session):
        pass

    async def cog_check(self, ctx: Context):
        return self.bot.is_owner(ctx.author)

    @commands.command('keyboard', aliases=['kb'])
    async def _cmd_keyboard(self, ctx: Context):
        await ctx.reply('ok')


class Controller:
    class Ext:
        @staticmethod
        async def to_page(ctrl, index: int):
            if index > len(ctrl._pages):
                raise IndexError(f"Страница не существует с индексом {index}")
            ctrl._current = index
            ctrl.update_msg_ctrl()

    def __int__(self, cog: Cog):
        self.cog = cog
        self._pages = []
        self._current = None
        self.msg_id = None

    async def send_msg_ctrl(self, ctx: Context):
        msg = await ctx.send()

    async def update_msg_ctrl(self):
        pass

    async def fixup_emojis(self):
        pass

    def add_page(self, page) -> int:
        if not isinstance(page, Page):
            raise TypeError(f"Параметр page должен быть класса '{Page.__name__}'. Получен {page.__class__.__name__}")
        self._pages.append(page)
        if self._current is None:
            self._current = 0
        return len(self._pages) - 1


class Page:
    class Field:
        def __init__(self, page, name, func: callable):
            self.page = page
            self.name = name
            self.func = func

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.func

        def __call__(self, *_, **__):
            return self.func(self.page)

    def __init__(self, ctrl: Controller, **options):
        self.ctrl = Controller

        self.title = options.pop('title', None)
        self.description = options.pop('description', None)
        self.author = options.pop('author', {'name': None, 'url': None, 'icon_url': None})
        self.footer = options.pop('footer', ctrl.cog.bot.footer)
        self.colour = options.pop('colour', ctrl.cog.bot.colour)
        self.thumbnail = options.pop('thumbnail', None)
        self.fields = []

    def add_field(self, name: str, val: str):
        self.fields.append(self.Field(self, name, lambda _: val))

    def bind_field(self, name: str, func: callable):
        self.fields.append(self.Field(self, name, func))

    def make_embed(self) -> discord.Embed:
        embed = discord.Embed(title=self.title, description=self.description, colour=self.colour)
        embed.set_author(**self.author)
        embed.set_footer(**self.footer)
        embed.set_thumbnail(url=self.thumbnail)
        return embed


class Keyboard:

    def __init__(self, page: Page, **options):
        self.page = page
        self.turn_emojis = []
        self.keys_funcs = {}

    def bind_emoji(self, emoji: str, func: callable):
        if emoji not in self.turn_emojis:
            self.turn_emojis.append(emoji)
        self.keys_funcs[emoji] = func

    async def on_emoji_press(self, by: discord.User, emoji):
        pass


class Session:
    def __init__(self, ctx: Context, ctrl: Controller):
        self.ctx = ctx
        self.ctrl = ctrl

    async def close(self):
        pass


def setup(bot: Bot):
    bot.add_cog(KeyboardCog(bot))
