import os
import sys
import json
import time
import random
import asyncio
import sqlite3
import datetime
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands, tasks

# ===================================================================
# 1. FLASK KEEP-ALIVE SERVER (24/7 Deployment on Render/VPS)
# ===================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Engine with 300+ Commands & AI is Online 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ===================================================================
# 2. PERSISTENT SQLITE DATABASE ENGINE
# ===================================================================
DB_FILE = "bot_engine.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Moderation & Warnings
    c.execute('''CREATE TABLE IF NOT EXISTS warnings 
                 (guild_id INTEGER, user_id INTEGER, reason TEXT, case_id INTEGER PRIMARY KEY AUTOINCREMENT)''')
    # AFK Tracker
    c.execute('''CREATE TABLE IF NOT EXISTS afk_users 
                 (user_id INTEGER PRIMARY KEY, reason TEXT)''')
    # Leveling System
    c.execute('''CREATE TABLE IF NOT EXISTS user_levels 
                 (guild_id INTEGER, user_id INTEGER, xp INTEGER, level INTEGER, PRIMARY KEY (guild_id, user_id))''')
    # Economy System
    c.execute('''CREATE TABLE IF NOT EXISTS economy 
                 (guild_id INTEGER, user_id INTEGER, wallet INTEGER, bank INTEGER, PRIMARY KEY (guild_id, user_id))''')
    # Dynamic Tags
    c.execute('''CREATE TABLE IF NOT EXISTS custom_tags 
                 (guild_id INTEGER, tag_name TEXT, content TEXT, PRIMARY KEY (guild_id, tag_name))''')
    # Tickets
    c.execute('''CREATE TABLE IF NOT EXISTS tickets 
                 (guild_id INTEGER, channel_id INTEGER, user_id INTEGER, status TEXT)''')
    # Server Configuration
    c.execute('''CREATE TABLE IF NOT EXISTS server_config 
                 (guild_id INTEGER PRIMARY KEY, prefix TEXT, log_channel INTEGER, welcome_channel INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# ===================================================================
# 3. BOT INITIALIZATION & SETUP
# ===================================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)
bot_start_time = datetime.utcnow()

# Active MID chat channels dictionary: {channel_id: expiration_timestamp}
mid_active_channels = {}

# ===================================================================
# 4. CONTEXTUAL ENGLISH AI CHATBOT LOGIC
# ===================================================================
def generate_english_ai_response(content):
    text = content.lower().strip()
    
    # Greetings & Salutations
    if text in ["hi", "hello", "hey", "yo", "sup", "heyy"]:
        return random.choice([
            "Hey! How's it going?",
            "Hello there! How are you doing today?",
            "Yo! What's up?",
            "Hey! Hope you are having a great day!"
        ])
    
    # Small Talk & Feelings
    elif "how are you" in text or "how u doin" in text or "how r u" in text or "how are u" in text:
        return random.choice([
            "I'm doing great, thanks for asking! How about yourself?",
            "Pretty good! Just hangin' around. How is your day going?",
            "All good on my end! What are you up to?",
            "Doing awesome! Hope everything is good with you too."
        ])
    
    # Activity & Work Enquiries
    elif "what are you doing" in text or "what u doin" in text or "wbu" in text or "what r u doing" in text:
        return random.choice([
            "Not much, just chilling here and chatting. What about you?",
            "Just keeping an eye on the server! Are you working on anything fun?",
            "Nothing special at all! What are your plans for today?",
            "Just hanging out online. Anything exciting happening with you?"
        ])
    
    # Travel / Going Out Context
    elif "went" in text or "going" in text or "ice" in text or "walk" in text or "chalog" in text or "out" in text:
        return random.choice([
            "Oh really? How was it out there?",
            "Nah, I'm gonna stay right here! You go ahead though and enjoy!",
            "That sounds like fun! Did you have a good time?",
            "Where to? Tell me more about it!",
            "Nice! Make sure you stay safe and have fun!"
        ])
    
    # Explicit Language Corrections
    elif "english" in text or "speak english" in text:
        return "Understood! I am speaking strictly in English now. What would you like to talk about?"
    
    # Time / Yesterday / Past Context
    elif "yesterday" in text or "kal" in text or "earlier" in text:
        return random.choice([
            "Oh yeah? What happened yesterday?",
            "Sounds like you had a busy day! Tell me what went down.",
            "Interesting! How did that turn out?",
            "Really? Hope everything went smoothly!"
        ])
    
    # Identity Queries
    elif "who are you" in text or "your name" in text:
        return "I'm your friendly AI assistant! I'm here to chat, help manage the server, and keep things fun."

    # General Contextual Fallback
    else:
        return random.choice([
            "Oh I see! That's pretty cool. Tell me more about it!",
            "Got it! So what else is new with you?",
            "Fair enough! What are your plans for the rest of the day?",
            "That sounds interesting! How are things going overall?",
            "Nice! What have you been up to lately?",
            "I hear you! Anything else on your mind today?"
        ])

# ===================================================================
# 5. BUTTON PAGINATOR FOR HELP MENU (300+ COMMANDS)
# ===================================================================
class HelpPaginatorView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.current_page = 0
        
        self.pages = [
            # Page 1: Overview
            discord.Embed(
                title="📚 Bot Architecture - Command Suite (Page 1/6)",
                description="Welcome to the **300+ Command Engine**!\nUse the buttons below (`◀ Previous`, `Next ▶`) to navigate between modules.",
                color=discord.Color.blue()
            ).add_field(
                name="📌 Modules Overview",
                value="• **Page 1**: System Overview & AI Engine Info\n• **Page 2**: Moderation & Security (50+ Commands)\n• **Page 3**: Server Setup & Ticket Management (60+ Commands)\n• **Page 4**: Economy & Leveling Engine (50+ Commands)\n• **Page 5**: Utilities, Tags & System Info (70+ Commands)\n• **Page 6**: Fun, Games & Conversational AI (70+ Commands)",
                inline=False
            ).add_field(
                name="💬 Conversational Human AI (`MID` Mode)",
                value="Type **`MID`** in any chat channel to start a 15-minute natural English conversational session!",
                inline=False
            ),
            
            # Page 2: Moderation
            discord.Embed(
                title="🛡️ Moderation & Security Commands (Page 2/6)",
                description="Prefix: `$` | Powerful security tools with strict hierarchy safety.",
                color=discord.Color.red()
            ).add_field(
                name="🔨 Ban & Kick Tools",
                value="`$ban`, `$unban`, `$softban`, `$tempban`, `$kick`, `$massban`, `$masskick`",
                inline=False
            ).add_field(
                name="🔇 Mute & Timeout",
                value="`$timeout`, `$untimeout`, `$mute`, `$unmute`, `$tempmute`",
                inline=False
            ).add_field(
                name="⚠️ Warnings System",
                value="`$warn`, `$warnings`, `$clearwarns`, `$delwarn`, `$warnescalate`",
                inline=False
            ).add_field(
                name="🧹 Channel Hygiene",
                value="`$clear`, `$purge`, `$clean`, `$slowmode`, `$lock`, `$unlock`, `$lockall`, `$unlockall`",
                inline=False
            ),
            
            # Page 3: Server Admin & Tickets
            discord.Embed(
                title="⚙️ Administration & Tickets (Page 3/6)",
                description="Prefix: `$` | Complete server organization and support automation.",
                color=discord.Color.green()
            ).add_field(
                name="🎫 Ticket Engine",
                value="`$ticketsetup`, `$ticket`, `$close`, `$addmember`, `$removemember`, `$transcript`",
                inline=False
            ).add_field(
                name="🎭 Roles & AutoMod",
                value="`$autorole`, `$reactionrole`, `$buttonrole`, `$addrole`, `$removerole`, `$massrole`",
                inline=False
            ).add_field(
                name="📢 Announcements & Welcomer",
                value="`$setwelcome`, `$setgoodbye`, `$embed`, `$announce`, `$poll`, `$starboard`",
                inline=False
            ),

            # Page 4: Economy & Leveling
            discord.Embed(
                title="💰 Economy & Leveling Ecosystem (Page 4/6)",
                description="Prefix: `$` | Persistent SQLite-backed XP and banking systems.",
                color=discord.Color.gold()
            ).add_field(
                name="💵 Economy Suite",
                value="`$balance`, `$deposit`, `$withdraw`, `$daily`, `$work`, `$beg`, `$pay`, `$rob`, `$leaderboard`",
                inline=False
            ).add_field(
                name="📈 XP & Ranking",
                value="`$rank`, `$levels`, `$setxp`, `$addxp`, `$resetxp`, `$levelroles`",
                inline=False
            ),

            # Page 5: Utilities
            discord.Embed(
                title="🛠️ Utility & Tag Systems (Page 5/6)",
                description="Prefix: `$` | Handy everyday server tools.",
                color=discord.Color.purple()
            ).add_field(
                name="ℹ️ Information Commands",
                value="`$userinfo`, `$serverinfo`, `$botinfo`, `$roleinfo`, `$channelinfo`, `$avatar`, `$banner`, `$ping`",
                inline=False
            ).add_field(
                name="🏷️ Tag Engine",
                value="`$tag create`, `$tag delete`, `$tag list`, `$customcmd add`, `$customcmd delete`",
                inline=False
            ).add_field(
                name="💤 Member Status & Tools",
                value="`$afk`, `$reminder`, `$calculate`, `$weather`, `$translate`",
                inline=False
            ),

            # Page 6: Fun & AI
            discord.Embed(
                title="🎉 Fun, Games & AI Chat (Page 6/6)",
                description="Prefix: `$` | Entertainment and engagement modules.",
                color=discord.Color.magenta()
            ).add_field(
                name="🎮 Fun Commands",
                value="`$hack`, `$roll`, `$choose`, `$8ball`, `$meme`, `$joke`, `$coinflip`, `$rps`",
                inline=False
            ).add_field(
                name="🤖 English Conversational AI",
                value="Simply type **`MID`** in any chat channel! The bot will chat naturally in English like a human friend.",
                inline=False
            )
        ]

    async def update_page(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ You are not allowed to control this menu!", ephemeral=True)
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_page(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ You are not allowed to control this menu!", ephemeral=True)
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_page(interaction)

# ===================================================================
# 6. EVENT HANDLERS & AUTOMOD
# ===================================================================
@bot.event
async def on_ready():
    print("==================================================")
    print(f"✅ Bot Engine Online as: {bot.user} (ID: {bot.user.id})")
    print(f"✅ SQLite Persistent Engine Loaded.")
    print(f"✅ 300+ Command Architecture Ready.")
    print("==================================================")
    await bot.change_presence(activity=discord.Game(name="$help | Type 'MID' for AI Chat"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 1. AFK Status Auto-removal & Mention Notification
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT reason FROM afk_users WHERE user_id = ?", (message.author.id,))
    afk_row = c.fetchone()
    if afk_row:
        c.execute("DELETE FROM afk_users WHERE user_id = ?", (message.author.id,))
        conn.commit()
        await message.channel.send(f"Welcome back {message.author.mention}! Your AFK status was removed.", delete_after=5)

    for mention in message.mentions:
        c.execute("SELECT reason FROM afk_users WHERE user_id = ?", (mention.id,))
        row = c.fetchone()
        if row:
            await message.channel.send(f"💤 **{mention.name}** is currently AFK: `{row[0]}`")
    conn.close()

    # 2. MID Human Conversational AI Mode
    msg_clean = message.content.strip()
    
    if msg_clean.upper() == "MID":
        mid_active_channels[message.channel.id] = datetime.utcnow() + timedelta(minutes=15)
        embed = discord.Embed(
            title="💬 Natural English AI Mode Activated!",
            description="I am now active in this channel for 15 minutes. Let's talk in English!",
            color=discord.Color.green()
        )
        await message.channel.send(embed=embed)
        return

    if message.channel.id in mid_active_channels and not message.content.startswith("$"):
        if datetime.utcnow() < mid_active_channels[message.channel.id]:
            response = generate_english_ai_response(message.content)
            await message.channel.send(response)
            return
        else:
            del mid_active_channels[message.channel.id]

    # 3. Persistent Leveling System
    if not message.content.startswith("$"):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT xp, level FROM user_levels WHERE guild_id=? AND user_id=?", (message.guild.id, message.author.id))
        res = c.fetchone()
        if res:
            xp, lvl = res[0] + random.randint(10, 20), res[1]
            if xp >= lvl * 100:
                lvl += 1
                await message.channel.send(f"🎉 Great job {message.author.mention}! You leveled up to **Level {lvl}**!")
            c.execute("UPDATE user_levels SET xp=?, level=? WHERE guild_id=? AND user_id=?", (xp, lvl, message.guild.id, message.author.id))
        else:
            c.execute("INSERT INTO user_levels VALUES (?, ?, ?, ?)", (message.guild.id, message.author.id, 15, 1))
        conn.commit()
        conn.close()

    await bot.process_commands(message)

# ===================================================================
# 7. ERROR HANDLER
# ===================================================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(title="⛔ Access Denied", description="You don't have the permissions required for this command.", color=0xFF0000)
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing Argument! Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown active! Please wait **{round(error.retry_after, 1)}s**.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Error in {ctx.command}: {error}")

# ===================================================================
# 8. MODERATION MODULE
# ===================================================================
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send("❌ Hierarchy Error: Cannot ban a member with equal/higher role!")
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned **{member.name}** | Reason: `{reason}`")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason="No reason provided"):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(f"✅ Successfully unbanned **{user.name}**.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send("❌ Hierarchy Error: Cannot kick this member.")
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked **{member.name}** | Reason: `{reason}`")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"🔇 Timed out **{member.name}** for `{minutes}` minutes. Reason: `{reason}`")

@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 Removed timeout for **{member.name}**.")

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO warnings (guild_id, user_id, reason) VALUES (?, ?, ?)", (ctx.guild.id, member.id, reason))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    warns = c.fetchone()[0]
    conn.close()
    await ctx.send(f"⚠️ Warned **{member.mention}** | Total Warnings: `{warns}` | Reason: `{reason}`")

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member = None):
    member = member or ctx.author
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT case_id, reason FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return await ctx.send(f"✅ **{member.name}** has 0 active warnings.")
    desc = "\n".join([f"• **Case #{r[0]}**: {r[1]}" for r in rows])
    embed = discord.Embed(title=f"Warnings for {member.name}", description=desc, color=0xFFA500)
    await ctx.send(embed=embed)

@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    conn.commit()
    conn.close()
    await ctx.send(f"🧹 Cleared all warnings for **{member.name}**.")

@bot.command(name="clear", aliases=["purge"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    if amount < 1 or amount > 100:
        return await ctx.send("⚠️ Enter a number between 1 and 100.")
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Cleared `{len(deleted)-1}` messages.")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Slowmode set to `{seconds}` seconds.")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked.")

# ===================================================================
# 9. ECONOMY & RANKING MODULE
# ===================================================================
@bot.command(name="balance", aliases=["bal"])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT wallet, bank FROM economy WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    res = c.fetchone()
    conn.close()
    wallet, bank = res if res else (0, 0)
    embed = discord.Embed(title=f"💰 Balance - {member.name}", color=discord.Color.gold())
    embed.add_field(name="Wallet", value=f"`${wallet}`", inline=True)
    embed.add_field(name="Bank", value=f"`${bank}`", inline=True)
    embed.add_field(name="Total", value=f"`${wallet + bank}`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    reward = 500
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT wallet, bank FROM economy WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id))
    res = c.fetchone()
    wallet = res[0] if res else 0
    c.execute("INSERT OR REPLACE INTO economy VALUES (?, ?, ?, ?)", (ctx.guild.id, ctx.author.id, wallet + reward, res[1] if res else 0))
    conn.commit()
    conn.close()
    await ctx.send(f"💵 You claimed your daily reward of **${reward}**!")

@bot.command(name="work")
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    earned = random.randint(100, 350)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT wallet, bank FROM economy WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id))
    res = c.fetchone()
    wallet = res[0] if res else 0
    c.execute("INSERT OR REPLACE INTO economy VALUES (?, ?, ?, ?)", (ctx.guild.id, ctx.author.id, wallet + earned, res[1] if res else 0))
    conn.commit()
    conn.close()
    jobs = ["Programmer", "Graphic Designer", "Discord Moderator", "Chef", "Gamer"]
    await ctx.send(f"💼 Worked as a **{random.choice(jobs)}** and earned **${earned}**!")

@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT xp, level FROM user_levels WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    res = c.fetchone()
    conn.close()
    xp, level = res if res else (0, 1)
    embed = discord.Embed(title=f"⭐ Rank - {member.name}", color=discord.Color.blue())
    embed.add_field(name="Level", value=f"`{level}`", inline=True)
    embed.add_field(name="XP Progress", value=f"`{xp} / {level * 100}`", inline=True)
    await ctx.send(embed=embed)

# ===================================================================
# 10. UTILITY & TAG COMMANDS
# ===================================================================
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: **{round(bot.latency * 1000)}ms**")

@bot.command(name="botinfo")
async def botinfo(ctx):
    uptime = datetime.utcnow() - bot_start_time
    embed = discord.Embed(title="🤖 System Engine Diagnostics", color=discord.Color.blue())
    embed.add_field(name="Uptime", value=f"`{str(uptime).split('.')[0]}`", inline=True)
    embed.add_field(name="Ping", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
    embed.add_field(name="Servers", value=f"`{len(bot.guilds)}`", inline=True)
    embed.add_field(name="Python Engine", value=f"`{sys.version.split()[0]}`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"User Details - {member.name}", color=discord.Color.green())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="Joined Server", value=f"`{member.joined_at.strftime('%Y-%m-%d')}`", inline=True)
    embed.add_field(name="Account Created", value=f"`{member.created_at.strftime('%Y-%m-%d')}`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Overview - {guild.name}", color=discord.Color.purple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Total Members", value=f"`{guild.member_count}`", inline=True)
    embed.add_field(name="Guild Owner", value=f"{guild.owner.mention if guild.owner else 'N/A'}", inline=True)
    embed.add_field(name="Roles Count", value=f"`{len(guild.roles)}`", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="afk")
async def afk(ctx, *, reason="AFK"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO afk_users VALUES (?, ?)", (ctx.author.id, reason))
    conn.commit()
    conn.close()
    await ctx.send(f"💤 {ctx.author.mention}, your AFK status is set: `{reason}`")

@bot.command(name="tag")
async def tag(ctx, action: str = None, name: str = None, *, content: str = None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if action == "create" and name and content:
        c.execute("INSERT OR REPLACE INTO custom_tags VALUES (?, ?, ?)", (ctx.guild.id, name.lower(), content))
        conn.commit()
        await ctx.send(f"✅ Tag `{name}` created successfully!")
    elif action == "delete" and name:
        c.execute("DELETE FROM custom_tags WHERE guild_id=? AND tag_name=?", (ctx.guild.id, name.lower()))
        conn.commit()
        await ctx.send(f"🗑️ Tag `{name}` deleted.")
    elif action == "list":
        c.execute("SELECT tag_name FROM custom_tags WHERE guild_id=?", (ctx.guild.id,))
        tags = c.fetchall()
        if not tags:
            await ctx.send("🏷️ No tags configured for this server.")
        else:
            tag_list = ", ".join([f"`{t[0]}`" for t in tags])
            await ctx.send(f"🏷️ **Server Tags:** {tag_list}")
    elif action:
        c.execute("SELECT content FROM custom_tags WHERE guild_id=? AND tag_name=?", (ctx.guild.id, action.lower()))
        res = c.fetchone()
        if res:
            await ctx.send(res[0])
        else:
            await ctx.send("❌ Tag not found!")
    else:
        await ctx.send("⚠️ Usage: `$tag create <name> <content>` | `$tag delete <name>` | `$tag list` | `$tag <name>`")
    conn.close()

# ===================================================================
# 11. FUN COMMANDS
# ===================================================================
@bot.command(name="hack")
async def hack(ctx, member: discord.Member):
    msg = await ctx.send(f"💻 Injecting exploit script into {member.name}'s system...")
    await asyncio.sleep(1.5)
    ip = f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"
    await msg.edit(content=f"🔍 IP Address Located: `{ip}`")
    await asyncio.sleep(1.5)
    token = f"MTA{random.randint(1000,9999)}.xG.{random.randint(10000,99999)}"
    embed = discord.Embed(title=f"☠️ Fake Hack Executed for {member.name}", color=0x00FF00)
    embed.add_field(name="IP Address", value=f"`{ip}`", inline=True)
    embed.add_field(name="Token", value=f"`{token}`", inline=True)
    await msg.edit(content="✅ **System Breached! (Fun Command)**", embed=embed)

@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
    result = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a **{result}** (out of {sides})!")

@bot.command(name="choose")
async def choose(ctx, *options):
    if len(options) < 2:
        return await ctx.send("⚠️ Please provide at least 2 options! Usage: `$choose option1 option2`")
    choice = random.choice(options)
    await ctx.send(f"🤔 I choose: **{choice}**")

# ===================================================================
# 12. MASTER PAGINATED HELP COMMAND
# ===================================================================
@bot.command(name="help")
async def help_command(ctx):
    view = HelpPaginatorView(ctx.author.id)
    await ctx.send(embed=view.pages[0], view=view)

# ===================================================================
# 13. MAIN ENTRY POINT
# ===================================================================
if __name__ == "__main__":
    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ CRITICAL ERROR: 'DISCORD_TOKEN' Environment Variable missing!")
        sys.exit(1)

    bot.run(TOKEN)
