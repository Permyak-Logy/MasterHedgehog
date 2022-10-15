import re
from typing import Optional

import discord
from discord.ext import commands

from PLyBot import Bot, Cog, BotEmbed


class F:
    @staticmethod
    def mapattr(attr, arr, sep=', '):
        def local_get_attr(elem):
            return str(getattr(elem, attr))

        return sep.join(list(map(local_get_attr, arr)))


class PythonConsoleCog(Cog, name='PyConsole'):
    """
    Модуль для взаимодействия с системой бота через команды
    Доступно только узкому кругу лиц
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, emoji_icon='🖥️')
        self.locals = {}

    # @tasks.loop(seconds=10)
    async def input_eval(self):
        pass

    # @tasks.loop(seconds=10)
    async def input_await_eval(self):
        pass

    # @tasks.loop(seconds=10)
    async def input_exec(self):
        pass

    @commands.command('eval', aliases=['ev'])
    @commands.is_owner()
    async def _cmd_eval(self, ctx: commands.Context, inc_str: Optional[bool] = True, inc_repr: Optional[bool] = False,
                        *, exp: str):
        """
        ```python
        return eval(exp)```
        """

        # noinspection PyUnusedLocal
        def for_func(function: callable, i: iter):
            output = ""
            for elem in i:
                output += function(elem) + "\n"
            return output

        result = eval(exp)
        exp = '```python\n' + exp.replace('`', '\\`') + '```'
        embed = BotEmbed(ctx=ctx, title="Выполнена команда eval", description=exp, colour=self.bot.colour)
        if inc_str:
            embed.add_field(name='str', value=str(result) or "<empty_string>")
        if inc_repr:
            embed.add_field(name='repr', value=repr(result) or "<empty_repr>")
        await ctx.send(embed=embed)

    @commands.command('await_eval', aliases=['ae', 'await'])
    @commands.is_owner()
    async def _cmd_await_eval(self, ctx: commands.Context, inc_result: Optional[bool] = False, *, exp: str):
        """
        ```python
        return await eval(exp)```
        """

        # noinspection PyUnusedLocal
        async def for_async_func(function: callable, i: iter):
            output = ""
            for elem in i:
                output += str(await function(self, elem)) + "\n"
            return output

        # noinspection PyUnusedLocal
        for_af = faf = for_async_func

        result = await eval(exp)
        exp = '```python\nawait ' + exp.replace('`', '\\`') + '```'
        embed = BotEmbed(ctx=ctx, title="Выполнена команда await eval", description=exp, colour=self.bot.colour)
        if inc_result:
            embed.add_field(name='str', value=str(result))
            embed.add_field(name='repr', value=str(result))
        try:
            await ctx.send(embed=embed)
        except RuntimeError:
            pass

    # TODO: Сделать вложенные await'ы

    @commands.command('exec', aliases=['ex'])
    @commands.is_owner()
    async def _cmd_exec(self, ctx: commands.Context, *lines: str):
        """
        ```python
        def _print(*obj, sep=' ', end='\\n'):
            '''print in ctx'''
            ...
        exec('\\n'.join(lines))```
        """

        __output__ = ""

        # noinspection PyUnusedLocal
        def _print(*obj, sep=' ', end='\n'):
            nonlocal __output__
            __output__ += sep.join(map(str, obj)) + end

        exp = "\n".join(lines)
        exec(exp)
        exp = '```python\n' + exp.replace('`', '\\`') + '```'
        embed = BotEmbed(ctx=ctx, title="Выполнена команда exec", description=exp,
                         colour=self.bot.colour)
        if __output__:
            embed.add_field(name='output', value=f'```python\n{__output__}```')

        await ctx.send(embed=embed)

    @staticmethod
    async def check(message: discord.Message):
        res = any(map(lambda x: re.search(eval(f"r'[ .]?{x}[ .(]?'"), message.content),
                      ["exit", "print", "input", "exec", "self",
                       "discord", "import", "del", "=", "open", "re", "DataCenter",
                       "commands", "sys", "os", "asyncio"]))
        if res and not any(map(lambda x: message.author.id == x, [403910550028943361])):
            return False
        return True


async def setup(bot: Bot):
    await bot.add_cog(PythonConsoleCog(bot))
