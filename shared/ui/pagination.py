"""Paginated embeds with interaction ownership checks."""
import math
import discord

class Paginator(discord.ui.View):
    def __init__(self, title: str, lines: list[str], *, owner_id: int, page_size: int = 7, timeout: float = 180):
        super().__init__(timeout=timeout)
        if not 1 <= page_size <= 20:
            raise ValueError("page_size must be between 1 and 20")
        self.title, self.lines, self.owner_id = title, list(lines), owner_id
        self.page_size, self.page = page_size, 0
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page >= self.page_count - 1

    @property
    def page_count(self) -> int:
        return max(1, math.ceil(len(self.lines) / self.page_size))

    def embed(self) -> discord.Embed:
        start = self.page * self.page_size
        embed = discord.Embed(title=self.title, description="\n".join(self.lines[start:start+self.page_size]) or "No records.")
        embed.set_footer(text=f"Page {self.page+1}/{self.page_count}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Open your own copy of this menu.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.page_count - 1, self.page + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
