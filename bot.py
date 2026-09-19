
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# توکن جدید ربات را اینجا وارد کن
TOKEN = "8850373531:AAHe0CfB5f2-C382MtqG3wt0RxBLvjXFO8Q"

# بعداً شناسه عددی خودت را اینجا قرار می‌دهیم

ADMIN_ID = 8276323231

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👗 لباس‌های مجلسی", callback_data="majlesi")],
        [InlineKeyboardButton("👖 سرپطلونی", callback_data="sarpatloni")],
        [InlineKeyboardButton("🧵 سفارش دوخت", callback_data="dokht")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
        [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
    ]

    await update.message.reply_text(
        "🌸 به Mohammadi Fashion خوش آمدید 🌸\n\n"
        "عرضه کننده لباس‌های زنانه",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
if query.data == "admin":
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product")],
        [InlineKeyboardButton("🖼️ افزودن عکس", callback_data="add_photo")],
        [InlineKeyboardButton("💰 تغییر قیمت", callback_data="change_price")],
        [InlineKeyboardButton("🗑️ حذف محصول", callback_data="delete_product")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
    ]

    await query.edit_message_text(
        "⚙️ مدیریت فروشگاه\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    elif query.data == "majlesi":
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
            "✨ بخمل نگین‌دار ✨\n\n"
            "💰 قیمت: ۷۰۰",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "sarpatloni":
        keyboard = [
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")]
        ]

        await query.edit_message_text(
            "👖 سرپطلونی\n\n"
            "محصولات این بخش به‌زودی اضافه می‌شوند.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "dokht":
        keyboard = [
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")]
        ]

        await query.edit_message_text(
            "🧵 سفارش دوخت\n\n"
            "لطفاً مشخصات لباس مورد نظر خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "order":
        keyboard = [
            [InlineKeyboardButton("🔙 برگشت", callback_data="velvet")]
        ]

        await query.edit_message_text(
            "🛒 ثبت سفارش\n\n"
            "لطفاً نام و شماره تماس خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "contact":
        keyboard = [
            [InlineKeyboardButton(
                "💬 پیام در تلگرام",
                url="https://t.me/Rohullah1375"
            )],
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
        ]

        await query.edit_message_text(
            "📞 تماس با ما\n\n"
            "📱 شماره تماس اول: 0775816499\n"
            "📱 شماره تماس دوم: 0744763112\n"
            "💬 تلگرام: @Rohullah1375\n\n"
            "🌸 Mohammadi Fashion 🌸",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "home":
        keyboard = [
            [InlineKeyboardButton("👗 لباس‌های مجلسی", callback_data="majlesi")],
            [InlineKeyboardButton("👖 سرپطلونی", callback_data="sarpatloni")],
            [InlineKeyboardButton("🧵 سفارش دوخت", callback_data="dokht")],
            [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
            [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
        ]

        await query.edit_message_text(
            "🌸 Mohammadi Fashion 🌸\n\n"
            "لطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


def main():
    if not TOKEN or TOKEN == "توکن_جدید_خودت":
        raise RuntimeError("توکن ربات وارد نشده است.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
