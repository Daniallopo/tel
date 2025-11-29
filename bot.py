import json
import datetime
import random
import string
from io import BytesIO

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
# حتماً توکن رو اینجا با توکن جدید یا از متغیر محیطی بذار
TOKEN = "8273360781:AAEONUlCKNfM6DsqNukdN-wEN9J4eo26RUY"

# چند ادمین
ADMINS = {7756216825, 6354377138, 8543557767, 7388257524}

# آیدی که بکاپ TXT برایش فرستاده می‌شود
ADMIN_BACKUP_ID = 7388257524

DATA_FILE = "data.json"
PENDING_FILE = "pending.json"
USERS_FILE = "users.txt"


# =======================
# دیتابیس (خواندن/نوشتن امن)
# =======================
def init_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    # ساختار پایه
    if "users" not in data:
        data["users"] = {}

    if "categories" not in data:
        data["categories"] = {}

    # دسته ویژه لذت 1 دقیقه‌ای
    if "one_minute" not in data["categories"]:
        data["categories"]["one_minute"] = {
            "name": "لذت ۱ دقیقه‌ای 1️⃣",
            "videos": []
        }

    if "protect" not in data:
        data["protect"] = True  # پیش‌فرض فعال

    if "bans" not in data:
        data["bans"] = {}

    # ذخیره اگر نیاز است
    save_data(data)
    return data


def load_data():
    return init_data()


def save_data(data):
    """فقط ذخیره فایل data.json (synchronous)"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_pending():
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_pending(p):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=4, ensure_ascii=False)


# =======================
# بکاپ خودکار به صورت TXT (async — فقط فرستادن پیام)
# =======================
async def save_database_and_send_backup(context: ContextTypes.DEFAULT_TYPE, data_obj: dict, pending_obj: dict):
    """
    data_obj و pending_obj را به فایل می‌نویسد (همان‌ها قبلاً باید با save_data/save_pending نوشته شده باشند)
    سپس محتوای آن‌ها را به صورت یک فایل TXT به ADMIN_BACKUP_ID ارسال می‌کند.
    """
    try:
        # اطمینان از نوشتن فایل‌ها (در صورتی که caller فراموش کرده)
        save_data(data_obj)
        save_pending(pending_obj)

        # خواندن مجدد برای تهیه متن
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data_text = f.read()
        except Exception:
            data_text = "{}\n(خطا در خواندن data.json)"

        try:
            with open(PENDING_FILE, "r", encoding="utf-8") as f:
                pending_text = f.read()
        except Exception:
            pending_text = "{}\n(خطا در خواندن pending.json)"

        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        final_text = f"""بکاپ خودکار دیتابیس

زمان: {now}

=== data.json ===
{data_text}

=== pending.json ===
{pending_text}

(این فایل بصورت خودکار پس از تغییر در دیتابیس ارسال شده)
"""

        await context.bot.send_document(
            chat_id=ADMIN_BACKUP_ID,
            document=BytesIO(final_text.encode("utf-8")),
            filename=f"backup_{now}.txt",
            caption="📦 بکاپ خودکار دیتابیس"
        )

    except Exception as e:
        # لاگ ساده در صورت خطا
        print("خطا در save_database_and_send_backup:", e)


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
    except Exception:
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
    except Exception:
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
            except Exception:
                pass

    msg_ids = []

    # ارسال محتوا
    for item in chunk:
        try:
            if item["type"] == "text":
                m = await context.bot.send_message(user_id, item["data"], protect_content=protect)
            elif item["type"] == "photo":
                m = await context.bot.send_photo(user_id, item["data"], protect_content=protect)
            elif item["type"] == "video":
                m = await context.bot.send_video(user_id, item["data"], protect_content=protect)
            else:
                continue
            msg_ids.append(m.message_id)
        except Exception:
            continue

    total_pages = ((len(videos) - 1) // PER_PAGE) + 1 if videos else 1

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
🔥 سلام! خوش اومدی به دنیای فیلم های اکشن 🔞
اینجا می‌تونی جدیدترین و باکیفیت‌ترین ویدیوها رو ببینی.
از منوی پایین دسته مورد نظر رو انتخاب کن 👇

📌 برای خرید اشتراک هم می‌تونی از بخش مربوطه استفاده کنی.
"""
    await update.message.reply_text(welcome_text, reply_markup=kb)


# =======================
# دستور /backup (ارسال ZIP دستی)
# =======================
import zipfile
from io import BytesIO as _BytesIO

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("فقط ادمین می‌تونه بکاپ بگیره!")
        return

    await update.message.reply_chat_action("upload_document")

    buffer = _BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        files = [
            ("data.json", DATA_FILE),
            ("pending.json", PENDING_FILE),
            ("users.txt", USERS_FILE)
        ]
        for display_name, real_path in files:
            try:
                with open(real_path, "rb") as f:
                    zip_file.writestr(display_name, f.read())
            except Exception:
                zip_file.writestr(display_name, "{}")

    buffer.seek(0)
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"Backup_{now}.zip"

    await update.message.reply_document(
        document=buffer,
        filename=filename,
        caption=f"بکاپ کامل ربات\nتاریخ: {now}\nتعداد فایل: ۳ تا"
    )


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
    try:
        days = int(context.args[1])
    except Exception:
        return await update.message.reply_text("مقدار روز باید عدد باشد.")

    data = load_data()
    expiry = datetime.datetime.now() + datetime.timedelta(days=days)
    data["users"][uid] = {"expiry": expiry.isoformat()}

    save_data(data)
    # بکاپ بفرست
    await save_database_and_send_backup(context, data, load_pending())

    await update.message.reply_text(f"اشتراک {uid} برای {days} روز فعال شد")

    try:
        await context.bot.send_message(uid, "✅ اشتراک شما فعال شد")
    except Exception:
        pass


# =======================
# remove subscription
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
    await save_database_and_send_backup(context, data, load_pending())

    await update.message.reply_text(f"❌ اشتراک کاربر {uid} حذف شد.")

    try:
        await context.bot.send_message(uid, "❕ اشتراک شما توسط ادمین حذف شد.")
    except Exception:
        pass


# =======================
# /subs (لیست اشتراک‌ها)
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
                try:
                    user = await context.bot.get_chat(user_id)
                    username = f"@{user.username}" if user.username else "ندارد"
                except Exception:
                    username = "ندارد (مسدود یا حذف شده)"

                persian_date = expiry.strftime('%Y/%m/%d')
                active_users.append((user_id, username, persian_date))
        except Exception:
            continue

    active_users.sort(key=lambda x: x[2], reverse=True)

    if not active_users:
        await update.message.reply_text("هیچکس اشتراک فعال نداره!")
        return

    lines = [f"اشتراک‌های فعال ({len(active_users)} نفر)\n"]
    for i, (uid, username, exp) in enumerate(active_users, 1):
        lines.append(f"{i}. `{uid}`  →  {username}  (تا {exp})")

    text = "\n".join(lines)

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
# /ban و /unban
# =======================
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("❌ شما ادمین نیستید.")

    if len(context.args) < 2:
        return await update.message.reply_text(
            "فرمت درست:\n/ban perm USERID\n/ban HOURS USERID\n"
        )

    mode = context.args[0]
    uid = str(context.args[1])

    data = load_data()
    if "bans" not in data:
        data["bans"] = {}

    if mode.lower() == "perm":
        data["bans"][uid] = "PERMANENT"
        save_data(data)
        await save_database_and_send_backup(context, data, load_pending())
        await update.message.reply_text(f"🚫 کاربر {uid} برای همیشه بن شد.")
        try:
            await context.bot.send_message(uid, "🚫 شما به طور دائمی بن شدید.")
        except Exception:
            pass
        return

    if mode.isdigit():
        hours = int(mode)
        if hours > 8760:
            return await update.message.reply_text("❗ حداکثر مقدار مجاز 8760 ساعت است (۱ سال).")
        ban_until = datetime.datetime.now() + datetime.timedelta(hours=hours)
        data["bans"][uid] = ban_until.isoformat()
        save_data(data)
        await save_database_and_send_backup(context, data, load_pending())
        await update.message.reply_text(f"⛔ کاربر {uid} برای {hours} ساعت بن شد.")
        try:
            await context.bot.send_message(uid, f"⛔ شما برای {hours} ساعت بن شدید.")
        except Exception:
            pass
        return

    return await update.message.reply_text("❗ حالت نامعتبر است. فقط perm یا عدد ساعت وارد کنید.")


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
    await save_database_and_send_backup(context, data, load_pending())

    await update.message.reply_text(f"✅ کاربر {uid} از بن خارج شد.")
    try:
        await context.bot.send_message(uid, "✅ شما از لیست بن خارج شدید و دوباره می‌توانید استفاده کنید.")
    except Exception:
        pass


# =======================
# منو و مدیریت دسته‌ها / نمایش محتوا
# =======================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_banned(user_id):
        return await update.message.reply_text("🚫 شما بن شده‌اید و امکان استفاده از ربات را ندارید.")

    text = update.message.text
    data = load_data()

    # خرید اشتراک (نمایش)
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
        await save_database_and_send_backup(context, data, load_pending())
        status = "فعال" if data["protect"] else "غیرفعال"
        await update.message.reply_text(f"قفل فوروارد: {status}")
        return

    # لغو
    if text == "لغو":
        context.user_data.clear()
        kb = build_main_keyboard(user_id in ADMINS)
        await update.message.reply_text("لغو شد", reply_markup=kb)
        return

    # ساخت دسته جدید (مرحله‌ای)
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

        data = load_data()
        if key in data["categories"]:
            await update.message.reply_text("این شناسه وجود دارد.")
            return

        name = context.user_data["tmp_name"]
        data["categories"][key] = {"name": name, "videos": []}
        save_data(data)
        await save_database_and_send_backup(context, data, load_pending())

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
                await save_database_and_send_backup(context, data, load_pending())
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
    if text == "لذت ۱ دقیقه‌ای 1️⃣":
        if not has_subscription(user_id):
            return await update.message.reply_text("❌ اشتراک ندارید")

        special_key = "one_minute"
        if special_key not in data["categories"]:
            return await update.message.reply_text("❗ این دسته هنوز تنظیم نشده است.")

        videos = data["categories"][special_key]["videos"]
        if len(videos) == 0:
            return await update.message.reply_text("محتوایی برای این دسته موجود نیست.")

        vid = random.choice(videos)
        protect = data.get("protect", True)

        if vid["type"] == "text":
            await update.message.reply_text(vid["data"], protect_content=protect)
        elif vid["type"] == "photo":
            await update.message.reply_photo(vid["data"], protect_content=protect)
        elif vid["type"] == "video":
            await update.message.reply_video(vid["data"], protect_content=protect)
        return

    # نمایش محتوا برای دیگر دسته‌ها
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
# افزودن محتوا توسط ادمین (ساخت pending)
# =======================
async def admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if is_banned(update.effective_user.id):
        return

    now_time = datetime.datetime.now().isoformat()
    content = None

    # متن
    if update.message.text:
        content = {"type": "text", "data": update.message.text, "time": now_time}

    # عکس
    elif update.message.photo:
        # فقط photo
        content = {"type": "photo", "data": update.message.photo[-1].file_id, "time": now_time}

    # ویدیو معمولی
    elif update.message.video:
        content = {"type": "video", "data": update.message.video.file_id, "time": now_time}

    # ویدیو نوت
    elif update.message.video_note:
        content = {"type": "video", "data": update.message.video_note.file_id, "time": now_time}

    else:
        return

    # ساخت کلید موقت برای pending
    pkey = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    pending = load_pending()
    pending[pkey] = content
    save_pending(pending)

    # فراخوانی بکاپ (چون pending تغییر کرده)
    await save_database_and_send_backup(context, load_data(), pending)

    # ساخت کیبورد انتخاب دسته
    data = load_data()
    kb = [
        [InlineKeyboardButton(info["name"], callback_data=f"ADD::{cat_key}::{pkey}")]
        for cat_key, info in data["categories"].items()
    ]
    kb.append([InlineKeyboardButton("لغو", callback_data="CANCEL")])

    await update.message.reply_text(
        "به کدوم دسته اضافه بشه؟",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# =======================
# دکمه‌های اینلاین
# =======================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = load_data()

    # افزودن محتوا از pending به data
if query.data.startswith("ADD::"):
    if query.from_user.id not in ADMINS:
        await query.answer("اجازه ندارید", show_alert=True)
        return

    try:
        _, cat_key, pkey = query.data.split("::")
    except:
        await query.answer("خطا در داده‌ها", show_alert=True)
        return

    pending = load_pending()

    # <<<<< این قسمت جدید و ضدگلوله >>>>>
    if pkey not in pending:
        # اگر پیدا نشد → احتمالاً بات ری‌استارت شده
        # پس دوباره به ادمین اجازه بده محتوا بفرسته
        await query.message.delete() if query.message else None
        await context.bot.send_message(
            query.from_user.id,
            "محتوا پیدا نشد (احتمالاً ربات ری‌استارت شده)\n"
            "لطفاً دوباره ویدیو/عکس/متن رو بفرستید 🙏"
        )
        await query.answer()
        return
    # <<<<< تا اینجا >>>>>

    # بقیه کد همون قبلی
    data = load_data()
    data["categories"][cat_key]["videos"].append(pending[pkey])
    save_data(data)

    pending.pop(pkey)
    save_pending(pending)

    await save_database_and_send_backup(context, data, pending)

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(query.from_user.id, "محتوای جدید با موفقیت اضافه شد ✅")
    await query.answer()
    return


# =======================
# اجرای بات
# =======================
def main():
    # اطمینان از وجود فایل‌ها
    init_data()
    # اگر pending وجود نداشت یک فایل خالی بساز
    if not load_pending():
        save_pending({})

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addsub", add_sub))
    app.add_handler(CommandHandler("removesub", remove_subscription))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("subs", subs))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(
    MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VIDEO_NOTE | filters.Document.VIDEO,
        admin_media
    )
)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started. ✅")
    app.run_polling()


if __name__ == "__main__":
    main()






