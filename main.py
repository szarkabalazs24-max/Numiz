import discord
from discord.ext import commands
from discord import app_commands
import os, json, datetime, asyncio, random, re

TOKEN = os.getenv("DISCORD_TOKEN")
WARN_FILE, WELCOME_FILE, LEAVE_FILE = "warns.json", "welcome.json", "leave.json"
AUTO_ROLE_FILE, VIDEO_FILE = "autorole.json", "videos.json"
FORBIDDEN_WORDS = ["fasz","geci","buzi","bazdmeg","kurva","anyád","szar","szarka","any@d","apád","cigány"]
LINK_REGEX, user_messages = r"http[s]?://", {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f, "r", encoding="utf-8") as file: return json.load(file)
    except: return {}

def save_json(f, d):
    with open(f, "w", encoding="utf-8") as file: json.dump(d, file, indent=4, ensure_ascii=False)

def make_embed(t, d, c):
    e = discord.Embed(title=t, description=d, color=c, timestamp=datetime.datetime.utcnow())
    e.set_footer(text="✨ SERVICE | HUN ✨")
    return e

def mod_check(i: discord.Interaction): return i.user.guild_permissions.administrator or i.user.guild_permissions.manage_messages

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online: {bot.user}")

@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    is_mod = mod_check(msg) # Segéd hívás
    uid, now = str(msg.author.id), datetime.datetime.now()

    if not is_mod:
        # AUTO ANTI-SPAM
        user_messages.setdefault(uid, [])
        user_messages[uid] = [t for t in user_messages[uid] if (now - t).total_seconds() < 3]
        user_messages[uid].append(now)
        if len(user_messages[uid]) > 5:
            await msg.delete()
            await msg.author.timeout(datetime.timedelta(minutes=10))
            await msg.channel.send(embed=make_embed("🛡️ Auto Anti-Spam", f"{msg.author.mention}, ne spamelj!", discord.Color.red()), delete_after=10)
            return
        
        # LINK ÉS KÁROMKODÁS
        txt = msg.content.lower()
        if re.search(LINK_REGEX, txt) or any(w in txt for w in FORBIDDEN_WORDS):
            await msg.delete()
            data = load_json(WARN_FILE); data.setdefault(uid, []); data[uid].append("Automata szűrő"); save_json(WARN_FILE, data)
            m_time = len(data[uid]) * 2
            await msg.author.timeout(datetime.timedelta(minutes=m_time))
            await msg.channel.send(embed=make_embed("🛡️ Automod", f"{msg.author.mention} büntetve. 🔇 {m_time} perc", discord.Color.orange()))
            return

    await bot.process_commands(msg)

@bot.event
async def on_member_join(m):
    ar = load_json(AUTO_ROLE_FILE); role = m.guild.get_role(ar.get("role_id", 0))
    if role: await m.add_roles(role)
    data = load_json(WELCOME_FILE); ch = m.guild.get_channel(data.get("channel_id", 0))
    if ch: await ch.send(f"👋 Üdv {m.mention}!")

@bot.event
async def on_member_remove(m):
    data = load_json(LEAVE_FILE); ch = m.guild.get_channel(data.get("channel_id", 0))
    if ch: await ch.send(f"🚪 {m.name} elment.")

@bot.tree.command(name="üdvözlő_beállítás")
@app_commands.check(mod_check)
async def w_set(i, ch: discord.TextChannel): save_json(WELCOME_FILE, {"channel_id": ch.id}); await i.response.send_message("✅")

@bot.tree.command(name="kilépő_beállítás")
@app_commands.check(mod_check)
async def l_set(i, ch: discord.TextChannel): save_json(LEAVE_FILE, {"channel_id": ch.id}); await i.response.send_message("✅")

@bot.tree.command(name="autorole_beállítás")
@app_commands.check(mod_check)
async def a_set(i, r: discord.Role): save_json(AUTO_ROLE_FILE, {"role_id": r.id}); await i.response.send_message("✅")

@bot.tree.command(name="figyelmeztetés")
@app_commands.check(mod_check)
async def warn(i, t: discord.Member, indok: str):
    d = load_json(WARN_FILE); d.setdefault(str(t.id), []).append(indok); save_json(WARN_FILE, d)
    mt = len(d[str(t.id)]) * 2
    await t.timeout(datetime.timedelta(minutes=mt))
    await i.response.send_message(embed=make_embed("⚠️ Warn", f"{t.mention} - {indok}\n🔇 {mt} perc", discord.Color.orange()))

@bot.tree.command(name="némítás")
@app_commands.check(mod_check)
async def mute(i, t: discord.Member, p: int, ind: str):
    await t.timeout(datetime.timedelta(minutes=p)); await i.response.send_message(f"🔇 {t.mention} {p} perc.")

@bot.tree.command(name="kirúgás")
@app_commands.check(mod_check)
async def kick(i, t: discord.Member, indok: str):
    await t.timeout(datetime.timedelta(minutes=15))
    await i.response.send_message(embed=make_embed("🛡️ Anti-Spam", f"👤 {t.mention}\n📄 Indok: {indok}\n🔇 15 perc némítás", discord.Color.blue()))

@bot.tree.command(name="kitiltás")
@app_commands.check(mod_check)
async def ban(i, t: discord.Member, ind: str):
    await t.ban(reason=ind); await i.response.send_message(f"🚫 {t.mention} kitiltva.")

@bot.tree.command(name="videó")
@app_commands.check(mod_check)
async def video(i, sz: str, v: discord.Attachment):
    await i.response.defer(); d = load_json(VIDEO_FILE); d["count"] = d.get("count", 146) + 1; save_json(VIDEO_FILE, d)
    await i.followup.send(content=f"**{d['count']}. Trade**\n{sz}", file=await v.to_file())

if TOKEN: bot.run(TOKEN)
                      
