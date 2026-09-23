import os
import random
import asyncio
import sqlite3
import logging
import threading
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands
from flask import Flask

# ---------------------------------------------------------
# CONFIGURATION & LOGGING
# ---------------------------------------------------------
TOKEN = os.getenv('DISCORD_TOKEN', 'YOUR_DISCORD_BOT_TOKEN_HERE')
DEFAULT_PREFIX = '!'
DB_PATH = os.getenv('DATABASE_PATH', 'bot_data.db')
PORT = int(os.getenv('PORT', '10000'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
log = logging.getLogger('ProBotEngine')

# ---------------------------------------------------------
# DATABASE ENGINE (SQLite WAL Mode)
# ---------------------------------------------------------
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute('PRAGMA journal_mode=WAL')

def init_db():
    with db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '!',
                mod_log_channel INTEGER,
                welcome_channel INTEGER,
                autorole_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                mod_id INTEGER,
                reason TEXT,
                timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS economy (
                guild_id INTEGER,
                user_id INTEGER,
                wallet INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                PRIMARY KEY(guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER,
                user_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                PRIMARY KEY(guild_id, user_id)
            );
        ''')

init_db()

def get_prefix(bot, message):
    if not message.guild:
        return DEFAULT_PREFIX
    cursor = db.cursor()
    cursor.execute('SELECT prefix FROM guild_settings WHERE guild_id = ?', (message.guild.id,))
    row = cursor.fetchone()
    return row['prefix'] if row and row['prefix'] else DEFAULT_PREFIX

# ---------------------------------------------------------
# BOT INITIALIZATION & FLASK KEEP-ALIVE
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None, case_insensitive=True)
bot.db = db

app = Flask(__name__)

@app.route('/')
def health():
    return {"status": "online", "guilds": len(bot.guilds)}, 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# ---------------------------------------------------------
# EVENTS ENGINE
# ---------------------------------------------------------
@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user.name} ({bot.user.id})")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{DEFAULT_PREFIX}help | Pro Engine"))

@bot.event
async def on_member_join(member):
    cursor = db.cursor()
    cursor.execute('SELECT welcome_channel, autorole_id FROM guild_settings WHERE guild_id = ?', (member.guild.id,))
    row = cursor.fetchone()
    if row:
        if row['autorole_id']:
            role = member.guild.get_role(row['autorole_id'])
            if role:
                try:
                    await member.add_roles(role)
                except Exception as e:
                    log.error(f"Auto-role error: {e}")
        if row['welcome_channel']:
            channel = member.guild.get_channel(row['welcome_channel'])
            if channel:
                embed = discord.Embed(
                    title="👋 Welcome to the Server!",
                    description=f"Hey {member.mention}, welcome to **{member.guild.name}**!",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # XP Leveling Logic
    cursor = db.cursor()
    cursor.execute('SELECT xp, level FROM levels WHERE guild_id = ? AND user_id = ?', (message.guild.id, message.author.id))
    row = cursor.fetchone()

    if not row:
        db.execute('INSERT INTO levels (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)', (message.guild.id, message.author.id, 15, 0))
        db.commit()
    else:
        xp, level = row['xp'], row['level']
        new_xp = xp + random.randint(10, 20)
        xp_needed = 100 + (level * 50)
        
        if new_xp >= xp_needed:
            new_level = level + 1
            db.execute('UPDATE levels SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?', (new_xp - xp_needed, new_level, message.guild.id, message.author.id))
            await message.channel.send(f"🎉 {message.author.mention} level up hoke **Level {new_level}** pe pahunch gaye!")
        else:
            db.execute('UPDATE levels SET xp = ? WHERE guild_id = ? AND user_id = ?', (new_xp, message.guild.id, message.author.id))
        db.commit()

    await bot.process_commands(message)

# Helper function for Mod Logs
async def log_action(guild, embed):
    cursor = db.cursor()
    cursor.execute('SELECT mod_log_channel FROM guild_settings WHERE guild_id = ?', (guild.id,))
    row = cursor.fetchone()
    if row and row['mod_log_channel']:
        channel = guild.get_channel(row['mod_log_channel'])
        if channel:
            await channel.send(embed=embed)

# ---------------------------------------------------------
# ADMIN & CONFIGURATION COMMANDS
# ---------------------------------------------------------
@bot.command(name="setprefix", aliases=["prefix"])
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix: str):
    with db:
        db.execute('''
            INSERT INTO guild_settings (guild_id, prefix) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET prefix = excluded.prefix
        ''', (ctx.guild.id, new_prefix))
    await ctx.send(f"✅ Prefix change karke `{new_prefix}` kar diya hai.")

@bot.command(name="setmodlog")
@commands.has_permissions(administrator=True)
async def setmodlog(ctx, channel: discord.TextChannel):
    with db:
        db.execute('''
            INSERT INTO guild_settings (guild_id, mod_log_channel) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET mod_log_channel = excluded.mod_log_channel
        ''', (ctx.guild.id, channel.id))
    await ctx.send(f"📑 Mod logs channel set to {channel.mention}")

@bot.command(name="setautorole")
@commands.has_permissions(administrator=True)
async def setautorole(ctx, role: discord.Role):
    with db:
        db.execute('''
            INSERT INTO guild_settings (guild_id, autorole_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET autorole_id = excluded.autorole_id
        ''', (ctx.guild.id, role.id))
    await ctx.send(f"🎭 Auto-role set to **{role.name}**")

@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    with db:
        db.execute('''
            INSERT INTO guild_settings (guild_id, welcome_channel) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET welcome_channel = excluded.welcome_channel
        ''', (ctx.guild.id, channel.id))
    await ctx.send(f"👋 Welcome channel set to {channel.mention}")

# ---------------------------------------------------------
# MODERATION COMMANDS (CARL & DYNO STYLE)
# ---------------------------------------------------------
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ Apni top role se upar ya barabar wale member ko ban nahi kar sakte!")
    
    await member.ban(reason=reason)
    await ctx.send(f"🔨 **{member}** ko ban kar diya gaya hai. | Reason: {reason}")
    
    embed = discord.Embed(title="Member Banned", color=discord.Color.red())
    embed.add_field(name="User", value=f"{member} ({member.id})")
    embed.add_field(name="Moderator", value=ctx.author.mention)
    embed.add_field(name="Reason", value=reason)
    await log_action(ctx.guild, embed)

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ Apni top role se upar wale ko kick nahi kar sakte!")
    
    await member.kick(reason=reason)
    await ctx.send(f"👢 **{member}** ko kick kar diya. | Reason: {reason}")

@bot.command(name="mute", aliases=["timeout"])
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    try:
        seconds = int(duration[:-1]) * units[duration[-1].lower()]
    except Exception:
        return await ctx.send("❌ Sahi format use karo! Ex: `10s`, `15m`, `1h`, or `1d`")
    
    await member.timeout(timedelta(seconds=seconds), reason=reason)
    await ctx.send(f"🔇 **{member}** ko `{duration}` ke liye mute kar diya. | Reason: {reason}")

@bot.command(name="unmute", aliases=["untimeout"])
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 **{member}** ko unmute kar diya.")

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Cleared `{len(deleted)-1}` messages.", delete_after=3)

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str):
    with db:
        db.execute(
            'INSERT INTO warnings (guild_id, user_id, mod_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)',
            (ctx.guild.id, member.id, ctx.author.id, reason, datetime.now(timezone.utc).isoformat())
        )
    await ctx.send(f"⚠️ **{member}** ko warn diya gaya: {reason}")

@bot.command(name="warnings", aliases=["warns"])
async def warnings(ctx, member: discord.Member = None):
    target = member or ctx.author
    cursor = db.cursor()
    cursor.execute('SELECT reason, timestamp FROM warnings WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, target.id))
    rows = cursor.fetchall()
    
    if not rows:
        return await ctx.send(f"✅ **{target.display_name}** ke paas koi warning nahi hai.")
    
    embed = discord.Embed(title=f"Warnings for {target.display_name}", color=discord.Color.gold())
    for idx, row in enumerate(rows, 1):
        embed.add_field(name=f"Warning #{idx}", value=f"**Reason:** {row['reason']}\n**Date:** {row['timestamp'][:10]}", inline=False)
    await ctx.send(embed=embed)

# ---------------------------------------------------------
# ECONOMY SYSTEM
# ---------------------------------------------------------
def get_eco_acc(guild_id, user_id):
    cursor = db.cursor()
    cursor.execute('SELECT wallet, bank FROM economy WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
    row = cursor.fetchone()
    if not row:
        db.execute('INSERT INTO economy (guild_id, user_id, wallet, bank) VALUES (?, ?, 0, 0)', (guild_id, user_id))
        db.commit()
        return 0, 0
    return row['wallet'], row['bank']

def update_eco_acc(guild_id, user_id, w_delta=0, b_delta=0):
    w, b = get_eco_acc(guild_id, user_id)
    db.execute('UPDATE economy SET wallet = MAX(0, wallet + ?), bank = MAX(0, bank + ?) WHERE guild_id = ? AND user_id = ?', (w_delta, b_delta, guild_id, user_id))
    db.commit()

@bot.command(name="balance", aliases=["bal"])
async def balance(ctx, target: discord.Member = None):
    target = target or ctx.author
    w, b = get_eco_acc(ctx.guild.id, target.id)
    embed = discord.Embed(title=f"💰 Balance - {target.display_name}", color=discord.Color.gold())
    embed.add_field(name="Wallet", value=f"`${w}`")
    embed.add_field(name="Bank", value=f"`${b}`")
    embed.add_field(name="Total", value=f"`${w + b}`")
    await ctx.send(embed=embed)

@bot.command(name="work")
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    earned = random.randint(50, 250)
    update_eco_acc(ctx.guild.id, ctx.author.id, w_delta=earned)
    await ctx.send(f"💼 Aapne kaam karke `${earned}` kamaye!")

@work.error
async def work_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Thoda rest karo! Wapas kaam `{round(error.retry_after / 60)}` mins baad kar sakte ho.")

@bot.command(name="deposit", aliases=["dep"])
async def deposit(ctx, amount: str):
    w, _ = get_eco_acc(ctx.guild.id, ctx.author.id)
    val = w if amount.lower() == "all" else int(amount)
    if val > w or val <= 0:
        return await ctx.send("❌ Valid amount daalo jo wallet me ho!")
    update_eco_acc(ctx.guild.id, ctx.author.id, w_delta=-val, b_delta=val)
    await ctx.send(f"🏦 `${val}` bank me deposit kar diye.")

@bot.command(name="withdraw", aliases=["with"])
async def withdraw(ctx, amount: str):
    _, b = get_eco_acc(ctx.guild.id, ctx.author.id)
    val = b if amount.lower() == "all" else int(amount)
    if val > b or val <= 0:
        return await ctx.send("❌ Bank me utna paisa nahi hai!")
    update_eco_acc(ctx.guild.id, ctx.author.id, w_delta=val, b_delta=-val)
    await ctx.send(f"💵 `${val}` bank se nikal liye.")

# ---------------------------------------------------------
# UTILITY & FUN COMMANDS
# ---------------------------------------------------------
@bot.command(name="rank", aliases=["level", "xp"])
async def rank(ctx, target: discord.Member = None):
    target = target or ctx.author
    cursor = db.cursor()
    cursor.execute('SELECT xp, level FROM levels WHERE guild_id = ? AND user_id = ?', (ctx.guild.id, target.id))
    row = cursor.fetchone()
    
    xp = row['xp'] if row else 0
    level = row['level'] if row else 0
    xp_needed = 100 + (level * 50)
    
    await ctx.send(f"📊 **{target.display_name}** | Level `{level}` | XP `{xp}/{xp_needed}`")

@bot.command(name="userinfo", aliases=["ui"])
async def userinfo(ctx, member: discord.Member = None):
    target = member or ctx.author
    roles = [role.mention for role in target.roles if role != ctx.guild.default_role]
    embed = discord.Embed(title=f"User Info - {target}", color=target.color)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Created Account", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if roles else "None", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo", aliases=["si"])
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.blue())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%Y-%m-%d"), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")

@bot.command(name="8ball")
async def eightball(ctx, *, question: str):
    responses = ["Haan zaroor!", "Bilkul nahi.", "Shayad...", "Aapka waqt bura chal raha hai.", "Pakka nahi keh sakta."]
    await ctx.send(f"🎱 **Sawaal:** {question}\n**Jawaab:** {random.choice(responses)}")

# ---------------------------------------------------------
# HELP COMMAND
# ---------------------------------------------------------
@bot.command(name="help")
async def help_command(ctx):
    p = get_prefix(bot, ctx.message)
    embed = discord.Embed(
        title="🤖 Bot Command Menu",
        description=f"Current Guild Prefix: `{p}`\nUse `{p}<command>` to run.",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="🛠️ Setup (Admin)",
        value=f"`{p}setprefix`, `{p}setmodlog`, `{p}setautorole`, `{p}setwelcome`",
        inline=False
    )
    embed.add_field(
        name="🛡️ Moderation",
        value=f"`{p}ban`, `{p}kick`, `{p}mute`, `{p}unmute`, `{p}purge`, `{p}warn`, `{p}warnings`",
        inline=False
    )
    embed.add_field(
        name="💰 Economy & Levels",
        value=f"`{p}bal`, `{p}work`, `{p}dep`, `{p}with`, `{p}rank`",
        inline=False
    )
    embed.add_field(
        name="📊 Utility & Fun",
        value=f"`{p}userinfo`, `{p}serverinfo`, `{p}ping`, `{p}8ball`, `{p}help`",
        inline=False
    )
    await ctx.send(embed=embed)

# ---------------------------------------------------------
# RUN BOT
# ---------------------------------------------------------
if __name__ == '__main__':
    if TOKEN == 'YOUR_DISCORD_BOT_TOKEN_HERE':
        log.error("DISCORD_TOKEN set nahi hai!")
    else:
        bot.run(TOKEN)
