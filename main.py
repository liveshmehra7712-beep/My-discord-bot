import os
import time
import random
import asyncio
import urllib.request
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
import discord
from discord.ext import commands, tasks

# ================= 🌐 KEEP ALIVE SERVER =================
app = Flask('')

@app.route('/')
def home():
    return "Bot is 24/7 Alive & Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ================= 🤖 BOT CONFIGURATION =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix='$', intents=intents, help_command=None)

# Databases
warnings_db = {}
custom_cmds = {}
autorole_db = {}
welcome_db = {}
goodbye_db = {}
logs_db = {}
message_track = {}
afk_users = {}
invites_cache = {}
ticket_category_db = {}

AUTOMOD_CONFIG = {
    "badwords": ["badword1", "scamlink", "abuseword"],
    "anti_link": True,
    "anti_spam": True,
    "anti_caps": True,
    "anti_massmention": True
}

# ================= 🌐 SELF-PING TASK =================
@tasks.loop(minutes=4)
async def self_ping():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if app_url:
        try:
            urllib.request.urlopen(app_url)
            print("🌐 Self-ping successful!")
        except Exception as e:
            print(f"⚠️ Self-ping error: {e}")

# ================= 🔄 EVENTS =================
@bot.event
async def on_ready():
    print(f"✅ BOT ONLINE: {bot.user.name} ({bot.user.id})")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="$help | 24/7 Active"))
    
    if not self_ping.is_running():
        self_ping.start()

    # Cache Server Invites for Invite Tracking
    for guild in bot.guilds:
        try:
            invites_cache[guild.id] = await guild.invites()
        except Exception:
            invites_cache[guild.id] = []

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing required argument! Usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Access Denied:** Aapke paas is admin/unsafe command ko chalane ke permissions nahi hain!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Mentioned member server me nahi mila!")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Mere paas is command ko chalane ke permissions (Admin/Manage Server) nahi hain!")
    else:
        print(f"Error executing {ctx.command}: {error}")

# ================= 👥 INVITE TRACKER & WELCOME EVENT =================
@bot.event
async def on_member_join(member):
    guild = member.guild
    inviter_text = "Unknown Inviter"

    # Invite Tracking Logic
    if guild.id in invites_cache:
        try:
            old_invites = invites_cache[guild.id]
            new_invites = await guild.invites()
            for inv in new_invites:
                for old_inv in old_invites:
                    if inv.code == old_inv.code and inv.uses > old_inv.uses:
                        inviter_text = inv.inviter.mention
                        break
            invites_cache[guild.id] = new_invites
        except Exception:
            pass

    # Auto Role
    if guild.id in autorole_db:
        role = guild.get_role(autorole_db[guild.id])
        if role:
            try: await member.add_roles(role)
            except: pass

    # Welcome Message
    if guild.id in welcome_db:
        ch = guild.get_channel(welcome_db[guild.id])
        if ch:
            emb = discord.Embed(
                title=f"🎉 Welcome to {guild.name}!",
                description=f"Welcome {member.mention}!\n\n👤 **Member:** #{len(guild.members)}\n🔗 **Invited By:** {inviter_text}",
                color=0x00ff00
            )
            emb.set_thumbnail(url=member.display_avatar.url)
            await ch.send(embed=emb)

@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    if guild_id in goodbye_db:
        ch = member.guild.get_channel(goodbye_db[guild_id])
        if ch:
            await ch.send(f"👋 Goodbye **{member.name}**, hope to see you again!")

# ================= 🛡️ AUTOMOD & CHAT SYSTEM =================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    author_id = message.author.id
    content = message.content

    # AFK Handling
    if author_id in afk_users:
        del afk_users[author_id]
        await message.channel.send(f"Welcome back {message.author.mention}, aapka AFK remove kar diya hai!", delete_after=3)

    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"💤 **{mention.name}** abhi AFK hai: {afk_users[mention.id]}")

    # Process Commands first if starting with $if content.startswith('$'):
        await bot.process_commands(message)
        return

    # Trigger Smart AI Chat: On Bot Mention OR "MID" / "mid" keyword
    if bot.user.mentioned_in(message) or "mid" in content.lower().split():
        chat_responses = [
            f"Haan ji {message.author.mention}, bataiye kya help chahiye?",
            "Mid Bot yahan hai! Main aapke server ki security aur moderation handle kar raha hu.",
            "Aapne yaad kiya aur MID haazir ho gaya! Type `$help` for commands list.",
            "Server full active aur safe hai! Main 24/7 online hoon.",
            "Namaste! Main MID Discord Bot hoon. Sab badhiya chal raha hai?"
        ]
        await message.channel.send(random.choice(chat_responses))
        return

    # Automod Checks for Non-Admins
    if not message.author.guild_permissions.administrator:
        now = time.time()
        
        # Anti-Spam
        if AUTOMOD_CONFIG["anti_spam"]:
            if author_id not in message_track: message_track[author_id] = []
            message_track[author_id].append(now)
            message_track[author_id] = [t for t in message_track[author_id] if now - t < 4]
            if len(message_track[author_id]) > 5:
                await message.delete()
                await message.channel.send(f"🚨 {message.author.mention}, spam mat karo!", delete_after=3)
                return

        # Bad Words
        if any(word in content.lower() for word in AUTOMOD_CONFIG["badwords"]):
            await message.delete()
            await message.channel.send(f"🚫 Abuse/Bad words yahan allowed nahi hain!", delete_after=3)
            return

        # Anti-Link
        if AUTOMOD_CONFIG["anti_link"] and ("http://" in content or "https://" in content or "discord.gg/" in content):
            await message.delete()
            await message.channel.send(f"🔗 Server par links allow nahi hain!", delete_after=3)
            return

        # Mass Mention
        if AUTOMOD_CONFIG["anti_massmention"] and len(message.mentions) > 3:
            await message.delete()
            await message.channel.send(f"🚨 Mass mentions block kar diye gaye hain!", delete_after=3)
            return

    # Custom Command Trigger
    if content in custom_cmds:
        await message.channel.send(custom_cmds[content])
        return

    await bot.process_commands(message)

# ================= 👑 SAFE & WORKING ADMIN COMMANDS (20+) =================
@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    pos = ctx.channel.position
    new_ch = await ctx.channel.clone(reason="Nuke Channel")
    await ctx.channel.delete()
    await new_ch.edit(position=pos)
    await new_ch.send("💥 Channel successfully nuke ho gaya aur reset kar diya gaya!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, ch: discord.TextChannel):
    welcome_db[ctx.guild.id] = ch.id
    await ctx.send(f"✅ Welcome channel set: {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setgoodbye(ctx, ch: discord.TextChannel):
    goodbye_db[ctx.guild.id] = ch.id
    await ctx.send(f"✅ Goodbye channel set: {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setautorole(ctx, role: discord.Role):
    autorole_db[ctx.guild.id] = role.id
    await ctx.send(f"✅ Auto-role set: `{role.name}`")

@bot.command()
@commands.has_permissions(administrator=True)
async def setlogs(ctx, ch: discord.TextChannel):
    logs_db[ctx.guild.id] = ch.id
    await ctx.send(f"✅ Logs channel set: {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def poll(ctx, *, question: str):
    emb = discord.Embed(title="📊 Server Poll", description=question, color=0x00ffff)
    msg = await ctx.send(embed=emb)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
@commands.has_permissions(administrator=True)
async def embed(ctx, title: str, *, description: str):
    emb = discord.Embed(title=title, description=description, color=0x3498db)
    await ctx.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def serverlock(ctx):
    for ch in ctx.guild.text_channels:
        await ch.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Poora server successfully lock ho gaya!")

@bot.command()
@commands.has_permissions(administrator=True)
async def serverunlock(ctx):
    for ch in ctx.guild.text_channels:
        await ch.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Server unlock kar diya gaya hai!")

@bot.command()
@commands.has_permissions(administrator=True)
async def announcement(ctx, *, text: str):
    emb = discord.Embed(title="📢 Official Announcement", description=text, color=0xe74c3c)
    await ctx.send("@everyone", embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def botnick(ctx, *, nick: str):
    await ctx.guild.me.edit(nick=nick)
    await ctx.send(f"✅ Bot ka nickname badal kar **{nick}** kar diya!")

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def createchannel(ctx, *, name: str):
    ch = await ctx.guild.create_text_channel(name)
    await ctx.send(f"✅ Text channel ban gaya: {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def deletechannel(ctx, ch: discord.TextChannel):
    await ch.delete()
    await ctx.send("🗑️ Channel delete kar diya gaya!")

@bot.command()
@commands.has_permissions(administrator=True)
async def createrole(ctx, *, name: str):
    role = await ctx.guild.create_role(name=name)
    await ctx.send(f"✅ Role create ho gaya: `{role.name}`")

@bot.command()
@commands.has_permissions(administrator=True)
async def deleterole(ctx, role: discord.Role):
    await role.delete()
    await ctx.send(f"🗑️ Role `{role.name}` delete kar diya gaya!")

@bot.command()
@commands.has_permissions(administrator=True)
async def massrole(ctx, role: discord.Role):
    await ctx.send(f"⚙️ Sabhi members ko `{role.name}` role diya ja raha hai...")
    count = 0
    for m in ctx.guild.members:
        if not m.bot:
            try:
                await m.add_roles(role)
                count += 1
            except: pass
    await ctx.send(f"✅ Completed! {count} members ko role mil gaya.")

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketsetup(ctx):
    category = await ctx.guild.create_category("📩 TICKETS")
    ticket_category_db[ctx.guild.id] = category.id
    emb = discord.Embed(
        title="🎫 Support Ticket System",
        description="Ticket open karne ke liye niche `$openticket` type karein!",
        color=0x2ecc71
    )
    await ctx.send(embed=emb)

@bot.command()
async def openticket(ctx):
    guild = ctx.guild
    cat_id = ticket_category_db.get(guild.id)
    category = guild.get_channel(cat_id) if cat_id else None
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    ch = await guild.create_text_channel(name=f"ticket-{ctx.author.name}", category=category, overwrites=overwrites)
    await ch.send(f"🎫 Welcome {ctx.author.mention}! Support team aapse jaldi contact karegi.\nClose karne ke liye `$closeticket` likhein.")
    await ctx.send(f"✅ Aapka ticket channel create ho gaya: {ch.mention}", delete_after=5)

@bot.command()
async def closeticket(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.send("🔒 Ticket 5 seconds me close ho raha hai...")
        await asyncio.sleep(5)
        await ctx.channel.delete()
    else:
        await ctx.send("❌ Yeh command sirf ticket channel me use ki ja sakti hai!")

@bot.command()
@commands.has_permissions(administrator=True)
async def dmall(ctx, *, message: str):
    await ctx.send("📩 Direct messaging process start kar diya gaya hai...")
    for m in ctx.guild.members:
        if not m.bot:
            try: await m.send(f"📢 **{ctx.guild.name}:** {message}")
            except: pass
    await ctx.send("✅ DM process complete ho gaya!")

# ================= 🛡️ MODERATION COMMANDS (14) =================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="None"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned **{member.name}** | Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🔓 Unbanned **{user.name}**")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="None"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked **{member.name}** | Reason: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int = 10, *, reason="None"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"⏱️ Muted **{member.name}** for {minutes}m.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 Unmuted **{member.name}**")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="None"):
    warnings_db[member.id] = warnings_db.get(member.id, 0) + 1
    current_warns = warnings_db[member.id]
    
    if current_warns >= 3:
        try:
            await member.timeout(timedelta(minutes=20), reason="Reached 3 Warnings")
            warnings_db[member.id] = 0
            await ctx.send(
                f"🚨 **{member.mention} ko 3 Warnings milne par 20 minutes ke liye Timeout (Mute) kar diya gaya hai!**\n"
                f"Reason: {reason}"
            )
        except Exception:
            await ctx.send(f"⚠️ **{member.name}** ke 3 warnings ho gaye hain, lekin permissions lack hone ki wajah se timeout nahi lag sakka.")
    else:
        await ctx.send(f"⚠️ **{member.name}** ko warn kiya gaya! (Total Warnings: **{current_warns}/3**) | Reason: {reason}")

@bot.command()
async def warnings(ctx, member: discord.Member):
    await ctx.send(f"📋 **{member.name}** ke total {warnings_db.get(member.id, 0)} warnings hain.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarns(ctx, member: discord.Member):
    warnings_db[member.id] = 0
    await ctx.send(f"🧹 **{member.name}** ke warnings clear kar diye gaye hain.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Cleared {amount} messages!", delete_after=3)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏳ Slowmode set to {seconds} seconds.")

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

@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✅ `{role.name}` role **{member.name}** ko de diya gaya.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"❌ `{role.name}` role **{member.name}** se hata diya gaya.")

# ================= 🎭 SAFE FUN & UTILITY =================
@bot.command()
async def hack(ctx, member: discord.Member):
    msg = await ctx.send(f"💻 Initiating fun simulation scan on **{member.name}**...")
    await asyncio.sleep(1)
    await msg.edit(content=f"🔍 Reading favorite emoji...")
    await asyncio.sleep(1)
    await msg.edit(content=f"🎮 Calculating gaming skill score... 99.9%")
    await asyncio.sleep(1)
    await msg.edit(content=f"🎉 **Fun Scan Complete:** {member.mention} is officially 100% Awesome!")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: **{round(bot.latency * 1000)}ms**")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    m = member or ctx.author
    await ctx.send(m.display_avatar.url)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    m = member or ctx.author
    await ctx.send(f"👤 Name: **{m.name}** | ID: `{m.id}` | Joined: `{m.joined_at.strftime('%Y-%m-%d')}`")

@bot.command()
async def serverinfo(ctx):
    await ctx.send(f"🏰 **Server Name:** {ctx.guild.name}\n👥 **Total Members:** {ctx.guild.member_count}")

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"💤 {ctx.author.mention} ab AFK hai: {reason}")

@bot.command()
async def chat(ctx, *, message: str):
    await ctx.send(f"🤖 **MID:** Aapne bola '{message}'. Server me sab smooth chal raha hai!")

# ================= 🎮 GAMES (10) =================
@bot.command()
async def roll(ctx): await ctx.send(f"🎲 Rolled: **{random.randint(1, 6)}**")

@bot.command()
async def toss(ctx): await ctx.send(f"🪙 Coin Result: **{random.choice(['Heads', 'Tails'])}**")

@bot.command()
async def rps(ctx, choice: str):
    bot_choice = random.choice(["rock", "paper", "scissors"])
    await ctx.send(f"🎮 Aap: `{choice}` | Bot: `{bot_choice}`")

@bot.command()
async def slots(ctx):
    e = ["🍎", "🍋", "🍒"]
    a, b, c = random.choice(e), random.choice(e), random.choice(e)
    await ctx.send(f"[ {a} | {b} | {c} ] -> {'🎉 WIN!' if a==b==c else '❌ Try Again!'}")

@bot.command()
async def guess(ctx, n: int): await ctx.send("🎉 Right Guess!" if n == random.randint(1, 3) else "❌ Wrong Guess!")

@bot.command(name="8ball")
async def eightball(ctx, *, q: str): await ctx.send(f"🎱 Answer: **{random.choice(['Yes', 'No', 'Never', 'Definitely'])}**")

@bot.command()
async def dice(ctx): await ctx.send(f"🎲 Dice: **{random.randint(1, 20)}**")

@bot.command()
async def coinflip(ctx): await ctx.send(f"🪙 Coin: **{random.choice(['Heads', 'Tails'])}**")

@bot.command()
async def mathquiz(ctx): await ctx.send("🧮 What is 12 x 12? (Answer: 144)")

@bot.command()
async def fasttype(ctx): await ctx.send("⚡ Fast Type: `MIDBOT247`")

# ================= 📜 HELP SYSTEM =================
@bot.command(name="help")
async def help_cmd(ctx, category: str = None):
    if category is None:
        emb = discord.Embed(title="🤖 MID Discord Bot Master Help", description="Categories list view karne ke liye `$help <category>` likhein.\nExample: `$help admin` or `$help mod`", color=0x00ffff)
        emb.add_field(name="🛡️ Moderation (14)", value="`$help mod`", inline=True)
        emb.add_field(name="👑 Admin (20+)", value="`$help admin`", inline=True)
        emb.add_field(name="🎮 Games (10)", value="`$help games`", inline=True)
        emb.add_field(name="🎭 Fun & Utility", value="`$help fun`", inline=True)
        emb.add_field(name="🤖 Smart Chat", value="Mention `@Bot` or write `MID` in chat", inline=False)
        emb.set_footer(text="Status: $help | 24/7 Active")
        await ctx.send(embed=emb)
    
    elif category.lower() == "mod":
        await ctx.send("🛡️ **Moderation Commands:** `$ban`, `$unban`, `$kick`, `$mute`, `$unmute`, `$warn`, `$warnings`, `$clearwarns`, `$purge`, `$slowmode`, `$lock`, `$unlock`, `$addrole`, `$removerole`")
    
    elif category.lower() == "admin":
        await ctx.send("👑 **Admin Commands:** `$nuke`, `$setwelcome`, `$setgoodbye`, `$setautorole`, `$setlogs`, `$poll`, `$embed`, `$serverlock`, `$serverunlock`, `$announcement`, `$botnick`, `$say`, `$createchannel`, `$deletechannel`, `$createrole`, `$deleterole`, `$massrole`, `$ticketsetup`, `$openticket`, `$closeticket`, `$dmall`")
    
    elif category.lower() == "games":
        await ctx.send("🎮 **Games Commands:** `$roll`, `$toss`, `$rps`, `$slots`, `$guess`, `$8ball`, `$dice`, `$coinflip`, `$mathquiz`, `$fasttype`")
    
    elif category.lower() == "fun":
        await ctx.send("🎭 **Fun & Utility:** `$ping`, `$avatar`, `$userinfo`, `$serverinfo`, `$afk`, `$hack`, `$chat`")

# ================= 🚀 RUNNER =================
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token, reconnect=True)
    else:
        print("❌ Error: DISCORD_TOKEN Environment variable not found!")
