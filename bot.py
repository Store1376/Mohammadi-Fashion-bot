from telegram import os Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = osgetenv("8850373531:AAEaNxDYTYNhQ5aYKQnPmp7m-f34PD-tzg4")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛍️ مشاهده محصولات", callback_data="products")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")]
    ]

    await update.message.reply_text(
        "سلام دوست من! 👋\nبه فروشگاه محمدی فیشن خوش آمدید 🌹",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "products":
        keyboard = [
            [InlineKeyboardButton("👗 لباس مجلسی", callback_data="party")],
            [InlineKeyboardButton("🧕 لباس محجبه", callback_data="modest")],
            [InlineKeyboardButton("🌸 لباس روزمره", callback_data="daily")],
            [InlineKeyboardButton("✂️ سفارش دوخت", callback_data="tailoring")]
        ]

        await query.message.reply_text(
            "🛍️ دسته‌بندی محصولات را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "party":
        await query.message.reply_text(
            "👗 لباس بخمل نگین‌دار\n\n"
            "💰 قیمت: ۷۰۰ افغانی\n\n"
            "📦 برای ثبت سفارش با ما تماس بگیرید."
        )

    elif query.data == "contact":
        await query.message.reply_text(
            "📞 برای سفارش و معلومات بیشتر با ما تماس بگیرید."
        )

    elif query.data == "modest":
        await query.message.reply_text("🧕 لباس‌های محجبه به‌زودی اضافه می‌شوند.")

    elif query.data == "daily":
        await query.message.reply_text("🌸 لباس‌های روزمره به‌زودی اضافه می‌شوند.")

    elif query.data == "tailoring":
        await query.message.reply_text("✂️ برای سفارش دوخت، با ما تماس بگیرید.")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()
