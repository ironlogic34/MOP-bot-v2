"""Shared message activity for levels, rankcards and future autoroles."""
import discord
from io import BytesIO
from PIL import Image, ImageDraw
from discord import app_commands
from discord.ext import commands

THRESHOLDS = [40,60,90,120,150,180,210,240,290,340,390,490,590,690,790,1580,3160]

def level_for_words(words):
    level = 0
    required = 0
    while True:
        step = THRESHOLDS[level] if level < len(THRESHOLDS) else THRESHOLDS[-1] * (2**(level-len(THRESHOLDS)+1))
        if words < required+step:
            return level, words-required, step
        required += step
        level += 1

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return
        words = len(message.content.split())
        if not words or words > 500:
            return
        await self.bot.storage.execute("""INSERT INTO activity(guild_id,user_id,words,messages) VALUES(?,?,?,1)
            ON CONFLICT(guild_id,user_id) DO UPDATE SET words=words+excluded.words,messages=messages+1""",
            (message.guild.id,message.author.id,words))

    @app_commands.command(description="View a member's recorded word-based level.")
    @app_commands.guild_only()
    async def level(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        rows = await self.bot.storage.rows("SELECT words FROM activity WHERE guild_id=? AND user_id=?",(interaction.guild_id,member.id))
        lvl,progress,required = level_for_words(rows[0]["words"] if rows else 0)
        await interaction.response.send_message(f"{member.mention}: Level {lvl} • {progress}/{required} words toward next level.",ephemeral=True)

    @app_commands.command(description="View a member's level progress (text preview).")
    @app_commands.guild_only()
    async def rankcard(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        rows = await self.bot.storage.rows("SELECT words FROM activity WHERE guild_id=? AND user_id=?",(interaction.guild_id,member.id))
        lvl,progress,required = level_for_words(rows[0]["words"] if rows else 0)
        image = Image.new("RGB", (800, 240), (28, 35, 53))
        draw = ImageDraw.Draw(image)
        draw.text((40, 35), member.display_name[:50], fill="white")
        draw.text((40, 80), f"Level {lvl} | {progress:,}/{required:,} words", fill="white")
        draw.rounded_rectangle((40, 135, 760, 170), radius=12, fill=(65, 72, 92))
        filled = round(720 * max(0, min(1, progress / max(1, required))))
        if filled:
            draw.rounded_rectangle((40, 135, 40 + max(12, filled), 170), radius=12, fill=(95, 150, 245))
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        await interaction.response.send_message(file=discord.File(output, filename="rankcard.png"), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
