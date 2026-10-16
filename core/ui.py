import discord

class Pages(discord.ui.View):
    def __init__(self, title, lines, page_size=7):
        super().__init__(timeout=180)
        self.title, self.lines, self.page_size, self.page = title, lines, page_size, 0

    def embed(self):
        start = self.page*self.page_size
        embed = discord.Embed(title=self.title, description="\n".join(self.lines[start:start+self.page_size]) or "No records.")
        embed.set_footer(text=f"Page {self.page+1}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0,self.page-1)
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(max(0,(len(self.lines)-1)//self.page_size),self.page+1)
        await interaction.response.edit_message(embed=self.embed(), view=self)
