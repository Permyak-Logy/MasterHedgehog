import inspect
import itertools
import re
import typing

import discord
from discord.ext import commands

from .paginator import Paginator


class HelpCommand(commands.MinimalHelpCommand):
    def __init__(self, **params):

        super(HelpCommand, self).__init__(paginator=Paginator(prefix=None, suffix=None, max_size=1800),
                                          commands_heading="Команды",
                                          aliases_heading="Псевдонимы", **params)
        self.subcommands_heading = "Подкоманды"

        self.colour = params.pop('colour', discord.colour.Colour.from_rgb(127, 127, 127))
        self.hint_types = params.pop('hint_types', True)

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
            print(val.__class__)
        if self.hint_types:
            return "%s%s %s" % (self.clean_prefix,
                            command.qualified_name,
                            ' '.join(map(lambda data: f"<{data[0]}:{data[1]}>", annotations.items())))
        else:
            return "%s%s %s" % (self.clean_prefix,
                                command.qualified_name,
                                ' '.join(map(lambda data: f"<{data[0]}>", annotations.items())))

    def add_bot_commands_formatting(self, commands_, heading):
        if commands_:
            joined = '`' + '`\u2002`'.join(c.name for c in commands_) + '`'
            self.paginator.add_line(
                f'# ' + "%s ({}{} %s)".format(self.context.bot.command_prefix,
                                              self.context.bot.get_command("help")) % (heading, heading))
            self.paginator.add_line(joined)

    def add_subcommand_formatting(self, command):
        self.paginator.add_line(f"# " + "{}{} ({}{} {})".format(
            self.context.bot.command_prefix,
            command, self.context.bot.command_prefix, self.context.bot.get_command('help'), command))

        if command.short_doc:
            self.paginator.add_line(command.short_doc)

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
        if command.aliases:
            self.paginator.add_line("```python\n{}\n```".format(signature))
            self.add_aliases_formatting(command.aliases)
        else:
            self.paginator.add_line("```python\n{}\n```".format(signature), empty=True)

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
            embed=discord.Embed(title="Упс. Ошибка", description=error, colour=self.colour))

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        self.paginator.add_line(f"<t> " + str(bot.user.avatar_url), empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        def get_category(command, *, no_category_="Без имени"):
            cog = command.cog
            return cog.qualified_name if cog is not None else no_category_

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        self.paginator.add_line("==== **Доступные категории и команды** ====", empty=True)
        for category, commands_ in to_iterate:
            commands_ = sorted(commands_, key=lambda c: c.name) if self.sort_commands else list(commands_)
            self.add_bot_commands_formatting(commands_, category)

        await self.send_pages(rd=True)
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

        await self.send_pages(rd=True)
        return cog

    async def send_group_help(self, group: commands.Group):
        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        if filtered:
            self.paginator.add_line('**%s**' % self.subcommands_heading)
            for command in filtered:
                self.add_subcommand_formatting(command)

        await self.send_pages(rd=True)

    async def send_command_help(self, command: commands.Command):
        self.paginator.add_line(
            f"<t> " + str(self.context.bot.user.avatar_url), empty=True)

        self.add_command_formatting(command)
        self.paginator.close_page()
        await self.send_pages(rd=True)
        return command

    async def send_pages(self, rd=False):
        destination = self.get_destination()
        title = footer = author = image = thumbnail = video = None
        for page in self.paginator.pages:
            if not rd:
                await destination.send("\n".join(page))
                continue
            cur = None
            fields = {None: []}
            for line in page:
                if re.match(r"#{2} .+", line):
                    title = line[3:]
                    cur = None
                    fields[cur] = []
                elif re.match(r"# .+", line):
                    cur = line[2:]
                    fields[cur] = []
                elif re.match(r"<f> .+", line):
                    pass
                elif re.match(r"<a> .+", line):
                    pass
                elif re.match(r"<i> .+", line):
                    image = line[4:]
                elif re.match(r"<t> .+", line):
                    thumbnail = line[4:]
                elif re.match(r"<d>", line):
                    cur = None
                elif re.match(r"<v>", line):
                    video = line[4:]
                else:
                    fields[cur].append(line)

            embed = discord.Embed(
                title=title or self.context.bot.user.name,
                colour=self.colour,
                description="\n".join(fields[None]) if fields[None] else None,
                video=str(video) if video is not None else None,
                image=str(image) if image is not None else None,
                thumbnail=str(thumbnail) if thumbnail is not None else None
            )
            not footer or embed.set_footer(text=str(footer))
            not author or embed.set_author(name=str(author))
            not image or embed.set_image(url=str(image))
            not thumbnail or embed.set_thumbnail(url=str(thumbnail))
            for field, lines in fields.items():
                if field is not None:
                    embed.add_field(name=field, value="\n".join(lines) or "||Нет описания||",
                                    inline=False)
            await destination.send(embed=embed)
