import logging

from discord.ext import commands
from .bot import Bot, Cog, Context
import discord

logging = logging.getLogger(__name__)


async def can_run(self, ctx: Context):
    """override discord.ext.commands.Command.can_run"""

    if not self.enabled:
        raise commands.DisabledCommand('{0.name} command is disabled'.format(self))

    original = ctx.command
    ctx.command = self

    try:
        if not await ctx.bot.can_run(ctx):
            raise commands.CheckFailure(
                'The global check functions for command {0.qualified_name} failed.'.format(self))

        cog = self.cog
        if cog is not None:
            local_check = Cog._get_overridden_method(cog.cog_check)
            if local_check is not None:
                ret = await discord.utils.maybe_coroutine(local_check, ctx)
                if not ret:
                    return False

        predicates = self.checks
        if not predicates:
            # since we have no checks, then we just return True.
            return True

        # PASTED CODE ===================================================================
        bot: Bot = ctx.bot
        if bot.root_active and ctx.author.id == bot.root_id:
            for predicate in predicates:
                try:
                    predicate = await discord.utils.maybe_coroutine(predicate, ctx)
                    if not predicate:
                        return False
                except commands.MissingPermissions:
                    logging.warning(f"[IGNORE_ERROR] [{ctx}] Ignored error MissingPermissions because active 'sudo su'")
            return True
        # ================================================================================
        return await discord.utils.async_all(predicate(ctx) for predicate in predicates)
    finally:
        ctx.command = original


commands.Command.can_run = can_run
