import json
import os
import shutil
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# تنظیمات
# =========================================================
TOKEN = "8850373531:AAGJRJL7ufyIVFn6xC4K3m8cCtRvdV7MX4E"
ADMIN_ID = 8276323231

SHOP_NAME = "Mohammadi Fashion"
CONTACT1 = "0775816499"
CONTACT2 = "0744763112"
TELEGRAM_USERNAME = "Rohullah1375"
WHATSAPP_NUMBER = "93744763112"

PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"

# =========================================================
# فایل‌ها
# =========================================================
def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_products():
    return load_json(PRODUCTS_FILE, [])


def save_products(products):
    save_json(PRODUCTS_FILE, products)


def load_orders():
    return load_json(ORDERS_FILE, [])


def save_orders(orders):
    save_json(ORDERS_FILE, orders)


def next_id(items):
    nums = []
    for item in items:
        try:
            nums.append(int(item.get("id", 0)))
        except Exception:
            pass
    return str(max(nums, default=0) + 1)


def product_by_id(product_id):
    return next((p for p in load_products() if p.get("id") == product_id), None)


def order_by_id(order_id):
    return next((o for o in load_orders() if o.get("id") == order_id), None)


# =========================================================
# دکمه‌ها
# =========================================================
def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👗 لباس‌های مجلسی", callback_data="category_majlesi")],
        [InlineKeyboardButton("👖 سرپطلونی", callback_data="category_sarpatloni")],
        [InlineKeyboardButton("🧵 سفارش دوخت", callback_data="custom_order")],
        [InlineKeyboardButton("🔎 جستجوی محصول", callback_data="search")],
        [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart")],
        [InlineKeyboardButton("📦 سفارش‌های من", callback_data="my_orders")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
        [InlineKeyboardButton("⚙️ مدیریت فروشگاه", callback_data="admin")],
    ])


def back_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 خانه", callback_data="home")]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product")],
        [InlineKeyboardButton("💰 تغییر قیمت", callback_data="change_price")],
        [InlineKeyboardButton("✏️ تغییر نام", callback_data="change_name")],
        [InlineKeyboardButton("🖼️ مدیریت عکس", callback_data="change_photo")],
        [InlineKeyboardButton("🗑️ حذف محصول", callback_data="delete_product")],
        [InlineKeyboardButton("📋 لیست محصولات", callback_data="list_products")],
        [InlineKeyboardButton("📦 سفارش‌های مشتریان", callback_data="admin_orders")],
        [InlineKeyboardButton("💾 پشتیبان‌گیری", callback_data="backup")],
        [InlineKeyboardButton("🏠 خانه", callback_data="home")],
    ])


def category_keyboard(category):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 برگشت", callback_data="home")]
    ])


# =========================================================
# شروع
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"🌸 به {SHOP_NAME} خوش آمدید 🌸\n\n"
        "عرضه‌کننده لباس‌های زنانه\n\n"
        "لطفاً گزینه مورد نظر را انتخاب کنید:",
        reply_markup=home_keyboard(),
    )


# =========================================================
# نمایش محصولات و محصول
# =========================================================
async def show_category(query, category):
    products = [
        p for p in load_products()
        if p.get("category", "majlesi") == category
    ]

    if not products:
        await query.message.reply_text(
            "📦 در این بخش هنوز محصولی اضافه نشده است.",
            reply_markup=back_home(),
        )
        return

    keyboard = []
    for p in products:
        keyboard.append([
            InlineKeyboardButton(
                f"✨ {p['name']} — {p['price']}",
                callback_data=f"product_{p['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="home")])

    title = "👗 لباس‌های مجلسی" if category == "majlesi" else "👖 سرپطلونی"
    await query.message.reply_text(
        f"{title}\n\nمحصولات موجود:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_product(query, context, product_id):
    product = product_by_id(product_id)
    if not product:
        await query.message.reply_text(
            "❌ محصول پیدا نشد.",
            reply_markup=back_home()
        )
        return

    # پشتیبانی از محصولات قدیمی که فقط کلید photo دارند
    photos = product.get("photos") or []
    if isinstance(photos, str):
        photos = [photos]

    old_photo = product.get("photo")
    if old_photo and old_photo not in photos:
        photos.insert(0, old_photo)

    # حذف مقادیر خالی
    photos = [p for p in photos if p]

    text = (
        f"✨ {product.get('name', 'بدون نام')} ✨\n\n"
        f"💰 قیمت: {product.get('price', 'توافقی')}\n"
        f"🏷️ دسته: "
        f"{'لباس مجلسی' if product.get('category', 'majlesi') == 'majlesi' else 'سرپطلونی'}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🛒 افزودن به سبد خرید",
            callback_data=f"cart_add_{product_id}"
        )],
        [InlineKeyboardButton(
            "🛍️ سفارش مستقیم",
            callback_data=f"order_{product_id}"
        )],
        [InlineKeyboardButton(
            "🔙 برگشت",
            callback_data=f"category_{product.get('category', 'majlesi')}"
        )],
    ])

    if not photos:
        await query.message.reply_text(
            text + "\n\n⚠️ برای این محصول هنوز عکسی ثبت نشده است.",
            reply_markup=keyboard
        )
        return

    # یک عکس: عکس + دکمه‌ها در همان پیام
    if len(photos) == 1:
        try:
            await query.message.reply_photo(
                photo=photos[0],
                caption=text,
                reply_markup=keyboard,
            )
            return
        except Exception as e:
            await query.message.reply_text(
                text + "\n\n⚠️ عکس محصول قابل نمایش نیست.\n"
                "مدیر باید عکس محصول را دوباره از قسمت «مدیریت عکس» ارسال کند.",
                reply_markup=keyboard
            )
            return

    # چند عکس: همه عکس‌ها را ارسال می‌کنیم و بعد دکمه‌ها را می‌فرستیم
    try:
        media = []
        for i, photo in enumerate(photos[:10]):
            item = InputMediaPhoto(media=photo)
            if i == 0:
                item.caption = text
            media.append(item)

        await query.message.reply_media_group(media=media)
        await query.message.reply_text(
            "🛍️ گزینه مورد نظر را انتخاب کنید:",
            reply_markup=keyboard
        )
    except Exception:
        # اگر یکی از file_idها خراب باشد، حداقل اولین عکس را امتحان می‌کنیم.
        try:
            await query.message.reply_photo(
                photo=photos[0],
                caption=text,
                reply_markup=keyboard,
            )
        except Exception:
            await query.message.reply_text(
                text + "\n\n⚠️ عکس محصول قابل نمایش نیست.\n"
                "لطفاً مدیر عکس محصول را دوباره ارسال کند.",
                reply_markup=keyboard
            )


# =========================================================
# سبد خرید
# =========================================================
def cart_items(context):
    return context.user_data.setdefault("cart", [])


def cart_text(context):
    cart = cart_items(context)
    if not cart:
        return "🛒 سبد خرید شما خالی است."

    lines = ["🛒 سبد خرید شما:\n"]
    total = 0
    for i, item in enumerate(cart, 1):
        lines.append(
            f"{i}. 👗 {item['name']}\n"
            f"   💰 {item['price']}\n"
            f"   🔢 تعداد: {item.get('quantity', 1)}"
        )
        try:
            total += float(str(item["price"]).replace(",", "").replace(" ", ""))
        except Exception:
            pass
    lines.append(f"\n💵 جمع تقریبی: {total:g}")
    return "\n\n".join(lines)


async def show_cart(query, context):
    cart = cart_items(context)
    keyboard = []
    if cart:
        keyboard.append([InlineKeyboardButton("✅ ثبت سفارش سبد", callback_data="checkout")])
        keyboard.append([InlineKeyboardButton("🗑️ خالی کردن سبد", callback_data="clear_cart")])
    keyboard.append([InlineKeyboardButton("🏠 خانه", callback_data="home")])

    await query.message.reply_text(
        cart_text(context),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================================================
# سفارش مستقیم و سبد
# =========================================================
def begin_customer_order(context, source="direct", product_id=None):
    context.user_data["ordering"] = True
    context.user_data["order_step"] = "name"
    context.user_data["order_source"] = source
    if product_id:
        p = product_by_id(product_id)
        if p:
            context.user_data["direct_product"] = {
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
            }


async def send_order_to_admin(update, context, order):
    cart_lines = []
    for item in order["items"]:
        cart_lines.append(
            f"• {item['name']} — {item['price']} × {item.get('quantity', 1)}"
        )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "🔔 سفارش جدید دریافت شد! 🔔\n\n"
            f"🆔 سفارش: #{order['id']}\n"
            f"👤 نام: {order['customer_name']}\n"
            f"📱 شماره: {order['phone']}\n"
            f"💬 تلگرام: {order['telegram']}\n\n"
            "🛍️ محصولات:\n"
            + "\n".join(cart_lines)
            + (
                f"\n\n🧵 مدل و توضیحات سفارش دوخت:\n{order.get('custom_description', '')}"
                if order.get("custom_description")
                else ""
            )
            + f"\n\n📌 وضعیت: {order['status']}"
        ),
    )


# =========================================================
# تماس
# =========================================================
async def show_contact(query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "💬 تلگرام",
            url=f"https://t.me/{TELEGRAM_USERNAME}"
        )],
        [InlineKeyboardButton(
            "📱 واتساپ",
            url=f"https://wa.me/{WHATSAPP_NUMBER}"
        )],
        [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
    ])
    await query.message.reply_text(
        f"📞 تماس با {SHOP_NAME}\n\n"
        f"📱 شماره اول: {CONTACT1}\n"
        f"📱 شماره دوم: {CONTACT2}\n"
        f"💬 تلگرام: @{TELEGRAM_USERNAME}\n"
        f"📱 واتساپ: +{WHATSAPP_NUMBER}",
        reply_markup=keyboard,
    )


# =========================================================
# سفارش دوخت
# =========================================================
async def start_custom_order(query, context):
    context.user_data.clear()
    context.user_data["custom_order"] = True
    context.user_data["custom_step"] = "description"
    await query.message.reply_text(
        "🧵 سفارش دوخت\n\n"
        "لطفاً مشخصات لباس، مدل، رنگ و هر توضیحی که لازم است را ارسال کن:"
    )


# =========================================================
# مدیریت
# =========================================================
def admin_only(query):
    return query.from_user.id == ADMIN_ID


async def admin_orders(query):
    orders = load_orders()
    if not orders:
        await query.message.reply_text(
            "📦 هنوز سفارشی ثبت نشده است.",
            reply_markup=admin_keyboard(),
        )
        return

    keyboard = []
    for o in orders[-30:][::-1]:
        keyboard.append([
            InlineKeyboardButton(
                f"#{o['id']} — {o['customer_name']} — {o['status']}",
                callback_data=f"view_order_{o['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 مدیریت", callback_data="admin")])

    await query.message.reply_text(
        "📦 سفارش‌های مشتریان:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def view_order(query, order_id):
    order = order_by_id(order_id)
    if not order:
        await query.message.reply_text("❌ سفارش پیدا نشد.")
        return

    items = "\n".join(
        f"• {i['name']} — {i['price']} × {i.get('quantity', 1)}"
        for i in order["items"]
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 جدید", callback_data=f"status_{order_id}_جدید")],
        [InlineKeyboardButton("✅ تأیید شد", callback_data=f"status_{order_id}_تأیید شد")],
        [InlineKeyboardButton("👗 آماده", callback_data=f"status_{order_id}_آماده")],
        [InlineKeyboardButton("📦 تحویل شد", callback_data=f"status_{order_id}_تحویل شد")],
        [InlineKeyboardButton("❌ لغو شد", callback_data=f"status_{order_id}_لغو شد")],
        [InlineKeyboardButton("🔙 سفارش‌ها", callback_data="admin_orders")],
    ])

    await query.message.reply_text(
        f"📦 سفارش #{order['id']}\n\n"
        f"👤 مشتری: {order['customer_name']}\n"
        f"📱 شماره: {order['phone']}\n"
        f"💬 تلگرام: {order['telegram']}\n"
        f"📅 تاریخ: {order['created_at']}\n"
        f"📌 وضعیت: {order['status']}\n\n"
        f"🛍️ محصولات:\n{items}"
        + (f"\n\n📝 توضیحات سفارش دوخت:\n{order.get('custom_description')}" if order.get("custom_description") else ""),
        reply_markup=keyboard,
    )


async def update_order_status(query, order_id, status):
    orders = load_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        await query.message.reply_text("❌ سفارش پیدا نشد.")
        return

    order["status"] = status
    save_orders(orders)

    await query.message.reply_text(
        f"✅ وضعیت سفارش #{order_id} به «{status}» تغییر کرد.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 مشاهده سفارش", callback_data=f"view_order_{order_id}")],
            [InlineKeyboardButton("🔙 سفارش‌ها", callback_data="admin_orders")],
        ]),
    )

    try:
        await context_bot_send_status(query, order, status)
    except Exception:
        pass


async def context_bot_send_status(query, order, status):
    # Telegram user id is saved with each order, so customer can be notified.
    await query.get_bot().send_message(
        chat_id=order["user_id"],
        text=f"📦 وضعیت سفارش #{order['id']} تغییر کرد:\n\n📌 {status}",
    )


async def backup_files(query):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{stamp}.json"
    data = {
        "created_at": datetime.now().isoformat(),
        "products": load_products(),
        "orders": load_orders(),
    }
    with open(backup_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    await query.message.reply_document(
        document=backup_name,
        caption="💾 پشتیبان محصولات و سفارش‌ها",
    )

    try:
        os.remove(backup_name)
    except Exception:
        pass


# =========================================================
# دکمه‌ها
# =========================================================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        context.user_data.clear()
        await query.message.reply_text(
            f"🌸 {SHOP_NAME} 🌸\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=home_keyboard(),
        )
        return

    if data.startswith("category_"):
        await show_category(query, data.replace("category_", ""))
        return

    if data.startswith("product_"):
        await show_product(query, context, data.replace("product_", ""))
        return

    if data == "cart":
        await show_cart(query, context)
        return

    if data.startswith("cart_add_"):
        product = product_by_id(data.replace("cart_add_", ""))
        if not product:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        cart = cart_items(context)
        existing = next((x for x in cart if x["id"] == product["id"]), None)
        if existing:
            existing["quantity"] = existing.get("quantity", 1) + 1
        else:
            cart.append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "quantity": 1,
            })
        await query.message.reply_text(
            "✅ محصول به سبد خرید اضافه شد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 سبد خرید", callback_data="cart")],
                [InlineKeyboardButton("🏠 خانه", callback_data="home")],
            ]),
        )
        return

    if data == "clear_cart":
        context.user_data["cart"] = []
        await query.message.reply_text("🗑️ سبد خرید خالی شد.", reply_markup=back_home())
        return

    if data == "checkout":
        if not cart_items(context):
            await query.message.reply_text("🛒 سبد خرید خالی است.", reply_markup=back_home())
            return
        begin_customer_order(context, "cart")
        await query.message.reply_text("👤 لطفاً نام خود را ارسال کنید:")
        return

    if data.startswith("order_"):
        begin_customer_order(context, "direct", data.replace("order_", ""))
        p = product_by_id(data.replace("order_", ""))
        await query.message.reply_text(
            f"🛒 ثبت سفارش\n\n"
            f"👗 محصول: {p['name'] if p else '---'}\n"
            f"💰 قیمت: {p['price'] if p else '---'}\n\n"
            "👤 لطفاً نام خود را ارسال کنید:"
        )
        return

    if data == "my_orders":
        orders = [
            o for o in load_orders()
            if o.get("user_id") == query.from_user.id
        ]
        if not orders:
            await query.message.reply_text(
                "📦 هنوز سفارشی برای شما ثبت نشده است.",
                reply_markup=back_home(),
            )
            return
        lines = ["📦 سفارش‌های من:\n"]
        for o in orders[-20:][::-1]:
            lines.append(
                f"🆔 #{o['id']} — {o['status']} — {o['created_at']}"
            )
        await query.message.reply_text("\n".join(lines), reply_markup=back_home())
        return

    if data == "contact":
        await show_contact(query)
        return

    if data == "custom_order":
        await start_custom_order(query, context)
        return

    if data == "search":
        context.user_data.clear()
        context.user_data["searching"] = True
        await query.message.reply_text("🔎 نام یا بخشی از نام محصول را ارسال کن:")
        return

    # ---------------- ADMIN ----------------
    if data == "admin":
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        await query.message.reply_text(
            "⚙️ مدیریت فروشگاه\n\nیک گزینه را انتخاب کن:",
            reply_markup=admin_keyboard(),
        )
        return

    if data == "admin_orders":
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        await admin_orders(query)
        return

    if data.startswith("view_order_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        await view_order(query, data.replace("view_order_", ""))
        return

    if data.startswith("status_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        parts = data.split("_", 2)
        await update_order_status(query, parts[1], parts[2])
        return

    if data == "backup":
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        await backup_files(query)
        return

    if data == "add_product":
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        context.user_data.clear()
        context.user_data["adding_product"] = True
        context.user_data["add_step"] = "name"
        await query.message.reply_text(
            "➕ افزودن محصول\n\nنام محصول را ارسال کن:"
        )
        return

    if data == "change_price":
        if not admin_only(query):
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
        keyboard.append([InlineKeyboardButton("🔙 مدیریت", callback_data="admin")])
        await query.message.reply_text(
            "💰 محصول مورد نظر را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("price_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("price_", "")
        p = product_by_id(pid)
        if not p:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        context.user_data.clear()
        context.user_data["changing_price"] = True
        context.user_data["price_product_id"] = pid
        await query.message.reply_text(
            f"💰 قیمت فعلی {p['name']}: {p['price']}\n\nقیمت جدید را ارسال کن:"
        )
        return

    if data == "change_name":
        if not admin_only(query):
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
        keyboard.append([InlineKeyboardButton("🔙 مدیریت", callback_data="admin")])
        await query.message.reply_text(
            "✏️ محصول را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("name_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("name_", "")
        if not product_by_id(pid):
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        context.user_data.clear()
        context.user_data["changing_name"] = True
        context.user_data["name_product_id"] = pid
        await query.message.reply_text("✏️ نام جدید را ارسال کن:")
        return

    if data == "change_photo":
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        products = load_products()
        keyboard = [
            [InlineKeyboardButton(
                f"🖼️ {p['name']}",
                callback_data=f"photos_{p['id']}"
            )]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 مدیریت", callback_data="admin")])
        await query.message.reply_text(
            "🖼️ محصول را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("photos_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("photos_", "")
        p = product_by_id(pid)
        if not p:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        photos = p.get("photos", [])
        keyboard = [
            [InlineKeyboardButton("➕ افزودن عکس", callback_data=f"photo_add_{pid}")],
            [InlineKeyboardButton("🔄 جایگزین کردن همه عکس‌ها", callback_data=f"photo_replace_{pid}")],
            [InlineKeyboardButton("🗑️ حذف عکس‌ها", callback_data=f"photo_clear_{pid}")],
            [InlineKeyboardButton("🔙 مدیریت", callback_data="admin")],
        ]
        await query.message.reply_text(
            f"🖼️ {p['name']}\n\n"
            f"تعداد عکس‌ها: {len(photos)}\n"
            "چه کاری انجام شود؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("photo_add_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("photo_add_", "")
        context.user_data.clear()
        context.user_data["photo_action"] = "add"
        context.user_data["photo_product_id"] = pid
        await query.message.reply_text(
            "🖼️ عکس جدید را ارسال کن. می‌توانی چند عکس را یکی‌یکی بفرستی؛ "
            "هر بار که عکس فرستادی ذخیره می‌شود."
        )
        return

    if data.startswith("photo_replace_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("photo_replace_", "")
        context.user_data.clear()
        context.user_data["photo_action"] = "replace"
        context.user_data["photo_product_id"] = pid
        await query.message.reply_text("🖼️ عکس جدید را ارسال کن:")
        return

    if data.startswith("photo_clear_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("photo_clear_", "")
        products = load_products()
        for p in products:
            if p["id"] == pid:
                p["photos"] = []
                p.pop("photo", None)
                break
        save_products(products)
        await query.message.reply_text(
            "✅ عکس‌های محصول حذف شد.",
            reply_markup=admin_keyboard(),
        )
        return

    if data == "delete_product":
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        products = load_products()
        keyboard = [
            [InlineKeyboardButton(
                f"🗑️ {p['name']}",
                callback_data=f"delete_{p['id']}"
            )]
            for p in products
        ]
        keyboard.append([InlineKeyboardButton("🔙 مدیریت", callback_data="admin")])
        await query.message.reply_text(
            "🗑️ محصولی را برای حذف انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("delete_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("delete_", "")
        p = product_by_id(pid)
        if not p:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        await query.message.reply_text(
            f"⚠️ آیا «{p['name']}» حذف شود؟",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ بله", callback_data=f"confirm_delete_{pid}"),
                    InlineKeyboardButton("❌ خیر", callback_data="delete_product"),
                ]
            ]),
        )
        return

    if data.startswith("confirm_delete_"):
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        pid = data.replace("confirm_delete_", "")
        products = [p for p in load_products() if p["id"] != pid]
        save_products(products)
        await query.message.reply_text(
            "✅ محصول حذف شد.",
            reply_markup=admin_keyboard(),
        )
        return

    if data == "list_products":
        if not admin_only(query):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return
        products = load_products()
        if not products:
            await query.message.reply_text("📋 محصولی وجود ندارد.", reply_markup=admin_keyboard())
            return
        lines = ["📋 محصولات:\n"]
        for p in products:
            lines.append(
                f"🆔 {p['id']} | 👗 {p['name']} | 💰 {p['price']} | "
                f"🖼️ {len(p.get('photos', []))}"
            )
        await query.message.reply_text("\n".join(lines), reply_markup=admin_keyboard())
        return


# =========================================================
# پیام‌های متنی
# =========================================================
async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # جستجو
    if context.user_data.get("searching"):
        context.user_data.clear()
        products = load_products()
        found = [
            p for p in products
            if text.lower() in p.get("name", "").lower()
        ]
        if not found:
            await update.message.reply_text(
                "❌ محصولی با این نام پیدا نشد.",
                reply_markup=home_keyboard(),
            )
            return

        keyboard = [
            [InlineKeyboardButton(
                f"✨ {p['name']} — {p['price']}",
                callback_data=f"product_{p['id']}"
            )]
            for p in found
        ]
        keyboard.append([InlineKeyboardButton("🏠 خانه", callback_data="home")])
        await update.message.reply_text(
            f"🔎 نتایج جستجو برای: {text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # سفارش دوخت
    if context.user_data.get("custom_order"):
        step = context.user_data.get("custom_step")
        if step == "description":
            context.user_data["custom_description"] = text
            context.user_data["custom_step"] = "phone"
            await update.message.reply_text("📱 شماره تماس خود را ارسال کن:")
            return

        if step == "phone":
            order = {
                "id": next_id(load_orders()),
                "user_id": user_id,
                "customer_name": update.effective_user.full_name,
                "phone": text,
                "telegram": f"@{update.effective_user.username}" if update.effective_user.username else "ندارد",
                "items": [{
                    "name": "🧵 سفارش دوخت",
                    "price": "توافقی",
                    "quantity": 1,
                }],
                "custom_description": context.user_data.get("custom_description", ""),
                "status": "جدید",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            orders = load_orders()
            orders.append(order)
            save_orders(orders)
            await send_order_to_admin(update, context, order)
            context.user_data.clear()
            description = order.get("custom_description", "")
            await update.message.reply_text(
                "✅ سفارش دوخت ثبت شد!\n\n"
                f"🧵 مدل/توضیحات ثبت‌شده:\n{description}\n\n"
                "📞 به‌زودی با شما تماس گرفته می‌شود.",
                reply_markup=home_keyboard(),
            )
            return

    # سفارش مشتری
    if context.user_data.get("ordering"):
        step = context.user_data.get("order_step")

        if step == "name":
            context.user_data["customer_name"] = text
            context.user_data["order_step"] = "phone"
            await update.message.reply_text("📱 حالا شماره تماس خود را ارسال کن:")
            return

        if step == "phone":
            cart = list(cart_items(context))
            if context.user_data.get("order_source") == "direct":
                p = context.user_data.get("direct_product")
                cart = [dict(p, quantity=1)] if p else []

            if not cart:
                context.user_data.clear()
                await update.message.reply_text("❌ سبد سفارش خالی است.", reply_markup=home_keyboard())
                return

            order = {
                "id": next_id(load_orders()),
                "user_id": user_id,
                "customer_name": context.user_data.get("customer_name", update.effective_user.full_name),
                "phone": text,
                "telegram": f"@{update.effective_user.username}" if update.effective_user.username else "ندارد",
                "items": cart,
                "status": "جدید",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

            orders = load_orders()
            orders.append(order)
            save_orders(orders)
            await send_order_to_admin(update, context, order)

            context.user_data.clear()
            await update.message.reply_text(
                f"✅ سفارش #{order['id']} با موفقیت ثبت شد! 🎉\n\n"
                "📦 سفارش برای فروشگاه ارسال شد.",
                reply_markup=home_keyboard(),
            )
            return

    # فقط مدیر
    if user_id != ADMIN_ID:
        return

    # افزودن محصول
    if context.user_data.get("adding_product"):
        step = context.user_data.get("add_step")

        if step == "name":
            context.user_data["product_name"] = text
            context.user_data["add_step"] = "price"
            await update.message.reply_text("💰 قیمت محصول را ارسال کن:")
            return

        if step == "price":
            context.user_data["product_price"] = text
            context.user_data["add_step"] = "category"
            await update.message.reply_text(
                "🏷️ دسته محصول را مشخص کن:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👗 لباس مجلسی", callback_data="newcat_majlesi")],
                    [InlineKeyboardButton("👖 سرپطلونی", callback_data="newcat_sarpatloni")],
                ]),
            )
            return

    # تغییر قیمت
    if context.user_data.get("changing_price"):
        pid = context.user_data.get("price_product_id")
        products = load_products()
        for p in products:
            if p["id"] == pid:
                p["price"] = text
                save_products(products)
                context.user_data.clear()
                await update.message.reply_text("✅ قیمت تغییر کرد.", reply_markup=admin_keyboard())
                return
        context.user_data.clear()
        await update.message.reply_text("❌ محصول پیدا نشد.", reply_markup=admin_keyboard())
        return

    # تغییر نام
    if context.user_data.get("changing_name"):
        pid = context.user_data.get("name_product_id")
        products = load_products()
        for p in products:
            if p["id"] == pid:
                p["name"] = text
                save_products(products)
                context.user_data.clear()
                await update.message.reply_text("✅ نام محصول تغییر کرد.", reply_markup=admin_keyboard())
                return
        context.user_data.clear()
        await update.message.reply_text("❌ محصول پیدا نشد.", reply_markup=admin_keyboard())
        return


# =========================================================
# عکس‌های مدیر
# =========================================================
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    photo_id = update.message.photo[-1].file_id

    # افزودن عکس به محصول موجود / جایگزینی
    if context.user_data.get("photo_action"):
        pid = context.user_data.get("photo_product_id")
        action = context.user_data.get("photo_action")
        products = load_products()

        for p in products:
            if p["id"] == pid:
                if action == "replace":
                    p["photos"] = [photo_id]
                else:
                    existing = p.get("photos") or []
                    if isinstance(existing, str):
                        existing = [existing]
                    if photo_id not in existing:
                        existing.append(photo_id)
                    p["photos"] = existing

                # برای سازگاری با نسخه‌های قبلی
                p["photo"] = p["photos"][0]
                save_products(products)
                if action == "replace":
                    context.user_data.clear()
                await update.message.reply_text(
                    "✅ عکس ذخیره شد.",
                    reply_markup=admin_keyboard(),
                )
                return

        await update.message.reply_text("❌ محصول پیدا نشد.")
        return

    # افزودن محصول جدید
    if context.user_data.get("adding_product") and context.user_data.get("add_step") == "photo":
        products = load_products()
        product = {
            "id": next_id(products),
            "name": context.user_data["product_name"],
            "price": context.user_data["product_price"],
            "category": context.user_data.get("category", "majlesi"),
            "photos": [photo_id],
            "photo": photo_id,
        }
        products.append(product)
        save_products(products)
        context.user_data.clear()

        await update.message.reply_text(
            f"✅ محصول با موفقیت ذخیره شد!\n\n"
            f"👗 {product['name']}\n"
            f"💰 {product['price']}",
            reply_markup=admin_keyboard(),
        )


# =========================================================
# انتخاب دسته محصول جدید
# =========================================================
async def new_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ دسترسی ندارید.", show_alert=True)
        return

    if not context.user_data.get("adding_product"):
        return

    category = query.data.replace("newcat_", "")
    context.user_data["category"] = category
    context.user_data["add_step"] = "photo"

    await query.message.reply_text(
        "🖼️ حالا عکس محصول را ارسال کن:"
    )


# =========================================================
# اجرای ربات
# =========================================================
def main():
    if not TOKEN:
        raise RuntimeError("توکن ربات وارد نشده است.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(new_category_callback, pattern=r"^newcat_"))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
