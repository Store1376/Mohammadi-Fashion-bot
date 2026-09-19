import json
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8850373531:AAF6hj98W0rOJIpNXuTZL5hQSvvYhnELY10"
ADMIN_ID = 8276323231

PRODUCTS_FILE = "products.json"


def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []

    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as file:
        json.dump(products, file, ensure_ascii=False, indent=2)


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
        products = load_products()

        keyboard = []

        for product in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"✨ {product['name']} — {product['price']}",
                    callback_data=f"product_{product['id']}"
                )
            ])

        if not products:
            text = "👗 لباس‌های مجلسی\n\nهنوز محصولی اضافه نشده است."
        else:
            text = "👗 لباس‌های مجلسی\n\nمحصولات موجود:"

        keyboard.append([
            InlineKeyboardButton("🔙 برگشت", callback_data="home")
        ])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data.startswith("product_"):
        product_id = query.data.replace("product_", "")

        products = load_products()

        product = None

        for item in products:
            if item["id"] == product_id:
                product = item
                break

        if product is None:
            await query.edit_message_text("❌ محصول پیدا نشد.")
            return

        keyboard = [
            [InlineKeyboardButton(
                "🛒 سفارش این لباس",
                callback_data=f"order_{product_id}"
            )],
            [InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="majlesi"
            )],
        ]

        text = (
            f"✨ {product['name']} ✨\n\n"
            f"💰 قیمت: {product['price']}"
        )

        if product.get("photo"):
            await query.message.reply_photo(
                photo=product["photo"],
                caption=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

            await query.edit_message_text(
                "🖼️ عکس محصول بالا نمایش داده شد."
            )
        else:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    elif query.data.startswith("order_"):
        await query.edit_message_text(
            "🛒 ثبت سفارش\n\n"
            "لطفاً نام و شماره تماس خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="majlesi"
                )]
            ]),
        )

    elif query.data == "sarpatloni":
        await query.edit_message_text(
            "👖 سرپطلونی\n\n"
            "محصولات این بخش به‌زودی اضافه می‌شوند.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ]),
        )

    elif query.data == "dokht":
        await query.edit_message_text(
            "🧵 سفارش دوخت\n\n"
            "لطفاً مشخصات لباس مورد نظر خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ]),
        )

    elif query.data == "contact":
        keyboard = [
            [InlineKeyboardButton(
                "💬 پیام در تلگرام",
                url="https://t.me/Rohullah1375"
            )],
            [InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="home"
            )],
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
            [InlineKeyboardButton(
                "👗 لباس‌های مجلسی",
                callback_data="majlesi"
            )],
            [InlineKeyboardButton(
                "👖 سرپطلونی",
                callback_data="sarpatloni"
            )],
            [InlineKeyboardButton(
                "🧵 سفارش دوخت",
                callback_data="dokht"
            )],
            [InlineKeyboardButton(
                "📞 تماس با ما",
                callback_data="contact"
            )],
            [InlineKeyboardButton(
                "⚙️ مدیریت فروشگاه",
                callback_data="admin"
            )],
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
            "ابتدا محصول را با گزینه «افزودن محصول» ایجاد کن."
        )

    elif query.data == "change_price":
        await query.edit_message_text(
            "💰 تغییر قیمت\n\n"
            "این قسمت را در مرحله بعد فعال می‌کنیم.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="admin"
                )]
            ]),
        )

    elif query.data == "delete_product":
        await query.edit_message_text(
            "🗑️ حذف محصول\n\n"
            "این قسمت را در مرحله بعد فعال می‌کنیم.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="admin"
                )]
            ]),
        )


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("adding_product"):
        product_name = update.message.text.strip()

        context.user_data["product_name"] = product_name
        context.user_data["adding_product"] = False
        context.user_data["adding_price"] = True

        await update.message.reply_text(
            f"✅ نام محصول ثبت شد:\n\n"
            f"👗 {product_name}\n\n"
            f"💰 حالا قیمت محصول را ارسال کن."
        )

        return

    if context.user_data.get("adding_price"):
        price = update.message.text.strip()

        context.user_data["product_price"] = price
        context.user_data["adding_price"] = False
        context.user_data["adding_photo"] = True

        await update.message.reply_text(
            f"💰 قیمت {price} ثبت شد.\n\n"
            f"🖼️ حالا عکس محصول را ارسال کن."
        )

        return


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("adding_photo"):
        photo = update.message.photo[-1]
        photo_id = photo.file_id

        product_name = context.user_data.get("product_name")
        product_price = context.user_data.get("product_price")

        products = load_products()

        new_product = {
            "id": str(len(products) + 1),
            "name": product_name,
            "price": product_price,
            "photo": photo_id,
        }

        products.append(new_product)
        save_products(products)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ محصول با موفقیت ذخیره شد!\n\n"
            f"👗 {product_name}\n"
            f"💰 قیمت: {product_price}\n"
            "🖼️ عکس: ثبت شد\n\n"
            "حالا محصول در بخش «لباس‌های مجلسی» نمایش داده می‌شود."
        )


def main():
    if not TOKEN or TOKEN == "توکن_جدید_خودت":
        raise RuntimeError("توکن ربات وارد نشده است.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_photo
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_message
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
