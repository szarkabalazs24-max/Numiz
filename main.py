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

FORBIDDEN_WORDS = ["fasz","geci","buzi","bazdmeg","kurva","anyád","szar","szarka","any@d","apád","cigány"]
LINK_REGEX = r"http[s]?://"
user_messages = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

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
    p = i.user.guild_permissions
    return p.administrator or p.manage_messages

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("✅ Slash parancsok szinkronizálva (Railway)")
    print(f"✅ Bot online: {bot.user}")

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    is_mod = msg.author.guild_permissions.administrator or msg.author.guild_permissions.manage_messages
    uid = str(msg.author.id)
    now = datetime.datetime.now()

    if not is_mod:
        if uid not in user_messages: user_messages[uid] = []
        user_messages[uid] = [t for t in user_messages[uid] if (now - t).total_seconds() < 3]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 5:
            await msg.delete()
            await msg.author.timeout(datetime.timedelta(minutes=10))
            await msg.channel.send(embed=make_embed("🛡️ Auto Anti-Spam", f"⚠️ {msg.author.mention}, ne spamelj!\n🔇 Némítás: 10 perc", discord.Color.red()), delete_after=10)
            return

    txt = msg.content.lower()
    if not is_mod and re.search(LINK_REGEX, txt):
        await msg.delete()
        data = load_json(WARN_FILE); data.setdefault(uid, []); data[uid].append("Link"); save_json(WARN_FILE, data)
        await msg.author.timeout(datetime.timedelta(minutes=len(data[uid])*2))
        await msg.channel.send(embed=make_embed("🔗 Link szűrő", f"{msg.author.mention} linket küldött.", discord.Color.red()))
        return
    if any(w in txt for w in FORBIDDEN_WORDS):
        await msg.delete()
        data = load_json(WARN_FILE); data.setdefault(uid, []); data[uid].append("Káromkodás"); save_json(WARN_FILE, data)
        await msg.author.timeout(datetime.timedelta(minutes=len(data[uid])*2))
        await msg.channel.send(embed=make_embed("🤬 Szűrő", f"{msg.author.mention} káromkodott.", discord.Color.orange()))
        return
    await bot.process_commands(msg)
@bot.event
async def on_member_join(member):
    ar = load_json(AUTO_ROLE_FILE); role = member.guild.get_role(ar.get("role_id", 0))
    if role: await member.add_roles(role)
    data = load_json(WELCOME_FILE); ch = member.guild.get_channel(data.get("channel_id", 0))
    if ch: await ch.send(f"👋 Üdv {member.mention}!\nTe vagy a {member.guild.member_count}. tag 💙")

@bot.event
async def on_member_remove(member):
    data = load_json(LEAVE_FILE); ch = member.guild.get_channel(data.get("channel_id", 0))
    if ch: await ch.send(f"🚪 {member.name} elment.")

@bot.tree.command(name="üdvözlő_beállítás")
@app_commands.check(mod_check)
async def welcome_set(i: discord.Interaction, csatorna: discord.TextChannel):
    save_json(WELCOME_FILE, {"channel_id": csatorna.id}); await i.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="kilépő_beállítás")
@app_commands.check(mod_check)
async def leave_set(i: discord.Interaction, csatorna: discord.TextChannel):
    save_json(LEAVE_FILE, {"channel_id": csatorna.id}); await i.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="autorole_beállítás")
@app_commands.check(mod_check)
async def autorole_set(i: discord.Interaction, rang: discord.Role):
    save_json(AUTO_ROLE_FILE, {"role_id": rang.id}); await i.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="figyelmeztetés")
@app_commands.check(mod_check)
async def warn(i: discord.Interaction, tag: discord.Member, indok: str):
    data = load_json(WARN_FILE); data.setdefault(str(tag.id), []).append(indok); save_json(WARN_FILE, data)
    await tag.timeout(datetime.timedelta(minutes=len(data[str(tag.id)])*2))
    await i.response.send_message(embed=make_embed("⚠️ Warn", f"{tag.mention} - {indok}", discord.Color.orange()))

@bot.tree.command(name="figyelmeztetés_törlés")
@app_commands.check(mod_check)
async def warn_del(i: discord.Interaction, tag: discord.Member, szám: int):
    data = load_json(WARN_FILE); warns = data.get(str(tag.id), [])
    if 0 < szám <= len(warns): warns.pop(szám-1); save_json(WARN_FILE, data); await i.response.send_message("✅")
    else: await i.response.send_message("❌", ephemeral=True)

@bot.tree.command(name="némítás")
@app_commands.check(mod_check)
async def mute(i: discord.Interaction, tag: discord.Member, perc: int, indok: str):
    await tag.timeout(datetime.timedelta(minutes=perc))
    await i.response.send_message(embed=make_embed("🔇 Mute", f"{tag.mention} - {perc}m", discord.Color.red()))

@bot.tree.command(name="némítás_feloldás")
@app_commands.check(mod_check)
async def unmute(i: discord.Interaction, tag: discord.Member):
    await tag.timeout(None); await i.response.send_message("🔊")

@bot.tree.command(name="kirúgás")
@app_commands.check(mod_check)
async def kick(i: discord.Interaction, tag: discord.Member, indok: str):
    await tag.timeout(datetime.timedelta(minutes=15))
    await i.response.send_message(embed=make_embed("🛡️ Manuális Anti-Spam", f"👤 **{tag.mention}**\n📄 **Indok:** {indok}\n🔇 **Némítás:** 15 perc", discord.Color.blue()))

@bot.tree.command(name="kitiltás")
@app_commands.check(mod_check)
async def ban(i: discord.Interaction, tag: discord.Member, indok: str):
    await tag.ban(reason=indok)
    await i.response.send_message(embed=make_embed("🚫 Ban", f"{tag.mention}", discord.Color.dark_red()))

@bot.tree.command(name="videó")
@app_commands.check(mod_check)
async def video(i: discord.Interaction, szoveg: str, video: discord.Attachment):
    await i.response.defer(); data = load_json(VIDEO_FILE); data["count"] = data.get("count", 146) + 1; save_json(VIDEO_FILE, data)
    await i.followup.send(content=f"**{data['count']}. Trade**\n{szoveg}", file=await video.to_file())

if TOKEN:
    bot.run(TOKEN)
      
