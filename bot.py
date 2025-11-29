import json
import datetime
import random
import string

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# =======================
# تنظیمات
# =======================

TOKEN = "8273360781:AAHCYMfoWk_Xvs3KqDbWuyuh6gfDeWfLGYU"

# چند ادمین
ADMINS = {7756216825, 6354377138, 8543557767, 7388257524}

DATA_FILE = "data.json"
PENDING_FILE = "pending.json"
USERS_FILE = "users.txt"


# =======================
# دیتابیس
# =======================

def init_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}

    if "users" not in data:
        data["users"] = {}

    if "categories" not in data:
        data["categories"] = {}

        # دسته ویژه لذت ۱ دقیقه‌ای
    if "one_minute" not in data["categories"]:
        data["categories"]["one_minute"] = {
            "name": "لذت ۱ دقیقه‌ای 1️⃣",
            "videos": []
        }

    if "protect" not in data:
        data["protect"] = True  # 🔒 پیش‌فرض فعال

    if "bans" not in data:
        data["bans"] = {}

    save_data(data)
    return data


def load_data():
    return init_data()


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_pending():
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_pending(p):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=4, ensure_ascii=False)


# =======================
# چک بن بودن
# =======================

def is_banned(user_id):
    data = load_data()
    bans = data.get("bans", {})
    uid = str(user_id)

    if uid not in bans:
        return False

    # بن دائمی
    if bans[uid] == "PERMANENT":
        return True

    # بن زمان‌دار
    try:
        until = datetime.datetime.fromisoformat(bans[uid])
    except:
        return False

    if until > datetime.datetime.now():
        return True

    # اگر زمانش تمام شده → حذف بن
    del bans[uid]
    save_data(data)
    return False


# =======================
# اشتراک
# =======================

def has_subscription(user_id):
    data = load_data()
    uid = str(user_id)

    if uid not in data["users"]:
        return False

    try:
        expiry = datetime.datetime.fromisoformat(data["users"][uid]["expiry"])
    except:
        return False

    return expiry > datetime.datetime.now()


# =======================
# کیبورد اصلی
# =======================

def build_main_keyboard(is_admin: bool):
    data = load_data()
    categories = data.get("categories", {})

    keyboard = []
    row = []

    for _, info in categories.items():
        row.append(KeyboardButton(info["name"]))
        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([KeyboardButton("👤 پروفایل"), KeyboardButton("📌 خرید اشتراک")])

    if is_admin:
        keyboard.append([KeyboardButton("➕ ساخت دسته جدید"), KeyboardButton("🗑 حذف دسته")])
        keyboard.append([KeyboardButton("🔒 قفل فوروارد")])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# =======================
# ثبت کاربر
# =======================

def log_user(update: Update):
    uid = update.effective_user.id
    name = update.effective_user.full_name
    username = update.effective_user.username

    with open(USERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"NAME: {name} | USERNAME: @{username} | USERID: {uid}\n")


# =======================
# صفحه‌بندی
# =======================

async def send_page(user_id, category_key, page, context):
    data = load_data()
    protect = data.get("protect", True)

    videos = data["categories"][category_key]["videos"]

    PER_PAGE = 5
    start = page * PER_PAGE
    end = start + PER_PAGE
    chunk = videos[start:end]

    # حذف پیام‌های قبلی
    if "last_msgs" in context.user_data:
        for mid in context.user_data["last_msgs"]:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=mid)
            except:
                pass

    msg_ids = []

    # ارسال محتوا
    for item in chunk:
        if item["type"] == "text":
            m = await context.bot.send_message(user_id, item["data"], protect_content=protect)
        elif item["type"] == "photo":
            m = await context.bot.send_photo(user_id, item["data"], protect_content=protect)
        elif item["type"] == "video":
            m = await context.bot.send_video(user_id, item["data"], protect_content=protect)
        else:
            continue

        msg_ids.append(m.message_id)

    total_pages = ((len(videos) - 1) // PER_PAGE) + 1

    buttons = []

    if page != 0:
        buttons.append(InlineKeyboardButton("⏮ اولین صفحه", callback_data=f"PAGE_{category_key}_0"))
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅ صفحه قبل", callback_data=f"PAGE_{category_key}_{page-1}"))
    if end < len(videos):
        buttons.append(InlineKeyboardButton("صفحه بعد ➡", callback_data=f"PAGE_{category_key}_{page+1}"))
    if page != total_pages - 1:
        buttons.append(InlineKeyboardButton("⏭ آخرین صفحه", callback_data=f"PAGE_{category_key}_{total_pages-1}"))

    if buttons:
        m = await context.bot.send_message(
            user_id,
            f"📄 صفحه {page+1} از {total_pages}",
            reply_markup=InlineKeyboardMarkup([buttons])
        )
        msg_ids.append(m.message_id)

    context.user_data["last_msgs"] = msg_ids


# =======================
# START
# =======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id):
        return await update.message.reply_text("🚫 شما بن شده‌اید و امکان استفاده از ربات را ندارید.")

    log_user(update)
    kb = build_main_keyboard(update.effective_user.id in ADMINS)

    welcome_text = """
🔥 سلام! خوش اومدی به دنیای فیلم های پورن 🔞
اینجا می‌تونی جدیدترین و باکیفیت‌ترین ویدیوها رو ببینی.
از منوی پایین دسته مورد نظر رو انتخاب کن 👇

📌 برای خرید اشتراک هم می‌تونی از بخش مربوطه استفاده کنی.
"""

    await update.message.reply_text(welcome_text, reply_markup=kb)


# =======================
# /addsub
# =======================

async def add_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    if len(context.args) != 2:
        await update.message.reply_text("فرمت:\n/addsub USERID DAYS")
        return

    uid = context.args[0]
    days = int(context.args[1])

    data = load_data()
    expiry = datetime.datetime.now() + datetime.timedelta(days=days)
    data["users"][uid] = {"expiry": expiry.isoformat()}

    save_data(data)

    await update.message.reply_text(f"اشتراک {uid} برای {days} روز فعال شد")

    try:
        await context.bot.send_message(uid, "✅ اشتراک شما فعال شد")
    except:
        pass


# =======================
# /addsub
# =======================

async def remove_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("❌ شما ادمین نیستید.")

    if len(context.args) != 1:
        return await update.message.reply_text("فرمت درست:\n/removesub USERID")

    uid = context.args[0]
    data = load_data()

    if uid not in data["users"]:
        return await update.message.reply_text("❗ این کاربر هیچ اشتراکی ندارد.")

    del data["users"][uid]
    save_data(data)

    await update.message.reply_text(f"❌ اشتراک کاربر {uid} حذف شد.")

    try:
        await context.bot.send_message(uid, "❕ اشتراک شما توسط ادمین حذف شد.")
    except:
        pass

    
# =======================
# دستور /actives - لیست کامل کاربران با اشتراک فعال
# =======================
async def subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("فقط ادمین می‌تونه اینو ببینه!")
        return

    data = load_data()
    active_users = []

    for uid_str, info in data.get("users", {}).items():
        try:
            expiry = datetime.datetime.fromisoformat(info["expiry"])
            if expiry > datetime.datetime.now():
                user_id = int(uid_str)
                # سعی می‌کنیم یوزرنیم و اسم رو از تلگرام بگیریم
                try:
                    user = await context.bot.get_chat(user_id)
                    username = f"@{user.username}" if user.username else "ندارد"
                except:
                    username = "ندارد (مسدود یا حذف شده)"

                persian_date = expiry.strftime('%Y/%m/%d').replace('2025', '1404').replace('2026', '1405')  # تبدیل به شمسی تقریبی
                active_users.append((user_id, username, persian_date))
        except:
            continue

    # مرتب‌سازی بر اساس تاریخ انقضا (جدیدتر بالا)
    active_users.sort(key=lambda x: x[2], reverse=True)

    if not active_users:
        await update.message.reply_text("هیچکس اشتراک فعال نداره!")
        return

    lines = [f"اشتراک‌های فعال ({len(active_users)} نفر)\n"]
    for i, (uid, username, exp) in enumerate(active_users, 1):
        lines.append(f"{i}. `{uid}`  →  {username}  (تا {exp})")

    text = "\n".join(lines)

    # اگر متن خیلی بلند شد، به صورت فایل txt می‌فرستیم
    if len(text) > 4000:
        file_content = "\n".join([f"{uid} | {username} | تا {exp}" for uid, username, exp in active_users])
        file_content = "USERID | USERNAME | انقضا\n" + file_content
        await update.message.reply_document(
            document=("active_users.txt", file_content.encode('utf-8')),
            caption=f"لیست {len(active_users)} کاربر فعال به صورت فایل:"
        )
    else:
        await update.message.reply_text(text, parse_mode="Markdown")



# =======================
# /ban
# =======================

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("❌ شما ادمین نیستید.")

    if len(context.args) < 2:
        return await update.message.reply_text(
            "فرمت درست:\n"
            "/ban perm USERID\n"
            "/ban HOURS USERID\n"
            "مثال:\n"
            "/ban perm 123456789\n"
            "/ban 48 123456789"
        )

    mode = context.args[0]            # perm یا عدد
    uid = str(context.args[1])        # USERID

    data = load_data()

    # اگر بخش bans وجود نداشت ایجادش کنیم
    if "bans" not in data:
        data["bans"] = {}

    # --- بن دائمی ---
    if mode.lower() == "perm":
        data["bans"][uid] = "PERMANENT"
        save_data(data)

        await update.message.reply_text(f"🚫 کاربر {uid} برای همیشه بن شد.")
        try:
            await context.bot.send_message(uid, "🚫 شما به طور دائمی بن شدید.")
        except:
            pass

        return

    # --- اگر بن زمان‌دار بود ---
    if mode.isdigit():
        hours = int(mode)

        # جلوگیری از خطای OverflowError
        if hours > 8760:  # ۱ سال
            return await update.message.reply_text("❗ حداکثر مقدار مجاز 8760 ساعت است (۱ سال).")

        # محاسبه پایان بن
        ban_until = datetime.datetime.now() + datetime.timedelta(hours=hours)
        data["bans"][uid] = ban_until.isoformat()
        save_data(data)

        await update.message.reply_text(f"⛔ کاربر {uid} برای {hours} ساعت بن شد.")

        try:
            await context.bot.send_message(uid, f"⛔ شما برای {hours} ساعت بن شدید.")
        except:
            pass

        return

    return await update.message.reply_text("❗ حالت نامعتبر است. فقط perm یا عدد ساعت وارد کنید.")


# =======================
# /unban
# =======================

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("❌ شما ادمین نیستید.")

    if len(context.args) != 1:
        return await update.message.reply_text("فرمت درست:\n/unban USERID")

    uid = context.args[0]
    data = load_data()

    if "bans" not in data or uid not in data["bans"]:
        return await update.message.reply_text("❗ این کاربر بن نیست.")

    del data["bans"][uid]
    save_data(data)

    await update.message.reply_text(f"✅ کاربر {uid} از بن خارج شد.")

    try:
        await context.bot.send_message(uid, "✅ شما از لیست بن خارج شدید و دوباره می‌توانید استفاده کنید.")
    except:
        pass


# =======================
# منو
# =======================

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_banned(user_id):
        return await update.message.reply_text("🚫 شما بن شده‌اید و امکان استفاده از ربات را ندارید.")

    text = update.message.text
    data = load_data()

    # بررسی بن بودن کاربر
    bans = data.get("bans", {})
    uid = str(user_id)

    if uid in bans:
        if bans[uid] == "PERMANENT":
            return await update.message.reply_text("🚫 شما بن هستید و نمی‌توانید از بات استفاده کنید.")

        else:
            try:
                ban_until = datetime.datetime.fromisoformat(bans[uid])
            except:
                ban_until = None

            if ban_until and ban_until > datetime.datetime.now():
                remaining = ban_until - datetime.datetime.now()
                hours_left = int(remaining.total_seconds() // 3600)
                return await update.message.reply_text(
                    f"⛔ شما هنوز {hours_left} ساعت بن هستید."
                )
            else:
                # بن تمام شده → حذف بن
                del bans[uid]
                save_data(data)


    # خرید اشتراک
    if text == "📌 خرید اشتراک":
        msg = """
📌 **راهنما و پشتیبانی**

برای خرید اشتراک با آیدی‌های زیر تماس بگیرید:

💬 @Nuvrra
💬 @iamdaniaaal
"""
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # قفل فوروارد
    if text == "🔒 قفل فوروارد" and user_id in ADMINS:
        data["protect"] = not data.get("protect", True)
        save_data(data)
        status = "فعال" if data["protect"] else "غیرفعال"
        await update.message.reply_text(f"قفل فوروارد: {status}")
        return

    # لغو
    if text == "لغو":
        context.user_data.clear()
        kb = build_main_keyboard(user_id in ADMINS)
        await update.message.reply_text("لغو شد", reply_markup=kb)
        return

    # ساخت دسته جدید
    if text == "➕ ساخت دسته جدید" and user_id in ADMINS:
        context.user_data["create_state"] = "wait_name"
        await update.message.reply_text(
            "اسم دسته را بفرست:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("لغو")]], resize_keyboard=True)
        )
        return

    if context.user_data.get("create_state") == "wait_name" and user_id in ADMINS:
        context.user_data["tmp_name"] = text
        context.user_data["create_state"] = "wait_key"
        await update.message.reply_text(
            "شناسه انگلیسی دسته چیست؟",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("لغو")]], resize_keyboard=True)
        )
        return

    if context.user_data.get("create_state") == "wait_key" and user_id in ADMINS:
        key = text.strip()
        if not key.isalnum():
            await update.message.reply_text("شناسه فقط شامل حروف و عدد باشد.")
            return

        if key in data["categories"]:
            await update.message.reply_text("این شناسه وجود دارد.")
            return

        name = context.user_data["tmp_name"]
        data["categories"][key] = {"name": name, "videos": []}
        save_data(data)

        context.user_data.clear()
        kb = build_main_keyboard(True)
        await update.message.reply_text(f"دسته '{name}' ساخته شد.", reply_markup=kb)
        return

    # حذف دسته
    if text == "🗑 حذف دسته" and user_id in ADMINS:
        context.user_data["delete"] = True
        kb = [[KeyboardButton(info["name"])] for info in data["categories"].values()]
        kb.append([KeyboardButton("لغو")])
        await update.message.reply_text("کدام دسته حذف شود؟", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    if context.user_data.get("delete") and user_id in ADMINS:
        context.user_data.clear()
        for key, info in list(data["categories"].items()):
            if info["name"] == text:
                data["categories"].pop(key)
                save_data(data)
                kb = build_main_keyboard(True)
                await update.message.reply_text("حذف شد.", reply_markup=kb)
                return

    # پروفایل
    if text == "👤 پروفایل":
        name = update.effective_user.full_name
        username = '@' + update.effective_user.username if update.effective_user.username else "ندارد"
        uid = update.effective_user.id

        if has_subscription(uid):
            exp = data["users"][str(uid)]["expiry"]
            msg = f"""
👤 **مشخصات حساب**
🧑‍💼 نام: {name}
🔖 نام کاربری: {username}
🆔 شناسه:` {uid}`
📅 اشتراک: ✅ فعال تا {exp}
"""
        else:
            msg = f"""
👤 **مشخصات حساب**
🧑‍💼 نام: {name}
🔖 نام کاربری: {username}
🆔 شناسه:` {uid}`
📅 اشتراک: ❌ فعال نیست
"""

        await update.message.reply_text(msg, parse_mode="Markdown")
        return


    # دسته ویژه: لذت ۱ دقیقه‌ای
    if text == "لذت ۱ دقیقه‌ای":
        if not has_subscription(user_id):
            return await update.message.reply_text("❌ اشتراک ندارید")

        special_key = "one_minute"

        if special_key not in data["categories"]:
            return await update.message.reply_text("❗ این دسته هنوز تنظیم نشده است.")

        videos = data["categories"][special_key]["videos"]

        if len(videos) == 0:
            return await update.message.reply_text("محتوایی برای این دسته موجود نیست.")

        # انتخاب رندوم
        import random
        vid = random.choice(videos)

        protect = data.get("protect", True)

        if vid["type"] == "text":
            await update.message.reply_text(vid["data"], protect_content=protect)
        elif vid["type"] == "photo":
            await update.message.reply_photo(vid["data"], protect_content=protect)
        elif vid["type"] == "video":
            await update.message.reply_video(vid["data"], protect_content=protect)

        return


    # نمایش محتوا
    for key, info in data["categories"].items():
        if info["name"] == text:
            if not has_subscription(user_id):
                await update.message.reply_text("❌ اشتراک ندارید")
                return

            if len(info["videos"]) == 0:
                await update.message.reply_text("محتوایی موجود نیست.")
                return

            await send_page(user_id, key, 0, context)
            return


# =======================
# افزودن محتوا توسط ادمین
# =======================

async def admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    if is_banned(update.effective_user.id):
        return

    now_time = datetime.datetime.now().isoformat()

    if update.message.text:
        content = {"type": "text", "data": update.message.text, "time": now_time}
    elif update.message.photo:
        content = {"type": "photo", "data": update.message.photo[-1].file_id, "time": now_time}
    elif update.message.video:
        content = {"type": "video", "data": update.message.video.file_id, "time": now_time}
    else:
        return

    pkey = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    pending = load_pending()
    pending[pkey] = content
    save_pending(pending)

    data = load_data()

    kb = [
        [InlineKeyboardButton(info["name"], callback_data=f"ADD_{cat_key}_{pkey}")]
        for cat_key, info in data["categories"].items()
    ]

    kb.append([InlineKeyboardButton("لغو", callback_data="CANCEL")])

    await update.message.reply_text(
        "محتوا به کدام دسته اضافه شود؟",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# =======================
 test
# =======================
import hashlib
import asyncio

# شناسه ادمینی که می‌خوای بکاپ اتومات براش بیاد
AUTO_BACKUP_ADMIN = 7756216825  # ← اینجا آیدی خودتو بذار

# برای ذخیره هش قبلی فایل‌ها
_last_data_hash = None
_last_pending_hash = None

async def auto_backup_if_changed(context: ContextTypes.DEFAULT_TYPE):
    global _last_data_hash, _last_pending_hash

    try:
        with open(DATA_FILE, "rb") as f:
            current_data = f.read()
        data_hash = hashlib.md5(current_data).hexdigest()

        with open(PENDING_FILE, "rb") as f:
            current_pending = f.read()
        pending_hash = hashlib.md5(current_pending).hexdigest()
    except:
        return  # فایل‌ها هنوز نیستن

    # اگه data.json تغییر کرد یا pending.json تغییر کرد
    if data_hash != _last_data_hash or pending_hash != _last_pending_hash:
        _last_data_hash = data_hash
        _last_pending_hash = pending_hash

        # ساخت زیپ
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, name in [(DATA_FILE, "data.json"), (PENDING_FILE, "pending.json"), (USERS_FILE, "users.txt")]:
                try:
                    with open(path, "rb") as f:
                        zf.writestr(name, f.read())
                except:
                    zf.writestr(name, "{}")

        buffer.seek(0)
        now = datetime.datetime.now().strftime("%H:%M - %Y/%m/%d")

        await context.bot.send_document(
            chat_id=AUTO_BACKUP_ADMIN,
            document=buffer,
            filename=f"تغییرات_ربات_{now}.zip",
            caption=f"تغییر جدید تشخیص داده شد!\n"
                    f"زمان: {now}\n"
                    f"دیتابیس به‌روز شد"
        )
# =======================
# دکمه‌های اینلاین
# =======================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = load_data()

    # افزودن به دسته
    if query.data.startswith("ADD_"):
        if query.from_user.id not in ADMINS:
            await query.answer("اجازه ندارید", show_alert=True)
            return

        _, cat_key, pkey = query.data.split("_")
        pending = load_pending()

        if pkey not in pending:
            await query.message.reply_text("❌ یافت نشد")
            return

        data["categories"][cat_key]["videos"].append(pending[pkey])
        save_data(data)

        pending.pop(pkey)
        save_pending(pending)

        try:
            await query.message.delete()
        except:
            pass

        await context.bot.send_message(query.from_user.id, "✅ محتوای جدید اضافه شد.")
        await query.answer()
        return

    # صفحه‌بندی
    if query.data.startswith("PAGE_"):
        _, cat_key, page = query.data.split("_")
        page = int(page)

        await send_page(query.from_user.id, cat_key, page, context)
        await query.answer()
        return

    # لغو
    if query.data == "CANCEL":
        try:
            await query.message.delete()
        except:
            pass

        await context.bot.send_message(query.from_user.id, "لغو شد.")
        await query.answer()


# =======================
# اجرای بات
# =======================

def main():
    init_data()
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addsub", add_sub))
    application.add_handler(CommandHandler("removesub", remove_subscription))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("subs", subs))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.VIDEO_NOTE | filters.TEXT & ~filters.COMMAND, admin_media))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot Ba Movafaghiat Bala Umad.")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()











