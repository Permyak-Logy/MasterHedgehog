import inspect
import itertools
import re

import discord
from discord.ext import commands
from .embed import BotEmbed

from .paginator import Paginator

# Шпаргалка по описанию Embed
"""
Title (После этой строчки остальное идёт в description)
## Заголовок

Начало описания description (Предыдущие записи не стираются)
<d> Следующая строка description

Название Field и начало описания этого field (Если повторно указать тот же
field name, то продолжит его описание)
# Название

Footer
<fn> Имя
<fi> url иконки

Author
<an> Имя
<ai> url Иконки

Картинка
<i> url Картинки

Thumbnail (Маленькая картинка справа)
<t> url thumbnail

Video
<v> url видео
"""


# TODO: примеры использования
class HelpCommand(commands.MinimalHelpCommand):
    def __init__(self, **params):

        super(HelpCommand, self).__init__(paginator=Paginator(prefix=None, suffix=None, max_size=1900),
                                          commands_heading="Команды",
                                          aliases_heading="Псевдонимы", **params)
        self.width = params.pop('width', 80)
        self.subcommands_heading = "Подкоманды"
        self.hint_types = params.pop('hint_types', True)

    def shorten_text(self, text):
        """:class:`str`: Shortens text to fit into the :attr:`width`."""
        if len(text) > self.width:
            return text[:self.width - 3] + '...'
        return text

    def get_command_signature(self, command):
        annotations = command.callback.__annotations__
        for key in list(annotations.keys()):
            val = annotations[key]
            if inspect.isclass(val):
                annotations[key] = val.__name__
                if any(issubclass(val, cls) for cls in [commands.Context, commands.Cog, commands.Bot]):
                    del annotations[key]
            if str(val).startswith('typing.'):
                annotations[key] = str(val).replace('typing.', '', 1)
        if self.hint_types:
            return "%s%s %s" % (self.clean_prefix, command.qualified_name,
                                ' '.join(map(
                                    lambda data: f"<{data[0]}:{data[1]}>" if data[1] is not None
                                    else f"<{data[0]}>", annotations.items())))
        else:
            return "%s%s %s" % (self.clean_prefix,
                                command.qualified_name,
                                ' '.join(map(lambda data: f"<{data[0]}>", annotations.items())))

    def add_bot_commands_formatting(self, commands_, heading, emoji=None):
        if commands_:
            self.paginator.add_line(
                f'# ' + "{}%s ({}{} %s)".format(emoji + ' ' if emoji else '',
                                                self.context.prefix,
                                                self.context.bot.get_command("help")) % (heading, heading))
            new_line = []
            while commands_:
                name = f'`{self.context.prefix}{commands_.pop(0).name}`'
                if sum(map(len, new_line)) + len(new_line) + len(name) > 61:
                    self.paginator.add_line(" ".join(new_line))  # \u2002
                    new_line.clear()
                new_line.append(name)
            if new_line:
                self.paginator.add_line(" ".join(new_line))

    def add_subcommand_formatting(self, command):
        self.paginator.add_line(f"# " + "{}{} ({}{} {})".format(
            self.context.prefix, command, self.context.prefix, self.context.bot.get_command('help'), command))

        if command.short_doc:
            # TODO: Сделать свой short_doc
            self.paginator.add_line(self.shorten_text(command.short_doc))

    def add_command_formatting(self, command: commands.Command):
        self.paginator.add_line(f"## " + "Команда {} ({})".format(
            command,
            command.cog.qualified_name if commands.cog is not None else "Без имени"))
        if command.description:
            self.paginator.add_line(command.description, empty=True)

        if command.help:
            try:
                self.paginator.add_line(command.help, empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()

        signature = self.get_command_signature(command)
        self.paginator.add_line(f"# " + "Оформление")
        self.paginator.add_line("```python\n{}\n```".format(signature))

        if command.aliases:
            self.add_aliases_formatting(command.aliases)

    def add_aliases_formatting(self, aliases):
        self.paginator.add_line("# " + self.aliases_heading)
        self.paginator.add_line("`%s`" % '`, `'.join(aliases), empty=True)

    def get_opening_note(self):
        command_name = self.invoked_with
        note = (
            "Используй `{}{} [command]` Для получения информации о команде\n"
            "Ты также можешь использовать `{}{} [category]` для большей информации о категории.\n"
            "Если ты не в курсе как работать и оформлять команды, "
            "то просто введи `{}syntax` и я объясню тебе это всё с примерами!"
        ).format(self.clean_prefix, command_name, self.clean_prefix, command_name, self.clean_prefix)
        return note

    async def command_not_found(self, string):
        return "Команда {} не найдена"

    async def send_error_message(self, error):
        await self.get_destination().send(
            embed=BotEmbed(ctx=self.context, title="Упс. Ошибка", description=error))

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot
        self.paginator.add_line(f"## Команды " + bot.user.name)
        self.paginator.add_line(f"<t> " + str(bot.user.avatar_url), empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        def get_category(command, *, no_category_="Без имени"):
            cog = command.cog
            return (cog.qualified_name, cog.emoji_icon) if cog is not None else (no_category_, None)

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        self.paginator.add_line("==== **Доступные категории и команды** ====", empty=True)
        for (category, emoji), commands_ in to_iterate:
            commands_ = sorted(commands_, key=lambda c: c.name) if self.sort_commands else list(commands_)
            self.add_bot_commands_formatting(commands_, category, emoji=emoji)

        if self.context.bot.footer:
            footer = self.context.bot.footer
            if 'text' in footer:
                self.paginator.add_line('<fn> ' + footer['text'])
            if 'icon_url' in footer:
                self.paginator.add_line('<fi> ' + footer['icon_url'])

        await self.send_pages()
        return bot

    async def send_cog_help(self, cog: commands.Cog):
        self.paginator.add_line('## ' + "Категория %s" % cog.qualified_name)

        self.paginator.add_line(f"<t> " + str(self.context.bot.user.avatar_url),
                                empty=True)

        if cog.description:
            self.paginator.add_line(cog.description, empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        if filtered:
            self.paginator.add_line("==== **Доступные команды** ====", empty=True)
            for command in filtered:
                self.add_subcommand_formatting(command)

        if self.context.bot.footer:
            footer = self.context.bot.footer
            if 'text' in footer:
                self.paginator.add_line('<fn> ' + footer['text'])
            if 'icon_url' in footer:
                self.paginator.add_line('<fi> ' + footer['icon_url'])

        await self.send_pages()
        return cog

    async def send_group_help(self, group: commands.Group):
        self.paginator.add_line(f"<t> " + str(self.context.bot.user.avatar_url),
                                empty=True)

        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        if filtered:
            self.paginator.add_line('**%s**' % self.subcommands_heading)
            for command in filtered:
                self.add_subcommand_formatting(command)

        if self.context.bot.footer:
            footer = self.context.bot.footer
            if 'text' in footer:
                self.paginator.add_line('<fn> ' + footer['text'])
            if 'icon_url' in footer:
                self.paginator.add_line('<fi> ' + footer['icon_url'])

        await self.send_pages()
        return group

    async def send_command_help(self, command: commands.Command):
        self.paginator.add_line(
            f"<t> " + str(self.context.bot.user.avatar_url), empty=True)

        self.add_command_formatting(command)

        if self.context.bot.footer:
            footer = self.context.bot.footer
            if 'text' in footer:
                self.paginator.add_line('<fn> ' + footer['text'])
            if 'icon_url' in footer:
                self.paginator.add_line('<fi> ' + footer['icon_url'])
        self.paginator.close_page()

        await self.send_pages()
        return command

    async def send_pages(self, embed_markup=True):
        destination = self.get_destination()
        title = author = footer = image = thumbnail = video = ''
        footer_icon = author_icon = discord.embeds.EmptyEmbed
        for page in self.paginator.pages:
            if not embed_markup:
                await destination.send("\n".join(page))
                break
            cur = None
            fields = {None: []}
            for line in page:
                if re.match(r"#{2} .+", line):  # Title Embed and start description
                    title = line[3:]
                    cur = None
                    fields[cur] = []
                elif re.match(r"# .+", line):  # Title Field and start this field
                    cur = line[2:]
                    fields.setdefault(cur, [])
                elif re.match(r"<fn> .+", line):  # Footer Name
                    footer = line[5:]
                elif re.match(r"<fi> .+", line):  # Footer Icon
                    footer_icon = line[5:]
                elif re.match(r"<an> .+", line):  # Author Name
                    author = line[5:]
                elif re.match(r"<ai> .+", line):  # Author Icon
                    author_icon = line[5:]
                elif re.match(r"<i> .+", line):  # Image
                    image = line[4:]
                elif re.match(r"<t> .+", line):  # Thumbnail
                    thumbnail = line[4:]
                elif re.match(r"<d>", line):  # Description Start
                    cur = None
                    if len(line.strip()) > 4:
                        fields[cur].append(line[4:])
                elif re.match(r"<v>", line):  # Video
                    video = line[4:]
                else:
                    fields[cur].append(line)

            embed = BotEmbed(ctx=self.context, title=title or self.context.bot.user.name,
                             description="\n".join(fields[None]) if fields[None] else None,
                             video=video if video else None
                             )
            not footer or embed.set_footer(text=footer, icon_url=footer_icon)
            not author or embed.set_author(name=author, icon_url=author_icon)
            not image or embed.set_image(url=image)
            not thumbnail or embed.set_thumbnail(url=thumbnail)

            for field, lines in fields.items():
                if isinstance(field, str):
                    embed.add_field(name=field, value="\n".join(lines) or "||Нет описания||",
                                    inline=False)

            await self.context.reply(embed=embed)
