"""Create a simple animated GIF from two uploaded image frames."""
import asyncio
from io import BytesIO
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, UnidentifiedImageError

def make_gif(first,second):
    images=[]
    for raw in (first,second):
        img=Image.open(BytesIO(raw))
        if img.width*img.height>12_000_000:
            raise ValueError("Image resolution is too large.")
        img.thumbnail((720,720))
        images.append(img.convert("RGBA"))
    out=BytesIO()
    images[0].save(out,format="GIF",save_all=True,append_images=[images[1]],duration=600,loop=0)
    out.seek(0)
    return out

class Conversion(commands.Cog):
    @app_commands.command(description="Combine two image attachments into a looping GIF.")
    async def img2gif(self,interaction:discord.Interaction,first:discord.Attachment,second:discord.Attachment):
        if first.size>8_000_000 or second.size>8_000_000:
            await interaction.response.send_message("Each image must be under 8 MB.",ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            result=await asyncio.to_thread(make_gif,await first.read(),await second.read())
        except (ValueError,UnidentifiedImageError,OSError):
            await interaction.followup.send("Both attachments must be valid images of reasonable size.",ephemeral=True)
            return
        await interaction.followup.send(file=discord.File(result,filename="mop.gif"),ephemeral=True)

async def setup(bot):
    await bot.add_cog(Conversion())
