# Mohammadi Fashion - Smart Telegram Shop Bot
# Python 3.10+
#
# امکانات:
# - محصولات و دسته‌بندی
# - جستجوی محصول
# - سبد خرید
# - ثبت سفارش
# - پیگیری سفارش
# - مدیریت مشتریان
# - مدیریت موجودی و قیمت
# - آمار فروش
# - پنل مدیریت
# - سفارش دوخت سفارشی
# - پرداخت آنلاین HesabPay
# - اعلان پرداخت و سفارش
# - دستیار هوش مصنوعی اختیاری
# - Webhook برای HesabPay
#
# نصب:
# pip install -r requirements.txt
#
# تنظیمات را در فایل .env قرار بده.

import os
import json
import uuid
import threading
import logging
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

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

# --------------------------------------------------
# ENV
# --------------------------------------------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

HESABPAY_API_KEY = os.getenv("HESABPAY_API_KEY", "").strip()

HESABPAY_API_URL = os.getenv(
    "HESABPAY_API_URL",
    "https://api.hesab.com/api/v1/payment/create-session"
).strip()

HESABPAY_SUCCESS_URL = os.getenv(
    "HESABPAY_SUCCESS_URL",
    "https://example.com/payment/success"
).strip()

HESABPAY_FAILURE_URL = os.getenv(
    "HESABPAY_FAILURE_URL",
    "https://example.com/payment/failure"
).strip()

HESABPAY_WEBHOOK_TOKEN = os.getenv(
    "HESABPAY_WEBHOOK_TOKEN",
    ""
).strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna"
).strip()

WEBHOOK_HOST = os.getenv(
    "WEBHOOK_HOST",
    "0.0.0.0"
).strip()

WEBHOOK_PORT = int(
    os.getenv("WEBHOOK_PORT", "8080")
)

DATA_DIR = Path(
    os.getenv("DATA_DIR", "data")
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# --------------------------------------------------
# FILES
# --------------------------------------------------

PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
PAYMENTS_FILE = DATA_DIR / "payments.json"
ADMIN_LOG_FILE = DATA_DIR / "admin_log.json"

# --------------------------------------------------
# LOGGING
# --------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(
    "MohammadiFashion"
)

# --------------------------------------------------
# DEFAULT PRODUCTS
# --------------------------------------------------

DEFAULT_PRODUCTS = [
    {
        "id": "p001",
        "name": "لباس مجلسی",
        "category": "majlesi",
        "description": "لباس مجلسی شیک و باکیفیت",
        "price": 2500,
        "stock": 5,
        "photo": ""
    },
    {
        "id": "p002",
        "name": "لباس سرپتلونی",
        "category": "sarpatloni",
        "description": "لباس سرپتلونی زیبا و مناسب استفاده روزمره",
        "price": 1800,
        "stock": 7,
        "photo": ""
    }
]

# --------------------------------------------------
# JSON HELPERS
# --------------------------------------------------

def load_json(path, default):
    try:
        if not path.exists():
            save_json(path, default)
            return default

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        logger.error(
            "JSON load error %s: %s",
            path,
            e
        )
        return default


def save_json(path, data):
    try:
        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )
    except Exception as e:
        logger.error(
            "JSON save error %s: %s",
            path,
            e
        )


def products():
    return load_json(
        PRODUCTS_FILE,
        DEFAULT_PRODUCTS
    )


def orders():
    return load_json(
        ORDERS_FILE,
        []
    )


def customers():
    return load_json(
        CUSTOMERS_FILE,
        {}
    )


def payments():
    return load_json(
        PAYMENTS_FILE,
        []
    )


def admin_logs():
    return load_json(
        ADMIN_LOG_FILE,
        []
    )

# --------------------------------------------------
# ADMIN
# --------------------------------------------------

def is_admin(user_id):
    return int(user_id) == ADMIN_ID


def log_admin(
    user_id,
    action
):
    data = admin_logs()

    data.append({
        "id": str(uuid.uuid4()),
        "admin_id": user_id,
        "action": action,
        "time": datetime.now().isoformat()
    })

    save_json(
        ADMIN_LOG_FILE,
        data
    )

# --------------------------------------------------
# CUSTOMER
# --------------------------------------------------

def ensure_customer(user):
    data = customers()

    uid = str(user.id)

    if uid not in data:
        data[uid] = {
            "telegram_id": user.id,
            "name": user.full_name,
            "username": user.username or "",
            "phone": "",
            "orders_count": 0,
            "total_spent": 0,
            "created_at": datetime.now().isoformat()
        }

        save_json(
            CUSTOMERS_FILE,
            data
        )

    return data[uid]


def update_customer_order(
    user_id,
    total
):
    data = customers()

    uid = str(user_id)

    if uid not in data:
        return

    data[uid]["orders_count"] += 1
    data[uid]["total_spent"] += total

    save_json(
        CUSTOMERS_FILE,
        data
    )

# --------------------------------------------------
# PRODUCT FUNCTIONS
# --------------------------------------------------

def get_product(product_id):
    for product in products():
        if product["id"] == product_id:
            return product

    return None


def category_name(category):
    if category == "majlesi":
        return "لباس مجلسی"

    if category == "sarpatloni":
        return "لباس سرپتلونی"

    return category


def format_price(price):
    return f"{price:,.0f} افغانی"


def search_products(query):
    query = query.lower().strip()

    result = []

    for p in products():
        text = (
            str(p.get("name", "")) +
            " " +
            str(p.get("description", ""))
        ).lower()

        if query in text:
            result.append(p)

    return result

# --------------------------------------------------
# ORDER FUNCTIONS
# --------------------------------------------------

def generate_order_id():
    return "MF-" + datetime.now().strftime(
        "%Y%m%d%H%M%S"
    ) + "-" + str(
        uuid.uuid4()
    )[:4].upper()


def get_order(order_id):
    for order in orders():
        if order["id"] == order_id:
            return order

    return None


def status_text(status):

    statuses = {
        "pending": "در انتظار پرداخت",
        "paid": "پرداخت شده",
        "confirmed": "تأیید شده",
        "ready": "آماده تحویل",
        "delivered": "تحویل شده",
        "cancelled": "لغو شده"
    }

    return statuses.get(
        status,
        status
    )

# --------------------------------------------------
# CART
# --------------------------------------------------

def get_cart(context):
    if "cart" not in context.user_data:
        context.user_data["cart"] = []

    return context.user_data["cart"]


def cart_total(context):

    total = 0

    for item in get_cart(context):

        product = get_product(
            item["product_id"]
        )

        if product:
            total += (
                product["price"] *
                item["quantity"]
            )

    return total


def cart_text(context):

    cart = get_cart(context)

    if not cart:
        return "🛒 سبد خرید شما خالی است."

    text = "🛒 *سبد خرید شما*\n\n"

    for item in cart:

        product = get_product(
            item["product_id"]
        )

        if not product:
            continue

        subtotal = (
            product["price"] *
            item["quantity"]
        )

        text += (
            f"• {product['name']}\n"
            f"  تعداد: {item['quantity']}\n"
            f"  قیمت: {format_price(subtotal)}\n\n"
        )

    text += (
        f"💰 مجموع: "
        f"{format_price(cart_total(context))}"
    )

    return text

# --------------------------------------------------
# TELEGRAM START
# --------------------------------------------------

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    ensure_customer(user)

    keyboard = [
        [
            InlineKeyboardButton(
                "🛍 محصولات",
                callback_data="products"
            ),
            InlineKeyboardButton(
                "🛒 سبد خرید",
                callback_data="cart"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 سفارش‌های من",
                callback_data="my_orders"
            ),
            InlineKeyboardButton(
                "🔎 جستجوی محصول",
                callback_data="search"
            )
        ],
        [
            InlineKeyboardButton(
                "✂️ سفارش دوخت",
                callback_data="custom_order"
            )
        ],
        [
            InlineKeyboardButton(
                "🤖 دستیار هوشمند",
                callback_data="ai"
            )
        ]
    ]

    if is_admin(user.id):
        keyboard.append([
            InlineKeyboardButton(
                "⚙️ پنل مدیریت",
                callback_data="admin"
            )
        ])

    await update.message.reply_text(
        "👗 *Mohammadi Fashion*\n\n"
        "به فروشگاه ما خوش آمدید 🌹\n\n"
        "از منوی زیر استفاده کنید:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# PRODUCTS
# --------------------------------------------------

async def show_products(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    items = products()

    if not items:
        await query.edit_message_text(
            "فعلاً محصولی موجود نیست."
        )
        return

    keyboard = []

    for p in items:

        stock_text = (
            "موجود"
            if p["stock"] > 0
            else "ناموجود"
        )

        keyboard.append([
            InlineKeyboardButton(
                f"{p['name']} | {format_price(p['price'])}",
                callback_data=f"product:{p['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="home"
        )
    ])

    await query.edit_message_text(
        "🛍 *محصولات فروشگاه*\n\n"
        "محصول مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# PRODUCT DETAIL
# --------------------------------------------------

async def product_detail(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    product_id = query.data.split(
        ":",
        1
    )[1]

    product = get_product(
        product_id
    )

    if not product:
        await query.edit_message_text(
            "❌ محصول پیدا نشد."
        )
        return

    stock = product["stock"]

    keyboard = []

    if stock > 0:
        keyboard.append([
            InlineKeyboardButton(
                "➕ افزودن به سبد",
                callback_data=f"add:{product_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 محصولات",
            callback_data="products"
        )
    ])

    text = (
        f"👗 *{product['name']}*\n\n"
        f"📂 دسته: {category_name(product['category'])}\n"
        f"📝 توضیحات: {product['description']}\n\n"
        f"💰 قیمت: {format_price(product['price'])}\n"
        f"📦 موجودی: {stock}\n"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADD TO CART
# --------------------------------------------------

async def add_to_cart(
    update,
    context
):

    query = update.callback_query

    await query.answer(
        "به سبد خرید اضافه شد ✅"
    )

    product_id = query.data.split(
        ":",
        1
    )[1]

    product = get_product(
        product_id
    )

    if not product:
        return

    if product["stock"] <= 0:
        await query.answer(
            "❌ محصول موجود نیست.",
            show_alert=True
        )
        return

    cart = get_cart(context)

    for item in cart:

        if item["product_id"] == product_id:

            if item["quantity"] >= product["stock"]:
                await query.answer(
                    "❌ بیشتر از موجودی نمی‌توانی انتخاب کنی.",
                    show_alert=True
                )
                return

            item["quantity"] += 1
            break

    else:

        cart.append({
            "product_id": product_id,
            "quantity": 1
        })

    await query.edit_message_text(
        cart_text(context),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💳 ثبت سفارش",
                    callback_data="checkout"
                )
            ],
            [
                InlineKeyboardButton(
                    "🛍 ادامه خرید",
                    callback_data="products"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗑 خالی کردن سبد",
                    callback_data="clear_cart"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# CART
# --------------------------------------------------

async def show_cart(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 ثبت سفارش",
                callback_data="checkout"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 خالی کردن سبد",
                callback_data="clear_cart"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="home"
            )
        ]
    ]

    await query.edit_message_text(
        cart_text(context),
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="Markdown"
    )


async def clear_cart(
    update,
    context
):

    query = update.callback_query

    await query.answer(
        "سبد خرید خالی شد."
    )

    context.user_data["cart"] = []

    await query.edit_message_text(
        "🛒 سبد خرید شما خالی شد.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🛍 محصولات",
                    callback_data="products"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 خانه",
                    callback_data="home"
                )
            ]
        ])
    )

# --------------------------------------------------
# CHECKOUT
# --------------------------------------------------

async def checkout(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not get_cart(context):
        await query.edit_message_text(
            "❌ سبد خرید خالی است."
        )
        return

    context.user_data["state"] = (
        "waiting_phone"
    )

    await query.edit_message_text(
        "📱 لطفاً شماره تماس خود را ارسال کنید.\n\n"
        "مثال:\n"
        "937XXXXXXXXX"
    )

# --------------------------------------------------
# CREATE ORDER
# --------------------------------------------------

async def create_order(
    update,
    context,
    phone
):

    user = update.effective_user

    cart = get_cart(context)

    if not cart:
        await update.message.reply_text(
            "❌ سبد خرید خالی است."
        )
        return

    total = 0
    order_items = []

    all_products = products()

    for item in cart:

        product = next(
            (
                p for p in all_products
                if p["id"] == item["product_id"]
            ),
            None
        )

        if not product:
            continue

        quantity = item["quantity"]

        if quantity > product["stock"]:
            await update.message.reply_text(
                f"❌ موجودی {product['name']} کافی نیست."
            )
            return

        subtotal = (
            product["price"] *
            quantity
        )

        total += subtotal

        order_items.append({
            "product_id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "quantity": quantity,
            "subtotal": subtotal
        })

    if not order_items:
        await update.message.reply_text(
            "❌ محصولی در سفارش وجود ندارد."
        )
        return

    order_id = generate_order_id()

    order = {
        "id": order_id,
        "user_id": user.id,
        "customer_name": user.full_name,
        "username": user.username or "",
        "phone": phone,
        "items": order_items,
        "total": total,
        "status": "pending",
        "payment_status": "unpaid",
        "created_at": datetime.now().isoformat()
    }

    order_list = orders()

    order_list.append(
        order
    )

    save_json(
        ORDERS_FILE,
        order_list
    )

    # کاهش موجودی
    for item in order_items:

        for product in all_products:

            if product["id"] == item["product_id"]:

                product["stock"] -= (
                    item["quantity"]
                )

    save_json(
        PRODUCTS_FILE,
        all_products
    )

    # ثبت مشتری
    customer_data = customers()

    uid = str(user.id)

    if uid in customer_data:
        customer_data[uid]["phone"] = phone

    save_json(
        CUSTOMERS_FILE,
        customer_data
    )

    context.user_data["cart"] = []

    update_customer_order(
        user.id,
        total
    )

    # اعلان ادمین
    await notify_admin_order(
        context,
        order
    )

    # پرداخت HesabPay
    payment_url = await create_hesabpay_payment(
        order
    )

    if payment_url:

        payment_data = payments()

        payment_data.append({
            "order_id": order_id,
            "user_id": user.id,
            "amount": total,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        })

        save_json(
            PAYMENTS_FILE,
            payment_data
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 پرداخت آنلاین",
                    url=payment_url
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 پیگیری سفارش",
                    callback_data=f"track:{order_id}"
                )
            ]
        ]

        await update.message.reply_text(
            f"✅ سفارش شما ثبت شد.\n\n"
            f"🧾 شماره سفارش: `{order_id}`\n"
            f"💰 مبلغ: {format_price(total)}\n\n"
            "برای تکمیل سفارش روی دکمه پرداخت بزنید:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="Markdown"
        )

    else:

        await update.message.reply_text(
            f"✅ سفارش شما ثبت شد.\n\n"
            f"🧾 شماره سفارش: `{order_id}`\n"
            f"💰 مبلغ: {format_price(total)}\n\n"
            "سفارش شما برای بررسی مدیر ارسال شد.",
            parse_mode="Markdown"
        )

    context.user_data["state"] = None

# --------------------------------------------------
# HESABPAY
# --------------------------------------------------

async def create_hesabpay_payment(
    order
):

    if not HESABPAY_API_KEY:
        logger.warning(
            "HesabPay API key is not configured."
        )
        return None

    headers = {
        "Authorization": (
            "API-KEY " +
            HESABPAY_API_KEY
        ),
        "Content-Type": "application/json"
    }

    items = []

    for item in order["items"]:

        items.append({
            "id": item["product_id"],
            "name": item["name"],
            "price": item["subtotal"]
        })

    payload = {
        "user_id": str(
            order["user_id"]
        ),
        "items": items,
        "success_redirect_url": (
            HESABPAY_SUCCESS_URL
        ),
        "failure_redirect_url": (
            HESABPAY_FAILURE_URL
        )
    }

    try:

        response = requests.post(
            HESABPAY_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code not in (
            200,
            201
        ):
            logger.error(
                "HesabPay error: %s %s",
                response.status_code,
                response.text
            )
            return None

        data = response.json()

        return data.get("url")

    except Exception as e:

        logger.exception(
            "HesabPay request failed: %s",
            e
        )

        return None

# --------------------------------------------------
# ADMIN NOTIFICATION
# --------------------------------------------------

async def notify_admin_order(
    context,
    order
):

    if not ADMIN_ID:
        return

    text = (
        "🔔 *سفارش جدید*\n\n"
        f"🧾 شماره: `{order['id']}`\n"
        f"👤 مشتری: {order['customer_name']}\n"
        f"📱 تلفن: {order['phone']}\n\n"
    )

    for item in order["items"]:

        text += (
            f"• {item['name']}\n"
            f"  تعداد: {item['quantity']}\n"
            f"  مبلغ: {format_price(item['subtotal'])}\n\n"
        )

    text += (
        f"💰 مجموع: {format_price(order['total'])}\n"
        f"📌 وضعیت: {status_text(order['status'])}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"order_confirm:{order['id']}"
            ),
            InlineKeyboardButton(
                "❌ لغو",
                callback_data=f"order_cancel:{order['id']}"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 آماده",
                callback_data=f"order_ready:{order['id']}"
            ),
            InlineKeyboardButton(
                "🚚 تحویل",
                callback_data=f"order_delivered:{order['id']}"
            )
        ]
    ]

    try:

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="Markdown"
        )

    except Exception as e:

        logger.error(
            "Admin notification error: %s",
            e
        )

# --------------------------------------------------
# MY ORDERS
# --------------------------------------------------

async def my_orders(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    user_orders = [
        o for o in orders()
        if o["user_id"] == user_id
    ]

    if not user_orders:

        await query.edit_message_text(
            "📦 هنوز سفارشی ثبت نکرده‌اید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛍 محصولات",
                        callback_data="products"
                    )
                ]
            ])
        )

        return

    text = "📦 *سفارش‌های شما*\n\n"

    keyboard = []

    for order in user_orders[-10:]:

        text += (
            f"🧾 `{order['id']}`\n"
            f"💰 {format_price(order['total'])}\n"
            f"📌 {status_text(order['status'])}\n\n"
        )

        keyboard.append([
            InlineKeyboardButton(
                f"🔎 {order['id']}",
                callback_data=f"track:{order['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔙 خانه",
            callback_data="home"
        )
    ])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# TRACK ORDER
# --------------------------------------------------

async def track_order(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    order_id = query.data.split(
        ":",
        1
    )[1]

    order = get_order(
        order_id
    )

    if not order:
        await query.edit_message_text(
            "❌ سفارش پیدا نشد."
        )
        return

    if (
        order["user_id"] != query.from_user.id
        and not is_admin(query.from_user.id)
    ):
        await query.edit_message_text(
            "❌ دسترسی غیرمجاز."
        )
        return

    text = (
        "📦 *جزئیات سفارش*\n\n"
        f"🧾 شماره: `{order['id']}`\n"
        f"💰 مبلغ: {format_price(order['total'])}\n"
        f"📌 وضعیت: {status_text(order['status'])}\n"
        f"💳 پرداخت: {order['payment_status']}\n"
        f"📅 تاریخ: {order['created_at'][:16]}\n\n"
        "🛍 محصولات:\n"
    )

    for item in order["items"]:

        text += (
            f"• {item['name']} × "
            f"{item['quantity']}\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 سفارش‌های من",
                    callback_data="my_orders"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADMIN PANEL
# --------------------------------------------------

async def admin_panel(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 آمار فروش",
                callback_data="admin_stats"
            ),
            InlineKeyboardButton(
                "👥 مشتریان",
                callback_data="admin_customers"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 سفارش‌ها",
                callback_data="admin_orders"
            ),
            InlineKeyboardButton(
                "💳 پرداخت‌ها",
                callback_data="admin_payments"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 محصولات",
                callback_data="admin_products"
            ),
            InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="admin_add_product"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 تغییر قیمت",
                callback_data="admin_price"
            ),
            InlineKeyboardButton(
                "📦 تغییر موجودی",
                callback_data="admin_stock"
            )
        ],
        [
            InlineKeyboardButton(
                "🤖 وضعیت AI",
                callback_data="admin_ai"
            ),
            InlineKeyboardButton(
                "🔐 امنیت",
                callback_data="admin_security"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 خانه",
                callback_data="home"
            )
        ]
    ]

    await query.edit_message_text(
        "⚙️ *پنل مدیریت Mohammadi Fashion*\n\n"
        "یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="Markdown"
    )

    log_admin(
        query.from_user.id,
        "opened admin panel"
    )

# --------------------------------------------------
# ADMIN STATS
# --------------------------------------------------

async def admin_stats(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    all_orders = orders()

    total_orders = len(
        all_orders
    )

    paid_orders = [
        o for o in all_orders
        if o["payment_status"] == "paid"
    ]

    delivered_orders = [
        o for o in all_orders
        if o["status"] == "delivered"
    ]

    revenue = sum(
        o["total"]
        for o in paid_orders
    )

    all_revenue = sum(
        o["total"]
        for o in all_orders
        if o["status"] != "cancelled"
    )

    text = (
        "📊 *آمار فروش*\n\n"
        f"📦 تعداد سفارش‌ها: {total_orders}\n"
        f"💳 پرداخت موفق: {len(paid_orders)}\n"
        f"🚚 تحویل شده: {len(delivered_orders)}\n"
        f"💰 درآمد پرداخت‌شده: {format_price(revenue)}\n"
        f"📈 مجموع سفارش‌های غیرلغوشده: "
        f"{format_price(all_revenue)}\n"
        f"👥 مشتریان: {len(customers())}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 مدیریت",
                    callback_data="admin"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADMIN CUSTOMERS
# --------------------------------------------------

async def admin_customers(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    data = customers()

    if not data:
        text = "👥 هنوز مشتری ثبت نشده است."

    else:

        text = "👥 *مشتریان*\n\n"

        for customer in list(
            data.values()
        )[-20:]:

            text += (
                f"👤 {customer['name']}\n"
                f"📱 {customer.get('phone', '-')}\n"
                f"📦 سفارش: {customer['orders_count']}\n"
                f"💰 خرید: {format_price(customer['total_spent'])}\n\n"
            )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 مدیریت",
                    callback_data="admin"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADMIN PRODUCTS
# --------------------------------------------------

async def admin_products(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    text = "📋 *محصولات*\n\n"

    for p in products():

        text += (
            f"🆔 {p['id']}\n"
            f"👗 {p['name']}\n"
            f"💰 {format_price(p['price'])}\n"
            f"📦 موجودی: {p['stock']}\n\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➕ افزودن",
                    callback_data="admin_add_product"
                )
            ],
            [
                InlineKeyboardButton(
                    "💰 تغییر قیمت",
                    callback_data="admin_price"
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 تغییر موجودی",
                    callback_data="admin_stock"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 مدیریت",
                    callback_data="admin"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADMIN ORDERS
# --------------------------------------------------

async def admin_orders(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    data = orders()

    if not data:

        text = "📦 هیچ سفارشی وجود ندارد."

    else:

        text = "📦 *آخرین سفارش‌ها*\n\n"

        for order in data[-15:][::-1]:

            text += (
                f"🧾 `{order['id']}`\n"
                f"👤 {order['customer_name']}\n"
                f"💰 {format_price(order['total'])}\n"
                f"📌 {status_text(order['status'])}\n"
                f"💳 {order['payment_status']}\n\n"
            )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 مدیریت",
                    callback_data="admin"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADMIN PAYMENTS
# --------------------------------------------------

async def admin_payments(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    data = payments()

    if not data:

        text = "💳 پرداختی ثبت نشده است."

    else:

        text = "💳 *پرداخت‌ها*\n\n"

        for payment in data[-20:][::-1]:

            text += (
                f"🧾 {payment['order_id']}\n"
                f"💰 {format_price(payment['amount'])}\n"
                f"📌 {payment['status']}\n\n"
            )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 مدیریت",
                    callback_data="admin"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADMIN AI
# --------------------------------------------------

async def admin_ai(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    status = (
        "فعال ✅"
        if OPENAI_API_KEY
        else "غیرفعال ❌"
    )

    await query.edit_message_text(
        "🤖 *وضعیت دستیار هوشمند*\n\n"
        f"وضعیت: {status}\n"
        f"مدل: `{OPENAI_MODEL}`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 مدیریت",
                    callback_data="admin"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ADMIN SECURITY
# --------------------------------------------------

async def admin_security(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    await query.edit_message_text(
        "🔐 *امنیت ربات*\n\n"
        "• توکن ربات از Environment خوانده می‌شود.\n"
        "• کلید HesabPay نباید داخل کد قرار گیرد.\n"
        "• دسترسی پنل مدیریت فقط برای ADMIN_ID است.\n"
        "• عملیات مدیر در لاگ ذخیره می‌شود.\n"
        "• برای پرداخت‌ها از Webhook استفاده می‌شود.\n\n"
        "⚠️ اگر توکن قدیمی قبلاً در فایل یا چت منتشر شده، "
        "حتماً آن را در BotFather تعویض کنید.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 مدیریت",
                    callback_data="admin"
                )
            ]
        ]),
        parse_mode="Markdown"
    )

# --------------------------------------------------
# ORDER STATUS
# --------------------------------------------------

async def admin_order_status(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    parts = query.data.split(
        ":"
    )

    action = parts[0]
    order_id = parts[1]

    order = get_order(
        order_id
    )

    if not order:
        await query.edit_message_text(
            "❌ سفارش پیدا نشد."
        )
        return

    mapping = {
        "order_confirm": "confirmed",
        "order_cancel": "cancelled",
        "order_ready": "ready",
        "order_delivered": "delivered"
    }

    new_status = mapping.get(
        action
    )

    if not new_status:
        return

    order["status"] = new_status

    if new_status == "cancelled":
        order["payment_status"] = "cancelled"

    data = orders()

    for index, item in enumerate(data):

        if item["id"] == order_id:
            data[index] = order

    save_json(
        ORDERS_FILE,
        data
    )

    log_admin(
        query.from_user.id,
        f"{order_id} -> {new_status}"
    )

    try:

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"📦 وضعیت سفارش `{order_id}` تغییر کرد.\n\n"
                f"وضعیت جدید: *{status_text(new_status)}*"
            ),
            parse_mode="Markdown"
        )

    except Exception:
        pass

    await query.edit_message_text(
        f"✅ وضعیت سفارش تغییر کرد.\n\n"
        f"🧾 {order_id}\n"
        f"📌 {status_text(new_status)}"
    )

# --------------------------------------------------
# SEARCH
# --------------------------------------------------

async def search_start(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    context.user_data["state"] = (
        "waiting_search"
    )

    await query.edit_message_text(
        "🔎 نام محصول را بنویسید."
    )


async def perform_search(
    update,
    context,
    search_text
):

    result = search_products(
        search_text
    )

    if not result:

        await update.message.reply_text(
            "❌ محصولی پیدا نشد."
        )

        context.user_data["state"] = None
        return

    keyboard = []

    for p in result:

        keyboard.append([
            InlineKeyboardButton(
                f"{p['name']} - {format_price(p['price'])}",
                callback_data=f"product:{p['id']}"
            )
        ])

    await update.message.reply_text(
        "🔎 نتایج جستجو:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )

    context.user_data["state"] = None

# --------------------------------------------------
# CUSTOM ORDER
# --------------------------------------------------

async def custom_order_start(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    context.user_data["state"] = (
        "custom_description"
    )

    await query.edit_message_text(
        "✂️ *سفارش دوخت سفارشی*\n\n"
        "لطفاً توضیح مدل، رنگ، سایز و خواسته‌های خود را بنویسید.",
        parse_mode="Markdown"
    )


async def custom_order_create(
    update,
    context,
    description
):

    user = update.effective_user

    context.user_data["custom_description"] = (
        description
    )

    context.user_data["state"] = (
        "custom_phone"
    )

    await update.message.reply_text(
        "📱 حالا شماره تماس خود را ارسال کنید."
    )


async def finish_custom_order(
    update,
    context,
    phone
):

    user = update.effective_user

    order_id = generate_order_id()

    order = {
        "id": order_id,
        "type": "custom",
        "user_id": user.id,
        "customer_name": user.full_name,
        "username": user.username or "",
        "phone": phone,
        "description": context.user_data.get(
            "custom_description",
            ""
        ),
        "photo": context.user_data.get(
            "custom_photo",
            ""
        ),
        "items": [],
        "total": 0,
        "status": "pending",
        "payment_status": "unpaid",
        "created_at": datetime.now().isoformat()
    }

    data = orders()

    data.append(order)

    save_json(
        ORDERS_FILE,
        data
    )

    await notify_admin_order(
        context,
        order
    )

    await update.message.reply_text(
        f"✅ سفارش دوخت شما ثبت شد.\n\n"
        f"🧾 شماره سفارش: `{order_id}`\n\n"
        "مدیر فروشگاه برای هماهنگی با شما تماس می‌گیرد.",
        parse_mode="Markdown"
    )

    context.user_data["state"] = None
    context.user_data["custom_description"] = None
    context.user_data["custom_photo"] = None

# --------------------------------------------------
# AI ASSISTANT
# --------------------------------------------------

async def ai_answer(
    user,
    message
):

    if not OPENAI_API_KEY:

        return (
            "🤖 دستیار هوشمند هنوز فعال نشده است.\n\n"
            "برای فعال کردن آن باید OPENAI_API_KEY "
            "در فایل .env تنظیم شود."
        )

    try:

        from openai import OpenAI

        client = OpenAI(
            api_key=OPENAI_API_KEY
        )

        product_info = []

        for p in products():

            product_info.append(
                f"{p['name']} | "
                f"{format_price(p['price'])} | "
                f"موجودی: {p['stock']} | "
                f"{p['description']}"
            )

        customer = customers().get(
            str(user.id),
            {}
        )

        system_prompt = f"""
تو دستیار فروشگاه Mohammadi Fashion هستی.

به زبان دری/فارسی ساده و دوستانه جواب بده.

اطلاعات محصولات:
{chr(10).join(product_info)}

اطلاعات مشتری فعلی:
نام: {customer.get('name', '')}
تعداد سفارش: {customer.get('orders_count', 0)}
مجموع خرید: {customer.get('total_spent', 0)}

قوانین:
- درباره قیمت و موجودی فقط بر اساس اطلاعات داده‌شده جواب بده.
- اطلاعات مشتریان دیگر را هرگز فاش نکن.
- اگر چیزی را نمی‌دانی، حدس نزن.
- کاربر را برای ثبت سفارش به ربات راهنمایی کن.
- پاسخ‌ها کوتاه و کاربردی باشند.
"""

        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=system_prompt,
            input=message
        )

        return response.output_text

    except Exception as e:

        logger.error(
            "AI error: %s",
            e
        )

        return (
            "❌ فعلاً دستیار هوشمند نتوانست پاسخ بدهد."
        )

# --------------------------------------------------
# TEXT MESSAGE HANDLER
# --------------------------------------------------

async def text_handler(
    update,
    context
):

    if not update.message:
        return

    user = update.effective_user

    ensure_customer(user)

    text = update.message.text.strip()

    state = context.user_data.get(
        "state"
    )

    # شماره تلفن
    if state == "waiting_phone":

        await create_order(
            update,
            context,
            text
        )

        return

    # جستجو
    if state == "waiting_search":

        await perform_search(
            update,
            context,
            text
        )

        return

    # سفارش دوخت
    if state == "custom_description":

        await custom_order_create(
            update,
            context,
            text
        )

        return

    if state == "custom_phone":

        await finish_custom_order(
            update,
            context,
            text
        )

        return

    # تغییر قیمت
    if state == "admin_price":

        if not is_admin(user.id):
            return

        try:

            parts = text.split()

            product_id = parts[0]
            new_price = float(parts[1])

            data = products()

            found = False

            for p in data:

                if p["id"] == product_id:

                    p["price"] = new_price
                    found = True

            if not found:

                await update.message.reply_text(
                    "❌ محصول پیدا نشد."
                )
                return

            save_json(
                PRODUCTS_FILE,
                data
            )

            context.user_data["state"] = None

            log_admin(
                user.id,
                f"price changed {product_id} -> {new_price}"
            )

            await update.message.reply_text(
                "✅ قیمت با موفقیت تغییر کرد."
            )

        except Exception:

            await update.message.reply_text(
                "فرمت صحیح:\n"
                "`product_id price`\n\n"
                "مثال:\n"
                "`p001 3000`",
                parse_mode="Markdown"
            )

        return

    # تغییر موجودی
    if state == "admin_stock":

        if not is_admin(user.id):
            return

        try:

            parts = text.split()

            product_id = parts[0]
            new_stock = int(parts[1])

            data = products()

            found = False

            for p in data:

                if p["id"] == product_id:

                    p["stock"] = new_stock
                    found = True

            if not found:

                await update.message.reply_text(
                    "❌ محصول پیدا نشد."
                )
                return

            save_json(
                PRODUCTS_FILE,
                data
            )

            context.user_data["state"] = None

            log_admin(
                user.id,
                f"stock changed {product_id} -> {new_stock}"
            )

            await update.message.reply_text(
                "✅ موجودی تغییر کرد."
            )

        except Exception:

            await update.message.reply_text(
                "فرمت صحیح:\n"
                "`product_id stock`\n\n"
                "مثال:\n"
                "`p001 10`",
                parse_mode="Markdown"
            )

        return

    # AI
    answer = await ai_answer(
        user,
        text
    )

    await update.message.reply_text(
        answer
    )

# --------------------------------------------------
# PHOTO HANDLER
# --------------------------------------------------

async def photo_handler(
    update,
    context
):

    if context.user_data.get(
        "state"
    ) == "custom_photo":

        photo = update.message.photo[-1]

        file = await photo.get_file()

        file_path = (
            DATA_DIR /
            f"custom_{update.effective_user.id}_{uuid.uuid4()}.jpg"
        )

        await file.download_to_drive(
            str(file_path)
        )

        context.user_data["custom_photo"] = str(
            file_path
        )

        context.user_data["state"] = (
            "custom_phone"
        )

        await update.message.reply_text(
            "📱 عکس دریافت شد.\n\n"
            "حالا شماره تماس خود را ارسال کنید."
        )

# --------------------------------------------------
# CALLBACK ROUTER
# --------------------------------------------------

async def callback_router(
    update,
    context
):

    query = update.callback_query

    data = query.data

    if data == "home":

        await query.answer()

        keyboard = [
            [
                InlineKeyboardButton(
                    "🛍 محصولات",
                    callback_data="products"
                ),
                InlineKeyboardButton(
                    "🛒 سبد خرید",
                    callback_data="cart"
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 سفارش‌های من",
                    callback_data="my_orders"
                ),
                InlineKeyboardButton(
                    "🔎 جستجو",
                    callback_data="search"
                )
            ],
            [
                InlineKeyboardButton(
                    "✂️ سفارش دوخت",
                    callback_data="custom_order"
                )
            ],
            [
                InlineKeyboardButton(
                    "🤖 دستیار هوشمند",
                    callback_data="ai"
                )
            ]
        ]

        if is_admin(
            query.from_user.id
        ):
            keyboard.append([
                InlineKeyboardButton(
                    "⚙️ پنل مدیریت",
                    callback_data="admin"
                )
            ])

        await query.edit_message_text(
            "👗 *Mohammadi Fashion*\n\n"
            "به فروشگاه خوش آمدید.",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="Markdown"
        )

        return

    if data == "products":
        await show_products(
            update,
            context
        )
        return

    if data.startswith("product:"):
        await product_detail(
            update,
            context
        )
        return

    if data.startswith("add:"):
        await add_to_cart(
            update,
            context
        )
        return

    if data == "cart":
        await show_cart(
            update,
            context
        )
        return

    if data == "clear_cart":
        await clear_cart(
            update,
            context
        )
        return

    if data == "checkout":
        await checkout(
            update,
            context
        )
        return

    if data == "my_orders":
        await my_orders(
            update,
            context
        )
        return

    if data.startswith("track:"):
        await track_order(
            update,
            context
        )
        return

    if data == "search":
        await search_start(
            update,
            context
        )
        return

    if data == "custom_order":
        await custom_order_start(
            update,
            context
        )
        return

    if data == "ai":

        await query.answer()

        context.user_data["state"] = "ai"

        await query.edit_message_text(
            "🤖 سوال خود را درباره محصولات، "
            "قیمت، موجودی یا سفارش بنویسید."
        )

        return

    if data == "admin":

        await admin_panel(
            update,
            context
        )

        return

    if data == "admin_stats":

        await admin_stats(
            update,
            context
        )

        return

    if data == "admin_customers":

        await admin_customers(
            update,
            context
        )

        return

    if data == "admin_products":

        await admin_products(
            update,
            context
        )

        return

    if data == "admin_orders":

        await admin_orders(
            update,
            context
        )

        return

    if data == "admin_payments":

        await admin_payments(
            update,
            context
        )

        return

    if data == "admin_ai":

        await admin_ai(
            update,
            context
        )

        return

    if data == "admin_security":

        await admin_security(
            update,
            context
        )

        return

    if data == "admin_price":

        if not is_admin(
            query.from_user.id
        ):
            return

        await query.answer()

        context.user_data["state"] = (
            "admin_price"
        )

        await query.edit_message_text(
            "💰 تغییر قیمت\n\n"
            "فرمت:\n"
            "`product_id price`\n\n"
            "مثال:\n"
            "`p001 3000`",
            parse_mode="Markdown"
        )

        return

    if data == "admin_stock":

        if not is_admin(
            query.from_user.id
        ):
            return

        await query.answer()

        context.user_data["state"] = (
            "admin_stock"
        )

        await query.edit_message_text(
            "📦 تغییر موجودی\n\n"
            "فرمت:\n"
            "`product_id stock`\n\n"
            "مثال:\n"
            "`p001 10`",
            parse_mode="Markdown"
        )

        return

    if data == "admin_add_product":

        if not is_admin(
            query.from_user.id
        ):
            return

        await query.answer()

        context.user_data["state"] = (
            "admin_add_product"
        )

        await query.edit_message_text(
            "➕ برای افزودن محصول، اطلاعات را این‌طور بفرست:\n\n"
            "`نام | دسته | توضیحات | قیمت | موجودی`\n\n"
            "مثال:\n"
            "`لباس آبی | majlesi | لباس مجلسی آبی | 2500 | 5`",
            parse_mode="Markdown"
        )

        return

    if data.startswith("order_confirm:") or \
       data.startswith("order_cancel:") or \
       data.startswith("order_ready:") or \
       data.startswith("order_delivered:"):

        await admin_order_status(
            update,
            context
        )

        return

# --------------------------------------------------
# ADD PRODUCT TEXT
# --------------------------------------------------

async def admin_add_product_text(
    update,
    context
):

    if not is_admin(
        update.effective_user.id
    ):
        return

    text = update.message.text

    parts = [
        x.strip()
        for x in text.split("|")
    ]

    if len(parts) != 5:

        await update.message.reply_text(
            "❌ فرمت نادرست است.\n\n"
            "مثال:\n"
            "`لباس آبی | majlesi | توضیحات | 2500 | 5`",
            parse_mode="Markdown"
        )
        return

    try:

        name = parts[0]
        category = parts[1]
        description = parts[2]
        price = float(parts[3])
        stock = int(parts[4])

        product = {
            "id": "p" + str(uuid.uuid4())[:8],
            "name": name,
            "category": category,
            "description": description,
            "price": price,
            "stock": stock,
            "photo": ""
        }

        data = products()

        data.append(
            product
        )

        save_json(
            PRODUCTS_FILE,
            data
        )

        context.user_data["state"] = None

        log_admin(
            update.effective_user.id,
            f"added product {product['id']}"
        )

        await update.message.reply_text(
            "✅ محصول با موفقیت اضافه شد.\n\n"
            f"نام: {name}\n"
            f"قیمت: {format_price(price)}\n"
            f"موجودی: {stock}"
        )

    except Exception as e:

        logger.error(e)

        await update.message.reply_text(
            "❌ اطلاعات محصول صحیح نیست."
        )

# --------------------------------------------------
# UNIVERSAL TEXT ROUTER
# --------------------------------------------------

async def universal_text_handler(
    update,
    context
):

    state = context.user_data.get(
        "state"
    )

    if state == "admin_add_product":

        await admin_add_product_text(
            update,
            context
        )

        return

    if state == "ai":

        answer = await ai_answer(
            update.effective_user,
            update.message.text
        )

        await update.message.reply_text(
            answer
        )

        return

    await text_handler(
        update,
        context
    )

# --------------------------------------------------
# FLASK
# --------------------------------------------------

app = Flask(
    __name__
)


@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "Mohammadi Fashion Bot"
    })


@app.post("/webhooks/hesabpay")
def hesabpay_webhook():

    # امنیت پایه
    if HESABPAY_WEBHOOK_TOKEN:

        incoming = request.headers.get(
            "X-Webhook-Token",
            ""
        )

        if incoming != HESABPAY_WEBHOOK_TOKEN:

            return jsonify({
                "error": "unauthorized"
            }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        logger.info(
            "HesabPay webhook: %s",
            data
        )

        event = data.get(
            "event",
            data.get(
                "type",
                ""
            )
        )

        payload = data.get(
            "data",
            data
        )

        order_id = (
            payload.get("order_id")
            or payload.get("reference")
            or payload.get("merchant_reference")
        )

        if not order_id:

            return jsonify({
                "status": "ignored"
            })

        if event in (
            "payment_success",
            "payment.success",
            "success"
        ):

            update_payment_status(
                order_id,
                "paid"
            )

        elif event in (
            "payment_failure",
            "payment.failed",
            "failure"
        ):

            update_payment_status(
                order_id,
                "failed"
            )

        return jsonify({
            "status": "ok"
        })

    except Exception as e:

        logger.exception(e)

        return jsonify({
            "error": "server_error"
        }), 500


def update_payment_status(
    order_id,
    status
):

    payment_data = payments()

    for payment in payment_data:

        if payment["order_id"] == order_id:

            payment["status"] = status

    save_json(
        PAYMENTS_FILE,
        payment_data
    )

    order_data = orders()

    for order in order_data:

        if order["id"] == order_id:

            if status == "paid":

                order["payment_status"] = "paid"

                if order["status"] == "pending":
                    order["status"] = "paid"

            elif status == "failed":

                order["payment_status"] = "failed"

    save_json(
        ORDERS_FILE,
        order_data
    )

# --------------------------------------------------
# FLASK THREAD
# --------------------------------------------------

def run_flask():

    app.run(
        host=WEBHOOK_HOST,
        port=WEBHOOK_PORT,
        debug=False,
        use_reloader=False
    )

# --------------------------------------------------
# ERROR HANDLER
# --------------------------------------------------

async def error_handler(
    update,
    context
):

    logger.error(
        "Bot error: %s",
        context.error
    )

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN در .env تنظیم نشده است."
        )

    if not ADMIN_ID:

        raise RuntimeError(
            "ADMIN_ID در .env تنظیم نشده است."
        )

    logger.info(
        "Starting Mohammadi Fashion..."
    )

    # Flask برای health/webhook
    flask_thread = threading.Thread(
        target=run_flask,
        daemon=True
    )

    flask_thread.start()

    # Telegram
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            universal_text_handler
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot is running..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
