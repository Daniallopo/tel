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

# تنظیم delay برای هر نوع محتوا
DELAYS = {
    'photo': 2,      # ثانیه برای عکس
    'video': 5,      # ثانیه برای ویدیو
    'animation': 10  # ثانیه برای گیف
}

# زمان آخرین فوروارد برای هر نوع
last_times = {
    'photo': 0,
    'video': 0,
    'animation': 0
}

# آمار فورواردها
forward_stats = {
    'photo': 0,
    'video': 0,
    'animation': 0,
    'total': 0
}

# 🔴 اضافه کردن: ردیابی پیام‌های فوروارد شده
forwarded_messages = set()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('forward_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

async def forward_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد عکس و فیلم با delay هوشمند"""
    
    # بررسی گروه مبدا
    if update.effective_chat.id != SOURCE_GROUP_ID:
        return
    
    try:
        message = update.message
        message_id = message.message_id
        
        # 🔴 جلوگیری از فوروارد مجدد
        if message_id in forwarded_messages:
            logging.info(f"⏭️ پیام {message_id} قبلاً فوروارد شده، رد شد")
            return
        
        current_time = time.time()
        
        # تشخیص نوع محتوا
        if message.photo:
            media_type = "عکس"
            content_type = 'photo'
            
        elif message.video:
            media_type = "ویدیو"
            content_type = 'video'
            
        elif message.animation:
            media_type = "گیف"
            content_type = 'animation'
            
        else:
            return
        
        # محاسبه delay لازم
        required_delay = DELAYS[content_type]
        last_time = last_times[content_type]
        time_passed = current_time - last_time
        
        # اگر زمان لازم نگذشته، صبر کن
        if time_passed < required_delay:
            wait_time = required_delay - time_passed
            logging.info(f"⏳ {wait_time:.1f} ثانیه تاخیر برای {media_type}...")
            await asyncio.sleep(wait_time)
        
        # 🔴 مهم: استفاده از forward_message به جای send_photo/send_video
        await context.bot.forward_message(
            chat_id=DESTINATION_GROUP_ID,
            from_chat_id=SOURCE_GROUP_ID,
            message_id=message_id
        )
        
        # 🔴 علامت‌گذاری پیام به عنوان فوروارد شده
        forwarded_messages.add(message_id)
        
        # آپدیت زمان آخرین فوروارد
        last_times[content_type] = time.time()
        
        # آپدیت آمار
        forward_stats[content_type] += 1
        forward_stats['total'] += 1
        
        # لاگ اطلاعات ارسال کننده
        sender_info = "نامشخص"
        if message.from_user:
            if message.from_user.username:
                sender_info = f"@{message.from_user.username}"
            elif message.from_user.first_name:
                sender_info = message.from_user.first_name
            elif message.from_user.id:
                sender_info = f"کاربر {message.from_user.id}"
        
        logging.info(f"✅ {media_type} از {sender_info} فوروارد شد | 📊 کل: {forward_stats['total']}")
        
        # 🔴 پاک‌سازی پیام‌های قدیمی از حافظه (برای جلوگیری از مصرف زیاد RAM)
        if len(forwarded_messages) > 1000:
            # پاک‌سازی 200 تا از قدیمی‌ترین‌ها
            oldest_messages = sorted(forwarded_messages)[:200]
            for old_msg in oldest_messages:
                forwarded_messages.remove(old_msg)
            logging.info(f"🧹 حافظه پاک‌سازی شد: {len(oldest_messages)} پیام قدیمی حذف شد")
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"❌ خطا در فوروارد: {error_msg}")
        
        # تشخیص Rate Limit
        if "Too Many Requests" in error_msg or "429" in error_msg:
            logging.warning("⚠️ محدودیت سرعت! 20 ثانیه صبر...")
            # پنالتی برای همه نوع محتواها
            penalty_time = time.time() + 20
            for key in last_times:
                last_times[key] = penalty_time
            await asyncio.sleep(20)
            
        elif "timed out" in error_msg.lower():
            logging.warning("⏱️ Timeout! 10 ثانیه صبر...")
            await asyncio.sleep(10)
            
        elif "Connection" in error_msg:
            logging.warning("🌐 مشکل اتصال! 5 ثانیه صبر...")
            await asyncio.sleep(5)
            
        elif "Message to forward not found" in error_msg:
            logging.warning(f"⚠️ پیام {message_id} پیدا نشد (احتمالاً حذف شده)")
            # حتی اگر پیدا نشد، علامت‌گذاری کن تا دوباره تلاش نکند
            forwarded_messages.add(message_id)
            
        elif "bot was blocked" in error_msg.lower():
            logging.error("🚫 بات بلاک شده است!")
            raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    # 🔴 اضافه کردن اطلاعات جدید
    welcome_text = f"""
🤖 **ربات فوروارد مدیا فعال شد**

📍 **گروه مبدا:** `{SOURCE_GROUP_ID}`
📍 **گروه مقصد:** `{DESTINATION_GROUP_ID}`

⚙️ **تنظیمات Delay:**
• 📸 عکس: {DELAYS['photo']} ثانیه
• 🎥 ویدیو: {DELAYS['video']} ثانیه  
• 🎬 گیف: {DELAYS['animation']} ثانیه

📊 **آمار فعلی:**
• کل فورواردها: {forward_stats['total']}
• عکس: {forward_stats['photo']}
• ویدیو: {forward_stats['video']}
• گیف: {forward_stats['animation']}

🔒 **حافظه:**
• پیام‌های رد شده: {len(forwarded_messages)}

💡 **نکته جدید:** 
این بات از forward_message استفاده می‌کند، بنابراین:
1. پیام‌ها دوباره آپلود نمی‌شوند
2. همه اطلاعات اصلی حفظ می‌شود
3. بات‌های دیگر هم فوروارد می‌شوند
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کامل"""
    
    def format_timestamp(timestamp):
        if timestamp > 0:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return "هنوز هیچ"
    
    # محاسبه زمان‌های باقی‌مانده
    current_time = time.time()
    time_remaining = {}
    for content_type, last_time in last_times.items():
        remaining = DELAYS[content_type] - (current_time - last_time)
        time_remaining[content_type] = max(0, round(remaining, 1))
    
    stats_text = f"""
📊 **آمار کامل ربات**

🔢 **تعداد فورواردها:**
• 📸 عکس: {forward_stats['photo']}
• 🎥 ویدیو: {forward_stats['video']}
• 🎬 گیف: {forward_stats['animation']}
• 📈 کل: {forward_stats['total']}

⏰ **زمان آخرین فوروارد:**
• عکس: {format_timestamp(last_times['photo'])}
• ویدیو: {format_timestamp(last_times['video'])}
• گیف: {format_timestamp(last_times['animation'])}

⏳ **زمان باقی‌مانده تا فوروارد بعدی:**
• عکس: {time_remaining['photo']} ثانیه
• ویدیو: {time_remaining['video']} ثانیه
• گیف: {time_remaining['animation']} ثانیه

🔒 **حافظه:**
• پیام‌های رد شده: {len(forwarded_messages)}

🔄 **وضعیت:** ✅ فعال
📅 **آپ‌تایم:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک‌سازی حافظه کش"""
    old_count = len(forwarded_messages)
    forwarded_messages.clear()
    
    # لاگ اطلاعات
    logging.info(f"🧹 حافظه پاک‌سازی شد: {old_count} پیام حذف شد")
    
    await update.message.reply_text(
        f"✅ حافظه پاک‌سازی شد\n"
        f"🗑️ {old_count} پیام از کش حذف شد\n"
        f"📊 فورواردهای کل: {forward_stats['total']}"
    )

def main():
    """تابع اصلی اجرای ربات"""
    
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرهای دستور
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("clear", clear_cache))  # 🔴 کامند جدید
    
    # هندلر مدیا
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION,
        forward_media
    ))
    
    # هندلر خطا
    application.add_error_handler(error_handler)
    
    # نمایش اطلاعات شروع
    logging.info("=" * 60)
    logging.info("🤖 ربات فوروارد مدیا شروع به کار کرد")
    logging.info(f"📍 گروه مبدا: {SOURCE_GROUP_ID}")
    logging.info(f"📍 گروه مقصد: {DESTINATION_GROUP_ID}")
    logging.info(f"⏱️ تنظیمات Delay:")
    logging.info(f"   • عکس: {DELAYS['photo']} ثانیه")
    logging.info(f"   • ویدیو: {DELAYS['video']} ثانیه")
    logging.info(f"   • گیف: {DELAYS['animation']} ثانیه")
    logging.info(f"🔒 روش: forward_message (فوروارد مستقیم)")
    logging.info(f"📝 لاگ در فایل: forward_bot.log")
    logging.info("=" * 60)
    
    # اجرای ربات
    try:
        application.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except KeyboardInterrupt:
        logging.info("⏹️ ربات توسط کاربر متوقف شد")
    except Exception as e:
        logging.error(f"❌ خطای غیرمنتظره: {e}")

if __name__ == '__main__':
    main()
