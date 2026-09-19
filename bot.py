from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8850373531:AAHe0CfB5f2-C382MtqG3wt0RxBLvjXFO8Q"
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
        await query.edit_message_text(
            "👖 سرپطلونی\n\n"
            "محصولات این بخش به‌زودی اضافه می‌شوند.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="home")]
            ]),
        )

    elif query.data == "dokht":
        await query.edit_message_text(
            "🧵 سفارش دوخت\n\n"
            "لطفاً مشخصات لباس مورد نظر خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="home")]
            ]),
        )

    elif query.data == "order":
        await query.edit_message_text(
            "🛒 ثبت سفارش\n\n"
            "لطفاً نام و شماره تماس خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="velvet")]
            ]),
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

    elif query.data == "add_product":
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        context.user_data["adding_product"] = True

        await query.edit_message_text(
            "➕ افزودن محصول\n\n"
            "لطفاً نام محصول را ارسال کن."
        )

    elif query.data == "add_photo":
        await query.edit_message_text(
            "🖼️ افزودن عکس\n\n"
            "این قسمت را بعداً فعال می‌کنیم.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="admin")]
            ]),
        )

    elif query.data == "change_price":
        await query.edit_message_text(
            "💰 تغییر قیمت\n\n"
            "این قسمت را بعداً فعال می‌کنیم.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="admin")]
            ]),
        )

    elif query.data == "delete_product":
        await query.edit_message_text(
            "🗑️ حذف محصول\n\n"
            "این قسمت را بعداً فعال می‌کنیم.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="admin")]
            ]),
        )


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("adding_product"):
        product_name = update.message.text

        context.user_data["product_name"] = product_name
        context.user_data["adding_product"] = False

        await update.message.reply_text(
            f"✅ محصول ثبت شد:\n\n"
            f"👗 {product_name}\n\n"
            f"مرحله بعد: تعیین قیمت محصول."
        )


def main():
    if not TOKEN or TOKEN == "توکن_جدید_خودت":
        raise RuntimeError("توکن ربات وارد نشده است.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
