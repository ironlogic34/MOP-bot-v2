"""Member preferences and per-guild role automation."""
from datetime import datetime,timezone
import discord
from discord import app_commands
from discord.ext import commands
from modules.server_management.services.member_rules import record_opt_out,get_opt_out,delete_opt_out
from shared.validators.text import bounded_text

class MemberRules(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(description="Set or view your global MOP alias (48-hour cooldown).")
    async def alias(self,interaction:discord.Interaction,name:app_commands.Range[str,2,32]|None=None):
        rows=await self.bot.storage.rows("SELECT alias,updated_at FROM user_aliases WHERE user_id=?",(interaction.user.id,))
        if name is None:
            await interaction.response.send_message(f"Alias: {rows[0]['alias']}" if rows else "No alias configured.",ephemeral=True)
            return
        name=bounded_text(name,min_length=2,max_length=32,label="Alias")
        now=datetime.now(timezone.utc)
        if rows and (now-datetime.fromisoformat(rows[0]["updated_at"])).total_seconds()<172800:
            await interaction.response.send_message("You can change your alias once every 48 hours.",ephemeral=True)
            return
        await self.bot.storage.execute("INSERT INTO user_aliases(user_id,alias,updated_at) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET alias=excluded.alias,updated_at=excluded.updated_at",(interaction.user.id,name,now.isoformat()))
        await self.bot.storage.execute("INSERT INTO alias_history(user_id,alias) VALUES(?,?)",(interaction.user.id,name))
        await interaction.response.send_message(f"Your MOP alias is now {discord.utils.escape_markdown(name)}.",ephemeral=True)

    @app_commands.command(description="Configure automatic roles for new or active members.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.choices(rule=[
        app_commands.Choice(name="On join",value="join"),
        app_commands.Choice(name="Messages",value="messages"),
        app_commands.Choice(name="Words",value="words"),
        app_commands.Choice(name="Tenure days",value="tenure_days")
    ])
    async def autorole(self,interaction:discord.Interaction,role:discord.Role,rule:app_commands.Choice[str],threshold:app_commands.Range[int,0,1000000]=0,enabled:bool=True):
        if role.is_default() or role.managed or role>=interaction.guild.me.top_role or (interaction.user.id!=interaction.guild.owner_id and role>=interaction.user.top_role):
            raise app_commands.CheckFailure("This role cannot be assigned by MOP.")
        if enabled:
            await self.bot.storage.execute("INSERT INTO autorole_rules(guild_id,role_id,rule,threshold) VALUES(?,?,?,?) ON CONFLICT(guild_id,role_id,rule) DO UPDATE SET threshold=excluded.threshold",(interaction.guild_id,role.id,rule.value,threshold))
        else:
            await self.bot.storage.execute("DELETE FROM autorole_rules WHERE guild_id=? AND role_id=? AND rule=?",(interaction.guild_id,role.id,rule.value))
        await interaction.response.send_message("Autorole rule updated.",ephemeral=True)

    @app_commands.command(description="Opt out of writing in a channel until you restore access.")
    @app_commands.guild_only()
    async def leave(self,interaction:discord.Interaction,channel:discord.TextChannel|None=None,restore:bool=False):
        channel=channel or interaction.channel
        if not isinstance(channel,discord.TextChannel):
            raise app_commands.CheckFailure("Text channel required.")
        if not channel.permissions_for(interaction.guild.me).manage_roles:
            raise app_commands.CheckFailure("MOP needs Manage Roles in this channel.")
        storage=self.bot.storage
        overwrite=channel.overwrites_for(interaction.user)
        if not restore:
            if not await record_opt_out(storage,interaction.guild_id,channel.id,interaction.user.id,overwrite.send_messages):
                await interaction.response.send_message("You already opted out of this channel. Use /leave restore:true to return.",ephemeral=True)
                return
            overwrite.send_messages=False
            try:
                await channel.set_permissions(interaction.user,overwrite=overwrite,reason="Voluntary channel writing restriction")
            except discord.HTTPException:
                await delete_opt_out(storage,interaction.guild_id,channel.id,interaction.user.id)
                raise
            await interaction.response.send_message("You opted out of writing in this channel. Use /leave restore:true to return.",ephemeral=True)
            return
        found,original=await get_opt_out(storage,interaction.guild_id,channel.id,interaction.user.id)
        if not found:
            await interaction.response.send_message("Nothing to restore: MOP has no opt-out recorded for you in this channel. If staff restricted you, ask them to lift it.",ephemeral=True)
            return
        overwrite.send_messages=original
        await channel.set_permissions(interaction.user,overwrite=None if overwrite.is_empty() else overwrite,reason="Voluntary channel opt-out ended")
        await delete_opt_out(storage,interaction.guild_id,channel.id,interaction.user.id)
        await interaction.response.send_message("Your previous writing permission in this channel has been restored.",ephemeral=True)

    @app_commands.command(description="Show members Discord currently reports as streaming.")
    @app_commands.guild_only()
    async def live(self,interaction:discord.Interaction):
        members=[m for m in interaction.guild.members if any(isinstance(a,discord.Streaming) for a in m.activities)]
        await interaction.response.send_message("\n".join(m.mention for m in members[:30]) or "No visible streaming activities. Discord Go Live is not reliably exposed.",ephemeral=True)

    @app_commands.command(description="Set this server's preferred language tag.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def language(self,interaction:discord.Interaction,code:app_commands.Range[str,2,12]):
        if not all(c.isascii() and (c.isalpha() or c=="-") for c in code):
            await interaction.response.send_message("Use a language tag such as en, hi, or en-US.",ephemeral=True)
            return
        await self.bot.storage.set_setting(interaction.guild_id,"language",code.lower())
        await interaction.response.send_message(f"Preferred language: {code.lower()}. Automatic translation is not available yet.",ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self,member):
        rows=await self.bot.storage.rows("SELECT role_id FROM autorole_rules WHERE guild_id=? AND rule='join'",(member.guild.id,))
        for row in rows:
            role=member.guild.get_role(row["role_id"])
            if role and not role.managed and role<member.guild.me.top_role:
                try:
                    await member.add_roles(role,reason="MOP join autorole")
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.guild or message.author.bot or not isinstance(message.author,discord.Member):
            return
        rows=await self.bot.storage.rows("SELECT role_id,rule,threshold FROM autorole_rules WHERE guild_id=? AND rule IN ('messages','words','tenure_days')",(message.guild.id,))
        if not rows:
            return
        activity=await self.bot.storage.rows("SELECT words,messages FROM activity WHERE guild_id=? AND user_id=?",(message.guild.id,message.author.id))
        words=activity[0]["words"] if activity else 0
        messages=activity[0]["messages"] if activity else 0
        tenure=(datetime.now(timezone.utc)-message.author.joined_at).days if message.author.joined_at else 0
        values={"messages":messages,"words":words,"tenure_days":tenure}
        for row in rows:
            role=message.guild.get_role(row["role_id"])
            if role and role not in message.author.roles and role<message.guild.me.top_role and values[row["rule"]]>=row["threshold"]:
                try:
                    await message.author.add_roles(role,reason="MOP activity autorole")
                except discord.HTTPException:
                    pass

async def setup(bot):
    await bot.add_cog(MemberRules(bot))
