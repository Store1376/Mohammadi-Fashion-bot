import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8850373531:AAEaNxDYTYNhQ5aYKQnPmp7m-f34PD-tzg4"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👗 لباس‌های مجلسی", callback_data="majlesi")],
        [InlineKeyboardButton("👖 سرپطلونی", callback_data="sarpatloni")],
        [InlineKeyboardButton("🧵 سفارش دوخت", callback_data="dokht")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
    ]

    await update.message.reply_text(
        "🌸 به Mohammadi Fashion خوش آمدید 🌸\n\n"
        "عرضه کننده لباس‌های زنانه",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "majlesi":
        keyboard = [
            [InlineKeyboardButton("✨ بخمل نگین‌دار — ۷۰۰", callback_data="velvet")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
        ]
        await query.edit_message_text(
            "👗 لباس‌های مجلسی\n\nمحصولات موجود:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "velvet":
        keyboard = [
            [InlineKeyboardButton("🛒 سفارش این لباس", callback_data="order")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="majlesi")],
        ]
        await query.edit_message_text(
            "✨ بخمل نگین‌دار ✨\n\n💰 قیمت: ۷۰۰",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "sarpatloni":
        keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="home")]]
        await query.edit_message_text(
            "👖 سرپطلونی\n\nمحصولات این بخش به‌زودی اضافه می‌شوند.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "dokht":
        keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="home")]]
        await query.edit_message_text(
            "🧵 سفارش دوخت\n\nلطفاً مشخصات لباس مورد نظر خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "order":
        keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="velvet")]]
        await query.edit_message_text(
            "🛒 ثبت سفارش\n\nلطفاً نام و شماره تماس خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "contact":
        keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data="home")]]
        await query.edit_message_text(
            "📞 تماس با ما\n\nاطلاعات تماس فروشگاه بعداً اضافه می‌شود.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "home":
        keyboard = [
            [InlineKeyboardButton("👗 لباس‌های مجلسی", callback_data="majlesi")],
            [InlineKeyboardButton("👖 سرپطلونی", callback_data="sarpatloni")],
            [InlineKeyboardButton("🧵 سفارش دوخت", callback_data="dokht")],
            [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
        ]
        await query.edit_message_text(
            "🌸 Mohammadi Fashion 🌸\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
