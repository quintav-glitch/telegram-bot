import os
import io
import json
import requests
import urllib.parse
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

# ---------------------------------------------
# CONFIG
# ---------------------------------------------

BOT_TOKEN = "8595570620:AAFOMUMHKDlZUDRb37DAqVFmc8xVTJEB5-k"
ADMIN_ID = 6695034607
CHANNEL_USERNAME = "dev_portal_2"
DB_FILE = "users.json"
REF_BONUS = 5

# SMM Key
SMM_API_KEY = "mkdevClT5NtYU9f5n_unlimited_1"

# RegCheck username (apna username daal dena)
REGCHECK_USERNAME = "ITACHI_UCHIHA_34"

# ---------------------------------------------
# DB HELPERS
# ---------------------------------------------

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

def init_user(user_id: int):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "credits": 10,
            "last_bonus": "",
            "premium": False,
            "premium_expiry": "",
            "referred_by": "",
            "joined": False
        }
        save_db(db)

# ---------------------------------------------
# PREMIUM + REFERRAL
# ---------------------------------------------

def is_premium(user_id: int) -> bool:
    db = load_db()
    user = db.get(str(user_id))
    if not user or not user.get("premium"):
        return False
    expiry = user.get("premium_expiry")
    if expiry == "lifetime":
        return True
    if expiry:
        try:
            return datetime.now() < datetime.strptime(expiry, "%Y-%m-%d")
        except:
            return False
    return False

def apply_referral(new_user_id: int, ref_id: int) -> bool:
    db = load_db()
    new_uid = str(new_user_id)
    ref_uid = str(ref_id)
    if new_uid not in db:
        return False
    new_user = db[new_uid]
    if new_user.get("joined"):
        return False
    if ref_uid not in db or new_uid == ref_uid:
        return False

    ref_user = db[ref_uid]
    ref_user["credits"] = ref_user.get("credits", 0) + REF_BONUS
    new_user["referred_by"] = ref_uid
    new_user["joined"] = True
    save_db(db)
    return True

# ---------------------------------------------
# GENERIC API HELPER
# ---------------------------------------------

def safe_api(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=20)

        content_type = r.headers.get("Content-Type", "")
        if any(x in content_type for x in ["video", "image", "octet-stream", "audio"]):
            return {"binary": r.content, "type": content_type}

        try:
            return r.json()
        except:
            return {"raw": r.text[:2000]}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------
# MENUS
# ---------------------------------------------

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 FF UID", callback_data="ffuid"),
         InlineKeyboardButton("📸 Insta", callback_data="insta")],
        [InlineKeyboardButton("📍 Pincode", callback_data="pincode"),
         InlineKeyboardButton("🚗 Vehicle", callback_data="vehicle")],
        [InlineKeyboardButton("🌐 Universal", callback_data="universal"),
         InlineKeyboardButton("🗣 TTS", callback_data="tts")],
        [InlineKeyboardButton("🎨 AI Image", callback_data="aiimg"),
         InlineKeyboardButton("🤖 AI Text", callback_data="aitext")],
        [InlineKeyboardButton("📞 Number", callback_data="num"),
         InlineKeyboardButton("⛅ Weather", callback_data="weather")],
        [InlineKeyboardButton("🎵 Song", callback_data="song"),
         InlineKeyboardButton("🔳 QR Code", callback_data="qr")],
        [InlineKeyboardButton("🎵 TikTok", callback_data="tiktok"),
         InlineKeyboardButton("🐶 Dog", callback_data="dog")],
        [InlineKeyboardButton("🌐 Search", callback_data="search"),
         InlineKeyboardButton("🤖 AI Chat", callback_data="aichat")],
        [InlineKeyboardButton("✨ Enhance", callback_data="enhance"),
         InlineKeyboardButton("🖼 Placeholder", callback_data="phold")],
        [InlineKeyboardButton("💳 My Credits", callback_data="credits")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_panel_menu():
    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("👥 Users", callback_data="admin_total_users")],
        [InlineKeyboardButton("➕ Add Premium", callback_data="admin_add_premium"),
         InlineKeyboardButton("➖ Remove Premium", callback_data="admin_remove_premium")],
        [InlineKeyboardButton("💸 Send Credits", callback_data="admin_send_credits"),
         InlineKeyboardButton("⬅ Menu", callback_data="mainmenu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------------------------------------------
# CHECK JOIN
# ---------------------------------------------

async def ensure_joined(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if chat.type != "private":
        return True

    try:
        member = await context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user.id)
        if member.status in ("member", "administrator", "creator"):
            return True
    except:
        pass

    keyboard = [
        [InlineKeyboardButton("🔔 JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✔️ I HAVE JOINED", callback_data="check_join")],
    ]
    await context.bot.send_message(
        chat.id, "⚠️ Pehle channel join karo:", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return False

# ---------------------------------------------
# MAIN LOGIC PROCESSOR
# ---------------------------------------------

async def process_tool_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, text: str):
    user_id = update.effective_user.id
    init_user(user_id)
    db = load_db()

    # Credit Deduction
    if not is_premium(user_id):
        if db[str(user_id)].get("credits", 0) <= 0:
            await update.message.reply_text("❌ Credits khatam! /daily_bonus use karo.")
            return
        db[str(user_id)]["credits"] -= 1
        save_db(db)

    try:
        # Show typing / uploading
        if mode in ["insta", "universal", "aiimg", "enhance"]:
            await update.message.reply_chat_action("upload_video")
        else:
            await update.message.reply_chat_action("typing")

        # ---------------- FF UID ----------------
        if mode == "ffuid":
            uid = text.strip()
            url = f"https://smm.mksocial.site/api/ff?uid={uid}&key={SMM_API_KEY}"
            res = safe_api(url)

            info = None
            if isinstance(res, dict):
                if "basicInfo" in res:
                    info = res["basicInfo"]
                elif "result" in res:
                    info = res["result"]
                else:
                    info = res

            if info and ("nickname" in info or "name" in info):
                name = info.get("nickname") or info.get("name")
                lvl = info.get("level") or info.get("lv") or info.get("levelStr") or "N/A"
                region = info.get("region") or info.get("server") or "N/A"

                msg = (
                    "🎮 *Free Fire Profile*\n"
                    f"👤 *Name:* `{name}`\n"
                    f"🆔 *UID:* `{uid}`\n"
                    f"📊 *Level:* `{lvl}`\n"
                    f"🌍 *Region:* `{region}`"
                )
                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Player nahi mila. UID check karein.")

        # ---------------- PINCODE ----------------
        elif mode == "pincode":
            pin = text.strip()
            url = f"https://api.postalpincode.in/pincode/{pin}"

            success = False
            data = None
            for _ in range(2):
                try:
                    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                    data = r.json()
                    success = True
                    break
                except:
                    continue

            if success and isinstance(data, list) and len(data) > 0 and data[0]["Status"] == "Success":
                details = data[0]["PostOffice"][0]
                msg = (
                    "📍 *Pincode Information*\n"
                    f"📮 *Area:* `{details.get('Name')}`\n"
                    f"🏙 *District:* `{details.get('District')}`\n"
                    f"🏛 *State:* `{details.get('State')}`\n"
                    f"🔢 *Pincode:* `{pin}`"
                )
                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Invalid Pincode ya Server Busy hai.")

        # ---------------- INSTAGRAM & UNIVERSAL ----------------
        elif mode in ["insta", "universal"]:
            link = urllib.parse.quote_plus(text)
            if mode == "insta":
                api_url = f"https://smm.mksocial.site/api/instagram?link={link}&apikey={SMM_API_KEY}"
            else:
                api_url = f"https://smm.mksocial.site/api/download?url={link}&apikey={SMM_API_KEY}"

            res = safe_api(api_url)

            # Case 1: direct binary (video/image)
            if "binary" in res:
                await update.message.reply_video(
                    video=InputFile(io.BytesIO(res["binary"]), filename="video.mp4"),
                    caption="✅ Downloaded",
                )
            elif isinstance(res, dict):
                # try to find any URL inside JSON (deep search)
                found_url = None

                def find_url(obj):
                    nonlocal found_url
                    if found_url is not None:
                        return
                    if isinstance(obj, dict):
                        for v in obj.values():
                            find_url(v)
                    elif isinstance(obj, list):
                        for v in obj:
                            find_url(v)
                    elif isinstance(obj, str):
                        if obj.startswith("http"):
                            found_url = obj

                find_url(res)

                if found_url:
                    await update.message.reply_text(f"🔗 *Link:* {found_url}", parse_mode="Markdown")
                else:
                    await update.message.reply_text("❌ Media nahi mila. Link private ho sakta hai.")
            else:
                await update.message.reply_text("❌ Error downloading.")

        # ---------------- VEHICLE INFO (RegCheck India) ----------------
        elif mode == "vehicle":
            v_num = text.strip().replace(" ", "").upper()
            try:
                url = (
                    f"http://www.regcheck.org.uk/api/reg.asmx/CheckIndia"
                    f"?RegistrationNumber={v_num}&username={REGCHECK_USERNAME}"
                )
                r = requests.get(url, timeout=20)
                xml_text = r.text

                start = xml_text.find("<vehicleJson>")
                end = xml_text.find("</vehicleJson>")
                if start == -1 or end == -1:
                    await update.message.reply_text("❌ Vehicle data nahi mila.")
                else:
                    json_str = xml_text[start + len("<vehicleJson>"):end]
                    data = json.loads(json_str)

                    desc = data.get("Description") or "-"
                    year = data.get("RegistrationYear") or "-"
                    make = (data.get("CarMake") or {}).get("CurrentTextValue") or "-"
                    model = data.get("CarModel") or data.get("ModelDescription") or "-"
                    fuel = (data.get("FuelType") or {}).get("CurrentTextValue") or "-"

                    msg = (
                        "🚗 *Vehicle Info (RTO)*\n"
                        f"🔢 *Number:* `{v_num}`\n"
                        f"🏷 *Make:* `{make}`\n"
                        f"🚘 *Model:* `{model}`\n"
                        f"📄 *Description:* `{desc}`\n"
                        f"📆 *Registration Year:* `{year}`\n"
                        f"⛽ *Fuel:* `{fuel}`"
                    )
                    await update.message.reply_text(msg, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text("❌ Vehicle data nahi mila.")

        # ---------------- TTS ----------------
        elif mode == "tts":
            enc = urllib.parse.quote(text)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={enc}&tl=en&client=tw-ob"
            r = requests.get(url)
            if r.status_code == 200:
                await update.message.reply_audio(io.BytesIO(r.content), filename="voice.mp3")
            else:
                await update.message.reply_text("❌ TTS Error.")

        # ---------------- AI IMAGE ----------------
        elif mode == "aiimg":
            prompt = urllib.parse.quote(text)
            await update.message.reply_photo(f"https://image.pollinations.ai/prompt/{prompt}")

        # ---------------- AI TEXT ----------------
        elif mode == "aitext":
            prompt = urllib.parse.quote(text)
            r = requests.get(f"https://text.pollinations.ai/{prompt}", timeout=20)
            await update.message.reply_text(r.text[:3000])

        # ---------------- SEARCH ----------------
        elif mode == "search":
            res = safe_api(f"https://search-engine.hazex.workers.dev/?q={text}&type=web")
            await update.message.reply_text(str(res)[:1000])

        # ---------------- NUMBER INFO ----------------
        elif mode == "num":
            res = safe_api(
                f"https://dark-trace-networks.vercel.app/api?"
                f"key=DarkTrace_Network&type=mobile&term={text}"
            )
            # Pretty JSON
            if isinstance(res, dict):
                pretty = json.dumps(res, indent=2, ensure_ascii=False)
                await update.message.reply_text(f"```json\n{pretty}\n```", parse_mode="Markdown")
            else:
                await update.message.reply_text(str(res)[:2000])

        # ---------------- DOG ----------------
        elif mode == "dog":
            r = requests.get("https://dog.ceo/api/breeds/image/random").json()
            await update.message.reply_photo(r["message"])

        # ---------------- QR ----------------
        elif mode == "qr":
            await update.message.reply_photo(
                f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={text}"
            )

        # ---------------- WEATHER ----------------
        elif mode == "weather":
            res = safe_api(f"https://apitools.pages.dev/api/v1/tool/weather?city={text}")
            await update.message.reply_text(str(res)[:2000])

        # ---------------- AI CHAT ----------------
        elif mode == "aichat":
            prompt = urllib.parse.quote(text)
            res = safe_api(
                f"https://smm.mksocial.site/api/opneai?text={prompt}&key={SMM_API_KEY}"
            )
            reply = res.get("result") if isinstance(res, dict) else None
            reply = reply or (res.get("reply") if isinstance(res, dict) else None) or str(res)
            await update.message.reply_text(str(reply)[:3000])

        # ---------------- PLACEHOLDER IMAGE (FIXED) ----------------
        elif mode == "phold":
            # user text example: 600x400/000/FFF
            # use placehold.co – more reliable
            await update.message.reply_photo(f"https://placehold.co/{text}.png")

        # ---------------- ENHANCE (unchanged) ----------------
        elif mode == "enhance":
            res = safe_api(
                f"https://apitools.pages.dev/api/v1/tool/enhance?url={urllib.parse.quote_plus(text)}"
            )
            if "binary" in res:
                await update.message.reply_photo(
                    InputFile(io.BytesIO(res["binary"]), filename="enhanced.png")
                )
            elif isinstance(res, dict) and res.get("url"):
                await update.message.reply_photo(res["url"])
            else:
                await update.message.reply_text("❌ Enhance failed.")

        # ---------------- TIKTOK (still maintenance) ----------------
        elif mode == "tiktok":
            await update.message.reply_text("Feature in maintenance.")

        # ---------------- SONG (Saavn API) ----------------
        elif mode == "song":
            query = urllib.parse.quote_plus(text)
            try:
                # search songs
                r = requests.get(
                    f"https://saavn.dev/api/search/songs?query={query}", timeout=20
                )
                data = r.json()
                results = data.get("data", {}).get("results", [])
            except Exception:
                await update.message.reply_text("❌ Song API error. Thoda baad try karo.")
                return

            if not results:
                await update.message.reply_text("❌ Song nahi mila. Dusra naam try karo.")
                return

            song = results[0]

            downloads = song.get("downloadUrl") or []
            best_url = None

            def q_val(q):
                return int("".join(ch for ch in q if ch.isdigit()) or 0)

            if isinstance(downloads, list) and downloads:
                best = max(downloads, key=lambda d: q_val(d.get("quality", "")))
                best_url = best.get("url")

            if not best_url and isinstance(song.get("downloadUrl"), str):
                best_url = song["downloadUrl"]

            if not best_url:
                await update.message.reply_text("❌ Song link nahi mila.")
                return

            try:
                audio_bytes = requests.get(best_url, timeout=30).content
            except Exception:
                await update.message.reply_text("❌ MP3 download error.")
                return

            title = song.get("name") or song.get("title") or text
            caption = f"🎵 {title}\n👨‍🎤 {song.get('primaryArtists') or song.get('artists') or ''}"

            await update.message.reply_audio(
                audio=io.BytesIO(audio_bytes),
                filename=f"{title}.mp3",
                caption=caption,
            )

        else:
            await update.message.reply_text(f"Mode '{mode}' logic executed.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Bot Error: {e}")

# ---------------------------------------------
# AUTO WELCOME HANDLER
# ---------------------------------------------

async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        chat_title = update.effective_chat.title
        name = member.full_name
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"👋 Welcome {name} to {chat_title}!\nEnjoy your stay!",
        )

# ---------------------------------------------
# COMMAND HANDLERS HELPERS
# ---------------------------------------------

async def generic_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, prompt: str):
    if not await ensure_joined(update, context):
        return
    if context.args:
        text = " ".join(context.args)
        context.user_data["mode"] = mode
        await process_tool_logic(update, context, mode, text)
    else:
        context.user_data["mode"] = mode
        await update.message.reply_text(prompt)

# ---------------------------------------------
# COMMANDS
# ---------------------------------------------

async def start(update, context):
    user = update.message.from_user
    init_user(user.id)
    # Referral
    if context.args and context.args[0].startswith("ref_"):
        try:
            apply_referral(user.id, int(context.args[0].split("_")[1]))
        except:
            pass

    keyboard = [
        [InlineKeyboardButton("🔔 JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✔️ I HAVE JOINED", callback_data="check_join")],
    ]
    await update.message.reply_text(
        "👋 Welcome! Pehle channel join karo:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_cmd(update, context):
    if await ensure_joined(update, context):
        await update.message.reply_text("📂 Main Menu:", reply_markup=main_menu())

async def invite_cmd(update, context):
    bot = (await context.bot.get_me()).username
    await update.message.reply_text(
        f"🔗 Link: https://t.me/{bot}?start=ref_{update.message.from_user.id}"
    )

async def daily_bonus(update, context):
    user = update.message.from_user
    init_user(user.id)
    db = load_db()
    today = datetime.now().strftime("%Y-%m-%d")
    if db[str(user.id)].get("last_bonus") != today:
        db[str(user.id)]["last_bonus"] = today
        db[str(user.id)]["credits"] += 5
        save_db(db)
        await update.message.reply_text("🎁 +5 Credits Added!")
    else:
        await update.message.reply_text("⏳ Kal aana!")

async def admin_cmd(update, context):
    if update.message.from_user.id == ADMIN_ID:
        await update.message.reply_text("Admin Panel", reply_markup=admin_panel_menu())

# ---- /mypremium ----

async def mypremium_cmd(update, context):
    user_id = update.message.from_user.id
    init_user(user_id)
    db = load_db()
    u = db.get(str(user_id), {})

    if is_premium(user_id):
        expiry = u.get("premium_expiry", "")
        if expiry == "lifetime":
            status = "⭐ *Lifetime Premium* active hai."
        else:
            status = f"⭐ *Premium* active till `{expiry}`."
    else:
        status = "⚪ *Free User* (Premium nahi hai)."

    credits = u.get("credits", 0)
    msg = f"{status}\n💳 *Credits:* `{credits}`"
    await update.message.reply_text(msg, parse_mode="Markdown")

# Tool Commands
async def ffuid_cmd(update, context):      await generic_command_handler(update, context, "ffuid", "🎮 Send FF UID:")
async def vehicle_cmd(update, context):    await generic_command_handler(update, context, "vehicle", "🚗 Send Vehicle No:")
async def pincode_cmd(update, context):    await generic_command_handler(update, context, "pincode", "📍 Send Pincode:")
async def number_cmd(update, context):     await generic_command_handler(update, context, "num", "📞 Send Number:")
async def insta_cmd(update, context):      await generic_command_handler(update, context, "insta", "📸 Send Insta Link:")
async def universal_cmd(update, context):  await generic_command_handler(update, context, "universal", "🌐 Send Video Link:")
async def tts_cmd(update, context):        await generic_command_handler(update, context, "tts", "🗣 Send Text:")
async def aiimage_cmd(update, context):    await generic_command_handler(update, context, "aiimg", "🎨 Send Prompt:")
async def aitext_cmd(update, context):     await generic_command_handler(update, context, "aitext", "🤖 Ask AI:")
async def aichat_cmd(update, context):     await generic_command_handler(update, context, "aichat", "🤖 Chat with AI:")
async def song_cmd(update, context):       await generic_command_handler(update, context, "song", "🎵 Song Name:")
async def search_cmd(update, context):     await generic_command_handler(update, context, "search", "🌐 Query:")
async def dog_cmd(update, context):        await generic_command_handler(update, context, "dog", "🐶 Send anything:")
async def qr_cmd(update, context):         await generic_command_handler(update, context, "qr", "🔳 Text for QR:")
async def weather_cmd(update, context):    await generic_command_handler(update, context, "weather", "⛅ City:")
async def enhance_cmd(update, context):    await generic_command_handler(update, context, "enhance", "✨ Image URL:")
async def tiktok_cmd(update, context):     await generic_command_handler(update, context, "tiktok", "🎵 TikTok Search:")
async def placeholder_cmd(update, context):await generic_command_handler(update, context, "phold", "🖼 Ex: 600x400/000/FFF")

# ---------------------------------------------
# CALLBACK & TEXT HANDLERS
# ---------------------------------------------

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id

    # Admin special actions
    if user_id == ADMIN_ID and context.user_data.get("admin_action"):
        action = context.user_data["admin_action"]
        text = update.message.text.strip()
        db = load_db()

        # ---- Broadcast ----
        if action == "broadcast":
            sent = 0
            for uid in db.keys():
                try:
                    await context.bot.send_message(chat_id=int(uid), text=text)
                    sent += 1
                except:
                    pass
            await update.message.reply_text(f"✅ Broadcast sent to {sent} users.")
        # ---- Add Premium ----
        elif action == "add_premium":
            try:
                parts = text.split()
                target_id = int(parts[0])
                days = parts[1].lower()
                init_user(target_id)
                db = load_db()
                u = db[str(target_id)]
                u["premium"] = True
                if days == "lifetime":
                    u["premium_expiry"] = "lifetime"
                else:
                    d = int(days)
                    u["premium_expiry"] = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d")
                save_db(db)
                await update.message.reply_text("✅ Premium updated.")
            except Exception:
                await update.message.reply_text("❌ Format: `user_id days` (ya `user_id lifetime`)", parse_mode="Markdown")
        # ---- Remove Premium ----
        elif action == "remove_premium":
            try:
                target_id = int(text)
                init_user(target_id)
                db = load_db()
                u = db[str(target_id)]
                u["premium"] = False
                u["premium_expiry"] = ""
                save_db(db)
                await update.message.reply_text("✅ Premium removed.")
            except Exception:
                await update.message.reply_text("❌ Format: sirf `user_id` bhejo.")
        # ---- Send Credits ----
        elif action == "send_credits":
            try:
                uid_str, amt_str = text.split()
                target_id = int(uid_str)
                amt = int(amt_str)
                init_user(target_id)
                db = load_db()
                db[str(target_id)]["credits"] = db[str(target_id)].get("credits", 0) + amt
                save_db(db)
                await update.message.reply_text("✅ Credits sent.")
            except Exception:
                await update.message.reply_text("❌ Format: `user_id amount`", parse_mode="Markdown")

        context.user_data["admin_action"] = None
        return

    # Normal user flow
    if "mode" in context.user_data:
        await process_tool_logic(update, context, context.user_data["mode"], update.message.text)
    else:
        await update.message.reply_text("⚠️ Select a tool from /menu")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data == "mainmenu":
        await query.edit_message_text("📂 Main Menu:", reply_markup=main_menu())
        return
    if data == "check_join":
        await check_join_callback(update, context)
        return

    if data == "credits":
        db = load_db()
        cr = db.get(str(user_id), {}).get("credits", 0)
        await query.edit_message_text(f"💳 Balance: {cr} Credits", reply_markup=main_menu())
        return

    # Tool prompts
    prompts = {
        "ffuid": "🎮 Send Free Fire UID:",
        "vehicle": "🚗 Send Vehicle Number:",
        "pincode": "📍 Send Pincode:",
        "num": "📞 Send Mobile Number:",
        "insta": "📸 Send Instagram Link:",
        "universal": "🌐 Send Video Link:",
        "aiimg": "🎨 Send Image Prompt:",
        "aitext": "🤖 Ask me anything:",
        "tts": "🗣 Send text to speak:",
        "song": "🎵 Send Song Name:",
        "weather": "⛅ Send City Name:",
        "qr": "🔳 Send text for QR:",
        "dog": "🐶 Send anything:",
        "aichat": "🤖 Send message:",
        "search": "🌐 Send query:",
        "tiktok": "🎵 Send keyword:",
        "enhance": "✨ Send Image URL:",
        "phold": "🖼 Format: 600x400/000/FFF/Text",
    }

    if data in prompts:
        context.user_data["mode"] = data
        await query.edit_message_text(prompts[data])

    elif data.startswith("admin"):
        # Only admin
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ Only admin can use this.")
            return

        if data == "admin_broadcast":
            context.user_data["admin_action"] = "broadcast"
            await query.edit_message_text("📢 Send broadcast message:")
        elif data == "admin_total_users":
            db = load_db()
            await query.edit_message_text(
                f"👥 Total users: {len(db)}", reply_markup=admin_panel_menu()
            )
        elif data == "admin_add_premium":
            context.user_data["admin_action"] = "add_premium"
            await query.edit_message_text(
                "➕ Send: `user_id days` ya `user_id lifetime`", parse_mode="Markdown"
            )
        elif data == "admin_remove_premium":
            context.user_data["admin_action"] = "remove_premium"
            await query.edit_message_text("➖ Send: `user_id`", parse_mode="Markdown")
        elif data == "admin_send_credits":
            context.user_data["admin_action"] = "send_credits"
            await query.edit_message_text(
                "💸 Send: `user_id amount`", parse_mode="Markdown"
            )

async def check_join_callback(update, context):
    try:
        member = await context.bot.get_chat_member(
            f"@{CHANNEL_USERNAME}", update.callback_query.from_user.id
        )
        if member.status in ("member", "administrator", "creator"):
            await update.callback_query.edit_message_text(
                "✅ Joined!",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📂 Open Menu", callback_data="mainmenu")]]
                ),
            )
    except:
        pass

# ---------------------------------------------
# MAIN APP
# ---------------------------------------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Welcome handler
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("invite", invite_cmd))
    app.add_handler(CommandHandler("daily_bonus", daily_bonus))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("mypremium", mypremium_cmd))

    # Tool Commands
    app.add_handler(CommandHandler("ffuid", ffuid_cmd))
    app.add_handler(CommandHandler("vehicle", vehicle_cmd))
    app.add_handler(CommandHandler("pincode", pincode_cmd))
    app.add_handler(CommandHandler("number", number_cmd))
    app.add_handler(CommandHandler("instagram", insta_cmd))
    app.add_handler(CommandHandler("universal", universal_cmd))
    app.add_handler(CommandHandler("tts", tts_cmd))
    app.add_handler(CommandHandler("aiimage", aiimage_cmd))
    app.add_handler(CommandHandler("aitext", aitext_cmd))
    app.add_handler(CommandHandler("aichat", aichat_cmd))
    app.add_handler(CommandHandler("song", song_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("dog", dog_cmd))
    app.add_handler(CommandHandler("qr", qr_cmd))
    app.add_handler(CommandHandler("weather", weather_cmd))
    app.add_handler(CommandHandler("enhance", enhance_cmd))
    app.add_handler(CommandHandler("tiktok", tiktok_cmd))
    app.add_handler(CommandHandler("placeholder", placeholder_cmd))

    # Callbacks & Messages
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Bot is Online & Fixed!")
    app.run_polling()