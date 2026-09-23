import os
import sys
import asyncio
from datetime import datetime
from flask import Flask
from threading import Thread

import discord
from discord.ext import commands

# -------------------------------------------------------------------
# 1. FLASK WEB SERVER (For Render Web Service Hosting)
# -------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running fine!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# -------------------------------------------------------------------
# 2. DISCORD BOT SETUP
# -------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

logs_db = {}  # In-memory channel log database

# -------------------------------------------------------------------
# 3. HELPER & UTILITY FUNCTIONS
# -------------------------------------------------------------------
async def log_abuse(guild, message_text, author, reason="Abuse / DM Command Usage"):
    if guild and guild.id in logs_db:
        log_ch = guild.get_channel(logs_db[guild.id])
        if log_ch:
            emb = discord.Embed(
                title="🚨 Security / Abuse Log Alert",
                description=f"**User:** {author.mention} (`{author.id}`)\n**Reason:** {reason}\n**Content:** {message_text}",
                color=0xFF0000,
                timestamp=datetime.utcnow()
            )
            try:
                await log_ch.send(embed=emb)
            except Exception:
                pass

# -------------------------------------------------------------------
# 4. BOT EVENTS
# -------------------------------------------------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot is online! Logged in as: {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game(name="!help | Managing Server"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Aapke paas is command ko use karne ki **Administrator** permission nahi hai!",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="⚠️ Missing Arguments",
            description=f"Sahi format: `{ctx.prefix}{ctx.command.signature}`",
            color=0xFFA500
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        pass  # Unknown commands ignore karne ke liye
    else:
        print(f"Error executing command '{ctx.command}': {error}")

# -------------------------------------------------------------------
# 5. MEMBER COMMANDS (SABHI USERS KE LIYE)
# -------------------------------------------------------------------
@bot.command(name="ping")
async def ping(ctx):
    """Latency check karne ke liye"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: **{latency}ms**")

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    """User ki details dekhne ke liye"""
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    
    embed = discord.Embed(
        title=f"User Info - {member.name}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="User ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name=f"Roles [{len(roles)}]", value=", ".join(roles) if roles else "None", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    """Server ki jankari ke liye"""
    guild = ctx.guild
    embed = discord.Embed(
        title=f"Server Info - {guild.name}",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "N/A", inline=True)
    embed.add_field(name="Total Members", value=guild.member_count, inline=True)
    embed.add_field(name="Text Channels", value=len(guild.text_channels), inline=True)
    embed.add_field(name="Voice Channels", value=len(guild.voice_channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """User avatar download/view karne ke liye"""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=discord.Color.purple())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="help")
async def help_command(ctx):
    """General help menu"""
    embed = discord.Embed(
        title="📚 Bot Commands List",
        description="Aapke server ke liye sabhi commands niche hain:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="👤 Member Commands",
        value="`!ping` - Check latency\n`!userinfo` - Get user details\n`!serverinfo` - Get server details\n`!avatar` - View avatar",
        inline=False
    )
    embed.add_field(
        name="🛡️ Admin Commands (Requires Administrator)",
        value="`!kick` - Kick member\n`!ban` - Ban member\n`!clear` - Delete messages\n`!setlogchannel` - Set security logs channel",
        inline=False
    )
    await ctx.send(embed=embed)

# -------------------------------------------------------------------
# 6. ADMIN COMMANDS (ONLY FOR ADMINISTRATORS)
# -------------------------------------------------------------------
@bot.command(name="kick")
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    """Member ko server se kick karne ke liye"""
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ Aap apne se barabar ya higher role wale ko kick nahi kar sakte.")
    
    await member.kick(reason=reason)
    embed = discord.Embed(
        title="👢 Member Kicked",
        description=f"**User:** {member.mention}\n**Kicked By:** {ctx.author.mention}\n**Reason:** {reason}",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command(name="ban")
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """Member ko server se ban karne ke liye"""
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ Aap apne se barabar ya higher role wale ko ban nahi kar sakte.")
    
    await member.ban(reason=reason)
    embed = discord.Embed(
        title="🔨 Member Banned",
        description=f"**User:** {member.mention}\n**Banned By:** {ctx.author.mention}\n**Reason:** {reason}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name="clear")
@commands.has_permissions(administrator=True)
async def clear(ctx, amount: int = 5):
    """Messages bulk delete karne ke liye"""
    if amount < 1 or amount > 100:
        return await ctx.send("⚠️ Kripya 1 se 100 ke beech ka number dein.")
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 `{len(deleted)-1}` messages delete kar diye gaye hain.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="setlogchannel")
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel):
    """Log channel set karne ke liye"""
    logs_db[ctx.guild.id] = channel.id
    embed = discord.Embed(
        title="✅ Log Channel Set",
        description=f"Security/Abuse logs ab {channel.mention} me bheje jayenge.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# -------------------------------------------------------------------
# 7. MAIN EXECUTION ENTRY POINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Start web server for 24/7 uptime monitoring
    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN environment variable me missing hai!")
        sys.exit(1)

    bot.run(TOKEN)
