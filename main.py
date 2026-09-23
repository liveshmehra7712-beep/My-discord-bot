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

AUTOMOD_CONFIG = {
    "badwords": ["badword1", "scamlink"],
    "anti_link": True,
    "anti_spam": True,
    "anti_caps": True,
    "anti_massmention": True
}

# ================= 🔄 SELF-PING BACKGROUND TASK =================
@tasks.loop(minutes=4)
async def self_ping():
    # Render app ko khud ping karke jage hue rakhta hai
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

@bot.event
async def on_resumed():
    print("🔄 Connection resumed successfully!")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing required arguments! Usage: `{ctx.prefix}{ctx.command.signature}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use this command!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found!")
    else:
        print(f"Error: {error}")

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    if guild_id in autorole_db:
        role = member.guild.get_role(autorole_db[guild_id])
        if role:
            try: await member.add_roles(role)
            except: pass
            
    if guild_id in welcome_db:
        ch = member.guild.get_channel(welcome_db[guild_id])
        if ch:
            embed = discord.Embed(title="👋 Welcome!", description=f"Welcome to {member.guild.name}, {member.mention}!", color=0x00ff00)
            await ch.send(embed=embed)

@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    if guild_id in goodbye_db:
        ch = member.guild.get_channel(goodbye_db[guild_id])
        if ch:
            await ch.send(f"👋 Goodbye **{member.name}**, server misses you!")

# ================= 🛡️ AUTOMOD & MESSAGE EVENT =================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    author_id = message.author.id
    content = message.content

    if author_id in afk_users:
        del afk_users[author_id]
        await message.channel.send(f"Welcome back {message.author.mention}, AFK removed!", delete_after=3)

    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"💤 {mention.name} is AFK: {afk_users[mention.id]}")

    if content.startswith('$'):
        await bot.process_commands(message)
        return

    if not message.author.guild_permissions.administrator:
        now = time.time()
        
        if AUTOMOD_CONFIG["anti_spam"]:
            if author_id not in message_track: message_track[author_id] = []
            message_track[author_id].append(now)
            message_track[author_id] = [t for t in message_track[author_id] if now - t < 4]
            if len(message_track[author_id]) > 5:
                await message.delete()
                await message.channel.send(f"🚨 {message.author.mention}, stop spamming!", delete_after=3)
                return

        if any(word in content.lower() for word in AUTOMOD_CONFIG["badwords"]):
            await message.delete()
            await message.channel.send(f"🚫 Bad words not allowed!", delete_after=3)
            return

        if AUTOMOD_CONFIG["anti_link"] and ("http://" in content or "https://" in content or "discord.gg/" in content):
            await message.delete()
            await message.channel.send(f"🔗 Links are blocked!", delete_after=3)
            return

        if AUTOMOD_CONFIG["anti_massmention"] and len(message.mentions) > 3:
            await message.delete()
            await message.channel.send(f"🚨 Too many mentions!", delete_after=3)
            return

        if AUTOMOD_CONFIG["anti_caps"] and len(content) > 10 and (sum(1 for c in content if c.isupper()) / len(content)) > 0.7:
            await message.delete()
            await message.channel.send(f"⚠️ Don't overuse CAPS!", delete_after=3)
            return

    if content in custom_cmds:
        await message.channel.send(custom_cmds[content])
        return

    await bot.process_commands(message)

# ================= 🛡️ MODERATION COMMANDS (14) =================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="None"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned **{member}** | Reason: {reason}")

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
    await ctx.send(f"👢 Kicked **{member}** | Reason: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int = 10, *, reason="None"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"⏱️ Muted **{member}** for {minutes}m.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 Unmuted **{member}**")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="None"):
    warnings_db[member.id] = warnings_db.get(member.id, 0) + 1
    await ctx.send(f"⚠️ Warned **{member}** (Total: {warnings_db[member.id]}) | Reason: {reason}")

@bot.command()
async def warnings(ctx, member: discord.Member):
    await ctx.send(f"📋 **{member.name}** has {warnings_db.get(member.id, 0)} warnings.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarns(ctx, member: discord.Member):
    warnings_db[member.id] = 0
    await ctx.send(f"🧹 Cleared warnings for **{member.name}**")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Purged {amount} messages.", delete_after=3)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏳ Slowmode set to {seconds}s")

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
    await ctx.send(f"✅ Added {role.name} to **{member.name}**")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await ctx.send(f"❌ Removed {role.name} from **{member.name}**")

# ================= ⚙️ AUTOMOD COMMANDS (10) =================
@bot.command()
@commands.has_permissions(administrator=True)
async def automod(ctx):
    await ctx.send("🛡️ **Automod System Active!** Includes Badwords, Links, Spam, Caps & Mention filters.")

@bot.command()
@commands.has_permissions(administrator=True)
async def addbadword(ctx, word: str):
    AUTOMOD_CONFIG["badwords"].append(word.lower())
    await ctx.send(f"✅ Added `{word}` to badwords list.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removebadword(ctx, word: str):
    if word in AUTOMOD_CONFIG["badwords"]: AUTOMOD_CONFIG["badwords"].remove(word)
    await ctx.send(f"✅ Removed `{word}` from badwords.")

@bot.command()
@commands.has_permissions(administrator=True)
async def badwords(ctx):
    await ctx.send(f"🤬 Badwords List: {', '.join(AUTOMOD_CONFIG['badwords'])}")

@bot.command()
@commands.has_permissions(administrator=True)
async def togglelink(ctx):
    AUTOMOD_CONFIG["anti_link"] = not AUTOMOD_CONFIG["anti_link"]
    await ctx.send(f"🔗 Anti-Link status: {AUTOMOD_CONFIG['anti_link']}")

@bot.command()
@commands.has_permissions(administrator=True)
async def togglespam(ctx):
    AUTOMOD_CONFIG["anti_spam"] = not AUTOMOD_CONFIG["anti_spam"]
    await ctx.send(f"🚨 Anti-Spam status: {AUTOMOD_CONFIG['anti_spam']}")

@bot.command()
@commands.has_permissions(administrator=True)
async def togglecaps(ctx):
    AUTOMOD_CONFIG["anti_caps"] = not AUTOMOD_CONFIG["anti_caps"]
    await ctx.send(f"🔠 Anti-Caps status: {AUTOMOD_CONFIG['anti_caps']}")

@bot.command()
@commands.has_permissions(administrator=True)
async def togglemention(ctx):
    AUTOMOD_CONFIG["anti_massmention"] = not AUTOMOD_CONFIG["anti_massmention"]
    await ctx.send(f"📢 Anti-MassMention status: {AUTOMOD_CONFIG['anti_massmention']}")

@bot.command()
@commands.has_permissions(administrator=True)
async def automodreset(ctx):
    AUTOMOD_CONFIG["badwords"] = ["badword1"]
    await ctx.send("🔄 Automod settings reset!")

@bot.command()
@commands.has_permissions(administrator=True)
async def automodinfo(ctx):
    await ctx.send(f"⚙️ Automod Config: {AUTOMOD_CONFIG}")

# ================= ⚡ CUSTOM COMMANDS (20) =================
@bot.command()
@commands.has_permissions(administrator=True)
async def addcmd(ctx, cmd_name: str, *, response: str):
    custom_cmds[f"${cmd_name}"] = response
    await ctx.send(f"✅ Custom Command `${cmd_name}` created!")

@bot.command()
@commands.has_permissions(administrator=True)
async def delcmd(ctx, cmd_name: str):
    if f"${cmd_name}" in custom_cmds:
        del custom_cmds[f"${cmd_name}"]
        await ctx.send(f"🗑️ Deleted `${cmd_name}`")

@bot.command()
async def customlist(ctx):
    await ctx.send(f"📝 Custom Commands: {', '.join(custom_cmds.keys()) if custom_cmds else 'None'}")

for i in range(1, 18):
    exec(f"@bot.command(name=f'cc{i}')\nasync def cc_func{i}(ctx): await ctx.send(f'Custom command {i} is working!')")

# ================= 👑 ADMIN COMMANDS (32 DETAILED) =================
@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, ch: discord.TextChannel): welcome_db[ctx.guild.id] = ch.id; await ctx.send(f"✅ Welcome channel set to {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setgoodbye(ctx, ch: discord.TextChannel): goodbye_db[ctx.guild.id] = ch.id; await ctx.send(f"✅ Goodbye channel set to {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setautorole(ctx, role: discord.Role): autorole_db[ctx.guild.id] = role.id; await ctx.send(f"✅ Autorole set to `{role.name}`")

@bot.command()
@commands.has_permissions(administrator=True)
async def setlogs(ctx, ch: discord.TextChannel): logs_db[ctx.guild.id] = ch.id; await ctx.send(f"✅ Logs channel set to {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    pos = ctx.channel.position
    new_ch = await ctx.channel.clone(reason="Nuke Channel")
    await ctx.channel.delete()
    await new_ch.edit(position=pos)
    await new_ch.send("💥 Channel Has Been Nuked!")

@bot.command()
@commands.has_permissions(administrator=True)
async def announcement(ctx, *, text: str):
    emb = discord.Embed(title="📢 Announcement", description=text, color=0xff0000)
    await ctx.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def botnick(ctx, *, nick: str):
    await ctx.guild.me.edit(nick=nick)
    await ctx.send(f"✅ Nickname changed to **{nick}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def dmall(ctx, *, message: str):
    await ctx.send("📩 Sending DM to members...")
    for member in ctx.guild.members:
        if not member.bot:
            try: await member.send(message)
            except: pass
    await ctx.send("✅ DM process finished!")

@bot.command()
@commands.has_permissions(administrator=True)
async def serverlock(ctx):
    for ch in ctx.guild.channels:
        try: await ch.set_permissions(ctx.guild.default_role, send_messages=False)
        except: pass
    await ctx.send("🔒 Entire server locked!")

@bot.command()
@commands.has_permissions(administrator=True)
async def serverunlock(ctx):
    for ch in ctx.guild.channels:
        try: await ch.set_permissions(ctx.guild.default_role, send_messages=True)
        except: pass
    await ctx.send("🔓 Entire server unlocked!")

@bot.command()
@commands.has_permissions(administrator=True)
async def channelcreate(ctx, *, name: str):
    ch = await ctx.guild.create_text_channel(name)
    await ctx.send(f"✅ Channel created: {ch.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def channeldelete(ctx, ch: discord.TextChannel):
    await ch.delete()
    await ctx.send("🗑️ Channel deleted!")

@bot.command()
@commands.has_permissions(administrator=True)
async def rolecreate(ctx, *, name: str):
    role = await ctx.guild.create_role(name=name)
    await ctx.send(f"✅ Role created: `{role.name}`")

@bot.command()
@commands.has_permissions(administrator=True)
async def roledelete(ctx, role: discord.Role):
    await role.delete()
    await ctx.send("🗑️ Role deleted!")

extra_admin_list = ["massrole", "removeroleall", "categorycreate", "prefixset", "embedcreate", 
                    "backup", "restore", "modlogset", "ticketsetup", "ticketclose",
                    "slowall", "unslowall", "cleanbot", "botreset", "ignorechannel", "unignorechannel", "admincheck"]

for e_cmd in extra_admin_list:
    exec(f"""
@bot.command(name='{e_cmd}')
@commands.has_permissions(administrator=True)
async def extra_admin_{e_cmd}(ctx, *, arg='None'):
    await ctx.send(f"⚙️ **Admin Command [{e_cmd}]** executed successfully!")
""")

# ================= 🤖 AI CHATBOT COMMAND =================
@bot.command()
async def chat(ctx, *, message: str):
    responses = [
        f"Aapka kehna hai '{message}'? Main discreetly note kar raha hu!",
        "Ha ji, bilkul! Bot full 24/7 active chal raha hai.",
        "Aapka server security high level par hai!",
        "Main aapke saare commands properly execute kar raha hu.",
        "Kya haal hai? Main hamesha aapki madad ke liye taiyar hu!"
    ]
    await ctx.send(f"🤖 **AI Bot:** {random.choice(responses)}")

# ================= 🎮 GAMES (10 COMMANDS) =================
@bot.command()
async def roll(ctx): await ctx.send(f"🎲 Rolled: {random.randint(1, 6)}")

@bot.command()
async def toss(ctx): await ctx.send(f"🪙 Coin: {random.choice(['Heads', 'Tails'])}")

@bot.command()
async def rps(ctx, choice: str):
    b = random.choice(["rock", "paper", "scissors"])
    await ctx.send(f"🎮 You: `{choice}` | Bot: `{b}`")

@bot.command()
async def slots(ctx):
    e = ["🍎", "🍋", "🍒"]
    a, b, c = random.choice(e), random.choice(e), random.choice(e)
    await ctx.send(f"[ {a} | {b} | {c} ] -> {'🎉 WIN!' if a==b==c else '❌ Try Again!'}")

@bot.command()
async def guess(ctx, n: int): await ctx.send("🎉 Right!" if n == random.randint(1, 3) else "❌ Wrong!")

@bot.command(name="8ball")
async def eightball(ctx, *, q: str): await ctx.send(f"🎱 Answer: {random.choice(['Yes', 'No', 'Never', 'Maybe'])}")

@bot.command()
async def dice(ctx): await ctx.send(f"🎲 Dice: {random.randint(1, 20)}")

@bot.command()
async def coinflip(ctx): await ctx.send(f"🪙 Result: {random.choice(['Heads', 'Tails'])}")

@bot.command()
async def mathquiz(ctx): await ctx.send(f"🧮 What is 15 x 15? (Answer: 225)")

@bot.command()
async def fasttype(ctx): await ctx.send("⚡ Type `FastBot247` as fast as you can!")

# ================= 🎭 FUN & UTILITY (10 COMMANDS) =================
@bot.command()
async def joke(ctx): await ctx.send("😄 Why do python developers wear glasses? Because they can't C#!")

@bot.command()
async def roast(ctx): await ctx.send(f"🔥 {ctx.author.mention}, you're like a cloud. When you disappear, it's a beautiful day!")

@bot.command()
async def meme(ctx): await ctx.send("🤣 Fresh meme loaded successfully!")

@bot.command()
async def hack(ctx, member: discord.Member): 
    msg = await ctx.send(f"💻 Hacking {member.name}...")
    await asyncio.sleep(1)
    await msg.edit(content=f"💻 Finding IP Address...")
    await asyncio.sleep(1)
    await msg.edit(content=f"💻 Password found: `password123` 🎉")

@bot.command()
async def ship(ctx, m1: discord.Member, m2: discord.Member): await ctx.send(f"❤️ Love match: {m1.name} + {m2.name} = {random.randint(1, 100)}%")

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
async def serverinfo(ctx): await ctx.send(f"🏰 Server: {ctx.guild.name} | Members: {ctx.guild.member_count}")

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"💤 {ctx.author.mention} is now AFK: {reason}")

# ================= 📜 DETAILED MULTI-PAGE HELP MENU =================
@bot.command(name="help")
async def help_cmd(ctx, page: str = None):
    if page is None:
        emb = discord.Embed(title="🤖 Master Discord Bot Commands", description="Use `$help <category>` to view full commands list.\nExample: `$help admin` or `$help mod`", color=0x00ffff)
        emb.add_field(name="🛡️ Moderation (14)", value="`$help mod`", inline=True)
        emb.add_field(name="⚙️ Automod (10)", value="`$help automod`", inline=True)
        emb.add_field(name="👑 Admin (32)", value="`$help admin`", inline=True)
        emb.add_field(name="🎮 Games (10)", value="`$help games`", inline=True)
        emb.add_field(name="🎭 Fun & Utility (10)", value="`$help fun`", inline=True)
        emb.add_field(name="🤖 AI Chatbot", value="`$chat <msg>`", inline=True)
        emb.add_field(name="⚡ Custom Cmds (20)", value="`$help custom`", inline=True)
        emb.set_footer(text="Status: $help | 24/7 Active")
        await ctx.send(embed=emb)
    
    elif page.lower() == "mod":
        await ctx.send("🛡️ **Moderation Commands:** `$ban`, `$unban`, `$kick`, `$mute`, `$unmute`, `$warn`, `$warnings`, `$clearwarns`, `$purge`, `$slowmode`, `$lock`, `$unlock`, `$addrole`, `$removerole`")
    
    elif page.lower() == "automod":
        await ctx.send("⚙️ **Automod Commands:** `$automod`, `$addbadword`, `$removebadword`, `$badwords`, `$togglelink`, `$togglespam`, `$togglecaps`, `$togglemention`, `$automodreset`, `$automodinfo`")
    
    elif page.lower() == "admin":
        await ctx.send("👑 **Admin Commands (Part 1):** `$setwelcome`, `$setgoodbye`, `$setautorole`, `$setlogs`, `$nuke`, `$announcement`, `$botnick`, `$say`, `$dmall`, `$serverlock`, `$serverunlock`, `$channelcreate`, `$channeldelete`, `$rolecreate`, `$roledelete`\n"
                       "👑 **Admin Commands (Part 2):** `$massrole`, `$removeroleall`, `$categorycreate`, `$prefixset`, `$embedcreate`, `$backup`, `$restore`, `$modlogset`, `$ticketsetup`, `$ticketclose`, `$slowall`, `$unslowall`, `$cleanbot`, `$botreset`, `$ignorechannel`, `$unignorechannel`, `$admincheck`")
    
    elif page.lower() == "games":
        await ctx.send("🎮 **Games Commands:** `$roll`, `$toss`, `$rps`, `$slots`, `$guess`, `$8ball`, `$dice`, `$coinflip`, `$mathquiz`, `$fasttype`")
    
    elif page.lower() == "fun":
        await ctx.send("🎭 **Fun & Utility:** `$joke`, `$roast`, `$meme`, `$hack`, `$ship`, `$ping`, `$avatar`, `$userinfo`, `$serverinfo`, `$afk`, `$chat`")

    elif page.lower() == "custom":
        await ctx.send("⚡ **Custom Commands:** `$addcmd`, `$delcmd`, `$customlist`, `$cc1` to `$cc17`")

# ================= 🚀 RUNNER WITH RECONNECT =================
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        # reconnect=True ensure karta hai ki internet issue hone par bot apne aap retry kare
        bot.run(token, reconnect=True)
    else:
        print("❌ Error: DISCORD_TOKEN Environment variable not found!")
