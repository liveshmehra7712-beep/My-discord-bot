import os
import sys
import json
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

import discord
from discord.ext import commands, tasks

# -------------------------------------------------------------------
# 1. FLASK WEB SERVER (Render Keep-Alive Endpoint)
# -------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: 24/7 Engine Operational!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# -------------------------------------------------------------------
# 2. PERSISTENT SQLITE DATABASE ENGINE
# -------------------------------------------------------------------
DB_FILE = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Warnings table
    cursor.execute('''CREATE TABLE IF NOT EXISTS warnings 
                      (guild_id INTEGER, user_id INTEGER, reason TEXT, case_id INTEGER PRIMARY KEY AUTOINCREMENT)''')
    # Config table
    cursor.execute('''CREATE TABLE IF NOT EXISTS guild_config 
                      (guild_id INTEGER PRIMARY KEY, prefix TEXT, log_channel INTEGER, welcome_channel INTEGER, autorole_id INTEGER)''')
    # AFK table
    cursor.execute('''CREATE TABLE IF NOT EXISTS afk_users 
                      (user_id INTEGER PRIMARY KEY, reason TEXT)''')
    # Leveling table
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_levels 
                      (guild_id INTEGER, user_id INTEGER, xp INTEGER, level INTEGER, PRIMARY KEY (guild_id, user_id))''')
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------------
# 3. DISCORD BOT INSTANCE & INTENTS
# -------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)
bot_start_time = datetime.utcnow()

# Human Conversational Dictionary Matrix (Real Human Style Responses)
HUMAN_CHAT_PATTERNS = {
    "kya kar raha h": ["Kuch nahi yaar, bas aise hi betha hu. Tum batao?", "Kuch khas nahi, bas chill kar raha hu. Tum batao kya chal raha hai?"],
    "kya kar rhe ho": ["Kuch nahi, bas free betha hu. Tum kya kar rahe ho?", "Sab shanti hai bro, tum batao?"],
    "kya kar rha h": ["Sofa pe pada hu, bore ho raha hu. Tum batao?", "Kuch nahi bhai, bas tumhare message ka wait kar raha tha."],
    "chal rha h": ["Kahan chal raha hai bhai? Frame me hi hu!", "Khade khade thak gaya hu, chalne ki taqat nahi hai."],
    "chal raha h": ["Kahan jana hai bolo? Main toh idhar hi hu!", "Sab badhiya chal raha hai, tum apna sunao!"],
    "hi": ["Hey! Kaise ho?", "Hello boss! Kya haal chal?"],
    "hello": ["Hey there! Kaise ho?", "Yo! Kya chal raha hai?"],
    "kaise ho": ["Ekdum mast! Tum batao, sab sahi?", "Main badhiya hu bro, tum sunao!"],
    "sahi h": ["Haan bhai, bilkul sahi!", "Arey ekdum badhiya!"],
}

# Active mid-chat session tracking: {channel_id: expire_timestamp}
mid_active_channels = {}

# -------------------------------------------------------------------
# 4. CORE ENGINE & ANTI-CRASH EVENT HANDLERS
# -------------------------------------------------------------------
@bot.event
async def on_ready():
    print(f"✅ [CORE ENGINE] Logged in as: {bot.user} (ID: {bot.user.id})")
    print(f"✅ [DATABASE] SQLite engine verified & persistent storage active.")
    await bot.change_presence(activity=discord.Game(name="$help | Type 'MID' for Human AI Chat"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    ctx = await bot.get_context(message)

    # 1. AFK Status Check
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT reason FROM afk_users WHERE user_id = ?", (message.author.id,))
    afk_row = c.fetchone()
    if afk_row:
        c.execute("DELETE FROM afk_users WHERE user_id = ?", (message.author.id,))
        conn.commit()
        await message.channel.send(f"Welcome back {message.author.mention}! Your AFK status has been removed.", delete_after=5)

    for mention in message.mentions:
        c.execute("SELECT reason FROM afk_users WHERE user_id = ?", (mention.id,))
        row = c.fetchone()
        if row:
            await message.channel.send(f"⚠️ **{mention.name}** is currently AFK: `{row[0]}`")
    conn.close()

    # 2. 'MID' Conversational AI Chat Trigger & Handler
    msg_clean = message.content.strip()
    
    if msg_clean.upper() == "MID":
        mid_active_channels[message.channel.id] = datetime.utcnow() + timedelta(minutes=10)
        await message.channel.send("Yo! Human AI Chat mode activated in this channel for 10 minutes. Aao baat karte hain! What's up?")
        return

    # Process AI Chat if channel is in active MID session & message is not a command
    if message.channel.id in mid_active_channels and not message.content.startswith("$"):
        if datetime.utcnow() < mid_active_channels[message.channel.id]:
            user_text = msg_clean.lower()
            matched = False
            for pattern, responses in HUMAN_CHAT_PATTERNS.items():
                if pattern in user_text:
                    await message.channel.send(random.choice(responses))
                    matched = True
                    break
            if not matched:
                default_replies = [
                    "Acha? Phir kya hua?",
                    "Haha sahi hai boss!",
                    "Waah! Aur batao naya purana?",
                    "Hmm samajh gaya, aur kya chal raha hai aajkal?",
                    "Sahi hai yaar, life me chill maaro!"
                ]
                await message.channel.send(random.choice(default_replies))
            return
        else:
            del mid_active_channels[message.channel.id]

    # 3. Leveling / XP System Process
    if not message.content.startswith("$"):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT xp, level FROM user_levels WHERE guild_id=? AND user_id=?", (message.guild.id, message.author.id))
        res = c.fetchone()
        if res:
            xp, lvl = res[0] + random.randint(5, 15), res[1]
            next_lvl = lvl * 100
            if xp >= next_lvl:
                lvl += 1
                await message.channel.send(f"🎉 Congratulations {message.author.mention}, you reached **Level {lvl}**!")
            c.execute("UPDATE user_levels SET xp=?, level=? WHERE guild_id=? AND user_id=?", (xp, lvl, message.guild.id, message.author.id))
        else:
            c.execute("INSERT INTO user_levels VALUES (?, ?, ?, ?)", (message.guild.id, message.author.id, 10, 1))
        conn.commit()
        conn.close()

    await bot.process_commands(message)

# -------------------------------------------------------------------
# 5. ERROR HANDLING & PERMISSION GATEWAYS
# -------------------------------------------------------------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="⛔ Access Denied",
            description="You do not have the required Administrator / Moderator permissions to execute this command.",
            color=0xFF0000
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.NotOwner):
        await ctx.send("❌ This command can only be executed by the Bot Owner.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing Argument! Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown active! Try again in **{round(error.retry_after, 1)}s**.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Unhandled Exception in command {ctx.command}: {error}")

# -------------------------------------------------------------------
# 6. ADVANCED MODERATION & SECURITY COMMANDS
# -------------------------------------------------------------------
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """Permanently bans a server member"""
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send("❌ You cannot ban a user with an equal or higher role hierarchy!")
    
    await member.ban(reason=reason)
    embed = discord.Embed(
        title="🔨 Member Banned",
        description=f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
        color=0xFF0000,
        timestamp=datetime.utcnow()
    )
    await ctx.send(embed=embed)

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason="No reason provided"):
    """Unbans a user by User ID"""
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(f"✅ Successfully unbanned **{user.name}**.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kicks a member from the server"""
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send("❌ Role hierarchy protection: Cannot kick this user!")
    
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked **{member.name}** | Reason: `{reason}`")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    """Timeouts a member temporarily"""
    if member.top_role >= ctx.author.top_role:
        return await ctx.send("❌ Cannot timeout a member with higher/equal role hierarchy.")
    
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f"🔇 Timed out **{member.name}** for `{minutes}` minutes. Reason: `{reason}`")

@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    """Removes timeout from a member"""
    await member.timeout(None)
    await ctx.send(f"🔊 Removed timeout for **{member.name}**.")

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    """Gives a recorded moderation warning"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO warnings (guild_id, user_id, reason) VALUES (?, ?, ?)", (ctx.guild.id, member.id, reason))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    total_warns = c.fetchone()[0]
    conn.close()
    
    await ctx.send(f"⚠️ Warned **{member.mention}** | Total Warnings: `{total_warns}` | Reason: `{reason}`")

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member = None):
    """Lists member warnings"""
    member = member or ctx.author
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT case_id, reason FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return await ctx.send(f"✅ **{member.name}** has no active warnings.")
    
    description = "\n".join([f"• **Case #{row[0]}**: {row[1]}" for row in rows])
    embed = discord.Embed(title=f"Warnings for {member.name}", description=description, color=0xFFA500)
    await ctx.send(embed=embed)

@bot.command(name="clear", aliases=["purge"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    """Deletes recent channel messages"""
    if amount < 1 or amount > 100:
        return await ctx.send("⚠️ Specify a limit between 1 and 100.")
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Purged `{len(deleted)-1}` messages.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    """Sets channel slowmode delay"""
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Channel slowmode set to `{seconds}` seconds.")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Locks the current channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Unlocks the current channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked.")

# -------------------------------------------------------------------
# 7. UTILITY & INFORMATION COMMANDS
# -------------------------------------------------------------------
@bot.command(name="ping")
async def ping(ctx):
    """Shows API latency"""
    await ctx.send(f"🏓 Pong! Latency: **{round(bot.latency * 1000)}ms**")

@bot.command(name="botinfo")
async def botinfo(ctx):
    """Shows bot technical details"""
    uptime = datetime.utcnow() - bot_start_time
    embed = discord.Embed(title="🤖 Bot Technical Specs", color=discord.Color.blue())
    embed.add_field(name="Uptime", value=f"`{str(uptime).split('.')[0]}`", inline=True)
    embed.add_field(name="Guilds", value=f"`{len(bot.guilds)}`", inline=True)
    embed.add_field(name="Latency", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
    embed.add_field(name="Python Version", value=f"`{sys.version.split()[0]}`", inline=True)
    embed.add_field(name="Library", value="`discord.py v2.4.0`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    """Shows user details"""
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed = discord.Embed(title=f"User Info - {member.name}", color=discord.Color.green())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="Joined Server", value=f"`{member.joined_at.strftime('%Y-%m-%d')}`", inline=True)
    embed.add_field(name="Account Created", value=f"`{member.created_at.strftime('%Y-%m-%d')}`", inline=True)
    embed.add_field(name=f"Roles [{len(roles)}]", value=", ".join(roles) if roles else "None", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    """Shows server info"""
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.purple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="Owner", value=f"{guild.owner.mention if guild.owner else 'N/A'}", inline=True)
    embed.add_field(name="Total Members", value=f"`{guild.member_count}`", inline=True)
    embed.add_field(name="Channels", value=f"`{len(guild.channels)}`", inline=True)
    embed.add_field(name="Roles", value=f"`{len(guild.roles)}`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    """Views user avatar"""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="afk")
async def afk(ctx, *, reason="AFK"):
    """Sets user AFK status"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO afk_users VALUES (?, ?)", (ctx.author.id, reason))
    conn.commit()
    conn.close()
    await ctx.send(f"💤 {ctx.author.mention}, your AFK status is set: `{reason}`")

@bot.command(name="choose")
async def choose(ctx, *options):
    """Chooses from multiple options"""
    if len(options) < 2:
        return await ctx.send("⚠️ Provide at least 2 options! Usage: `$choose option1 option2`")
    await ctx.send(f"🎲 I choose: **{random.choice(options)}**")

@bot.command(name="roll")
async def roll(ctx, limit: int = 100):
    """Rolls a random number"""
    await ctx.send(f"🎲 You rolled: **{random.randint(1, limit)}** (1-{limit})")

@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    """Shows level rank and XP"""
    member = member or ctx.author
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT xp, level FROM user_levels WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    res = c.fetchone()
    conn.close()
    
    if not res:
        return await ctx.send(f"📊 {member.mention} has not earned any XP yet.")
    
    xp, lvl = res
    await ctx.send(f"📊 **{member.name}** | Level: `{lvl}` | XP: `{xp}/{lvl*100}`")

# -------------------------------------------------------------------
# 8. MASTER HELP SYSTEM
# -------------------------------------------------------------------
@bot.command(name="help")
async def help_command(ctx):
    """Displays bot command manual"""
    embed = discord.Embed(
        title="📚 Discord Engine - Complete Command Suite",
        description="Default Prefix: `$` | Type **`MID`** anytime in chat to trigger Human Conversational Mode!",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🛠️ Moderation & Management",
        value="`$ban`, `$unban`, `$kick`, `$timeout`, `$untimeout`, `$warn`, `$warnings`, `$clear`, `$slowmode`, `$lock`, `$unlock`",
        inline=False
    )
    embed.add_field(
        name="📊 Utility & System Info",
        value="`$ping`, `$botinfo`, `$userinfo`, `$serverinfo`, `$avatar`, `$rank`",
        inline=False
    )
    embed.add_field(
        name="🎉 Member & Fun Commands",
        value="`$afk`, `$choose`, `$roll`, `MID` *(Human AI Mode)*",
        inline=False
    )
    embed.set_footer(text="Anti-Crash Protection Active | SQLite Database Engine Connected")
    await ctx.send(embed=embed)

# -------------------------------------------------------------------
# 9. SHUTDOWN & OWNER CONTROL
# -------------------------------------------------------------------
@bot.command(name="restart")
@commands.is_owner()
async def restart(ctx):
    """Safely restarts the bot (Owner Only)"""
    await ctx.send("🔄 Restarting bot engine gracefully...")
    os.execv(sys.executable, ['python'] + sys.argv)

# -------------------------------------------------------------------
# 10. MAIN ENTRY POINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ CRITICAL ERROR: 'DISCORD_TOKEN' Environment Variable is missing in Render!")
        sys.exit(1)

    bot.run(TOKEN)
