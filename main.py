import discord
from discord.ext import commands
from discord import app_commands
import os, json, datetime, asyncio, re

# ================== ALAP BEÁLLÍTÁSOK ==================

TOKEN = os.getenv("DISCORD_TOKEN")

# Fájlnevek
WARN_FILE = "warns.json"
WELCOME_FILE = "welcome.json"
LEAVE_FILE = "leave.json"
AUTO_ROLE_FILE = "autorole.json"
VIDEO_COUNTER_FILE = "video_counter.json"

FORBIDDEN_WORDS = [
    "fasz","geci","buzi","bazdmeg","kurva","anyád","szar",
    "szarka","any@d","apád","cigány"
]
LINK_REGEX = r"http[s]?://"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= SEGÉDFÜGGVÉNYEK =================

def load_json(file):
    try:
        if not os.path.exists(file):
            if file == VIDEO_COUNTER_FILE: return {"count": 147}
            return {}
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        if file == VIDEO_COUNTER_FILE: return {"count": 147}
        return {}

def save_json(file, data):
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Hiba a mentés során ({file}): {e}")

def make_embed(title, desc, color):
    e = discord.Embed(
        title=title,
        description=desc,
        color=color,
        timestamp=datetime.datetime.utcnow()
    )
    e.set_footer(text="✨ SERVICE | HUN ✨")
    return e

def mod_check(i: discord.Interaction):
    return i.user.guild_permissions.administrator or i.user.guild_permissions.manage_messages

# ================= ESEMÉNYEK =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online: {bot.user}")

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return

    is_mod = msg.author.guild_permissions.administrator or msg.author.guild_permissions.manage_messages
    txt = msg.content.lower()
    
    # Automod - Linkek (Moderátoroknak szabad)
    if not is_mod and re.search(LINK_REGEX, txt):
        try:
            await msg.delete()
            uid = str(msg.author.id)
            data = load_json(WARN_FILE)
            data.setdefault(uid, [])
            data[uid].append("Tiltott link")
            save_json(WARN_FILE, data)
            
            mute_time = len(data[uid]) * 2
            await msg.author.timeout(datetime.timedelta(minutes=mute_time))
            await msg.channel.send(embed=make_embed("🔗 Automod", f"{msg.author.mention} linket küldött.\n⚠️ Figyelmeztetések: {len(data[uid])}\n🔇 Némítás: {mute_time} perc", discord.Color.red()))
        except: pass
        return

    # Automod - Káromkodás
    if any(w in txt for w in FORBIDDEN_WORDS):
        try:
            await msg.delete()
            uid = str(msg.author.id)
            data = load_json(WARN_FILE)
            data.setdefault(uid, [])
            data[uid].append("Káromkodás")
            save_json(WARN_FILE, data)
            
            mute_time = len(data[uid]) * 2
            await msg.author.timeout(datetime.timedelta(minutes=mute_time))
            await msg.channel.send(embed=make_embed("🤬 Automod", f"{msg.author.mention} káromkodott.\n⚠️ Figyelmeztetések: {len(data[uid])}\n🔇 Némítás: {mute_time} perc", discord.Color.orange()))
        except: pass
        return

    await bot.process_commands(msg)

# ================= VIDEO PARANCS =================

@bot.tree.command(name="video", description="Videós bizonyíték feltöltése sorszámmal")
@app_commands.check(mod_check)
async def video_send(i: discord.Interaction, szoveg: str, video: discord.Attachment):
    # Railway-en fontos: jelezzük a Discordnak, hogy dolgozunk (defer)
    await i.response.defer()

    if not any(video.content_type.startswith(t) for t in):
        return await i.followup.send("❌ Kérlek, videót vagy képet tölts fel!", ephemeral=True)

    data = load_json(VIDEO_COUNTER_FILE)
    count = data.get("count", 147)
    
    formatted_msg = f"{szoveg}\n📸 **{count}. Bizonyíték:**"
    
    try:
        file = await video.to_file()
        await i.followup.send(content=formatted_msg, file=file)
        
        # Csak sikeres küldés után növeljük a számlálót
        data["count"] = count + 1
        save_json(VIDEO_COUNTER_FILE, data)
    except Exception as e:
        await i.followup.send(f"❌ Hiba történt a feltöltés során: {e}", ephemeral=True)

# ================= MODERÁCIÓ =================

@bot.tree.command(name="némítás")
@app_commands.check(mod_check)
async def mute(i: discord.Interaction, tag: discord.Member, perc: int, indok: str):
    await tag.timeout(datetime.timedelta(minutes=perc), reason=indok)
    await i.response.send_message(embed=make_embed("🔇 Némítás", f"👤 {tag.mention}\n⏱ {perc} perc\n📄 {indok}", discord.Color.red()))

@bot.tree.command(name="kitiltás")
@app_commands.check(mod_check)
async def ban(i: discord.Interaction, tag: discord.Member, indok: str):
    await tag.ban(reason=indok)
    await i.response.send_message(embed=make_embed("🚫 Kitiltás", f"{tag.mention}\n📄 {indok}", discord.Color.dark_red()))

# ================= BEÁLLÍTÁSOK =================

@bot.tree.command(name="üdvözlő_beállítás")
@app_commands.check(mod_check)
async def welcome_set(i: discord.Interaction, csatorna: discord.TextChannel):
    save_json(WELCOME_FILE, {"channel_id": csatorna.id})
    await i.response.send_message(f"✅ Üdvözlő csatorna: {csatorna.mention}", ephemeral=True)

# ================= BELÉPÉS/KILÉPÉS =================

@bot.event
async def on_member_join(member):
    ar = load_json(AUTO_ROLE_FILE)
    role = member.guild.get_role(ar.get("role_id", 0))
    if role: await member.add_roles(role)
    
    w_data = load_json(WELCOME_FILE)
    ch = member.guild.get_channel(w_data.get("channel_id", 0))
    if ch: await ch.send(f"👋 Üdv {member.mention}! Te vagy a **{member.guild.member_count}.** tag! 💙")

@bot.event
async def on_member_remove(member):
    l_data = load_json(LEAVE_FILE)
    ch = member.guild.get_channel(l_data.get("channel_id", 0))
    if ch: await ch.send(f"🚪 **{member.name}** elment. Köszönjük, hogy itt voltál!")

# ================= INDÍTÁS =================

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ HIÁNYZIK A DISCORD_TOKEN!")
  
