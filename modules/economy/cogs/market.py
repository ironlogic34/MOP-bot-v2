"""Global marketplace, isolated listing administration."""
import discord
from discord import app_commands
from discord.ext import commands
from shared.ui.pagination import Paginator
from shared.validators.text import normalized_product_name

class Market(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(description="Browse global MOP marketplace listings.")
    async def market(self,interaction:discord.Interaction,search:str|None=None):
        if search:
            term=search.strip().casefold().replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
            rows=await self.bot.storage.rows("SELECT * FROM market_items WHERE active=1 AND normalized_name LIKE ? ESCAPE '\\' ORDER BY id LIMIT 100",("%"+term+"%",))
        else:
            rows=await self.bot.storage.rows("SELECT * FROM market_items WHERE active=1 ORDER BY id LIMIT 100")
        lines=[f"**#{r['id']} {discord.utils.escape_markdown(r['name'])}** | {r['price']} Points | Stock: {r['stock']} | Server: {r['guild_id']}" for r in rows]
        view=Paginator("Global MOP Market",lines,owner_id=interaction.user.id,page_size=7)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

    @app_commands.command(description="Publish an item in the global marketplace (server owner only).")
    @app_commands.guild_only()
    async def additem(self,interaction:discord.Interaction,name:app_commands.Range[str,2,70],price:app_commands.Range[int,1,100000000],stock:app_commands.Range[int,1,100000],description:app_commands.Range[str,1,500]):
        if interaction.user.id!=interaction.guild.owner_id:
            raise app_commands.CheckFailure("Only the server owner can publish listings.")
        normalized=normalized_product_name(name)
        try:
            ident=await self.bot.storage.execute("INSERT INTO market_items(guild_id,owner_id,name,normalized_name,description,price,stock) VALUES(?,?,?,?,?,?,?)",
              (interaction.guild_id,interaction.user.id,name.strip(),normalized,description,price,stock))
        except Exception as exc:
            import aiosqlite
            if isinstance(exc,aiosqlite.IntegrityError):
                await interaction.response.send_message("That product name is already taken globally.",ephemeral=True)
                return
            raise
        await interaction.response.send_message(f"Created global item #{ident}.",ephemeral=True)
        try:
            await interaction.user.send(f"Your MOP marketplace item #{ident} ({name}) was created.")
        except discord.HTTPException:
            pass

    @app_commands.command(description="Purchase an available market item.")
    async def buy(self,interaction:discord.Interaction,item_id:int,quantity:app_commands.Range[int,1,100]=1):
        try:
            cost=await self.bot.ledger.buy(interaction.user.id,item_id,quantity)
            await interaction.response.send_message(f"Purchased {quantity} × item #{item_id} for {cost} Points.",ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)

    @app_commands.command(description="Sell an owned item back for 75% of what you originally paid.")
    async def sell(self,interaction:discord.Interaction,item_id:int,quantity:app_commands.Range[int,1,100]=1):
        try:
            payout=await self.bot.ledger.sell(interaction.user.id,item_id,quantity)
            await interaction.response.send_message(f"Sold {quantity} × item #{item_id} for {payout} Points.",ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)

    @app_commands.command(description="Show your globally owned market items.")
    async def inventory(self,interaction:discord.Interaction):
        rows=await self.bot.storage.rows("SELECT i.item_id,i.quantity,m.name FROM inventory i JOIN market_items m ON m.id=i.item_id WHERE i.user_id=? AND i.quantity>0 ORDER BY i.item_id",(interaction.user.id,))
        view=Paginator("Your inventory",[f"#{r['item_id']} {r['name']} × {r['quantity']}" for r in rows],owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)


    @app_commands.command(description="Edit or deactivate a marketplace listing you own.")
    @app_commands.guild_only()
    async def edititem(self, interaction:discord.Interaction, item_id:int, price:app_commands.Range[int,1,100000000]|None=None, stock:app_commands.Range[int,0,100000]|None=None, active:bool|None=None, description:app_commands.Range[str,1,500]|None=None):
        rows=await self.bot.storage.rows("SELECT owner_id,guild_id FROM market_items WHERE id=?",(item_id,))
        if not rows or rows[0]["owner_id"]!=interaction.user.id or rows[0]["guild_id"]!=interaction.guild_id or interaction.user.id!=interaction.guild.owner_id:
            raise app_commands.CheckFailure("Only the original listing owner, while still this server's owner, can manage this listing.")
        changes={"price":price,"stock":stock,"active":int(active) if active is not None else None,"description":description}
        selected={key:value for key,value in changes.items() if value is not None}
        if not selected:
            await interaction.response.send_message("Supply at least one field to change.",ephemeral=True)
            return
        columns=", ".join(f"{key}=?" for key in selected)
        await self.bot.storage.execute(f"UPDATE market_items SET {columns} WHERE id=? AND owner_id=? AND guild_id=?",(*selected.values(),item_id,interaction.user.id,interaction.guild_id))
        await interaction.response.send_message(f"Updated item #{item_id}.",ephemeral=True)

    @app_commands.command(description="View the listings you published in this server.")
    @app_commands.guild_only()
    async def myitems(self, interaction:discord.Interaction):
        rows=await self.bot.storage.rows("SELECT id,name,price,stock,active FROM market_items WHERE owner_id=? AND guild_id=? ORDER BY id DESC LIMIT 100",(interaction.user.id,interaction.guild_id))
        lines=[f"#{r['id']} {discord.utils.escape_markdown(r['name'])}: {r['price']} Points, {r['stock']} stock, {'active' if r['active'] else 'inactive'}" for r in rows]
        view=Paginator("My marketplace listings",lines,owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

async def setup(bot):
    await bot.add_cog(Market(bot))
