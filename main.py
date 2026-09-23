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
from discord.ui import Button, View, Select

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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="$help | MID Next-Gen 🚀"))
    
    if not self_ping.is_running():
        self_ping.start()

    for guild in bot.guilds:
        try:
            invites_cache[guild.id] = await guild.invites()
        except Exception:
            invites_cache[guild.id] = []

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ **Syntax Error:** `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Access Denied:** Aapke paas permissions nahi hain bro!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Mentioned member server me nahi mila!")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Mere paas required permissions (Admin/Manage Roles/Channels) nahi hain!")
    else:
        print(f"Error: {error}")

# ================= 🎫 R.O.T.I STYLE TICKET SYSTEM =================
class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 Ticket 5 seconds me close ho raha hai...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Claim Ticket 🛡️", style=discord.ButtonStyle.green, custom_id="claim_ticket_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Support team members hi ticket claim kar sakte hain!", ephemeral=True)
            return
        
        emb = discord.Embed(
            description=f"✅ **Ticket claimed by {interaction.user.mention}!**\nAb ye staff member aapki help karenge.",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=emb)

class TicketLaunchView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket 📩", style=discord.ButtonStyle.blurple, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        cat_id = ticket_category_db.get(guild.id)
        category = guild.get_channel(cat_id) if cat_id else None
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ch = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        
        emb = discord.Embed(
            title="🎫 Welcome to Support!",
            description=f"Hey {interaction.user.mention}, apni query yahan drop karo.\nStaff team bohot jaldi response karegi!",
            color=0x3498db
        )
        emb.set_footer(text="MID Ticket System • R.O.T.I Style UI")
        
        await ch.send(content=f"{interaction.user.mention}", embed=emb, view=TicketControlView())
        await interaction.response.send_message(f"✅ Ticket ban gaya hai: {ch.mention}", ephemeral=True)

# ================= 📜 INTERACTIVE DROPDOWN $HELP MENU =================
class HelpDropdown(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Moderation", description="Ban, Kick, Mute, Warn commands", emoji="🛡️"),
            discord.SelectOption(label="Admin & Setup", description="Nuke, Ticket, Welcome, Roles", emoji="👑"),
            discord.SelectOption(label="Games & Economy", description="Roll, Slots, RPS, Coinflip", emoji="🎮"),
            discord.SelectOption(label="Fun & Utility", description="Avatar, Ping, Custom Tag, AFK", emoji="🎭"),
        ]
        super().__init__(placeholder="⚡ Command Category Select Karo...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Moderation":
            emb = discord.Embed(title="🛡️ Moderation Commands", color=0xe74c3c)
            emb.description = "`$ban`, `$unban`, `$kick`, `$mute`, `$unmute`, `$warn`, `$warnings`, `$clearwarns`, `$purge`, `$slowmode`, `$lock`, `$unlock`, `$addrole`, `$removerole`"
        elif self.values[0] == "Admin & Setup":
            emb = discord.Embed(title="👑 Admin Commands", color=0xf1c40f)
            emb.description = "`$nuke`, `$setnick`, `$customtag`, `$setwelcome`, `$setgoodbye`, `$setautorole`, `$setlogs`, `$poll`, `$embed`, `$serverlock`, `$serverunlock`, `$announcement`, `$botnick`, `$say`, `$ticketsetup`, `$dmall`"
        elif self.values[0] == "Games & Economy":
            emb = discord.Embed(title="🎮 Games Commands", color=0x2ecc71)
            emb.description = "`$roll`, `$toss`, `$rps`, `$slots`, `$guess`, `$8ball`, `$dice`, `$coinflip`, `$mathquiz`, `$fasttype`"
        elif self.values[0] == "Fun & Utility":
            emb = discord.Embed(title="🎭 Fun & Utility Commands", color=0x9b59b6)
            emb.description = "`$ping`, `$avatar`, `$userinfo`, `$serverinfo`, `$afk`, `$hack`, `$chat`"
        
        emb.set_footer(text="MID Bot • Next-Gen Panel")
        await interaction.response.send_message(embed=emb, ephemeral=True)

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpDropdown())

# ================= 👥 INVITE TRACKER & WELCOME EVENT =================
@bot.event
async def on_member_join(member):
    guild = member.guild
    inviter_text = "Unknown Inviter"

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

    if guild.id in autorole_db:
        role = guild.get_role(autorole_db[guild.id])
        if role:
            try: await member.add_roles(role)
            except: pass

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

# ================= 🛡️ AUTOMOD & FRIENDLY CHAT SYSTEM =================
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

    # Friendly Hinglish AI Chat on MID Trigger
    if bot.user.mentioned_in(message) or "mid" in content.lower().split():
        friendly_responses = [
            f"How can I help u bro? Bolo kya scene hai {message.author.mention}? 😎",
            f"Haan bhai {message.author.mention}, batao kya help chahiye?",
            f"Yo {message.author.mention}! Bot full active hai, bolo kya kaam hai?",
            "Kaise ho bhai? Main ekdam mast hu, batao aaj kya plan hai?",
            f"Arey {message.author.mention} bhai! Chill maar, MID tere saath hai!⚡"
        ]
        await message.channel.send(random.choice(friendly_responses))
        return

    # Automod Checks for Non-Admins
    if not message.author.guild_permissions.administrator:
        now = time.time()
        
        if AUTOMOD_CONFIG["anti_spam"]:
            if author_id not in message_track: message_track[author_id] = []
            message_track[author_id].append(now)
            message_track[author_id] = [t for t in message_track[author_id] if now - t < 4]
            if len(message_track[author_id]) > 5:
                await message.delete()
                await message.channel.send(f"🚨 {message.author.mention}, spam mat karo bhai!", delete_after=3)
                return

        if any(word in content.lower() for word in AUTOMOD_CONFIG["badwords"]):
            await message.delete()
            await message.channel.send(f"🚫 Bad words yahan allowed nahi hain!", delete_after=3)
            return

        if AUTOMOD_CONFIG["anti_link"] and ("http://" in content or "https://" in content or "discord.gg/" in content):
            await message.delete()
            await message.channel.send(f"🔗 Links allow nahi hain bro!", delete_after=3)
            return

    await bot.process_commands(message)

# ================= 👑 ADMIN COMMANDS & CUSTOM TAGS =================
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def setnick(ctx, member: discord.Member, *, nickname: str):
    await member.edit(nick=nickname)
    await ctx.send(f"✅ **{member.name}** ka nickname badal kar **{nickname}** kar diya!")

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def customtag(ctx, member: discord.Member, tag: str):
    new_nick = f"[{tag}] {member.display_name}"
    await member.edit(nick=new_nick)
    await ctx.send(f"🚀 **{member.mention}** ko custom tag mil gaya: `{new_nick}`")

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketsetup(ctx):
    category = await ctx.guild.create_category("📩 TICKETS")
    ticket_category_db[ctx.guild.id] = category.id
    
    emb = discord.Embed(
        title="🎫 Support Ticket Center",
        description="Aapko koi help chahiye ya support team se baat karni hai?\nNiche button par click karke ticket open karein!",
        color=0x00ffff
    )
    emb.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    emb.set_footer(text="MID Ticket System • R.O.T.I Style")
    
    await ctx.send(embed=emb, view=TicketLaunchView())

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    pos = ctx.channel.position
    new_ch = await ctx.channel.clone(reason="Nuke Channel")
    await ctx.channel.delete()
    await new_ch.edit(position=pos)
    await new_ch.send("💥 **Channel reset kar diya gaya hai!**")

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

# ================= 🛡️ MODERATION COMMANDS =================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="None"):
    warnings_db[member.id] = warnings_db.get(member.id, 0) + 1
    current_warns = warnings_db[member.id]
    
    if current_warns >= 3:
        try:
            await member.timeout(timedelta(minutes=20), reason="Reached 3 Warnings")
            warnings_db[member.id] = 0
            await ctx.send(f"🚨 **{member.mention} ko 3 Warnings hone par 20 minutes Timeout de diya gaya hai!**")
        except Exception:
            await ctx.send(f"⚠️ 3 warnings ho gaye hain, lekin permissions lack hone se timeout nahi laga.")
    else:
        await ctx.send(f"⚠️ **{member.name}** ko warn kiya gaya! (Warnings: **{current_warns}/3**) | Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="None"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned **{member.name}** | Reason: {reason}")

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
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Cleared {amount} messages!", delete_after=3)

# ================= 🎭 FUN, UTILITY & GAMES =================
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: **{round(bot.latency * 1000)}ms**")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    m = member or ctx.author
    await ctx.send(m.display_avatar.url)

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"💤 {ctx.author.mention} ab AFK hai: {reason}")

@bot.command()
async def roll(ctx): await ctx.send(f"🎲 Rolled: **{random.randint(1, 6)}**")

@bot.command()
async def toss(ctx): await ctx.send(f"🪙 Coin Result: **{random.choice(['Heads', 'Tails'])}**")

@bot.command()
async def slots(ctx):
    e = ["🍎", "🍋", "🍒"]
    a, b, c = random.choice(e), random.choice(e), random.choice(e)
    await ctx.send(f"[ {a} | {b} | {c} ] -> {'🎉 WIN!' if a==b==c else '❌ Try Again!'}")

# ================= 📜 MASTER $HELP COMMAND =================
@bot.command(name="help")
async def help_cmd(ctx):
    emb = discord.Embed(
        title="🤖 MID Discord Master Control Panel",
        description="Niche dropdown menu se category select karo saare commands ek hi jagah dekhne ke liye!",
        color=0x00ffff
    )
    emb.add_field(name="✨ Key Highlights", value="• Dropdown Help Menu\n• R.O.T.I Style Button Tickets\n• Friendly Hinglish Chat (`MID`)\n• Custom Tags & Nick Manager", inline=False)
    emb.set_thumbnail(url=bot.user.display_avatar.url)
    emb.set_footer(text="MID Bot 24/7 Active • Powered by Render")
    
    await ctx.send(embed=emb, view=HelpView())

# ================= 🚀 RUNNER =================
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token, reconnect=True)
    else:
        print("❌ Error: DISCORD_TOKEN Environment variable missing!")
