import discord
from discord.ext import commands
from discord import app_commands
import os, json, datetime, asyncio, re

# ================== KONFIGURÁCIÓ ==================
TOKEN = os.getenv("DISCORD_TOKEN")
WARN_FILE = "warns.json"
WELCOME_FILE = "welcome.json"
LEAVE_FILE = "leave.json"
AUTO_ROLE_FILE = "autorole.json"
VIDEO_FILE = "videos.json"

FORBIDDEN_WORDS = ["fasz","geci","buzi","bazdmeg","kurva","anyád","szar","szarka","any@d","apád","cigány"]
LINK_REGEX = r"http[s]?://"
user_messages = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================== SEGÉDFÜGGVÉNYEK ==================
def load_json(file):
    if not os.path.exists(file): return {}
    try:
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def make_embed(title, desc, color):
    e = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.datetime.utcnow())
    e.set_footer(text="✨ SERVICE | HUN ✨")
    return e

def mod_check(i: discord.Interaction):
    return i.user.guild_permissions.administrator or i.user.guild_permissions.manage_messages

# ================== ESEMÉNYEK ==================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online: {bot.user}")

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    
    # Moderátor mentesség ellenőrzése
    is_mod = msg.author.guild_permissions.administrator or msg.author.guild_permissions.manage_messages
    uid = str(msg.author.id)
    now = datetime.datetime.now()

    if not is_mod:
        # --- AUTO ANTI-SPAM ---
        user_messages.setdefault(uid, [])
        user_messages[uid] = [t for t in user_messages[uid] if (now - t).total_seconds() < 3]
        user_messages[uid].append(now)
        
        if len(user_messages[uid]) > 5:
            await msg.delete()
            await msg.author.timeout(datetime.timedelta(minutes=10))
            await msg.channel.send(embed=make_embed("🛡️ Auto Anti-Spam", f"⚠️ {msg.author.mention}, ne spamelj!", discord.Color.red()), delete_after=10)
            return

        # --- LINK ÉS KÁROMKODÁS SZŰRŐ ---
        txt = msg.content.lower()
        if re.search(LINK_REGEX, txt) or any(w in txt for w in FORBIDDEN_WORDS):
            await msg.delete()
            data = load_json(WARN_FILE)
            data.setdefault(uid, [])
            data[uid].append("Automata szűrő")
            save_json(WARN_FILE, data)
            mute_m = len(data[uid]) * 2
            await msg.author.timeout(datetime.timedelta(minutes=mute_m))
            await msg.channel.send(embed=make_embed("🛡️ Automod", f"👤 {msg.author.mention}\n🔇 Némítás: {mute_m} perc", discord.Color.orange()))
            return

    await bot.process_commands(msg)

@bot.event
async def on_member_join(m):
    ar = load_json(AUTO_ROLE_FILE)
    role = m.guild.get_role(ar.get("role_id", 0))
    if role: await m.add_roles(role)
    data = load_json(WELCOME_FILE)
    ch = m.guild.get_channel(data.get("channel_id", 0))
    if ch: await ch.send(f"👋 Üdv a szerveren {m.mention}!")

@bot.event
async def on_member_remove(m):
    data = load_json(LEAVE_FILE)
    ch = m.guild.get_channel(data.get("channel_id", 0))
    if ch: await ch.send(f"🚪 {m.name} elment.")

# ================== PARANCSOK ==================
@bot.tree.command(name="üdvözlő_beállítás")
@app_commands.check(mod_check)
async def welcome_set(i: discord.Interaction, csatorna: discord.TextChannel):
    save_json(WELCOME_FILE, {"channel_id": csatorna.id})
    await i.response.send_message("✅ Üdvözlő beállítva.", ephemeral=True)

@bot.tree.command(name="kilépő_beállítás")
@app_commands.check(mod_check)
async def leave_set(i: discord.Interaction, csatorna: discord.TextChannel):
    save_json(LEAVE_FILE, {"channel_id": csatorna.id})
    await i.response.send_message("✅ Kilépő beállítva.", ephemeral=True)

@bot.tree.command(name="autorole_beállítás")
@app_commands.check(mod_check)
async def autorole_set(i: discord.Interaction, rang: discord.Role):
    save_json(AUTO_ROLE_FILE, {"role_id": rang.id})
    await i.response.send_message("✅ Autorole beállítva.", ephemeral=True)

@bot.tree.command(name="figyelmeztetés")
@app_commands.check(mod_check)
async def warn(i: discord.Interaction, tag: discord.Member, indok: str):
    data = load_json(WARN_FILE)
    data.setdefault(str(tag.id), []).append(indok)
    save_json(WARN_FILE, data)
    mt = len(data[str(tag.id)]) * 2
    await tag.timeout(datetime.timedelta(minutes=mt))
    await i.response.send_message(embed=make_embed("⚠️ Warn", f"{tag.mention} - {indok}\n🔇 {mt} perc némítás", discord.Color.orange()))

@bot.tree.command(name="némítás")
@app_commands.check(mod_check)
async def mute(i: discord.Interaction, tag: discord.Member, perc: int, indok: str):
    await tag.timeout(datetime.timedelta(minutes=perc))
    await i.response.send_message(f"🔇 {tag.mention} némítva {perc} percre. (Indok: {indok})")

@bot.tree.command(name="kirúgás")
@app_commands.check(mod_check)
async def kick(i: discord.Interaction, tag: discord.Member, indok: str):
    await tag.timeout(datetime.timedelta(minutes=15))
    await i.response.send_message(embed=make_embed("🛡️ Anti-Spam", f"👤 {tag.mention}\n📄 Indok: {indok}\n🔇 15 perc némítás", discord.Color.blue()))

@bot.tree.command(name="kitiltás")
@app_commands.check(mod_check)
async def ban(i: discord.Interaction, tag: discord.Member, indok: str):
    await tag.ban(reason=indok)
    await i.response.send_message(f"🚫 {tag.mention} kitiltva.")

@bot.tree.command(name="videó")
@app_commands.check(mod_check)
async def video(i: discord.Interaction, szoveg: str, video: discord.Attachment):
    await i.response.defer()
    data = load_json(VIDEO_FILE)
    data["count"] = data.get("count", 146) + 1
    save_json(VIDEO_FILE, data)
    await i.followup.send(content=f"**{data['count']}. Sikeres trade**\n{szoveg}", file=await video.to_file())

if TOKEN:
    bot.run(TOKEN)
  
