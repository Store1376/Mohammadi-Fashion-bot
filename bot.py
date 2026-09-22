# -*- coding: utf-8 -*-

import os
import json
import logging
import threading
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ============================================================
# MOHAMMADI FASHION
# Complete Telegram Store Bot
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

PORT = int(os.getenv("PORT", "10000"))

DATA_DIR = Path(os.getenv("DATA_DIR", "."))
DATA_DIR.mkdir(parents=True, exist_ok=True)

PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("MohammadiFashion")


# ============================================================
# FLASK / RENDER
# ============================================================

web_app = Flask(__name__)


@web_app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "Mohammadi Fashion",
        "status": "running"
    })


@web_app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "Mohammadi Fashion",
        "status": "healthy"
    })


def start_web_server():
    logger.info("Starting web server on port %s", PORT)

    web_app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


# ============================================================
# DATABASE
# ============================================================

def load_json(file_path, default):
    try:
        if not file_path.exists():
            save_json(file_path, default)
            return default

        content = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            return default

        return json.loads(content)

    except Exception as error:
        logger.error("Database read error: %s", error)
        return default


def save_json(file_path, data):
    try:
        file_path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    except Exception as error:
        logger.error("Database save error: %s", error)


def get_products():
    return load_json(PRODUCTS_FILE, [])


def get_orders():
    return load_json(ORDERS_FILE, [])


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id):
    return bool(
        ADMIN_ID
        and str(user_id) == str(ADMIN_ID)
    )


def get_product(product_id):
    for product in get_products():
        if str(product.get("id")) == str(product_id):
            return product

    return None


def next_product_id():
    products = get_products()

    numbers = []

    for product in products:
        try:
            numbers.append(
                int(product.get("id", 0))
            )
        except Exception:
            pass

    return str(max(numbers, default=0) + 1)


def next_order_id():
    orders = get_orders()

    numbers = []

    for order in orders:
        try:
            numbers.append(
                int(order.get("id", 0))
            )
        except Exception:
            pass

    return max(numbers, default=0) + 1


def money(value):
    try:
        number = float(value)

        if number.is_integer():
            return f"{int(number):,}"

        return f"{number:,.2f}"

    except Exception:
        return str(value)


def clear_state(context):
    cart = context.user_data.get("cart", [])

    context.user_data.clear()

    context.user_data["cart"] = cart


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard(user_id):

    buttons = [

        [
            InlineKeyboardButton(
                "👗 محصولات",
                callback_data="products"
            ),
            InlineKeyboardButton(
                "🛒 سبد خرید",
                callback_data="cart"
            ),
        ],

        [
            InlineKeyboardButton(
                "📦 سفارش‌های من",
                callback_data="my_orders"
            ),
            InlineKeyboardButton(
                "🔎 جستجوی محصول",
                callback_data="search"
            ),
        ],

        [
            InlineKeyboardButton(
                "🧵 دوخت سفارشی",
                callback_data="custom"
            ),
            InlineKeyboardButton(
                "📞 تماس با ما",
                callback_data="contact"
            ),
        ],
    ]

    if is_admin(user_id):
        buttons.append([
            InlineKeyboardButton(
                "⚙️ مدیریت فروشگاه",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(buttons)


def home_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🏠 صفحه اصلی",
                callback_data="home"
            )
        ]
    ])


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    user = update.effective_user

    logger.info(
        "START from user %s",
        user.id
    )

    text = (
        f"👋 سلام {user.first_name or 'دوست عزیز'}\n\n"
        "🌸 به فروشگاه Mohammadi Fashion خوش آمدید.\n\n"
        "👗 لباس‌های زنانه\n"
        "🧵 دوخت سفارشی\n"
        "🛒 ثبت سفارش آسان\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(user.id)
    )


# ============================================================
# HELP
# ============================================================

async def help_command(update, context):

    text = (
        "📖 راهنمای Mohammadi Fashion\n\n"
        "/start — صفحه اصلی\n"
        "/products — محصولات\n"
        "/cart — سبد خرید\n"
        "/orders — سفارش‌های من\n"
        "/cancel — لغو عملیات\n"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(
            update.effective_user.id
        )
    )


# ============================================================
# CANCEL
# ============================================================

async def cancel(update, context):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=main_keyboard(
            update.effective_user.id
        )
    )


# ============================================================
# PRODUCTS
# ============================================================

async def show_products(query):

    products = get_products()

    if not products:

        await query.edit_message_text(
            "👗 محصولات فروشگاه\n\n"
            "فعلاً محصولی ثبت نشده است.",
            reply_markup=home_button()
        )

        return

    keyboard = []

    for product in products[:50]:

        product_id = product.get("id")
        name = product.get("name", "محصول")
        price = product.get("price", 0)

        keyboard.append([
            InlineKeyboardButton(
                f"👗 {name} — {money(price)} افغانی",
                callback_data=f"product:{product_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🏠 صفحه اصلی",
            callback_data="home"
        )
    ])

    await query.edit_message_text(
        "👗 محصولات Mohammadi Fashion\n\n"
        "یک محصول را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# PRODUCT DETAILS
# ============================================================

async def show_product(query, product_id):

    product = get_product(product_id)

    if not product:

        await query.edit_message_text(
            "❌ محصول پیدا نشد.",
            reply_markup=home_button()
        )

        return

    name = product.get("name", "محصول")
    price = product.get("price", 0)
    stock = product.get("stock", 0)
    description = product.get("description", "")
    photo_id = product.get("photo_id")

    text = (
        f"👗 {name}\n\n"
        f"💰 قیمت: {money(price)} افغانی\n"
        f"📦 موجودی: {stock}\n"
    )

    if description:
        text += f"\n📝 توضیحات:\n{description}\n"

    keyboard = []

    if int(stock or 0) > 0:
        keyboard.append([
            InlineKeyboardButton(
                "🛒 افزودن به سبد خرید",
                callback_data=f"add:{product_id}"
            )
        ])

    keyboard.extend([
        [
            InlineKeyboardButton(
                "⬅️ محصولات",
                callback_data="products"
            ),
            InlineKeyboardButton(
                "🏠 خانه",
                callback_data="home"
            )
        ]
    ])

    markup = InlineKeyboardMarkup(keyboard)

    try:

        if photo_id:

            await query.message.delete()

            await query.message.chat.send_photo(
                photo=photo_id,
                caption=text,
                reply_markup=markup
            )

        else:

            await query.edit_message_text(
                text,
                reply_markup=markup
            )

    except Exception as error:

        logger.error(
            "Product display error: %s",
            error
        )

        try:
            await query.edit_message_text(
                text,
                reply_markup=markup
            )
        except Exception:
            pass


# ============================================================
# CART
# ============================================================

def get_cart(context):
    return context.user_data.setdefault(
        "cart",
        []
    )


def cart_total(context):

    total = 0

    for product_id in get_cart(context):

        product = get_product(product_id)

        if not product:
            continue

        try:
            total += float(
                product.get("price", 0)
            )
        except Exception:
            pass

    return total


async def show_cart(query, context):

    cart = get_cart(context)

    if not cart:

        await query.edit_message_text(
            "🛒 سبد خرید شما خالی است.",
            reply_markup=home_button()
        )

        return

    lines = [
        "🛒 سبد خرید شما\n"
    ]

    for product_id in cart:

        product = get_product(product_id)

        if product:

            lines.append(
                f"• {product.get('name')}\n"
                f"  💰 {money(product.get('price', 0))} افغانی"
            )

    lines.append(
        f"\n💰 مجموع: {money(cart_total(context))} افغانی"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "📱 ثبت سفارش",
                callback_data="checkout"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑️ خالی کردن سبد",
                callback_data="clear_cart"
            )
        ],

        [
            InlineKeyboardButton(
                "👗 محصولات",
                callback_data="products"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 صفحه اصلی",
                callback_data="home"
            )
        ],
    ]

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# CREATE ORDER
# ============================================================

def create_order(user, context, phone):

    cart = get_cart(context)

    if not cart:
        return None

    items = []
    total = 0

    for product_id in cart:

        product = get_product(product_id)

        if not product:
            continue

        try:
            price = float(
                product.get("price", 0)
            )
        except Exception:
            price = 0

        items.append({
            "product_id": product.get("id"),
            "name": product.get("name"),
            "price": price
        })

        total += price

    if not items:
        return None

    order = {

        "id": next_order_id(),

        "user_id": user.id,

        "name": user.full_name,

        "username": user.username or "",

        "phone": phone,

        "items": items,

        "total": total,

        "status": "جدید",

        "created_at": datetime.now().isoformat(),

    }

    orders = get_orders()

    orders.append(order)

    save_json(
        ORDERS_FILE,
        orders
    )

    return order


# ============================================================
# CHECKOUT
# ============================================================

async def checkout(query, context):

    if not get_cart(context):

        await query.edit_message_text(
            "🛒 سبد خرید شما خالی است.",
            reply_markup=home_button()
        )

        return

    context.user_data["state"] = "phone"

    await query.edit_message_text(
        "📱 لطفاً شماره تماس خود را ارسال کنید.\n\n"
        "مثال:\n"
        "0700000000",
        reply_markup=home_button()
    )


# ============================================================
# SEARCH
# ============================================================

async def search_products(query, context):

    context.user_data["state"] = "search"

    await query.edit_message_text(
        "🔎 نام محصول مورد نظر را بنویسید:",
        reply_markup=home_button()
    )


async def perform_search(update, context, text):

    results = []

    keyword = text.lower().strip()

    for product in get_products():

        name = str(
            product.get("name", "")
        ).lower()

        description = str(
            product.get("description", "")
        ).lower()

        if keyword in name or keyword in description:
            results.append(product)

    if not results:

        await update.message.reply_text(
            "❌ محصولی با این نام پیدا نشد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            )
        )

        context.user_data.pop("state", None)

        return

    keyboard = []

    for product in results[:30]:

        keyboard.append([
            InlineKeyboardButton(
                f"👗 {product.get('name')} — "
                f"{money(product.get('price', 0))} افغانی",
                callback_data=f"product:{product.get('id')}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🏠 صفحه اصلی",
            callback_data="home"
        )
    ])

    await update.message.reply_text(
        "🔎 نتایج جستجو:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data.pop("state", None)


# ============================================================
# CUSTOM ORDER
# ============================================================

async def custom_order(query, context):

    context.user_data["state"] = "custom"

    await query.edit_message_text(
        "🧵 دوخت سفارشی\n\n"
        "لطفاً توضیحات لباس مورد نظر خود را بنویسید.\n\n"
        "مثلاً:\n"
        "رنگ، مدل، سایز، نوع پارچه و تعداد.",
        reply_markup=home_button()
    )


# ============================================================
# CONTACT
# ============================================================

async def contact(query):

    text = (
        "📞 تماس با Mohammadi Fashion\n\n"
        "برای سفارش و هماهنگی می‌توانید با ما تماس بگیرید.\n\n"
        "📍 کابل، ده افغانان\n"
        "👗 عمده‌فروشی لباس‌های زنانه\n"
        "🧵 دوخت سفارشی"
    )

    await query.edit_message_text(
        text,
        reply_markup=home_button()
    )


# ============================================================
# MY ORDERS
# ============================================================

async def my_orders(query, user_id):

    orders = [

        order for order in get_orders()

        if str(order.get("user_id")) == str(user_id)

    ]

    if not orders:

        await query.edit_message_text(
            "📦 شما هنوز سفارشی ثبت نکرده‌اید.",
            reply_markup=home_button()
        )

        return

    lines = [
        "📦 سفارش‌های شما\n"
    ]

    for order in orders[-10:]:

        lines.append(
            f"🧾 سفارش #{order.get('id')}\n"
            f"💰 مبلغ: {money(order.get('total', 0))} افغانی\n"
            f"📌 وضعیت: {order.get('status', 'جدید')}\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=home_button()
    )


# ============================================================
# ADMIN PANEL
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="admin_add"
            )
        ],

        [
            InlineKeyboardButton(
                "✏️ ویرایش محصول",
                callback_data="admin_edit"
            ),
            InlineKeyboardButton(
                "🗑️ حذف محصول",
                callback_data="admin_delete"
            ),
        ],

        [
            InlineKeyboardButton(
                "📦 سفارش‌ها",
                callback_data="admin_orders"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار فروشگاه",
                callback_data="admin_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 صفحه اصلی",
                callback_data="home"
            )
        ],

    ])


async def admin_panel(query, user_id):

    if not is_admin(user_id):

        await query.edit_message_text(
            "⛔ دسترسی غیرمجاز.",
            reply_markup=home_button()
        )

        return

    products = get_products()
    orders = get_orders()

    text = (
        "⚙️ پنل مدیریت Mohammadi Fashion\n\n"
        f"👗 تعداد محصولات: {len(products)}\n"
        f"📦 تعداد سفارش‌ها: {len(orders)}\n\n"
        "یکی از گزینه‌ها را انتخاب کنید:"
    )

    await query.edit_message_text(
        text,
        reply_markup=admin_keyboard()
    )


# ============================================================
# ADMIN ADD PRODUCT
# ============================================================

async def admin_add_start(query, context):

    context.user_data["state"] = "admin_add_name"

    await query.edit_message_text(
        "➕ افزودن محصول\n\n"
        "نام محصول را ارسال کنید:",
        reply_markup=home_button()
    )


async def admin_add_name(update, context):

    context.user_data["new_product"] = {
        "name": update.message.text.strip()
    }

    context.user_data["state"] = "admin_add_price"

    await update.message.reply_text(
        "💰 قیمت محصول را به افغانی ارسال کنید:"
    )


async def admin_add_price(update, context):

    try:
        price = float(
            update.message.text.strip()
        )
    except Exception:

        await update.message.reply_text(
            "❌ قیمت نامعتبر است. فقط عدد ارسال کنید."
        )

        return

   
