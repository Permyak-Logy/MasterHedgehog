from discord.ext import commands


class Paginator(commands.Paginator):
    # noinspection PyAttributeOutsideInit,PyAttributeOutsideInit
    def close_page(self):
        """Prematurely terminate a page."""
        if self.suffix is not None:
            self._current_page.append(self.suffix)
        self._pages.append(self._current_page)

        if self.prefix is not None:
            self._current_page = [self.prefix]
            self._count = len(self.prefix) + 1  # prefix + newline
        else:
            self._current_page = []
            self._count = 0
