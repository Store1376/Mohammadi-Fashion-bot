
import json
import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8850373531:AAGJRJL7ufyIVFn6xC4K3m8cCtRvdV7MX4E"
ADMIN_ID = 8276323231

PRODUCTS_FILE = "products.json"


def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []

    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as file:
        json.dump(products, file, ensure_ascii=False, indent=2)


def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👗 لباس‌های مجلسی", callback_data="majlesi")],
        [InlineKeyboardButton("👖 سرپطلونی", callback_data="sarpatloni")],
        [InlineKeyboardButton("🧵 سفارش دوخت", callback_data="dokht")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
        [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "🌸 به Mohammadi Fashion خوش آمدید 🌸\n\n"
        "عرضه کننده لباس‌های زنانه",
        reply_markup=home_keyboard(),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # -------------------------
    # خانه
    # -------------------------
    if query.data == "home":
        context.user_data.clear()

        await query.message.reply_text(
            "🌸 Mohammadi Fashion 🌸\n\n"
            "لطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=home_keyboard(),
        )
        return

    # -------------------------
    # لباس‌های مجلسی
    # -------------------------
    if query.data == "majlesi":
        products = load_products()

        keyboard = []

        for product in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"✨ {product['name']} — {product['price']}",
                    callback_data=f"product_{product['id']}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔙 برگشت", callback_data="home")
        ])

        if not products:
            text = "👗 لباس‌های مجلسی\n\nهنوز محصولی اضافه نشده است."
        else:
            text = "👗 لباس‌های مجلسی\n\nمحصولات موجود:"

        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # -------------------------
    # نمایش محصول
    # -------------------------
    if query.data.startswith("product_"):
        product_id = query.data.replace("product_", "")

        products = load_products()
        product = None

        for item in products:
            if item["id"] == product_id:
                product = item
                break

        if product is None:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🛒 سفارش این لباس",
                callback_data=f"order_{product_id}"
            )],
            [InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="majlesi"
            )],
        ])

        text = (
            f"✨ {product['name']} ✨\n\n"
            f"💰 قیمت: {product['price']}"
        )

        if product.get("photo"):
            await query.message.reply_photo(
                photo=product["photo"],
                caption=text,
                reply_markup=keyboard,
            )
        else:
            await query.message.reply_text(
                text,
                reply_markup=keyboard,
            )

        return

    # -------------------------
    # سفارش محصول
    # -------------------------
    if query.data.startswith("order_"):
        product_id = query.data.replace("order_", "")

        products = load_products()
        product = None

        for item in products:
            if item["id"] == product_id:
                product = item
                break

        if product is None:
            await query.message.reply_text(
                "❌ این محصول دیگر موجود نیست."
            )
            return

        # ذخیره اطلاعات سفارش
        context.user_data["ordering"] = True
        context.user_data["order_step"] = "name"
        context.user_data["order_product_id"] = product_id
        context.user_data["order_product_name"] = product["name"]
        context.user_data["order_product_price"] = product["price"]

        await query.message.reply_text(
            "🛒 ثبت سفارش\n\n"
            f"👗 محصول: {product['name']}\n"
            f"💰 قیمت: {product['price']}\n\n"
            "👤 لطفاً نام خود را ارسال کنید:"
        )
        return

    # -------------------------
    # سفارش دوخت
    # -------------------------
    if query.data == "dokht":
        await query.message.reply_text(
            "🧵 سفارش دوخت\n\n"
            "لطفاً مشخصات لباس مورد نظر خود را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ]),
        )
        return

    # -------------------------
    # سرپطلونی
    # -------------------------
    if query.data == "sarpatloni":
        await query.message.reply_text(
            "👖 سرپطلونی\n\n"
            "محصولات این بخش به‌زودی اضافه می‌شوند.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )]
            ]),
        )
        return

    # -------------------------
    # تماس با ما
    # -------------------------
    if query.data == "contact":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "💬 پیام در تلگرام",
                url="https://t.me/Rohullah1375"
            )],
            [InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="home"
            )],
        ])

        await query.message.reply_text(
            "📞 تماس با ما\n\n"
            "📱 شماره تماس اول: 0775816499\n"
            "📱 شماره تماس دوم: 0744763112\n"
            "💬 تلگرام: @Rohullah1375\n\n"
            "🌸 Mohammadi Fashion 🌸",
            reply_markup=keyboard,
        )
        return

    # -------------------------
    # مدیریت فروشگاه
    # -------------------------
    if query.data == "admin":
        if query.from_user.id != ADMIN_ID:
            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )
            return

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="add_product"
            )],
            [InlineKeyboardButton(
                "🖼️ افزودن عکس",
                callback_data="add_photo"
            )],
            [InlineKeyboardButton(
                "💰 تغییر قیمت",
                callback_data="change_price"
            )],
            [InlineKeyboardButton(
                "🗑️ حذف محصول",
                callback_data="delete_product"
            )],
            [InlineKeyboardButton(
                "✏️ تغییر نام محصول",
                callback_data="change_name"
            )],
            [InlineKeyboardButton(
                "🖼️ تغییر عکس محصول",
                callback_data="change_photo"
            )],
            [InlineKeyboardButton(
                "📋 لیست محصولات",
                callback_data="list_products"
            )],
            [InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="home"
            )],
        ])

        await query.message.reply_text(
            "⚙️ مدیریت فروشگاه\n\n"
            "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=keyboard,
        )
        return

    # -------------------------
    # لیست محصولات
    # -------------------------
    if query.data == "list_products":
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        products = load_products()
        if not products:
            text = "📋 هنوز محصولی ثبت نشده است."
        else:
            lines = ["📋 لیست محصولات\n"]
            for i, p in enumerate(products, 1):
                lines.append(
                    f"{i}. 👗 {p['name']}\n"
                    f"   💰 {p['price']}\n"
                    f"   🆔 {p['id']}"
                )
            text = "\n\n".join(lines)

        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="admin")]
            ])
        )
        return

    # -------------------------
    # تغییر نام محصول
    # -------------------------
    if query.data == "change_name":
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        products = load_products()
        keyboard = [
            [InlineKeyboardButton(
                f"✏️ {p['name']}",
                callback_data=f"name_{p['id']}"
            )]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin")])

        await query.message.reply_text(
            "✏️ محصول مورد نظر را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if query.data.startswith("name_"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        product_id = query.data.replace("name_", "")
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)
        if product is None:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return

        context.user_data.clear()
        context.user_data["changing_name"] = True
        context.user_data["name_product_id"] = product_id

        await query.message.reply_text(
            f"✏️ نام فعلی: {product['name']}\n\n"
            "نام جدید را ارسال کن:"
        )
        return

    # -------------------------
    # تغییر عکس محصول
    # -------------------------
    if query.data == "change_photo":
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        products = load_products()
        keyboard = [
            [InlineKeyboardButton(
                f"🖼️ {p['name']}",
                callback_data=f"photo_{p['id']}"
            )]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin")])

        await query.message.reply_text(
            "🖼️ محصول مورد نظر را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if query.data.startswith("photo_"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        product_id = query.data.replace("photo_", "")
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)
        if product is None:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return

        context.user_data.clear()
        context.user_data["changing_photo"] = True
        context.user_data["photo_product_id"] = product_id

        await query.message.reply_text(
            f"🖼️ محصول: {product['name']}\n\n"
            "عکس جدید محصول را ارسال کن:"
        )
        return

    # -------------------------
    # افزودن محصول
    # -------------------------
    if query.data == "add_product":
        if query.from_user.id != ADMIN_ID:
            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )
            return

        context.user_data.clear()
        context.user_data["adding_product"] = True

        await query.message.reply_text(
            "➕ افزودن محصول\n\n"
            "لطفاً نام محصول را ارسال کن."
        )
        return

    # -------------------------
    # افزودن عکس
    # -------------------------
    if query.data == "add_photo":
        await query.message.reply_text(
            "🖼️ افزودن عکس\n\n"
            "ابتدا محصول را با گزینه «افزودن محصول» ایجاد کن."
        )
        return

    # -------------------------
    # تغییر قیمت
    # -------------------------
    if query.data == "change_price":
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        products = load_products()
        keyboard = [
            [InlineKeyboardButton(
                f"💰 {p['name']} — {p['price']}",
                callback_data=f"price_{p['id']}"
            )]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin")])

        await query.message.reply_text(
            "💰 تغییر قیمت

"
            "محصول مورد نظر را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # -------------------------
    # انتخاب محصول برای تغییر قیمت
    # -------------------------
    if query.data.startswith("price_"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        product_id = query.data.replace("price_", "")
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)

        if product is None:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return

        context.user_data.clear()
        context.user_data["changing_price"] = True
        context.user_data["price_product_id"] = product_id

        await query.message.reply_text(
            f"💰 تغییر قیمت

"
            f"👗 محصول: {product['name']}\n"
            f"💵 قیمت فعلی: {product['price']}\n\n"
            "قیمت جدید را ارسال کن:"
        )
        return

    # -------------------------
    # حذف محصول
    # -------------------------
    if query.data == "delete_product":
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        products = load_products()
        keyboard = [
            [InlineKeyboardButton(
                f"🗑️ {p['name']} — {p['price']}",
                callback_data=f"delete_{p['id']}"
            )]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="admin")])

        if not products:
            await query.message.reply_text(
                "🗑️ محصولی برای حذف وجود ندارد.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.message.reply_text(
                "🗑️ حذف محصول

"
                "محصولی را که می‌خواهی حذف کنی انتخاب کن:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    # -------------------------
    # تأیید حذف محصول
    # -------------------------
    if query.data.startswith("delete_"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        product_id = query.data.replace("delete_", "")
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)

        if product is None:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_delete_{product_id}"),
                InlineKeyboardButton("❌ لغو", callback_data="delete_product"),
            ]
        ])

        await query.message.reply_text(
            f"⚠️ مطمئنی می‌خواهی این محصول حذف شود؟\n\n"
            f"👗 {product['name']}\n"
            f"💰 {product['price']}",
            reply_markup=keyboard
        )
        return

    # -------------------------
    # تأیید نهایی حذف
    # -------------------------
    if query.data.startswith("confirm_delete_"):
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        product_id = query.data.replace("confirm_delete_", "")
        products = load_products()
        new_products = [p for p in products if p["id"] != product_id]

        if len(new_products) == len(products):
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return

        save_products(new_products)
        await query.message.reply_text(
            "✅ محصول با موفقیت حذف شد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
                [InlineKeyboardButton("🏠 خانه", callback_data="home")],
            ])
        )
        return


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # -------------------------
    # ثبت سفارش مشتری
    # -------------------------
    if context.user_data.get("ordering"):

        step = context.user_data.get("order_step")

        # دریافت نام
        if step == "name":

            context.user_data["customer_name"] = text
            context.user_data["order_step"] = "phone"

            await update.message.reply_text(
                f"✅ نام شما ثبت شد: {text}\n\n"
                "📱 حالا لطفاً شماره تماس خود را ارسال کنید:"
            )

            return

        # دریافت شماره
        if step == "phone":

            customer_phone = text

            product_name = context.user_data.get(
                "order_product_name"
            )

            product_price = context.user_data.get(
                "order_product_price"
            )

            customer_name = context.user_data.get(
                "customer_name"
            )

            username = update.effective_user.username

            if username:
                telegram_info = f"@{username}"
            else:
                telegram_info = "ندارد"

            # ارسال سفارش مستقیم برای مدیر
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "🔔 سفارش جدید دریافت شد! 🔔\n\n"
                    f"👗 محصول: {product_name}\n"
                    f"💰 قیمت: {product_price}\n\n"
                    f"👤 نام مشتری: {customer_name}\n"
                    f"📱 شماره تماس: {customer_phone}\n"
                    f"💬 تلگرام مشتری: {telegram_info}\n\n"
                    "🌸 Mohammadi Fashion 🌸"
                )
            )

            await update.message.reply_text(
                "✅ سفارش شما با موفقیت ثبت شد! 🎉\n\n"
                "📦 سفارش برای فروشگاه ارسال شد.\n"
                "📞 به‌زودی با شما تماس گرفته می‌شود.\n\n"
                "🌸 تشکر از اعتماد شما به Mohammadi Fashion 🌸"
            )

            context.user_data.clear()

            return

    # -------------------------
    # مدیریت فروشگاه
    # -------------------------
    if user_id != ADMIN_ID:
        return

    # تغییر نام محصول
    if context.user_data.get("changing_name"):
        product_id = context.user_data.get("name_product_id")
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)

        if product is None:
            context.user_data.clear()
            await update.message.reply_text("❌ محصول پیدا نشد.")
            return

        product["name"] = text
        save_products(products)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ نام محصول با موفقیت تغییر کرد!\n\n"
            f"👗 نام جدید: {product['name']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
                [InlineKeyboardButton("🏠 خانه", callback_data="home")],
            ])
        )
        return

    # تغییر قیمت محصول
    if context.user_data.get("changing_price"):
        product_id = context.user_data.get("price_product_id")
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)

        if product is None:
            context.user_data.clear()
            await update.message.reply_text("❌ محصول پیدا نشد.")
            return

        product["price"] = text
        save_products(products)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ قیمت با موفقیت تغییر کرد!\n\n"
            f"👗 محصول: {product['name']}\n"
            f"💰 قیمت جدید: {product['price']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
                [InlineKeyboardButton("🏠 خانه", callback_data="home")],
            ])
        )
        return

    # نام محصول
    if context.user_data.get("adding_product"):

        context.user_data["product_name"] = text
        context.user_data["adding_product"] = False
        context.user_data["adding_price"] = True

        await update.message.reply_text(
            f"✅ نام محصول ثبت شد:\n\n"
            f"👗 {text}\n\n"
            "💰 حالا قیمت محصول را ارسال کن."
        )

        return

    # قیمت محصول
    if context.user_data.get("adding_price"):

        context.user_data["product_price"] = text
        context.user_data["adding_price"] = False
        context.user_data["adding_photo"] = True

        await update.message.reply_text(
            f"💰 قیمت {text} ثبت شد.\n\n"
            "🖼️ حالا عکس محصول را ارسال کن."
        )

        return


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("changing_photo"):
        product_id = context.user_data.get("photo_product_id")
        products = load_products()
        product = next((p for p in products if p["id"] == product_id), None)

        if product is None:
            context.user_data.clear()
            await update.message.reply_text("❌ محصول پیدا نشد.")
            return

        photo_id = update.message.photo[-1].file_id
        product["photo"] = photo_id
        save_products(products)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ عکس محصول با موفقیت تغییر کرد! 🎉",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
                [InlineKeyboardButton("🏠 خانه", callback_data="home")],
            ])
        )
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
            "✅ محصول با موفقیت ذخیره شد! 🎉\n\n"
            f"👗 {product_name}\n"
            f"💰 قیمت: {product_price}\n"
            "🖼️ عکس: ثبت شد\n\n"
            "محصول اکنون در بخش لباس‌های مجلسی نمایش داده می‌شود."
        )


def main():

    if not TOKEN or TOKEN == "توکن_جدید_خودت":
        raise RuntimeError(
            "توکن ربات وارد نشده است."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

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
