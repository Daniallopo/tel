import asyncio
import logging
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات
SOURCE_GROUP_ID = -1003675789614
DESTINATION_GROUP_ID = -1003598921129
BOT_TOKEN = "8359064642:AAFzFYj8ZFSZ1Vl9hdcWIiMkcb4vAuAHZII"

# 🔴 لیست بات‌هایی که باید فوروارد بشن (شامل hlanti)
ALLOWED_BOTS = ['hlanti_bot', 'your_other_bot_username']  # یوزرنیم بات‌ها

# تنظیم delay
DELAYS = {'photo': 2, 'video': 5, 'animation': 10}

# زمان آخرین فوروارد
last_times = {'photo': 0, 'video': 0, 'animation': 0}

# آمار
forward_stats = {'photo': 0, 'video': 0, 'animation': 0, 'total': 0, 'from_bots': 0, 'from_users': 0}

# پیام‌های فوروارد شده
forwarded_messages = set()

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

async def should_forward_message(message) -> bool:
    """بررسی آیا پیام باید فوروارد شود"""
    
    # 🔴 مهم: اگر پیام از بات hlanti باشد، حتماً فوروارد کن
    if message.from_user and message.from_user.is_bot:
        logger.info(f"🤖 پیام از بات: {message.from_user.username or message.from_user.id}")
        
        # اگر یوزرنیم بات hlanti را می‌دانید، چک کنید
        if message.from_user.username:
            logger.info(f"   بات: @{message.from_user.username}")
        
        return True  # 🔴 همه پیام‌های بات‌ها رو فوروارد کن
    
    # پیام از کاربر عادی
    return True

async def forward_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد همه مدیا (هم از کاربران، هم از بات‌ها)"""
    
    chat_id = update.effective_chat.id
    
    # بررسی گروه مبدا
    if chat_id != SOURCE_GROUP_ID:
        return
    
    message = update.message
    message_id = message.message_id
    
    # جلوگیری از فوروارد مجدد
    if message_id in forwarded_messages:
        logger.info(f"⏭️ پیام {message_id} قبلاً فوروارد شده")
        return
    
    # 🔴 بررسی آیا پیام باید فوروارد شود
    if not await should_forward_message(message):
        logger.info(f"⏭️ پیام {message_id} فیلتر شد")
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
        logger.info(f"⏳ {wait_time:.1f} ثانیه تأخیر برای {media_type}")
        await asyncio.sleep(wait_time)
    
    try:
        # تشخیص فرستنده
        sender_type = "بات" if message.from_user and message.from_user.is_bot else "کاربر"
        sender_name = "نامشخص"
        
        if message.from_user:
            if message.from_user.username:
                sender_name = f"@{message.from_user.username}"
            elif message.from_user.first_name:
                sender_name = message.from_user.first_name
            elif message.from_user.id:
                sender_name = f"ID:{message.from_user.id}"
        
        logger.info(f"🔄 فوروارد {media_type} از {sender_type} {sender_name}...")
        
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
        
        logger.info(f"✅ فوروارد شد: {media_type} از {sender_type} {sender_name}")
        logger.info(f"📊 آمار: کل={forward_stats['total']}, بات‌ها={forward_stats['from_bots']}, کاربران={forward_stats['from_users']}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ خطا در فوروارد: {error_msg}")
        
        if "Too Many Requests" in error_msg or "429" in error_msg:
            logger.warning("⚠️ Rate Limit! 30 ثانیه پنالتی")
            penalty = time.time() + 30
            for key in last_times:
                last_times[key] = penalty
            await asyncio.sleep(30)
            
        elif "Message to forward not found" in error_msg:
            logger.warning(f"⚠️ پیام {message_id} پیدا نشد")
            forwarded_messages.add(message_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    stats_text = f"""
🤖 **backupfreemedia v2.0**

📍 **گروه‌ها:**
• مبدا: `{SOURCE_GROUP_ID}`
• مقصد: `{DESTINATION_GROUP_ID}`

📊 **آمار کامل:**
• کل فورواردها: {forward_stats['total']}
• از بات‌ها: {forward_stats['from_bots']}
• از کاربران: {forward_stats['from_users']}

📁 **براساس نوع:**
• عکس: {forward_stats['photo']}
• ویدیو: {forward_stats['video']}
• گیف: {forward_stats['animation']}

⚙️ **تنظیمات:**
• تأخیر عکس: {DELAYS['photo']}s
• تأخیر ویدیو: {DELAYS['video']}s
• تأخیر گیف: {DELAYS['animation']}s

🔒 **حافظه:**
• پیام‌های کش: {len(forwarded_messages)}

✅ **حالت: فوروارد همه پیام‌ها (هم کاربران، هم بات‌ها)**
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def test_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تست فوروارد دستی"""
    try:
        # فوروارد آخرین پیام گروه
        messages = await context.bot.get_chat_history(SOURCE_GROUP_ID, limit=1)
        
        if messages:
            last_msg = messages[0]
            await context.bot.forward_message(
                chat_id=DESTINATION_GROUP_ID,
                from_chat_id=SOURCE_GROUP_ID,
                message_id=last_msg.message_id
            )
            await update.message.reply_text("✅ تست فوروارد انجام شد")
        else:
            await update.message.reply_text("❌ پیامی در گروه نیست")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در تست: {str(e)}")

def main():
    """اجرای اصلی"""
    logger.info("=" * 60)
    logger.info("🚀 بات backupfreemedia v2.0 شروع شد")
    logger.info(f"📍 مبدا: {SOURCE_GROUP_ID}")
    logger.info(f"📍 مقصد: {DESTINATION_GROUP_ID}")
    logger.info("🔓 حالت: فوروارد همه (کاربران + بات‌ها)")
    logger.info("=" * 60)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # کامندها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test_forward))
    
    # 🔴 مهم: فیلتر ALL برای دریافت همه پیام‌ها
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION,
        forward_media
    ))
    
    try:
        app.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"❌ خطای اصلی: {e}")

if __name__ == '__main__':
    main()
