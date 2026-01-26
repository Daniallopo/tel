# کد نهایی با رفع خطای conflict
import asyncio
import logging
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sys

# تنظیمات
SOURCE_GROUP_ID = -1003675789614
DESTINATION_GROUP_ID = -1003598921129
BOT_TOKEN = "8359064642:AAFzFYj8ZFSZ1Vl9hdcWIiMkcb4vAuAHZII"

# تنظیم delay
DELAYS = {'photo': 2, 'video': 5, 'animation': 10}

# ذخیره داده‌ها در فایل برای جلوگیری از دست رفتن
import json
import os

DATA_FILE = "bot_data.json"

def load_data():
    """بارگذاری داده‌های ذخیره شده"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'last_times': {'photo': 0, 'video': 0, 'animation': 0},
        'forward_stats': {'photo': 0, 'video': 0, 'animation': 0, 'total': 0, 'from_bots': 0, 'from_users': 0},
        'forwarded_messages': []
    }

def save_data(last_times, forward_stats, forwarded_messages):
    """ذخیره داده‌ها"""
    data = {
        'last_times': last_times,
        'forward_stats': forward_stats,
        'forwarded_messages': list(forwarded_messages)[-1000:]  # فقط 1000 تا آخرین
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# بارگذاری داده‌ها
data = load_data()
last_times = data['last_times']
forward_stats = data['forward_stats']
forwarded_messages = set(data['forwarded_messages'])

# لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('forward_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def forward_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد مدیا"""
    
    chat_id = update.effective_chat.id
    
    # بررسی گروه مبدا
    if chat_id != SOURCE_GROUP_ID:
        return
    
    message = update.message
    message_id = message.message_id
    
    # جلوگیری از فوروارد مجدد
    if message_id in forwarded_messages:
        return
    
    # تشخیص نوع محتوا
    content_type = None
    if message.photo:
        content_type = 'photo'
        media_type = "عکس"
    elif message.video:
        content_type = 'video'
        media_type = "ویدیو"
    elif message.animation:
        content_type = 'animation'
        media_type = "گیف"
    else:
        return
    
    # محاسبه delay
    current_time = time.time()
    required_delay = DELAYS[content_type]
    last_time = last_times[content_type]
    time_passed = current_time - last_time
    
    if time_passed < required_delay:
        wait_time = required_delay - time_passed
        await asyncio.sleep(wait_time)
    
    try:
        # فوروارد پیام
        await context.bot.forward_message(
            chat_id=DESTINATION_GROUP_ID,
            from_chat_id=SOURCE_GROUP_ID,
            message_id=message_id
        )
        
        # بروزرسانی داده‌ها
        forwarded_messages.add(message_id)
        last_times[content_type] = time.time()
        forward_stats[content_type] += 1
        forward_stats['total'] += 1
        
        if message.from_user and message.from_user.is_bot:
            forward_stats['from_bots'] += 1
        else:
            forward_stats['from_users'] += 1
        
        # ذخیره داده‌ها
        save_data(last_times, forward_stats, forwarded_messages)
        
        # اطلاعات فرستنده
        sender_type = "بات" if message.from_user and message.from_user.is_bot else "کاربر"
        sender_name = "نامشخص"
        if message.from_user:
            if message.from_user.username:
                sender_name = f"@{message.from_user.username}"
            elif message.from_user.first_name:
                sender_name = message.from_user.first_name
        
        logger.info(f"✅ {media_type} از {sender_type} {sender_name} فوروارد شد")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ خطا: {error_msg}")
        
        if "Too Many Requests" in error_msg:
            await asyncio.sleep(30)
        elif "Message to forward not found" in error_msg:
            forwarded_messages.add(message_id)
            save_data(last_times, forward_stats, forwarded_messages)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    stats_text = f"""
🤖 **backupfreemedia**

✅ **وضعیت:** فعال
📍 **مبدا:** {SOURCE_GROUP_ID}
📍 **مقصد:** {DESTINATION_GROUP_ID}

📊 **آمار:**
• کل: {forward_stats['total']}
• از بات‌ها: {forward_stats['from_bots']}
• از کاربران: {forward_stats['from_users']}

🔧 **برای تست:** ویدیویی به گروه بفرستید
"""
    await update.message.reply_text(stats_text)

async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک‌سازی حافظه"""
    forwarded_messages.clear()
    save_data(last_times, forward_stats, forwarded_messages)
    await update.message.reply_text("✅ حافظه پاک شد")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاها"""
    logger.error(f"خطا: {context.error}")

def main():
    """تابع اصلی"""
    logger.info("🚀 شروع بات...")
    
    try:
        # 🔴 مهم: تنظیم timeout و drop_pending_updates
        app = Application.builder().token(BOT_TOKEN).build()
        
        # کامندها
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("cleanup", cleanup))
        
        # هندلر مدیا
        app.add_handler(MessageHandler(
            filters.PHOTO | filters.VIDEO | filters.ANIMATION,
            forward_media
        ))
        
        # هندلر خطا
        app.add_error_handler(error_handler)
        
        # 🔴 تنظیمات برای جلوگیری از conflict
        app.run_polling(
            poll_interval=1.0,
            timeout=60,
            drop_pending_updates=True,  # حذف آپدیت‌های قدیمی
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
        
    except Exception as e:
        logger.error(f"❌ خطای اصلی: {e}")
        # ذخیره داده‌ها قبل از خروج
        save_data(last_times, forward_stats, forwarded_messages)
        sys.exit(1)

if __name__ == '__main__':
    main()
