import json
import os
import re
from datetime import datetime
from pathlib import Path

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

# =========================================================
# Mohammadi Fashion - Enhanced Telegram Shop Bot
# =========================================================
# امنیت:
# بهتر است توکن را در متغیر محیطی BOT_TOKEN قرار بدهی.
# اگر قرار است همین فایل را مستقیم اجرا کنی، توکن فعلی را می‌توانی
# در BOT_TOKEN قرار بدهی.
TOKEN = "8850373531:AAGJRJL7ufyIVFn6xC4K3m8cCtRvdV7MX4E"
ADMIN_ID = int(os.getenv("ADMIN_ID", "8276323231"))

# پرداخت آنلاین:
# یک لینک پرداخت واقعی (مثلاً لینک درگاه خودت) را در PAYMENT_URL قرار بده.
# بدون URL/API واقعی، پرداخت آنلاین واقعی قابل فعال‌سازی نیست.
PAYMENT_URL = os.getenv("PAYMENT_URL", "")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "پرداخت آنلاین")

DATA_DIR = Path(".")
PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
PAYMENTS_FILE = DATA_DIR / "payments.json"
ADMIN_LOG_FILE = DATA_DIR / "admin_log.json"

STATUS_NEW = "جدید"
STATUS_CONFIRMED = "تأیید شد"
STATUS_READY = "آماده"
STATUS_DELIVERED = "تحویل شد"
STATUS_CANCELLED = "لغو شد"
ORDER_STATUSES = [
    STATUS_NEW,
    STATUS_CONFIRMED,
    STATUS_READY,
    STATUS_DELIVERED,
    STATUS_CANCELLED,
]


# -------------------------
# JSON helpers
# -------------------------
def load_json(path, default):
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return default


def save_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def load_products():
    return load_json(PRODUCTS_FILE, [])


def save_products(products):
    save_json(PRODUCTS_FILE, products)


def load_orders():
    return load_json(ORDERS_FILE, [])


def save_orders(orders):
    save_json(ORDERS_FILE, orders)


def load_customers():
    return load_json(CUSTOMERS_FILE, [])


def save_customers(customers):
    save_json(CUSTOMERS_FILE, customers)


def load_payments():
    return load_json(PAYMENTS_FILE, [])


def save_payments(payments):
    save_json(PAYMENTS_FILE, payments)


def load_admin_log():
    return load_json(ADMIN_LOG_FILE, [])


def save_admin_log(log):
    save_json(ADMIN_LOG_FILE, log)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def next_id(items):
    ids = []
    for item in items:
        try:
            ids.append(int(item.get("id", 0)))
        except Exception:
            pass
    return str(max(ids, default=0) + 1)


def normalize_product(product):
    product.setdefault("id", "")
    product.setdefault("name", "بدون نام")
    product.setdefault("price", "توافقی")
    product.setdefault("category", "majlesi")
    product.setdefault("stock", 0)

    # سازگاری با نسخه‌های قدیمی
    photos = product.get("photos", [])
    if isinstance(photos, str):
        photos = [photos] if photos else []
    if product.get("photo") and product["photo"] not in photos:
        photos.insert(0, product["photo"])
    product["photos"] = [x for x in photos if x]

    if product["photos"]:
        product["photo"] = product["photos"][0]

    return product


def get_product(product_id):
    for p in load_products():
        p = normalize_product(p)
        if str(p.get("id")) == str(product_id):
            return p
    return None


def price_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
    try:
        return float(cleaned)
    except Exception:
        return 0.0


def fmt_money(value):
    n = price_number(value)
    if n.is_integer():
        return f"{int(n):,}"
    return f"{n:,.2f}"


# -------------------------
# Security / admin
# -------------------------
def is_admin(user_id):
    return int(user_id) == ADMIN_ID


async def deny_non_admin(query):
    await query.answer("⛔ دسترسی ندارید.", show_alert=True)


def log_admin(user_id, action):
    log = load_admin_log()
    log.append({
        "user_id": user_id,
        "action": action,
        "created_at": now_text(),
    })
    save_admin_log(log)


# -------------------------
# Customer management
# -------------------------
def upsert_customer(user):
    customers = load_customers()
    uid = str(user.id)
    username = f"@{user.username}" if user.username else "ندارد"

    found = None
    for c in customers:
        if str(c.get("user_id")) == uid:
            found = c
            break

    if found is None:
        customers.append({
            "user_id": user.id,
            "name": user.full_name or "بدون نام",
            "username": username,
            "phone": "",
            "orders_count": 0,
            "total_spent": 0,
            "created_at": now_text(),
            "updated_at": now_text(),
        })
    else:
        found["name"] = user.full_name or found.get("name", "بدون نام")
        found["username"] = username
        found["updated_at"] = now_text()

    save_customers(customers)


def update_customer_after_order(user, phone, total):
    customers = load_customers()
    uid = str(user.id)

    for c in customers:
        if str(c.get("user_id")) == uid:
            c["phone"] = phone
            c["orders_count"] = int(c.get("orders_count", 0)) + 1
            c["total_spent"] = price_number(c.get("total_spent", 0)) + price_number(total)
            c["updated_at"] = now_text()
            break
    else:
        customers.append({
            "user_id": user.id,
            "name": user.full_name or "بدون نام",
            "username": f"@{user.username}" if user.username else "ندارد",
            "phone": phone,
            "orders_count": 1,
            "total_spent": price_number(total),
            "created_at": now_text(),
            "updated_at": now_text(),
        })

    save_customers(customers)


# -------------------------
# UI
# -------------------------
def home_keyboard(user_id=None):
    rows = [
        [
            InlineKeyboardButton("👗 لباس‌های مجلسی", callback_data="majlesi"),
            InlineKeyboardButton("👖 سرپطلونی", callback_data="sarpatloni"),
        ],
        [
            InlineKeyboardButton("🧵 سفارش دوخت", callback_data="dokht"),
            InlineKeyboardButton("🛒 سبد خرید", callback_data="cart"),
        ],
        [
            InlineKeyboardButton("📦 سفارش‌های من", callback_data="my_orders"),
            InlineKeyboardButton("🔎 جستجوی محصول", callback_data="search"),
        ],
        [
            InlineKeyboardButton("💳 پرداخت آنلاین", callback_data="payment_info"),
            InlineKeyboardButton("📞 تماس با ما", callback_data="contact"),
        ],
    ]
    if user_id is not None and is_admin(user_id):
        rows.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def back_home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 خانه", callback_data="home")]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 آمار فروش", callback_data="admin_stats"),
            InlineKeyboardButton("👥 مشتری‌ها", callback_data="admin_customers"),
        ],
        [
            InlineKeyboardButton("📦 موجودی", callback_data="admin_stock"),
            InlineKeyboardButton("🛍️ محصولات", callback_data="admin_products"),
        ],
        [
            InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product"),
            InlineKeyboardButton("💰 تغییر قیمت", callback_data="change_price"),
        ],
        [
            InlineKeyboardButton("🔢 تغییر موجودی", callback_data="change_stock"),
            InlineKeyboardButton("🗑️ حذف محصول", callback_data="delete_product"),
        ],
        [
            InlineKeyboardButton("🔔 سفارش‌های جدید", callback_data="admin_orders"),
            InlineKeyboardButton("💳 پرداخت‌ها", callback_data="admin_payments"),
        ],
        [
            InlineKeyboardButton("🔐 امنیت", callback_data="admin_security"),
            InlineKeyboardButton("🏠 خانه", callback_data="home"),
        ],
    ])


def product_keyboard(product_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 سفارش", callback_data=f"order_{product_id}"),
            InlineKeyboardButton("➕ سبد خرید", callback_data=f"addcart_{product_id}"),
        ],
        [InlineKeyboardButton("🔙 برگشت", callback_data="majlesi")],
        [InlineKeyboardButton("🏠 خانه", callback_data="home")],
    ])


def admin_order_keyboard(order_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تأیید", callback_data=f"status_{order_id}_تأیید شد"),
            InlineKeyboardButton("❌ لغو", callback_data=f"status_{order_id}_لغو شد"),
        ],
        [
            InlineKeyboardButton("📦 آماده", callback_data=f"status_{order_id}_آماده"),
            InlineKeyboardButton("🚚 تحویل", callback_data=f"status_{order_id}_تحویل شد"),
        ],
    ])


# -------------------------
# Order helpers
# -------------------------
def order_total(order):
    total = 0.0
    for item in order.get("items", []):
        total += price_number(item.get("price")) * int(item.get("quantity", 1))
    return total


def make_order(user, phone, items, custom_description="", custom_photos=None):
    orders = load_orders()
    order = {
        "id": next_id(orders),
        "user_id": user.id,
        "customer_name": user.full_name or "بدون نام",
        "phone": phone,
        "telegram": f"@{user.username}" if user.username else "ندارد",
        "items": items,
        "custom_description": custom_description,
        "custom_photos": custom_photos or [],
        "status": STATUS_NEW,
        "payment_status": "در انتظار پرداخت",
        "created_at": now_text(),
        "updated_at": now_text(),
    }
    orders.append(order)
    save_orders(orders)
    update_customer_after_order(user, phone, order_total(order))
    return order


async def send_professional_order_notification(context, order):
    items_text = []
    for item in order.get("items", []):
        qty = item.get("quantity", 1)
        items_text.append(
            f"• {item.get('name')} × {qty} — {item.get('price')}"
        )

    total = order_total(order)

    text = (
        "🔔 <b>سفارش جدید Mohammadi Fashion</b>\n\n"
        f"🆔 <b>شماره سفارش:</b> #{order['id']}\n"
        f"👤 <b>مشتری:</b> {order['customer_name']}\n"
        f"📱 <b>شماره:</b> {order['phone']}\n"
        f"💬 <b>تلگرام:</b> {order['telegram']}\n\n"
        "🛍️ <b>اقلام:</b>\n"
        + "\n".join(items_text)
        + f"\n\n💰 <b>مجموع:</b> {fmt_money(total)}\n"
        f"💳 <b>پرداخت:</b> {order.get('payment_status', 'در انتظار پرداخت')}\n"
        f"📌 <b>وضعیت:</b> {order.get('status', STATUS_NEW)}\n"
        f"🕒 <b>زمان:</b> {order.get('created_at')}"
    )

    if order.get("custom_description"):
        text += f"\n\n🧵 <b>توضیحات دوخت:</b>\n{order['custom_description']}"

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=admin_order_keyboard(order["id"]),
    )

    for photo_id in order.get("custom_photos", []):
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=f"🖼️ عکس مدل سفارش دوخت #{order['id']}",
        )


async def notify_customer_status(context, order):
    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "🔔 <b>به‌روزرسانی سفارش</b>\n\n"
                f"🆔 سفارش: #{order['id']}\n"
                f"📌 وضعیت جدید: <b>{order['status']}</b>\n\n"
                "🌸 Mohammadi Fashion"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


# -------------------------
# Start
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    upsert_customer(update.effective_user)

    await update.message.reply_text(
        "🌸 <b>به Mohammadi Fashion خوش آمدید</b> 🌸\n\n"
        "✨ فروشگاه آنلاین لباس زنانه\n"
        "🛍️ انتخاب کن، سفارش بده و با خیال راحت پیگیری کن.",
        parse_mode="HTML",
        reply_markup=home_keyboard(update.effective_user.id),
    )


# -------------------------
# Callback router
# -------------------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "home":
        context.user_data.clear()
        await query.message.reply_text(
            "🌸 <b>Mohammadi Fashion</b> 🌸\n\n"
            "لطفاً گزینه مورد نظر را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=home_keyboard(user_id),
        )
        return

    if data == "majlesi":
        products = [normalize_product(p) for p in load_products()
                    if normalize_product(p).get("category", "majlesi") == "majlesi"]
        rows = []
        for p in products:
            stock = int(p.get("stock", 0))
            stock_text = "موجود" if stock > 0 else "ناموجود"
            rows.append([InlineKeyboardButton(
                f"✨ {p['name']} | 💰 {p['price']} | 📦 {stock_text}",
                callback_data=f"product_{p['id']}"
            )])
        rows.append([InlineKeyboardButton("🏠 خانه", callback_data="home")])

        await query.message.reply_text(
            "👗 <b>لباس‌های مجلسی</b>\n\n"
            "محصول مورد نظر را انتخاب کن:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data == "sarpatloni":
        products = [normalize_product(p) for p in load_products()
                    if normalize_product(p).get("category") == "sarpatloni"]
        rows = []
        for p in products:
            rows.append([InlineKeyboardButton(
                f"👖 {p['name']} | 💰 {p['price']}",
                callback_data=f"product_{p['id']}"
            )])
        rows.append([InlineKeyboardButton("🏠 خانه", callback_data="home")])
        await query.message.reply_text(
            "👖 <b>سرپطلونی</b>\n\n"
            "محصول مورد نظر را انتخاب کن:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data.startswith("product_"):
        product = get_product(data.replace("product_", ""))
        if not product:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return

        stock = int(product.get("stock", 0))
        text = (
            f"✨ <b>{product['name']}</b> ✨\n\n"
            f"💰 قیمت: <b>{product['price']}</b>\n"
            f"📦 موجودی: <b>{stock}</b>"
        )
        keyboard = product_keyboard(product["id"]) if stock > 0 else back_home_keyboard()

        photos = product.get("photos", [])
        if photos:
            await query.message.reply_photo(
                photo=photos[0],
                caption=text if stock > 0 else text + "\n\n❌ فعلاً ناموجود است.",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await query.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        return

    if data.startswith("addcart_"):
        product = get_product(data.replace("addcart_", ""))
        if not product:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        if int(product.get("stock", 0)) <= 0:
            await query.message.reply_text("❌ این محصول ناموجود است.")
            return
        cart = context.user_data.setdefault("cart", [])
        existing = next((x for x in cart if str(x["product_id"]) == str(product["id"])), None)
        if existing:
            existing["quantity"] += 1
        else:
            cart.append({
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "quantity": 1,
            })
        await query.message.reply_text(
            f"✅ «{product['name']}» به سبد خرید اضافه شد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 مشاهده سبد", callback_data="cart")],
                [InlineKeyboardButton("🏠 خانه", callback_data="home")],
            ]),
        )
        return

    if data.startswith("order_"):
        product = get_product(data.replace("order_", ""))
        if not product:
            await query.message.reply_text("❌ محصول پیدا نشد.")
            return
        if int(product.get("stock", 0)) <= 0:
            await query.message.reply_text("❌ این محصول فعلاً موجود نیست.")
            return

        context.user_data.clear()
        context.user_data.update({
            "ordering": True,
            "order_step": "phone",
            "cart_items": [{
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "quantity": 1,
            }],
        })
        await query.message.reply_text(
            f"🛒 <b>ثبت سفارش</b>\n\n"
            f"👗 {product['name']}\n"
            f"💰 {product['price']}\n\n"
            "📱 لطفاً شماره تماس خود را ارسال کن:",
            parse_mode="HTML",
        )
        return

    if data == "cart":
        await show_cart(query, context)
        return

    if data == "clear_cart":
        context.user_data["cart"] = []
        await query.message.reply_text(
            "🗑️ سبد خرید خالی شد.",
            reply_markup=back_home_keyboard(),
        )
        return

    if data == "checkout_cart":
        cart = context.user_data.get("cart", [])
        if not cart:
            await query.message.reply_text("🛒 سبد خرید خالی است.")
            return
        context.user_data["ordering"] = True
        context.user_data["order_step"] = "phone"
        context.user_data["cart_items"] = cart
        await query.message.reply_text("📱 برای ثبت سفارش، شماره تماس خود را ارسال کن:")
        return

    if data == "my_orders":
        orders = [o for o in load_orders() if int(o.get("user_id", 0)) == user_id]
        if not orders:
            await query.message.reply_text(
                "📦 هنوز سفارشی ثبت نکرده‌ای.",
                reply_markup=back_home_keyboard(),
            )
            return

        lines = ["📦 <b>سفارش‌های من</b>\n"]
        for o in orders[-10:]:
            lines.append(
                f"🆔 #{o['id']} | 📌 {o.get('status', STATUS_NEW)} | "
                f"💰 {fmt_money(order_total(o))}\n"
                f"🕒 {o.get('created_at', '')}"
            )
        await query.message.reply_text(
            "\n\n".join(lines),
            parse_mode="HTML",
            reply_markup=back_home_keyboard(),
        )
        return

    if data == "search":
        context.user_data.clear()
        context.user_data["searching"] = True
        await query.message.reply_text(
            "🔎 نام یا بخشی از نام محصول را ارسال کن:"
        )
        return

    if data == "payment_info":
        if PAYMENT_URL:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💳 {PAYMENT_NAME}", url=PAYMENT_URL)],
                [InlineKeyboardButton("🏠 خانه", callback_data="home")],
            ])
            text = (
                "💳 <b>پرداخت آنلاین</b>\n\n"
                "برای پرداخت، روی دکمه زیر بزن."
            )
        else:
            keyboard = back_home_keyboard()
            text = (
                "💳 <b>پرداخت آنلاین</b>\n\n"
                "درگاه هنوز تنظیم نشده است.\n"
                "مدیر باید PAYMENT_URL یا API درگاه پرداخت را تنظیم کند."
            )
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )
        return

    if data == "dokht":
        context.user_data.clear()
        context.user_data.update({
            "custom_order": True,
            "custom_step": "description",
        })
        await query.message.reply_text(
            "🧵 <b>سفارش دوخت اختصاصی</b>\n\n"
            "مشخصات لباس، رنگ، مدل و هر توضیحی که لازم است را ارسال کن:",
            parse_mode="HTML",
        )
        return

    if data == "contact":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 پیام در تلگرام", url="https://t.me/Rohullah1375")],
            [InlineKeyboardButton("🏠 خانه", callback_data="home")],
        ])
        await query.message.reply_text(
            "📞 <b>تماس با ما</b>\n\n"
            "📱 واتساپ: 93744763112\n"
            "💬 تلگرام: @Rohullah1375\n\n"
            "🌸 Mohammadi Fashion 🌸",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    # -------------------------
    # Admin
    # -------------------------
    if data == "admin":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        log_admin(user_id, "open_admin")
        await query.message.reply_text(
            "⚙️ <b>پنل مدیریت Mohammadi Fashion</b>\n\n"
            "از این بخش فروش، مشتری‌ها، موجودی و سفارش‌ها را مدیریت کن.",
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )
        return

    if data.startswith("status_"):
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        parts = data.split("_", 2)
        if len(parts) != 3:
            return
        order_id, status = parts[1], parts[2]
        orders = load_orders()
        target = None
        for o in orders:
            if str(o.get("id")) == order_id:
                target = o
                break
        if not target:
            await query.message.reply_text("❌ سفارش پیدا نشد.")
            return

        target["status"] = status
        target["updated_at"] = now_text()
        save_orders(orders)
        log_admin(user_id, f"order_{order_id}_status_{status}")

        await query.message.reply_text(
            f"✅ وضعیت سفارش #{order_id} به «{status}» تغییر کرد."
        )
        await notify_customer_status(context, target)
        return

    if data == "admin_stats":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        orders = load_orders()
        customers = load_customers()
        delivered = [o for o in orders if o.get("status") == STATUS_DELIVERED]
        confirmed = [o for o in orders if o.get("status") in (STATUS_CONFIRMED, STATUS_READY, STATUS_DELIVERED)]
        revenue = sum(order_total(o) for o in delivered)
        pending = [o for o in orders if o.get("status") == STATUS_NEW]
        text = (
            "📊 <b>آمار فروش</b>\n\n"
            f"🧾 کل سفارش‌ها: <b>{len(orders)}</b>\n"
            f"👥 مشتری‌ها: <b>{len(customers)}</b>\n"
            f"🔔 سفارش‌های جدید: <b>{len(pending)}</b>\n"
            f"✅ سفارش‌های تأیید/آماده/تحویل: <b>{len(confirmed)}</b>\n"
            f"🚚 تحویل‌شده: <b>{len(delivered)}</b>\n"
            f"💰 فروش تحویل‌شده: <b>{fmt_money(revenue)}</b>"
        )
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=back_admin_keyboard()
        )
        return

    if data == "admin_customers":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        customers = load_customers()
        if not customers:
            text = "👥 هنوز مشتری ثبت نشده است."
        else:
            lines = ["👥 <b>مدیریت مشتری‌ها</b>\n"]
            for c in customers[-30:]:
                lines.append(
                    f"👤 {c.get('name')}\n"
                    f"💬 {c.get('username')}\n"
                    f"📱 {c.get('phone') or 'ثبت نشده'}\n"
                    f"🧾 سفارش: {c.get('orders_count', 0)} | "
                    f"💰 خرید: {fmt_money(c.get('total_spent', 0))}"
                )
            text = "\n\n".join(lines)
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=back_admin_keyboard()
        )
        return

    if data == "admin_stock":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        products = [normalize_product(p) for p in load_products()]
        if not products:
            text = "📦 محصولی وجود ندارد."
        else:
            lines = ["📦 <b>مدیریت موجودی</b>\n"]
            for p in products:
                lines.append(f"• {p['name']} — موجودی: <b>{p.get('stock', 0)}</b>")
            text = "\n".join(lines)
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=back_admin_keyboard()
        )
        return

    if data == "admin_products":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        products = [normalize_product(p) for p in load_products()]
        lines = ["🛍️ <b>محصولات فروشگاه</b>\n"]
        for p in products:
            lines.append(
                f"🆔 {p['id']} | {p['name']} | 💰 {p['price']} | 📦 {p.get('stock', 0)}"
            )
        await query.message.reply_text(
            "\n".join(lines) if products else "🛍️ محصولی ثبت نشده است.",
            parse_mode="HTML",
            reply_markup=back_admin_keyboard(),
        )
        return

    if data == "admin_orders":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        orders = load_orders()
        new_orders = [o for o in orders if o.get("status") == STATUS_NEW]
        if not new_orders:
            text = "🔔 سفارش جدیدی وجود ندارد."
        else:
            text = "🔔 <b>سفارش‌های جدید</b>\n\n" + "\n\n".join(
                f"🆔 #{o['id']} | 👤 {o['customer_name']} | 💰 {fmt_money(order_total(o))}"
                for o in new_orders[-20:]
            )
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=back_admin_keyboard()
        )
        return

    if data == "admin_payments":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        payments = load_payments()
        if not payments:
            text = "💳 هنوز پرداختی ثبت نشده است."
        else:
            text = "💳 <b>پرداخت‌ها</b>\n\n" + "\n\n".join(
                f"🧾 سفارش #{p.get('order_id')} | 💰 {p.get('amount')} | 📌 {p.get('status')}"
                for p in payments[-30:]
            )
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=back_admin_keyboard()
        )
        return

    if data == "admin_security":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        log = load_admin_log()
        await query.message.reply_text(
            "🔐 <b>امنیت پنل</b>\n\n"
            f"👤 شناسه مدیر مجاز: <code>{ADMIN_ID}</code>\n"
            f"🛡️ تعداد رویدادهای ثبت‌شده: <b>{len(log)}</b>\n\n"
            "✅ تمام دکمه‌های مدیریتی فقط برای ADMIN_ID فعال هستند.\n"
            "✅ عملیات مدیریتی در لاگ ثبت می‌شود.\n"
            "⚠️ توکن ربات را با دیگران به اشتراک نگذار.",
            parse_mode="HTML",
            reply_markup=back_admin_keyboard(),
        )
        return

    if data == "add_product":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        context.user_data.clear()
        context.user_data["adding_product"] = True
        context.user_data["add_step"] = "name"
        await query.message.reply_text(
            "➕ <b>افزودن محصول</b>\n\nنام محصول را ارسال کن:",
            parse_mode="HTML",
        )
        return

    if data == "change_price":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        context.user_data.clear()
        context.user_data["admin_action"] = "change_price"
        await query.message.reply_text(
            "💰 برای تغییر قیمت، شناسه محصول را به شکل زیر بفرست:\n"
            "<code>ID قیمت</code>\n\nمثال: <code>3 1250</code>",
            parse_mode="HTML",
        )
        return

    if data == "change_stock":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        context.user_data.clear()
        context.user_data["admin_action"] = "change_stock"
        await query.message.reply_text(
            "📦 برای تغییر موجودی:\n"
            "<code>ID تعداد</code>\n\nمثال: <code>3 12</code>",
            parse_mode="HTML",
        )
        return

    if data == "delete_product":
        if not is_admin(user_id):
            await deny_non_admin(query)
            return
        context.user_data.clear()
        context.user_data["admin_action"] = "delete_product"
        await query.message.reply_text(
            "🗑️ شناسه محصول را ارسال کن:",
        )
        return


def back_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")],
        [InlineKeyboardButton("🏠 خانه", callback_data="home")],
    ])


async def show_cart(query, context):
    cart = context.user_data.get("cart", [])
    if not cart:
        await query.message.reply_text(
            "🛒 سبد خرید خالی است.",
            reply_markup=back_home_keyboard(),
        )
        return

    total = sum(price_number(x["price"]) * int(x.get("quantity", 1)) for x in cart)
    lines = ["🛒 <b>سبد خرید</b>\n"]
    for item in cart:
        lines.append(
            f"• {item['name']} × {item.get('quantity', 1)} — {item['price']}"
        )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ثبت سفارش سبد", callback_data="checkout_cart")],
        [InlineKeyboardButton("🗑️ خالی کردن سبد", callback_data="clear_cart")],
        [InlineKeyboardButton("🏠 خانه", callback_data="home")],
    ])
    await query.message.reply_text(
        "\n".join(lines) + f"\n\n💰 <b>مجموع:</b> {fmt_money(total)}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# -------------------------
# Text input
# -------------------------
async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip()

    upsert_customer(user)

    # Search
    if context.user_data.get("searching"):
        context.user_data.clear()
        products = [normalize_product(p) for p in load_products()]
        found = [p for p in products if text.lower() in p["name"].lower()]
        if not found:
            await update.message.reply_text(
                "🔎 محصولی با این نام پیدا نشد.",
                reply_markup=back_home_keyboard(),
            )
            return
        rows = [[InlineKeyboardButton(
            f"✨ {p['name']} — {p['price']}",
            callback_data=f"product_{p['id']}"
        )] for p in found]
        rows.append([InlineKeyboardButton("🏠 خانه", callback_data="home")])
        await update.message.reply_text(
            "🔎 نتایج جستجو:",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    # Custom sewing
    if context.user_data.get("custom_order"):
        step = context.user_data.get("custom_step")
        if step == "description":
            context.user_data["custom_description"] = text
            context.user_data["custom_step"] = "phone"
            await update.message.reply_text("📱 شماره تماس خود را ارسال کن:")
            return

        if step == "phone":
            context.user_data["custom_phone"] = text
            context.user_data["custom_step"] = "photo"
            await update.message.reply_text(
                "🖼️ اگر عکس مدل لباس داری، همین حالا ارسال کن.\n"
                "اگر عکس نداری، «ندارم» بنویس."
            )
            return

        if step == "photo":
            if text == "ندارم":
                order = make_order(
                    user,
                    context.user_data.get("custom_phone", ""),
                    [{"name": "🧵 سفارش دوخت", "price": "توافقی", "quantity": 1}],
                    context.user_data.get("custom_description", ""),
                    [],
                )
                await send_professional_order_notification(context, order)
                context.user_data.clear()
                await update.message.reply_text(
                    "✅ سفارش دوخت ثبت شد و برای مدیر ارسال گردید.",
                    reply_markup=home_keyboard(user_id),
                )
                return

    # Normal order
    if context.user_data.get("ordering"):
        if context.user_data.get("order_step") == "phone":
            cart_items = context.user_data.get("cart_items", [])
            for item in cart_items:
                p = get_product(item["product_id"])
                if not p or int(p.get("stock", 0)) < int(item.get("quantity", 1)):
                    context.user_data.clear()
                    await update.message.reply_text("❌ موجودی محصول کافی نیست.")
                    return

            order = make_order(user, text, cart_items)
            products = load_products()
            for p in products:
                for item in cart_items:
                    if str(p.get("id")) == str(item.get("product_id")):
                        p["stock"] = max(0, int(p.get("stock", 0)) - int(item.get("quantity", 1)))
            save_products(products)

            await send_professional_order_notification(context, order)
            context.user_data.clear()

            # اگر درگاه تنظیم شده باشد، لینک پرداخت را هم نمایش می‌دهد.
            if PAYMENT_URL:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 پرداخت آنلاین", url=PAYMENT_URL)],
                    [InlineKeyboardButton("🏠 خانه", callback_data="home")],
                ])
                await update.message.reply_text(
                    "✅ سفارش ثبت شد.\n\n"
                    f"🧾 شماره سفارش: #{order['id']}\n"
                    "برای تکمیل پرداخت روی دکمه زیر بزن:",
                    reply_markup=keyboard,
                )
            else:
                await update.message.reply_text(
                    f"✅ سفارش #{order['id']} با موفقیت ثبت شد! 🎉\n"
                    "📞 به‌زودی با شما تماس گرفته می‌شود.",
                    reply_markup=home_keyboard(user_id),
                )
            return

    # Admin actions
    if not is_admin(user_id):
        return

    if context.user_data.get("adding_product"):
        step = context.user_data.get("add_step")

        if step == "name":
            context.user_data["product_name"] = text
            context.user_data["add_step"] = "price"
            await update.message.reply_text("💰 قیمت محصول را ارسال کن:")
            return

        if step == "price":
            context.user_data["product_price"] = text
            context.user_data["add_step"] = "stock"
            await update.message.reply_text("📦 تعداد موجودی را ارسال کن:")
            return

        if step == "stock":
            try:
                stock = max(0, int(text))
            except ValueError:
                await update.message.reply_text("❌ موجودی باید عدد باشد.")
                return
            context.user_data["product_stock"] = stock
            context.user_data["add_step"] = "category"
            await update.message.reply_text(
                "📂 دسته را ارسال کن:\n"
                "1 = مجلسی\n"
                "2 = سرپطلونی"
            )
            return

        if step == "category":
            category = "sarpatloni" if text == "2" else "majlesi"
            context.user_data["product_category"] = category
            context.user_data["add_step"] = "photo"
            await update.message.reply_text("🖼️ حالا عکس محصول را ارسال کن:")
            return

    if context.user_data.get("admin_action"):
        action = context.user_data["admin_action"]
        parts = text.split()

        if action == "change_price":
            if len(parts) != 2:
                await update.message.reply_text("فرمت درست: ID قیمت")
                return
            product = get_product(parts[0])
            if not product:
                await update.message.reply_text("❌ محصول پیدا نشد.")
                return
            products = load_products()
            for p in products:
                if str(p.get("id")) == str(parts[0]):
                    p["price"] = parts[1]
                    break
            save_products(products)
            log_admin(user_id, f"change_price_{parts[0]}")
            context.user_data.clear()
            await update.message.reply_text("✅ قیمت تغییر کرد.", reply_markup=back_admin_keyboard())
            return

        if action == "change_stock":
            if len(parts) != 2:
                await update.message.reply_text("فرمت درست: ID تعداد")
                return
            try:
                stock = max(0, int(parts[1]))
            except ValueError:
                await update.message.reply_text("❌ تعداد باید عدد باشد.")
                return
            products = load_products()
            found = False
            for p in products:
                if str(p.get("id")) == str(parts[0]):
                    p["stock"] = stock
                    found = True
                    break
            if not found:
                await update.message.reply_text("❌ محصول پیدا نشد.")
                return
            save_products(products)
            log_admin(user_id, f"change_stock_{parts[0]}_{stock}")
            context.user_data.clear()
            await update.message.reply_text("✅ موجودی تغییر کرد.", reply_markup=back_admin_keyboard())
            return

        if action == "delete_product":
            products = load_products()
            new_products = [p for p in products if str(p.get("id")) != text]
            if len(new_products) == len(products):
                await update.message.reply_text("❌ محصول پیدا نشد.")
                return
            save_products(new_products)
            log_admin(user_id, f"delete_product_{text}")
            context.user_data.clear()
            await update.message.reply_text("✅ محصول حذف شد.", reply_markup=back_admin_keyboard())
            return


# -------------------------
# Photo input
# -------------------------
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    photo_id = update.message.photo[-1].file_id

    # Customer custom sewing photo
    if context.user_data.get("custom_order") and context.user_data.get("custom_step") == "photo":
        order = make_order(
            user,
            context.user_data.get("custom_phone", ""),
            [{"name": "🧵 سفارش دوخت", "price": "توافقی", "quantity": 1}],
            context.user_data.get("custom_description", ""),
            [photo_id],
        )
        await send_professional_order_notification(context, order)
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ سفارش دوخت #{order['id']} ثبت شد و عکس مدل هم برای مدیر ارسال شد.",
            reply_markup=home_keyboard(user_id),
        )
        return

    # Admin product photo
    if not is_admin(user_id):
        return

    if context.user_data.get("adding_product") and context.user_data.get("add_step") == "photo":
        products = load_products()
        product = {
            "id": next_id(products),
            "name": context.user_data.get("product_name", "محصول"),
            "price": context.user_data.get("product_price", "توافقی"),
            "category": context.user_data.get("product_category", "majlesi"),
            "stock": int(context.user_data.get("product_stock", 0)),
            "photos": [photo_id],
            "photo": photo_id,
            "created_at": now_text(),
        }
        products.append(product)
        save_products(products)
        log_admin(user_id, f"add_product_{product['id']}")
        context.user_data.clear()

        await update.message.reply_text(
            "✅ محصول با موفقیت اضافه شد! 🎉\n\n"
            f"👗 {product['name']}\n"
            f"💰 {product['price']}\n"
            f"📦 موجودی: {product['stock']}",
            reply_markup=back_admin_keyboard(),
        )


# -------------------------
# Main
# -------------------------
def main():
    if not TOKEN or TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است. توکن ربات را در متغیر محیطی BOT_TOKEN قرار بده."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message))

    print("Mohammadi Fashion bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
