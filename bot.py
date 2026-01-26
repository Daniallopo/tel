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

# تنظیم لاگ
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
        current_time = time.time()
        caption = update.message.caption if update.message.caption else ""
        
        # تشخیص نوع محتوا
        if update.message.photo:
            media_type = "عکس"
            content_type = 'photo'
            send_func = context.bot.send_photo
            file_id = update.message.photo[-1].file_id
            
        elif update.message.video:
            media_type = "ویدیو"
            content_type = 'video'
            send_func = context.bot.send_video
            file_id = update.message.video.file_id
            
        elif update.message.animation:
            media_type = "گیف"
            content_type = 'animation'
            send_func = context.bot.send_animation
            file_id = update.message.animation.file_id
            
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
        
        # ارسال به گروه مقصد
        await send_func(
            chat_id=DESTINATION_GROUP_ID,
            **{content_type: file_id},
            caption=caption,
            parse_mode='HTML' if caption else None
        )
        
        # آپدیت زمان آخرین فوروارد
        last_times[content_type] = time.time()
        
        # آپدیت آمار
        forward_stats[content_type] += 1
        forward_stats['total'] += 1
        
        logging.info(f"✅ {media_type} فوروارد شد | 📊 کل: {forward_stats['total']}")
        
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
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

💡 **نکته:** delayها برای هر نوع محتوا جداگانه محاسبه می‌شوند.
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

🔄 **وضعیت:** ✅ فعال
📅 **آپ‌تایم:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای دستورات"""
    help_text = """
📚 **راهنمای دستورات ربات**

🎯 **دستورات اصلی:**
/start - راه‌اندازی و نمایش اطلاعات ربات
/stats - نمایش آمار کامل و وضعیت
/help - این راهنما
/settings - نمایش تنظیمات فعلی

⚙️ **تنظیمات فعلی:**
• Delay عکس: هر {DELAYS['photo']} ثانیه
• Delay ویدیو: هر {DELAYS['video']} ثانیه
• Delay گیف: هر {DELAYS['animation']} ثانیه

⚠️ **نکات مهم:**
1. delayها برای هر نوع محتوا جداگانه حساب می‌شوند
2. اگر Rate Limit بخوریم، 20 ثانیه صبر می‌کنیم
3. ربات فقط از گروه مبدا ({SOURCE_GROUP_ID}) دریافت می‌کند
4. تمام لاگ‌ها در فایل forward_bot.log ذخیره می‌شوند

🔧 **پشتیبانی:** برای گزارش مشکل یا پیشنهاد، با سازنده ربات تماس بگیرید.
"""
    await update.message.reply_text(help_text.format(**DELAYS, SOURCE_GROUP_ID=SOURCE_GROUP_ID))

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تنظیمات"""
    settings_text = f"""
⚙️ **تنظیمات ربات**

📌 **شناسه‌ها:**
• گروه مبدا: `{SOURCE_GROUP_ID}`
• گروه مقصد: `{DESTINATION_GROUP_ID}`

⏱️ **محدودیت‌های زمانی:**
• عکس: هر {DELAYS['photo']} ثانیه یکبار
• ویدیو: هر {DELAYS['video']} ثانیه یکبار  
• گیف: هر {DELAYS['animation']} ثانیه یکبار

🛡️ **مدیریت خطا:**
• Rate Limit: 20 ثانیه پنالتی
• Timeout: 10 ثانیه انتظار
• Connection Error: 5 ثانیه انتظار

📝 **لاگ‌گیری:**
• فایل لاگ: forward_bot.log
• سطح لاگ: INFO
• فرمت زمان: YYYY-MM-DD HH:MM:SS

💡 **برای تغییر تنظیمات، کد ربات را ویرایش کنید.**
"""
    await update.message.reply_text(settings_text, parse_mode='Markdown')

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بررسی وضعیت آنلاین بودن"""
    start_time = time.time()
    message = await update.message.reply_text("🔄 در حال بررسی...")
    end_time = time.time()
    response_time = round((end_time - start_time) * 1000, 2)
    
    ping_text = f"""
🏓 **Pong!**

✅ ربات آنلاین و فعال است
⚡ زمان پاسخ: {response_time} میلی‌ثانیه
📅 زمان سرور: {datetime.now().strftime("%H:%M:%S")}
📊 فوروارد امروز: {forward_stats['total']}
"""
    await message.edit_text(ping_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاهای全局"""
    logging.error(f"خطا در پردازش: {context.error}", exc_info=context.error)

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
