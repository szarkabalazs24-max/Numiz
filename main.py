import discord
from discord.ext import commands
from discord import app_commands
import os, json, datetime, asyncio, random, re

# ================== ALAP ==================

TOKEN = os.getenv("DISCORD_TOKEN")

WARN_FILE = "warns.json"
WELCOME_FILE = "welcome.json"
LEAVE_FILE = "leave.json"
AUTO_ROLE_FILE = "autorole.json"
VIDEO_FILE = "videos.json"

FORBIDDEN_WORDS = [
    "fasz","geci","buzi","bazdmeg","kurva","anyád","szar",
    "szarka","any@d","apád","cigány"
]
LINK_REGEX = r"http[s]?://"

# Anti-spam tároló
user_messages = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= SEGÉD =================

def load_json(file):
    if not os.path.exists(file):
        return {}
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
    p = i.user.guild_permissions
    return p.administrator or p.manage_messages

# ================= READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Slash parancsok szinkronizálva (Railway)")
    print(f"✅ Bot online: {bot.user}")

# ================= AUTOMOD & AUTO ANTI-SPAM =================

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild:
        return

    is_mod = msg.author.guild_permissions.administrator or msg.author.guild_permissions.manage_messages
    uid = str(msg.author.id)
    now = datetime.datetime.now()

    # --- AUTO ANTI-SPAM LOGIKA ---
    if not is_mod:
        if uid not in user_messages:
            user_messages[uid] = []
        
        user_messages[uid] = [t for t in user_messages[uid] if (now - t).total_seconds() < 3]
        user_messages[uid].append(now)

        if len(user_messages[uid]) > 5:
            await msg.delete()
            data = load_json(WARN_FILE)
            data.setdefault(uid, [])
            data[uid].append("Auto Anti-Spam")
            save_json(WARN_FILE, data)

            mute_time = 10
            await msg.author.timeout(datetime.timedelta(minutes=mute_time))

            await msg.channel.send(
                embed=make_embed(
                    "🛡️ Auto Anti-Spam",
                    f"⚠️ {msg.author.mention}, ne spamelj!\n"
                    f"📄 Indok: Túl gyors üzenetküldés\n"
                    f"🔇 Némítás: {mute_time} perc",
                    discord.Color.red()
                ), delete_after=10
            )
            return

    # LINK SZŰRŐ
    txt = msg.content.lower()
    if not is_mod and re.search(LINK_REGEX, txt):
        await msg.delete()
        data = load_json(WARN_FILE)
        data.setdefault(uid, [])
        data[uid].append("Tiltott link küldése")
        save_json(WARN_FILE, data)
        mute_time = len(data[uid]) * 2
        await msg.author.timeout(datetime.timedelta(minutes=mute_time))
        await msg.channel.send(embed=make_embed("🔗 Automatikus figyelmeztetés", f"👤 {msg.author.mention}\n📄 Indok: Tiltott link\n⚠️ Figy: {len(data[uid])}\n🔇 Némítás: {mute_time} perc", discord.Color.red()))
        return

    # KÁROMKODÁS
    if any(w in txt for w in FORBIDDEN_WORDS):
        await msg.delete()
        data = load_json(WARN_FILE)
        data.setdefault(uid, [])
        data[uid].append("Káromkodás")
        save_json(WARN_FILE, data)
        mute_time = len(data[uid]) * 2
        await msg.author.timeout(datetime.timedelta(minutes=mute_time))
        await msg.channel.send(embed=make_embed("🤬 Automatikus figyelmeztetés", f"👤 {msg.author.mention}\n📄 Indok: Káromkodás\n⚠️ Figy: {len(data[uid])}\n🔇 Némítás: {mute_time} perc", discord.Color.orange()))
        return

    await bot.process_commands(msg)

# ================= BELÉPÉS / KILÉPÉS / BEÁLLÍTÁSOK (Változatlan) =================
# ... [Itt a kódod többi része változatlan marad a korábbiak szerint] ...

# ================= FIGYELMEZTETÉS / NÉMÍTÁS (Változatlan) =================
# ... [Itt a kódod többi része változatlan marad a korábbiak szerint] ...

# ================= KIRÚGÁS HELYÉN AZ ANTI-SPAM =================

@bot.tree.command(name="kirúgás") # A név megmaradt, de a funkció Anti-Spam lett
@app_commands.check(mod_check)
async def kick(i: discord.Interaction, tag: discord.Member, indok: str):
    # Kirúgás helyett most manuális Anti-Spam figyelmeztetést küld és némít
    await tag.timeout(datetime.timedelta(minutes=15))
    
    await i.response.send_message(
        embed=make_embed(
            "🛡️ Manuális Anti-Spam",
            f"👤 **Felhasználó:** {tag.mention}\n"
            f"📄 **Indok:** {indok}\n"
            f"🔇 **Némítás:** 15 perc\n"
            f"👮‍♂️ **Adminisztrátor:** {i.user.mention}",
            discord.Color.dark_blue()
        )
    )

# ================= KITILTÁS & VIDEÓ (Változatlan) =================

@bot.tree.command(name="kitiltás")
@app_commands.check(mod_check)
async def ban(i: discord.Interaction, tag: discord.Member, indok: str):
    await tag.ban(reason=indok)
    await i.response.send_message(embed=make_embed("🚫 Kitiltás", f"{tag.mention}\n📄 {indok}\n👮‍♂️ {i.user.mention}", discord.Color.dark_red()))

@bot.tree.command(name="videó")
@app_commands.check(mod_check)
async def video(i: discord.Interaction, szoveg: str, video: discord.Attachment):
    await i.response.defer()
    if not video.content_type or not video.content_type.startswith("video"):
        return await i.followup.send("❌ Csak videó tölthető fel", ephemeral=True)
    data = load_json(VIDEO_FILE)
    data["count"] = data.get("count", 146) + 1
    save_json(VIDEO_FILE, data)
    await i.followup.send(content=f"**{data['count']}. Sikeres trade bizonyíték**\n{szoveg}\n📸 Bizonyíték:", file=await video.to_file())

if TOKEN:
    bot.run(TOKEN)
  
