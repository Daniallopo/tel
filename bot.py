import asyncio
import logging
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات
SOURCE_GROUP_ID = -1003675789614
DESTINATION_GROUP_ID = -1003598921129
BOT_TOKEN = "8359064642:AAFzFYj8ZFSZ1Vl9hdcWIiMkcb4vAuAHZII"

# تنظیم delay
DELAY_PHOTO = 2  # ثانیه برای عکس
DELAY_VIDEO = 5  # ثانیه برای ویدیو
DELAY_GIF = 3    # ثانیه برای گیف

# زمان آخرین فوروارد
last_forward_time = 0
forward_count = 0  # شمارنده فورواردها

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def forward_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد عکس و فیلم با delay هوشمند"""
    global last_forward_time, forward_count
    
    # بررسی گروه مبدا
    if update.effective_chat.id != SOURCE_GROUP_ID:
        return
    
    try:
        # تعیین delay براساس نوع محتوا
        if update.message.video:
            required_delay = DELAY_VIDEO
            media_type = "ویدیو"
        elif update.message.animation:
            required_delay = DELAY_GIF
            media_type = "گیف"
        elif update.message.photo:
            required_delay = DELAY_PHOTO
            media_type = "عکس"
        else:
            return
        
        # محاسبه زمان باقی‌مانده تا فوروارد بعدی
        current_time = time.time()
        time_passed = current_time - last_forward_time
        
        if time_passed < required_delay:
            wait_time = required_delay - time_passed
            logging.info(f"⏳ {wait_time:.1f}ثانیه تاخیر برای {media_type}...")
            await asyncio.sleep(wait_time)
        
        # فوروارد محتوا
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=DESTINATION_GROUP_ID,
                photo=update.message.photo[-1].file_id,
                caption=update.message.caption
            )
        
        elif update.message.video:
            await context.bot.send_video(
                chat_id=DESTINATION_GROUP_ID,
                video=update.message.video.file_id,
                caption=update.message.caption
            )
        
        elif update.message.animation:
            await context.bot.send_animation(
                chat_id=DESTINATION_GROUP_ID,
                animation=update.message.animation.file_id,
                caption=update.message.caption
            )
        
        # به‌روزرسانی زمان آخرین فوروارد
        last_forward_time = time.time()
        forward_count += 1
        
        logging.info(f"✅ {media_type} فوروارد شد (تعداد: {forward_count})")
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"❌ خطا: {error_msg}")
        
        # تشخیص Rate Limit
        if "Too Many Requests" in error_msg or "429" in error_msg:
            logging.warning("⚠️ محدودیت سرعت! 15 ثانیه صبر...")
            last_forward_time = time.time() + 15  # پنالتی سنگین
            await asyncio.sleep(15)
        elif "timed out" in error_msg.lower():
            logging.warning("⏱️ timeout! 5 ثانیه صبر...")
            await asyncio.sleep(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    await update.message.reply_text(
        "🤖 **ربات فوروارد فعال شد**\n\n"
        f"📍 **گروه مبدا:** `{SOURCE_GROUP_ID}`\n"
        f"📍 **گروه مقصد:** `{DESTINATION_GROUP_ID}`\n\n"
        "⚙️ **تنظیمات delay:**\n"
        f"• عکس: {DELAY_PHOTO} ثانیه\n"
        f"• ویدیو: {DELAY_VIDEO} ثانیه\n"
        f"• گیف: {DELAY_GIF} ثانیه"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار ربات"""
    await update.message.reply_text(
        f"📊 **آمار ربات:**\n"
        f"• تعداد فورواردها: {forward_count}\n"
        f"• وضعیت: ✅ فعال\n"
        f"• آخرین فوروارد: {time.ctime(last_forward_time) if last_forward_time > 0 else 'هنوز هیچ'}"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنما"""
    await update.message.reply_text(
        "📚 **راهنما:**\n\n"
        "/start - شروع ربات\n"
        "/stats - نمایش آمار\n"
        "/help - این راهنما\n\n"
        "⚠️ **توجه:**\n"
        "• بین فورواردها delay خودکار داریم\n"
        "• ویدیوها delay بیشتری می‌گیرند\n"
        "• اگر Rate Limit خوردیم، 15 ثانیه صبر می‌کنیم"
    )

def main():
    """تابع اصلی"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION,
        forward_media
    ))
    
    # اجرای ربات
    logging.info("=" * 50)
    logging.info("🤖 ربات فوروارد مدیا شروع به کار کرد")
    logging.info(f"📍 گروه مبدا: {SOURCE_GROUP_ID}")
    logging.info(f"📍 گروه مقصد: {DESTINATION_GROUP_ID}")
    logging.info(f"⏱️ Delay عکس: {DELAY_PHOTO}ث - ویدیو: {DELAY_VIDEO}ث - گیف: {DELAY_GIF}ث")
    logging.info("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
