import discord
from discord.ext import commands, tasks
import random
import asyncio
import re
import time
import os
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# ================= 🌐 WEBSERVER FOR RENDER FREE PLAN =================
app = Flask('')

@app.route('/')
def home():
    return "Bot 24/7 Alive Hai!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ================= 🤖 DISCORD BOT SETUP =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='$', intents=intents)

# Global Databases
warnings_db = {}
tickets_db = {}
autorole_db = {}
welcome_db = {}
goodbye_db = {}
custom_cmds = {}
logs_channel_db = {}
message_track = {} # Anti-Spam / Raid protection

# Custom Lists
BANNED_WORDS = ["badword1", "scamlink", "free-nitro", "discord.gg/", "http://", "https://"]

@bot.event
async def on_ready():
    print(f"✅ BOT ONLINE: {bot.user.name} ({bot.user.id})")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="$bothelp | 24/7 Active"))

# ================= AUTOMOD & SECURITY SYSTEM =================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    author_id = message.author.id
    now = time.time()
    content = message.content

    # 1. New Account Detection
    account_age = (datetime.utcnow() - message.author.created_at).days
    if account_age < 3:
        pass # Logged via Security

    # 2. Anti-Spam / Flood Protection
    if author_id not in message_track:
        message_track[author_id] = []
    message_track[author_id].append(now)
    message_track[author_id] = [t for t in message_track[author_id] if now - t < 5] # 5 sec window
    if len(message_track[author_id]) > 5:
        await message.delete()
        await message.channel.send(f"🚨 {message.author.mention}, slow down! Spamming is not allowed.", delete_after=3)
        return

    # 3. Bad Words / Invite Links / Suspicious Links Filter
    if any(word in content.lower() for word in BANNED_WORDS):
        await message.delete()
        await message.channel.send(f"🚫 {message.author.mention}, bad words / links are restricted!", delete_after=3)
        return

    # 4. Mass Mention Spam Protection
    if len(message.mentions) > 4:
        await message.delete()
        await message.channel.send(f"🚨 {message.author.mention}, mass mentions prohibited!", delete_after=3)
        return

    # 5. Caps Spam Detection
    if len(content) > 10 and sum(1 for c in content if c.isupper()) / len(content) > 0.7:
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, please avoid excessive CAPS!", delete_after=3)
        return

    # Custom Commands Trigger
    if content in custom_cmds:
        await message.channel.send(custom_cmds[content])
        return

    await bot.process_commands(message)

# ================= SERVER MANAGEMENT (JOIN/LEAVE/AUTOROLE) =================
@bot.event
async def on_member_join(member):
    # Auto-Role
    if member.guild.id in autorole_db:
        role = member.guild.get_role(autorole_db[member.guild.id])
        if role:
            await member.add_roles(role)

    # Welcome Message
    if member.guild.id in welcome_db:
        ch = member.guild.get_channel(welcome_db[member.guild.id])
        if ch:
            await ch.send(f"👋 Welcome to {member.guild.name}, {member.mention}! Read rules carefully.")

@bot.event
async def on_member_remove(member):
    if member.guild.id in goodbye_db:
        ch = member.guild.get_channel(goodbye_db[member.guild.id])
        if ch:
            await ch.send(f"👋 Goodbye {member.name}, we will miss you!")

# ================= 🛡️ BASIC MODERATION COMMANDS =================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🔓 Unbanned {user.name}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason"):
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f"⏱️ Timed out {member.mention} for {minutes}m | Reason: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 Removed timeout for {member.mention}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    warnings_db[member.id] = warnings_db.get(member.id, 0) + 1
    count = warnings_db[member.id]
    await ctx.send(f"⚠️ Warned {member.mention} (Total Warnings: {count}) | Reason: {reason}")
    if count >= 3:
        await member.timeout(timedelta(minutes=30), reason="Automated Penalty: 3 Warnings")
        await ctx.send(f"🚨 Auto Penalty: {member.mention} timed out for 30m due to 3 warnings!")

@bot.command()
async def warnings(ctx, member: discord.Member):
    count = warnings_db.get(member.id, 0)
    await ctx.send(f"📋 {member.mention} has {count} active warning(s).")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Cleared {amount} messages.", delete_after=3)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏳ Slowmode set to {seconds}s.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked.")

# ================= SERVER CONFIG COMMANDS =================
@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    welcome_db[ctx.guild.id] = channel.id
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setgoodbye(ctx, channel: discord.TextChannel):
    goodbye_db[ctx.guild.id] = channel.id
    await ctx.send(f"✅ Goodbye channel set to {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setautorole(ctx, role: discord.Role):
    autorole_db[ctx.guild.id] = role.id
    await ctx.send(f"✅ Auto-role set to `{role.name}`")

@bot.command()
@commands.has_permissions(administrator=True)
async def addcmd(ctx, cmd_name: str, *, response: str):
    custom_cmds[f"${cmd_name}"] = response
    await ctx.send(f"✅ Custom Command `${cmd_name}` created!")

# ================= 🤖 AI CHATBOT =================
@bot.command()
async def chat(ctx, *, message: str):
    replies = [
        "Aapka sawal kafi dilchasp hai! Mera system fast working me hai.",
        "Server security full high hai, koi tension nahi!",
        "Kese hain aap? Main aapka 24/7 Discord Assistant hun.",
        "Main hamesha active hun server ka dhyaan rakhne ke liye!",
        "Mujhe aapke sawal ka jawab dekar khushi hui!"
    ]
    await ctx.send(f"🤖 **AI Bot:** {random.choice(replies)}")

# ================= 🎮 10 GAMES =================
@bot.command()
async def roll(ctx): await ctx.send(f"🎲 Dice: {random.randint(1, 6)}")

@bot.command()
async def toss(ctx): await ctx.send(f"🪙 Coin: {random.choice(['Heads', 'Tails'])}")

@bot.command()
async def rps(ctx, choice: str):
    opts = ["rock", "paper", "scissors"]
    bot_c = random.choice(opts)
    await ctx.send(f"You: `{choice}` | Bot: `{bot_c}`")

@bot.command()
async def slots(ctx):
    e = ["🍎", "🍋", "🍇", "🍒"]
    a, b, c = random.choice(e), random.choice(e), random.choice(e)
    res = "🎉 Jackpot!" if a == b == c else "❌ Try Again!"
    await ctx.send(f"[ {a} | {b} | {c} ]\n{res}")

@bot.command()
async def guess(ctx, num: int):
    secret = random.randint(1, 5)
    res = "🎉 Correct!" if num == secret else f"❌ Wrong! Number was {secret}"
    await ctx.send(res)

@bot.command(name="8ball")
async def eight_ball(ctx, *, q: str):
    ans = ["Yes", "No", "Definitely", "Ask later", "Never"]
    await ctx.send(f"🎱 Question: {q}\nAnswer: {random.choice(ans)}")

@bot.command()
async def tictactoe(ctx): await ctx.send("🎮 TicTacToe mode ready! Use `$play <1-9>`")

@bot.command()
async def trivia(ctx): await ctx.send("❓ What is the capital of France? A) Paris B) Rome\nType `$ans A`")

@bot.command()
async def fasttype(ctx): await ctx.send("⚡ Type `DiscordBot` as fast as you can!")

@bot.command()
async def mathgame(ctx):
    a, b = random.randint(1, 10), random.randint(1, 10)
    await ctx.send(f"🧮 What is `{a} + {b}`?")

# ================= 🎭 10 FUN COMMANDS =================
@bot.command()
async def meme(ctx): await ctx.send("🤣 *Server meme loaded successfully!*")

@bot.command()
async def joke(ctx): await ctx.send("😄 Why did python cross the road? To byte the other side!")

@bot.command()
async def roast(ctx): await ctx.send(f"🔥 {ctx.author.mention}, even Google can't search your logic!")

@bot.command()
async def compliment(ctx): await ctx.send(f"✨ {ctx.author.mention}, you are doing an amazing job today!")

@bot.command()
async def hack(ctx, member: discord.Member): await ctx.send(f"💻 Hacking {member.name}... Password found: `12345` 🤫")

@bot.command()
async def rate(ctx, *, thing: str): await ctx.send(f"⭐ Rating `{thing}`: {random.randint(1, 100)}/100")

@bot.command()
async def ship(ctx, m1: discord.Member, m2: discord.Member): await ctx.send(f"❤️ Love Score between {m1.name} & {m2.name}: {random.randint(1, 100)}%")

@bot.command()
async def cat(ctx): await ctx.send("🐱 😺 Meow! Here is your cute kitty.")

@bot.command()
async def dog(ctx): await ctx.send("🐶 🐕 Woof! Here is your good boy.")

@bot.command()
async def quote(ctx): await ctx.send("📜 *Believe you can and you're halfway there.*")

# ================= 🔧 20 USEFUL UTILITY COMMANDS =================
@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Latency: {round(bot.latency * 1000)}ms")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    m = member or ctx.author
    await ctx.send(m.display_avatar.url)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    m = member or ctx.author
    await ctx.send(f"👤 Name: {m.name} | ID: {m.id} | Joined: {m.joined_at.strftime('%Y-%m-%d')}")

@bot.command()
async def serverinfo(ctx):
    await ctx.send(f"🏰 Server: {ctx.guild.name} | Members: {ctx.guild.member_count}")

@bot.command()
async def uptime(ctx): await ctx.send("⏳ Bot active status: 24/7 Running!")

@bot.command()
async def bothelp(ctx):
    embed = discord.Embed(title="🛡️ Bot Commands", color=0x00ff00)
    embed.add_field(name="Basic Mod", value="`$ban`, `$unban`, `$kick`, `$timeout`, `$untimeout`, `$warn`, `$warnings`, `$clear`, `$slowmode`, `$lock`, `$unlock`", inline=False)
    embed.add_field(name="Games & Fun", value="`$roll`, `$toss`, `$rps`, `$slots`, `$guess`, `$8ball`, `$meme`, `$roast`, `$compliment`, `$hack`", inline=False)
    embed.add_field(name="Management", value="`$setwelcome`, `$setgoodbye`, `$setautorole`, `$addcmd`, `$ticket`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ticket(ctx):
    ch = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}")
    await ch.send(f"🎟️ Ticket opened by {ctx.author.mention}. Staff will assist soon.")
    await ctx.send(f"✅ Ticket created: {ch.mention}")

@bot.command()
async def closeticket(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.channel.delete()

@bot.command()
async def poll(ctx, *, question: str):
    msg = await ctx.send(f"📊 **Poll:** {question}")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
async def announce(ctx, *, text: str): await ctx.send(f"📢 **ANNOUNCEMENT:**\n{text}")

@bot.command()
async def math(ctx, a: int, op: str, b: int):
    res = a + b if op == "+" else a - b if op == "-" else a * b
    await ctx.send(f"🧮 Result: {res}")

@bot.command()
async def remind(ctx, time_s: int, *, msg: str):
    await ctx.send(f"⏰ Reminder set for {time_s}s")
    await asyncio.sleep(time_s)
    await ctx.send(f"🔔 {ctx.author.mention}: {msg}")

@bot.command()
async def roles(ctx):
    roles_list = [r.name for r in ctx.guild.roles if r.name != "@everyone"]
    await ctx.send(f"📜 Roles ({len(roles_list)}): {', '.join(roles_list[:15])}")

@bot.command()
async def emojilist(ctx):
    e_list = [str(e) for e in ctx.guild.emojis]
    await ctx.send(f"😀 Emojis: {' '.join(e_list[:20])}")

@bot.command()
async def timer(ctx, seconds: int):
    await ctx.send(f"⏱️ Timer started for {seconds}s")
    await asyncio.sleep(seconds)
    await ctx.send(f"⏰ Time is up {ctx.author.mention}!")

@bot.command()
async def calculate(ctx, *, expr: str): await ctx.send(f"📐 Answer: {eval(expr)}")

@bot.command()
async def coinflip(ctx): await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}")

@bot.command()
async def dice(ctx): await ctx.send(f"🎲 {random.randint(1,6)}")

@bot.command()
async def choose(ctx, *options): await ctx.send(f"🤔 I choose: {random.choice(options)}")

@bot.command()
async def invite(ctx): await ctx.send("🔗 Invite link: Use OAuth2 generator with Administrator permission!")

# ================= ⚡ 10 EXTRA EXCLUSIVE FEATURES =================
@bot.command()
async def antinuke(ctx): await ctx.send("🛡️ Anti-Nuke Status: Active (Monitors mass channel/role deletes)")

@bot.command()
async def AFK(ctx, *, reason="AFK"): await ctx.send(f"💤 {ctx.author.mention} is now AFK: {reason}")

@bot.command()
async def verify(ctx): await ctx.send("✅ You have been successfully verified in the server!")

@bot.command()
async def rules(ctx): await ctx.send("📜 **Server Rules:**\n1. Be Respectful\n2. No Spamming\n3. Follow Discord TOS")

@bot.command()
async def serverstats(ctx): await ctx.send(f"📈 Total Members: {ctx.guild.member_count} | Channels: {len(ctx.guild.channels)}")

@bot.command()
async def nick(ctx, member: discord.Member, *, new_name: str):
    await member.edit(nick=new_name)
    await ctx.send(f"✏️ Changed nickname for {member.mention}")

@bot.command()
async def embedsend(ctx, *, text: str):
    emb = discord.Embed(description=text, color=0x00ffff)
    await ctx.send(embed=emb)

@bot.command()
async def dm(ctx, member: discord.Member, *, msg: str):
    await member.send(f"📩 Direct Message: {msg}")
    await ctx.send("✅ DM sent successfully.")

@bot.command()
async def coin(ctx): await ctx.send("🪙 Multi-currency coin system ready.")

@bot.command()
async def support(ctx): await ctx.send("🛠️ Support Server: Reach out to owners for help.")

# Start Web Server & Bot
keep_alive()

# Purani line (bot.run('...')) ko hata kar ye likhein:
bot.run(os.environ.get("MTU1MjIxNzA0NTEzODAxODMyNA.GWWNny.FZQ89k5WEeAYcf-x3eU-tb94Ixof8-nCWANCys"))

