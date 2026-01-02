import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات
SOURCE_GROUP_ID = -1003675789614  # آیدی گروه مبدا (منفی)
DESTINATION_GROUP_ID = -1003598921129  # آیدی گروه مقصد (منفی)
BOT_TOKEN = "8359064642:AAFzFYj8ZFSZ1Vl9hdcWIiMkcb4vAuAHZII"

# تنظیم لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def forward_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد عکس و فیلم"""
    try:
        # بررسی اینکه پیام از گروه مبدا است
        if update.effective_chat.id == SOURCE_GROUP_ID:

            # اگر پیام عکس باشد
            if update.message.photo:
                # گرفتن بزرگترین سایز عکس
                photo = update.message.photo[-1]
                await context.bot.send_photo(
                    chat_id=DESTINATION_GROUP_ID,
                    photo=photo.file_id,
                    caption=update.message.caption
                )
                logging.info(f"عکس فوروارد شد از {update.effective_chat.id}")

            # اگر پیام ویدیو باشد
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=DESTINATION_GROUP_ID,
                    video=update.message.video.file_id,
                    caption=update.message.caption
                )
                logging.info(f"ویدیو فوروارد شد از {update.effective_chat.id}")

            # اگر پیام انیمیشن (GIF) باشد
            elif update.message.animation:
                await context.bot.send_animation(
                    chat_id=DESTINATION_GROUP_ID,
                    animation=update.message.animation.file_id,
                    caption=update.message.caption
                )
                logging.info(f"انیمیشن فوروارد شد از {update.effective_chat.id}")

    except Exception as e:
        logging.error(f"خطا در فوروارد: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    await update.message.reply_text("ربات فعال است و منتظر محتوای گروه می‌باشد.")

def main():
    """تابع اصلی"""
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()

    # اضافه کردن هندلرها
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION,
        forward_media
    ))

    application.add_handler(CommandHandler("start", start))

    # اجرای ربات
    logging.info("ربات در حال اجراست...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
