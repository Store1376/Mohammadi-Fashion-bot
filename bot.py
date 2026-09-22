import os
import json
import threading
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, jsonify, request

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

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

HESABPAY_API_KEY = os.getenv("HESABPAY_API_KEY", "").strip()

HESABPAY_API_URL = os.getenv(
    "HESABPAY_API_URL",
    "https://api.hesab.com/api/v1/payment/create-session",
).strip()

HESABPAY_SUCCESS_URL = os.getenv(
    "HESABPAY_SUCCESS_URL",
    "",
).strip()

HESABPAY_FAILURE_URL = os.getenv(
    "HESABPAY_FAILURE_URL",
    "",
).strip()

HESABPAY_WEBHOOK_TOKEN = os.getenv(
    "HESABPAY_WEBHOOK_TOKEN",
    "",
).strip()

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
).strip()

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5",
).strip()

WEBHOOK_HOST = os.getenv(
    "WEBHOOK_HOST",
    "0.0.0.0",
).strip()
RENDER_URL = os.getenv("RENDER_URL", "https://mohammadi-fashion-bot.onrender.com").strip()

# مهم برای Render
WEBHOOK_PORT = int(
    os.getenv("PORT", "10000")
    WEBHOOK_PATH = "/telegram-webhook"
)

DATA_DIR = Path(
    os.getenv("DATA_DIR", ".")
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# FILES
# ============================================================

PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
PAYMENTS_FILE = DATA_DIR / "payments.json"
ADMIN_LOG_FILE = DATA_DIR / "admin_log.json"


# ============================================================
# STATUS
# ============================================================

STATUS_NEW = "جدید"
STATUS_CONFIRMED = "تایید شده"
STATUS_READY = "آماده"
STATUS_DELIVERED = "تحویل شده"
STATUS_CANCELLED = "لغو شده"

ORDER_STATUSES = [
    STATUS_NEW,
    STATUS_CONFIRMED,
    STATUS_READY,
    STATUS_DELIVERED,
    STATUS_CANCELLED,
]


# ============================================================
# STORAGE
# ============================================================

def load_json(path, default):
    try:
        if not path.exists():
            return default

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)

    except Exception as e:
        print(f"JSON LOAD ERROR {path}: {e}")
        return default


def save_json(path, data):
    try:
        temp_path = Path(str(path) + ".tmp")

        with open(
            temp_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

        temp_path.replace(path)

    except Exception as e:
        print(f"JSON SAVE ERROR {path}: {e}")


def load_products():
    return load_json(PRODUCTS_FILE, [])


def save_products(data):
    save_json(PRODUCTS_FILE, data)


def load_orders():
    return load_json(ORDERS_FILE, [])


def save_orders(data):
    save_json(ORDERS_FILE, data)


def load_customers():
    return load_json(CUSTOMERS_FILE, [])


def save_customers(data):
    save_json(CUSTOMERS_FILE, data)


def load_payments():
    return load_json(PAYMENTS_FILE, [])


def save_payments(data):
    save_json(PAYMENTS_FILE, data)


def load_admin_log():
    return load_json(ADMIN_LOG_FILE, [])


def save_admin_log(data):
    save_json(ADMIN_LOG_FILE, data)


# ============================================================
# HELPERS
# ============================================================

def now_text():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def next_id(items, prefix):
    numbers = []

    for item in items:
        value = str(item.get("id", ""))

        digits = "".join(
            c for c in value if c.isdigit()
        )

        if digits:
            try:
                numbers.append(int(digits))
            except Exception:
                pass

    number = max(numbers, default=0) + 1

    return f"{prefix}{number:04d}"


def price_number(value):
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return 0.0


def fmt_money(value):
    amount = price_number(value)

    if amount.is_integer():
        return f"{int(amount):,}"

    return f"{amount:,.2f}"


def normalize_product(product):
    product.setdefault("id", "")
    product.setdefault("name", "بدون نام")
    product.setdefault("category", "عمومی")
    product.setdefault("price", 0)
    product.setdefault("stock", 0)
    product.setdefault("description", "")
    product.setdefault("photo", "")

    return product


def get_product(product_id):
    products = load_products()

    for product in products:
        if str(product.get("id")) == str(product_id):
            return normalize_product(product)

    return None


def is_admin(user_id):
    try:
        return (
            str(user_id) == str(ADMIN_ID)
            and str(ADMIN_ID) != ""
            and str(ADMIN_ID) != "0"
        )
    except Exception:
        return False


# ============================================================
# ADMIN LOG
# ============================================================

def log_admin(user_id, action):
    logs = load_admin_log()

    logs.append({
        "user_id": str(user_id),
        "action": action,
        "time": now_text(),
    })

    save_admin_log(logs)


# ============================================================
# CUSTOMERS
# ============================================================

def upsert_customer(user):
    customers = load_customers()

    user_id = str(user.id)

    found = None

    for customer in customers:
        if str(customer.get("user_id")) == user_id:
            found = customer
            break

    if found:
        found["first_name"] = user.first_name or ""
        found["last_name"] = user.last_name or ""
        found["username"] = user.username or ""
        found["last_seen"] = now_text()
    else:
        customers.append({
            "user_id": user_id,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or "",
            "phone": "",
            "orders": 0,
            "total_spent": 0,
            "created_at": now_text(),
            "last_seen": now_text(),
        })

    save_customers(customers)


def update_customer_after_order(user_id, total):
    customers = load_customers()

    for customer in customers:
        if str(customer.get("user_id")) == str(user_id):
            customer["orders"] = int(
                customer.get("orders", 0)
            ) + 1

            customer["total_spent"] = (
                price_number(customer.get("total_spent", 0))
                + price_number(total)
            )

            break

    save_customers(customers)


# ============================================================
# KEYBOARDS
# ============================================================

def home_keyboard(user_id):
    rows = [
        [
            InlineKeyboardButton(
                "👔 مجلسی",
                callback_data="majlesi",
            ),
            InlineKeyboardButton(
                "👗 سرپتلونی",
                callback_data="sarpatloni",
            ),
        ],
        [
            InlineKeyboardButton(
                "🛒 سبد خرید",
                callback_data="cart",
            ),
            InlineKeyboardButton(
                "📦 سفارش‌های من",
                callback_data="my_orders",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔎 جستجوی محصول",
                callback_data="search",
            ),
            InlineKeyboardButton(
                "🤖 دستیار هوشمند",
                callback_data="ai_help",
            ),
        ],
        [
            InlineKeyboardButton(
                "🧵 دوخت سفارشی",
                callback_data="dokht",
            ),
            InlineKeyboardButton(
                "💳 پرداخت",
                callback_data="payment_info",
            ),
        ],
        [
            InlineKeyboardButton(
                "📞 تماس با ما",
                callback_data="contact",
            ),
        ],
    ]

    if is_admin(user_id):
        rows.append([
            InlineKeyboardButton(
                "⚙️ پنل مدیریت",
                callback_data="admin",
            )
        ])

    return InlineKeyboardMarkup(rows)


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 آمار فروش",
                callback_data="admin_stats",
            ),
            InlineKeyboardButton(
                "👥 مشتریان",
                callback_data="admin_customers",
            ),
        ],
        [
            InlineKeyboardButton(
                "📦 موجودی",
                callback_data="admin_stock",
            ),
            InlineKeyboardButton(
                "🛍 محصولات",
                callback_data="admin_products",
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="add_product",
            ),
            InlineKeyboardButton(
                "💰 تغییر قیمت",
                callback_data="change_price",
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 تغییر موجودی",
                callback_data="change_stock",
            ),
            InlineKeyboardButton(
                "🗑 حذف محصول",
                callback_data="delete_product",
            ),
        ],
        [
            InlineKeyboardButton(
                "🆕 سفارش‌های جدید",
                callback_data="admin_orders",
            ),
            InlineKeyboardButton(
                "💳 پرداخت‌ها",
                callback_data="admin_payments",
            ),
        ],
        [
            InlineKeyboardButton(
                "🤖 وضعیت AI",
                callback_data="admin_ai",
            ),
            InlineKeyboardButton(
                "🔐 امنیت",
                callback_data="admin_security",
            ),
        ],
        [
            InlineKeyboardButton(
                "🏠 خانه",
                callback_data="home",
            ),
        ],
    ])


def back_admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ برگشت",
                callback_data="admin",
            )
        ]
    ])


def product_keyboard(product_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛒 افزودن به سبد",
                callback_data=f"addcart_{product_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 خانه",
                callback_data="home",
            )
        ],
    ])


def admin_order_keyboard(order_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"status_{order_id}_{STATUS_CONFIRMED}",
            )
        ],
        [
            InlineKeyboardButton(
                "📦 آماده",
                callback_data=f"status_{order_id}_{STATUS_READY}",
            )
        ],
        [
            InlineKeyboardButton(
                "🚚 تحویل",
                callback_data=f"status_{order_id}_{STATUS_DELIVERED}",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data=f"status_{order_id}_{STATUS_CANCELLED}",
            )
        ],
    ])


# ============================================================
# ORDERS
# ============================================================

def order_total(order):
    return sum(
        price_number(item.get("price", 0))
        * int(item.get("quantity", 1))
        for item in order.get("items", [])
    )


def make_order(user, items, phone=""):
    orders = load_orders()

    order = {
        "id": next_id(orders, "ORD"),
        "user_id": str(user.id),
        "name": (
            f"{user.first_name or ''} "
            f"{user.last_name or ''}"
        ).strip(),
        "username": user.username or "",
        "phone": phone,
        "items": items,
        "total": 0,
        "status": STATUS_NEW,
        "payment_status": "pending",
        "created_at": now_text(),
    }

    order["total"] = order_total(order)

    orders.append(order)
    save_orders(orders)

    update_customer_after_order(
        user.id,
        order["total"],
    )

    return order


async def send_professional_order_notification(
    context,
    order,
):
    if not ADMIN_ID:
        return

    lines = [
        "🛍️ سفارش جدید",
        "",
        f"🆔 شماره سفارش: {order['id']}",
        f"👤 مشتری: {order.get('name', '')}",
        f"📱 تلفن: {order.get('phone', '')}",
        "",
    ]

    for item in order.get("items", []):
        lines.append(
            f"• {item.get('name')} × "
            f"{item.get('quantity', 1)}"
        )

    lines.extend([
        "",
        f"💰 مبلغ کل: {fmt_money(order['total'])} افغانی",
        f"📌 وضعیت: {order['status']}",
        f"🕐 زمان: {order['created_at']}",
    ])

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="\n".join(lines),
            reply_markup=admin_order_keyboard(
                order["id"]
            ),
        )
    except Exception as e:
        print(
            f"ADMIN NOTIFICATION ERROR: {e}"
        )


async def notify_customer_status(
    context,
    order,
):
    messages = {
        STATUS_CONFIRMED:
            "✅ سفارش شما تایید شد.",
        STATUS_READY:
            "📦 سفارش شما آماده است.",
        STATUS_DELIVERED:
            "🚚 سفارش شما تحویل داده شد.",
        STATUS_CANCELLED:
            "❌ سفارش شما لغو شد.",
    }

    message = messages.get(
        order.get("status")
    )

    if not message:
        return

    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"{message}\n\n"
                f"🆔 سفارش: {order['id']}"
            ),
        )
    except Exception as e:
        print(
            f"CUSTOMER STATUS ERROR: {e}"
        )


# ============================================================
# HESABPAY
# ============================================================

def hesabpay_configured():
    return bool(
        HESABPAY_API_KEY
        and HESABPAY_API_URL
    )


def create_hesabpay_session(order):
    if not hesabpay_configured():
        return None

    payload = {
        "amount": order["total"],
        "currency": "AFN",
        "order_id": order["id"],
        "success_url": HESABPAY_SUCCESS_URL,
        "failure_url": HESABPAY_FAILURE_URL,
    }

    headers = {
        "Authorization": (
            f"Bearer {HESABPAY_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            HESABPAY_API_URL,
            json=payload,
            headers=headers,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        payment_url = (
            data.get("payment_url")
            or data.get("url")
            or data.get("checkout_url")
            or data.get("data", {}).get("payment_url")
            or data.get("data", {}).get("url")
        )

        return {
            "success": True,
            "url": payment_url,
            "response": data,
        }

    except Exception as e:
        print(
            f"HESABPAY ERROR: {e}"
        )

        return {
            "success": False,
            "error": str(e),
        }


def save_payment(
    order_id,
    amount,
    status="pending",
    transaction_id="",
):
    payments = load_payments()

    payments.append({
        "id": next_id(
            payments,
            "PAY",
        ),
        "order_id": order_id,
        "amount": amount,
        "status": status,
        "transaction_id": transaction_id,
        "created_at": now_text(),
    })

    save_payments(payments)


# ============================================================
# AI
# ============================================================

def ai_enabled():
    return bool(
        OPENAI_API_KEY
        and OpenAI is not None
    )


def build_store_context():
    products = load_products()

    if not products:
        return "در حال حاضر محصولی ثبت نشده است."

    lines = []

    for product in products:
        product = normalize_product(product)

        lines.append(
            f"""
نام: {product['name']}
دسته: {product['category']}
قیمت: {fmt_money(product['price'])} افغانی
موجودی: {product['stock']}
توضیحات: {product['description']}
"""
        )

    return "\n".join(lines)


def ai_reply(message):
    if not ai_enabled():
        return (
            "🤖 دستیار هوشمند فعلاً فعال نیست.\n"
            "مدیر باید OPENAI_API_KEY را در Render تنظیم کند."
        )

    try:
        client = OpenAI(
            api_key=OPENAI_API_KEY
        )

        system_prompt = f"""
تو دستیار هوشمند فروشگاه Mohammadi Fashion هستی.

با مشتری به زبان دری ساده و محترمانه صحبت کن.
در مورد محصولات، قیمت، موجودی و سفارش کمک کن.
اطلاعات ساختگی درباره قیمت یا موجودی نده.

محصولات فعلی فروشگاه:

{build_store_context()}
"""

        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=system_prompt,
            input=message,
        )

        text = getattr(
            response,
            "output_text",
            None,
        )

        if text:
            return text

        return (
            "متأسفانه جواب هوشمند دریافت نشد."
        )

    except Exception as e:
        print(
            f"OPENAI ERROR: {e}"
        )

        return (
            "⚠️ دستیار هوشمند موقتاً با مشکل مواجه شده است."
        )


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    user = update.effective_user

    upsert_customer(user)

    text = (
        "👋 سلام و خوش آمدید به "
        "Mohammadi Fashion\n\n"
        "🛍️ خرید و فروش لباس\n"
        "🧵 دوخت سفارشی\n"
        "💳 پرداخت آنلاین\n"
        "🤖 دستیار هوشمند\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    await update.message.reply_text(
        text,
        reply_markup=home_keyboard(
            user.id
        ),
    )


# ============================================================
# SHOW PRODUCT
# ============================================================

async def show_product(
    query,
    product,
):
    product = normalize_product(product)

    text = (
        f"🛍️ {product['name']}\n\n"
        f"📂 دسته: {product['category']}\n"
        f"💰 قیمت: {fmt_money(product['price'])} افغانی\n"
        f"📦 موجودی: {product['stock']}\n\n"
        f"📝 {product['description'] or 'بدون توضیحات'}"
    )

    if product.get("photo"):
        try:
            await query.message.reply_photo(
                photo=product["photo"],
                caption=text,
                reply_markup=product_keyboard(
                    product["id"]
                ),
            )
            return
        except Exception:
            pass

    await query.message.reply_text(
        text,
        reply_markup=product_keyboard(
            product["id"]
        ),
    )


# ============================================================
# CART
# ============================================================

async def show_cart(
    query,
    context,
):
    cart = context.user_data.get(
        "cart",
        [],
    )

    if not cart:
        await query.message.reply_text(
            "🛒 سبد خرید شما خالی است.",
            reply_markup=home_keyboard(
                query.from_user.id
            ),
        )
        return

    total = 0
    lines = [
        "🛒 سبد خرید شما",
        "",
    ]

    for item in cart:
        subtotal = (
            price_number(item["price"])
            * item["quantity"]
        )

        total += subtotal

        lines.append(
            f"• {item['name']} × "
            f"{item['quantity']} = "
            f"{fmt_money(subtotal)} افغانی"
        )

    lines.extend([
        "",
        f"💰 مجموع: {fmt_money(total)} افغانی",
    ])

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ ثبت سفارش",
                callback_data="checkout_cart",
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ پاک کردن سبد",
                callback_data="clear_cart",
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 خانه",
                callback_data="home",
            )
        ],
    ])

    await query.message.reply_text(
        "\n".join(lines),
        reply_markup=keyboard,
    )


# ============================================================
# CALLBACK BUTTONS
# ============================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    # جلوگیری از خطای:
    # Query is too old...
    try:
        await query.answer()
    except Exception as e:
        print(
            f"Callback query warning: {e}"
        )

    data = query.data
    user_id = query.from_user.id

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "home":
        await query.message.reply_text(
            "🏠 منوی اصلی",
            reply_markup=home_keyboard(
                user_id
            ),
        )
        return

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    if data == "ai_help":
        context.user_data["ai_mode"] = True

        await query.message.reply_text(
            "🤖 دستیار هوشمند فعال شد.\n\n"
            "سوال خود را بفرستید.\n"
            "برای خروج از حالت هوشمند، /start را بزنید."
        )
        return

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    if data in ["majlesi", "sarpatloni"]:
        category_map = {
            "majlesi": "مجلسی",
            "sarpatloni": "سرپتلونی",
        }

        category = category_map[data]

        products = load_products()

        products = [
            normalize_product(p)
            for p in products
            if str(
                p.get("category", "")
            ).strip() == category
        ]

        if not products:
            await query.message.reply_text(
                f"برای دسته «{category}» "
                "محصولی موجود نیست.",
                reply_markup=home_keyboard(
                    user_id
                ),
            )
            return

        for product in products:
            text = (
                f"🛍️ {product['name']}\n"
                f"💰 {fmt_money(product['price'])} افغانی\n"
                f"📦 موجودی: {product['stock']}"
            )

            if product.get("photo"):
                try:
                    await query.message.reply_photo(
                        photo=product["photo"],
                        caption=text,
                        reply_markup=product_keyboard(
                            product["id"]
                        ),
                    )
                    continue
                except Exception:
                    pass

            await query.message.reply_text(
                text,
                reply_markup=product_keyboard(
                    product["id"]
                ),
            )

        return

    # --------------------------------------------------------
    # PRODUCT
    # --------------------------------------------------------

    if data.startswith("product_"):
        product_id = data.split(
            "_",
            1,
        )[1]

        product = get_product(
            product_id
        )

        if not product:
            await query.message.reply_text(
                "❌ محصول پیدا نشد."
            )
            return

        await show_product(
            query,
            product,
        )
        return

    # --------------------------------------------------------
    # ADD TO CART
    # --------------------------------------------------------

    if data.startswith("addcart_"):
        product_id = data.split(
            "_",
            1,
        )[1]

        product = get_product(
            product_id
        )

        if not product:
            await query.message.reply_text(
                "❌ محصول پیدا نشد."
            )
            return

        stock = int(
            product.get("stock", 0)
        )

        if stock <= 0:
            await query.message.reply_text(
                "❌ این محصول فعلاً موجود نیست."
            )
            return

        cart = context.user_data.setdefault(
            "cart",
            [],
        )

        found = None

        for item in cart:
            if str(item["id"]) == str(product_id):
                found = item
                break

        if found:
            if found["quantity"] >= stock:
                await query.message.reply_text(
                    "❌ بیشتر از موجودی نمی‌توانید اضافه کنید."
                )
                return

            found["quantity"] += 1

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
                [
                    InlineKeyboardButton(
                        "🛒 مشاهده سبد",
                        callback_data="cart",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 خانه",
                        callback_data="home",
                    )
                ],
            ]),
        )
        return

    # --------------------------------------------------------
    # CART
    # --------------------------------------------------------

    if data == "cart":
        await show_cart(
            query,
            context,
        )
        return

    if data == "clear_cart":
        context.user_data["cart"] = []

        await query.message.reply_text(
            "🗑️ سبد خرید پاک شد.",
            reply_markup=home_keyboard(
                user_id
            ),
        )
        return

    if data == "checkout_cart":
        cart = context.user_data.get(
            "cart",
            [],
        )

        if not cart:
            await query.message.reply_text(
                "🛒 سبد خرید خالی است."
            )
            return

        # دوباره موجودی بررسی می‌شود
        for item in cart:
            product = get_product(
                item["id"]
            )

            if not product:
                await query.message.reply_text(
                    f"❌ محصول {item['name']} دیگر موجود نیست."
                )
                return

            if int(product["stock"]) < int(
                item["quantity"]
            ):
                await query.message.reply_text(
                    f"❌ موجودی {item['name']} کافی نیست."
                )
                return

        context.user_data["order_step"] = "phone"

        await query.message.reply_text(
            "📱 لطفاً شماره تماس خود را ارسال کنید.\n\n"
            "مثال:\n"
            "07XXXXXXXX"
        )
        return

    # --------------------------------------------------------
    # MY ORDERS
    # --------------------------------------------------------

    if data == "my_orders":
        orders = load_orders()

        mine = [
            o for o in orders
            if str(o.get("user_id"))
            == str(user_id)
        ]

        if not mine:
            await query.message.reply_text(
                "📦 هنوز سفارشی ثبت نکرده‌اید.",
                reply_markup=home_keyboard(
                    user_id
                ),
            )
            return

        lines = [
            "📦 سفارش‌های شما",
            "",
        ]

        for order in mine[-10:]:
            lines.extend([
                f"🆔 {order['id']}",
                f"💰 {fmt_money(order['total'])} افغانی",
                f"📌 {order['status']}",
                f"💳 پرداخت: {order.get('payment_status', 'pending')}",
                f"🕐 {order['created_at']}",
                "",
            ])

        await query.message.reply_text(
            "\n".join(lines),
            reply_markup=home_keyboard(
                user_id
            ),
        )
        return

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if data == "search":
        context.user_data["search_mode"] = True

        await query.message.reply_text(
            "🔎 نام محصول را ارسال کنید."
        )
        return

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    if data == "payment_info":
        await query.message.reply_text(
            "💳 روش پرداخت\n\n"
            "پرداخت آنلاین از طریق HesabPay انجام می‌شود.\n\n"
            "بعد از ثبت سفارش، در صورت فعال بودن "
            "تنظیمات HesabPay، دکمه پرداخت برای شما ارسال می‌شود.",
            reply_markup=home_keyboard(
                user_id
            ),
        )
        return

    # --------------------------------------------------------
    # CUSTOM SEWING
    # --------------------------------------------------------

    if data == "dokht":
        context.user_data["custom_step"] = "description"

        await query.message.reply_text(
            "🧵 سفارش دوخت سفارشی\n\n"
            "لطفاً توضیحات لباس مورد نظر خود را ارسال کنید."
        )
        return

    # --------------------------------------------------------
    # CONTACT
    # --------------------------------------------------------

    if data == "contact":
        await query.message.reply_text(
            "📞 ارتباط با ما\n\n"
            "WhatsApp: +93 744 763 112\n"
            "Telegram: @Rohullah1375\n\n"
            "💳 پرداخت: HesabPay",
            reply_markup=home_keyboard(
                user_id
            ),
        )
        return

    # ========================================================
    # ADMIN
    # ========================================================

    if data == "admin":
        if not is_admin(user_id):
            await query.message.reply_text(
                "⛔ دسترسی غیرمجاز."
            )
            return

        log_admin(
            user_id,
            "باز کردن پنل مدیریت",
        )

        await query.message.reply_text(
            "⚙️ پنل مدیریت",
            reply_markup=admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADMIN STATS
    # --------------------------------------------------------

    if data == "admin_stats":
        if not is_admin(user_id):
            return

        orders = load_orders()
        customers = load_customers()

        delivered = [
            o for o in orders
            if o.get("status")
            == STATUS_DELIVERED
        ]

        sales = sum(
            price_number(o.get("total", 0))
            for o in delivered
        )

        total_orders = len(orders)

        await query.message.reply_text(
            "📊 آمار فروش\n\n"
            f"📦 کل سفارش‌ها: {total_orders}\n"
            f"👥 مشتریان: {len(customers)}\n"
            f"🚚 سفارش‌های تحویل‌شده: {len(delivered)}\n"
            f"💰 فروش تحویل‌شده: {fmt_money(sales)} افغانی",
            reply_markup=back_admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADMIN CUSTOMERS
    # --------------------------------------------------------

    if data == "admin_customers":
        if not is_admin(user_id):
            return

        customers = load_customers()

        if not customers:
            await query.message.reply_text(
                "👥 هنوز مشتری ثبت نشده است.",
                reply_markup=back_admin_keyboard(),
            )
            return

        lines = [
            "👥 مشتریان",
            "",
        ]

        for customer in customers[-30:]:
            name = (
                f"{customer.get('first_name', '')} "
                f"{customer.get('last_name', '')}"
            ).strip()

            if not name:
                name = "بدون نام"

            lines.append(
                f"• {name} | "
                f"سفارش: {customer.get('orders', 0)} | "
                f"مصرف: {fmt_money(customer.get('total_spent', 0))}"
            )

        await query.message.reply_text(
            "\n".join(lines),
            reply_markup=back_admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADMIN STOCK
    # --------------------------------------------------------

    if data == "admin_stock":
        if not is_admin(user_id):
            return

        products = load_products()

        if not products:
            await query.message.reply_text(
                "📦 محصولی وجود ندارد.",
                reply_markup=back_admin_keyboard(),
            )
            return

        lines = [
            "📦 موجودی محصولات",
            "",
        ]

        for product in products:
            lines.append(
                f"• {product['name']} — "
                f"{product['stock']} عدد"
            )

        await query.message.reply_text(
            "\n".join(lines),
            reply_markup=back_admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADMIN PRODUCTS
    # --------------------------------------------------------

    if data == "admin_products":
        if not is_admin(user_id):
            return

        products = load_products()

        if not products:
            await query.message.reply_text(
                "🛍️ محصولی ثبت نشده است.",
                reply_markup=back_admin_keyboard(),
            )
            return

        lines = [
            "🛍️ محصولات",
            "",
        ]

        for product in products:
            lines.extend([
                f"🆔 {product['id']}",
                f"نام: {product['name']}",
                f"دسته: {product['category']}",
                f"قیمت: {fmt_money(product['price'])}",
                f"موجودی: {product['stock']}",
                "",
            ])

        await query.message.reply_text(
            "\n".join(lines),
            reply_markup=back_admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADMIN ORDERS
    # --------------------------------------------------------

    if data == "admin_orders":
        if not is_admin(user_id):
            return

        orders = load_orders()

        new_orders = [
            o for o in orders
            if o.get("status")
            in [
                STATUS_NEW,
                STATUS_CONFIRMED,
                STATUS_READY,
            ]
        ]

        if not new_orders:
            await query.message.reply_text(
                "🆕 سفارشی برای بررسی وجود ندارد.",
                reply_markup=back_admin_keyboard(),
            )
            return

        for order in new_orders[-20:]:
            text = (
                f"🆔 {order['id']}\n"
                f"👤 {order.get('name', '')}\n"
                f"📱 {order.get('phone', '')}\n"
                f"💰 {fmt_money(order['total'])} افغانی\n"
                f"📌 {order['status']}\n"
                f"💳 {order.get('payment_status', 'pending')}\n"
            )

            await query.message.reply_text(
                text,
                reply_markup=admin_order_keyboard(
                    order["id"]
                ),
            )

        return

    # --------------------------------------------------------
    # ADMIN PAYMENTS
    # --------------------------------------------------------

    if data == "admin_payments":
        if not is_admin(user_id):
            return

        payments = load_payments()

        if not payments:
            await query.message.reply_text(
                "💳 هنوز پرداختی ثبت نشده است.",
                reply_markup=back_admin_keyboard(),
            )
            return

        lines = [
            "💳 پرداخت‌ها",
            "",
        ]

        for payment in payments[-30:]:
            lines.append(
                f"🆔 {payment.get('id')}\n"
                f"سفارش: {payment.get('order_id')}\n"
                f"مبلغ: {fmt_money(payment.get('amount', 0))}\n"
                f"وضعیت: {payment.get('status')}\n"
            )

        await query.message.reply_text(
            "\n".join(lines),
            reply_markup=back_admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADMIN AI
    # --------------------------------------------------------

    if data == "admin_ai":
        if not is_admin(user_id):
            return

        status = (
            "🟢 فعال"
            if ai_enabled()
            else "🔴 غیرفعال"
        )

        await query.message.reply_text(
            f"🤖 وضعیت دستیار هوشمند\n\n"
            f"{status}\n\n"
            f"مدل: {OPENAI_MODEL}",
            reply_markup=back_admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADMIN SECURITY
    # --------------------------------------------------------

    if data == "admin_security":
        if not is_admin(user_id):
            return

        await query.message.reply_text(
            "🔐 وضعیت امنیت\n\n"
            "✅ بررسی دسترسی مدیر فعال است.\n"
            "✅ فقط ADMIN_ID می‌تواند پنل مدیریت را ببیند.\n"
            "✅ درخواست‌های callback قدیمی باعث توقف ربات نمی‌شوند.",
            reply_markup=back_admin_keyboard(),
        )
        return

    # --------------------------------------------------------
    # ADD PRODUCT
    # --------------------------------------------------------

    if data == "add_product":
        if not is_admin(user_id):
            return

        context.user_data.clear()

        context.user_data["admin_action"] = "add_product"
        context.user_data["add_step"] = "name"

        await query.message.reply_text(
            "➕ افزودن محصول\n\n"
            "نام محصول را ارسال کنید."
        )
        return

    # --------------------------------------------------------
    # CHANGE PRICE
    # --------------------------------------------------------

    if data == "change_price":
        if not is_admin(user_id):
            return

        context.user_data["admin_action"] = "change_price"
        context.user_data["change_step"] = "product"

        await query.message.reply_text(
            "💰 تغییر قیمت\n\n"
            "شناسه محصول را ارسال کنید."
        )
        return

    # --------------------------------------------------------
    # CHANGE STOCK
    # --------------------------------------------------------

    if data == "change_stock":
        if not is_admin(user_id):
            return

        context.user_data["admin_action"] = "change_stock"
        context.user_data["change_step"] = "product"

        await query.message.reply_text(
            "📦 تغییر موجودی\n\n"
            "شناسه محصول را ارسال کنید."
        )
        return

    # --------------------------------------------------------
    # DELETE PRODUCT
    # --------------------------------------------------------

    if data == "delete_product":
        if not is_admin(user_id):
            return

        context.user_data["admin_action"] = "delete_product"

        await query.message.reply_text(
            "🗑️ حذف محصول\n\n"
            "شناسه محصول را ارسال کنید."
        )
        return

    # --------------------------------------------------------
    # ORDER STATUS
    # --------------------------------------------------------

    if data.startswith("status_"):
        if not is_admin(user_id):
            return

        parts = data.split(
            "_",
            2,
        )

        if len(parts) != 3:
            return

        order_id = parts[1]
        new_status = parts[2]

        if new_status not in ORDER_STATUSES:
            return

        orders = load_orders()

        target = None

        for order in orders:
            if str(order.get("id")) == str(order_id):
                target = order
                break

        if not target:
            await query.message.reply_text(
                "❌ سفارش پیدا نشد."
            )
            return

        target["status"] = new_status
        target["updated_at"] = now_text()

        save_orders(orders)

        await query.message.reply_text(
            f"✅ وضعیت سفارش {order_id} "
            f"به «{new_status}» تغییر کرد."
        )

        await notify_customer_status(
            context,
            target,
        )

        return


# ============================================================
# TEXT MESSAGE
# ============================================================

async def receive_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    text = update.message.text.strip()

    upsert_customer(user)

    # --------------------------------------------------------
    # AI MODE
    # --------------------------------------------------------

    if context.user_data.get("ai_mode"):
        answer = ai_reply(text)

        await update.message.reply_text(
            answer,
            reply_markup=home_keyboard(
                user.id
            ),
        )
        return

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if context.user_data.get("search_mode"):
        context.user_data["search_mode"] = False

        products = load_products()

        found = []

        search_text = text.lower()

        for product in products:
            name = str(
                product.get("name", "")
            ).lower()

            category = str(
                product.get("category", "")
            ).lower()

            description = str(
                product.get("description", "")
            ).lower()

            if (
                search_text in name
                or search_text in category
                or search_text in description
            ):
                found.append(product)

        if not found:
            await update.message.reply_text(
                "❌ محصولی با این نام پیدا نشد.",
                reply_markup=home_keyboard(
                    user.id
                ),
            )
            return

        for product in found:
            text_product = (
                f"🛍️ {product['name']}\n"
                f"💰 {fmt_money(product['price'])} افغانی\n"
                f"📦 موجودی: {product['stock']}"
            )

            await update.message.reply_text(
                text_product,
                reply_markup=product_keyboard(
                    product["id"]
                ),
            )

        return

    # ========================================================
    # CUSTOM SEWING
    # ========================================================

    custom_step = context.user_data.get(
        "custom_step"
    )

    if custom_step == "description":
        context.user_data[
            "custom_description"
        ] = text

        context.user_data[
            "custom_step"
        ] = "photo"

        await update.message.reply_text(
            "📸 اگر عکس نمونه دارید، همین حالا ارسال کنید.\n\n"
            "اگر عکس ندارید، بنویسید: ندارم"
        )
        return

    if custom_step == "photo":
        if text.lower() in [
            "ندارم",
            "ندارم.",
            "no",
            "none",
        ]:
            description = context.user_data.get(
                "custom_description",
                "",
            )

            await update.message.reply_text(
                "✅ درخواست دوخت شما ثبت شد.\n\n"
                f"📝 توضیحات:\n{description}\n\n"
                "مدیر با شما تماس خواهد گرفت.",
                reply_markup=home_keyboard(
                    user.id
                ),
            )

            if ADMIN_ID:
                try:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=(
                            "🧵 درخواست دوخت سفارشی جدید\n\n"
                            f"👤 مشتری: {user.first_name or ''}\n"
                            f"📱 User ID: {user.id}\n\n"
                            f"📝 {description}"
                        ),
                    )
                except Exception as e:
                    print(
                        f"CUSTOM ADMIN ERROR: {e}"
                    )

            context.user_data.pop(
                "custom_step",
                None,
            )

            return

        await update.message.reply_text(
            "📸 لطفاً عکس نمونه را ارسال کنید یا اگر عکس ندارید بنویسید «ندارم»."
        )
        return

    # ========================================================
    # CART PHONE
    # ========================================================

    if context.user_data.get(
        "order_step"
    ) == "phone":

        phone = text

        cart = context.user_data.get(
            "cart",
            [],
        )

        if not cart:
            context.user_data.pop(
                "order_step",
                None,
            )

            await update.message.reply_text(
                "🛒 سبد خرید خالی است."
            )
            return

        # دوباره بررسی موجودی
        for item in cart:
            product = get_product(
                item["id"]
            )

            if not product:
                await update.message.reply_text(
                    "❌ یکی از محصولات دیگر موجود نیست."
                )
                return

            if int(product["stock"]) < int(
                item["quantity"]
            ):
                await update.message.reply_text(
                    f"❌ موجودی {product['name']} کافی نیست."
                )
                return

        order = make_order(
            user,
            cart,
            phone,
        )

        # کاهش موجودی
        products = load_products()

        for product in products:
            for item in cart:
                if str(product.get("id")) == str(
                    item.get("id")
                ):
                    product["stock"] = max(
                        0,
                        int(product.get("stock", 0))
                        - int(item.get("quantity", 1)),
                    )

        save_products(products)

        context.user_data["cart"] = []
        context.user_data.pop(
            "order_step",
            None,
        )

        await send_professional_order_notification(
            context,
            order,
        )

        # HesabPay
        payment = create_hesabpay_session(
            order
        )

        if payment and payment.get("success"):
            payment_url = payment.get("url")

            save_payment(
                order["id"],
                order["total"],
                "pending",
            )

            if payment_url:
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "💳 پرداخت آنلاین",
                            url=payment_url,
                        )
                    ]
                ])

                await update.message.reply_text(
                    "✅ سفارش شما ثبت شد.\n\n"
                    f"🆔 شماره سفارش: {order['id']}\n"
                    f"💰 مبلغ: {fmt_money(order['total'])} افغانی\n\n"
                    "برای پرداخت روی دکمه زیر بزنید:",
                    reply_markup=keyboard,
                )
            else:
                await update.message.reply_text(
                    "✅ سفارش شما ثبت شد.\n\n"
                    f"🆔 {order['id']}\n"
                    f"💰 {fmt_money(order['total'])} افغانی\n\n"
                    "لینک پرداخت از طرف HesabPay دریافت نشد.",
                    reply_markup=home_keyboard(
                        user.id
                    ),
                )

        else:
            save_payment(
                order["id"],
                order["total"],
                "not_created",
            )

            await update.message.reply_text(
                "✅ سفارش شما با موفقیت ثبت شد.\n\n"
                f"🆔 شماره سفارش: {order['id']}\n"
                f"💰 مبلغ: {fmt_money(order['total'])} افغانی\n\n"
                "⚠️ پرداخت آنلاین در حال حاضر در دسترس نیست. "
                "مدیر سفارش شما را بررسی می‌کند.",
                reply_markup=home_keyboard(
                    user.id
                ),
            )

        return

    # ========================================================
    # ADMIN ADD PRODUCT
    # ========================================================

    if is_admin(user.id):

        # ----------------------------------------------------
        # ADD PRODUCT
        # ----------------------------------------------------

        if context.user_data.get(
            "admin_action"
        ) == "add_product":

            step = context.user_data.get(
                "add_step"
            )

            if step == "name":
                context.user_data[
                    "new_product_name"
                ] = text

                context.user_data[
                    "add_step"
                ] = "category"

                await update.message.reply_text(
                    "📂 دسته محصول را وارد کنید.\n\n"
                    "مثال:\n"
                    "مجلسی\n"
                    "سرپتلونی"
                )
                return

            if step == "category":
                context.user_data[
                    "new_product_category"
                ] = text

                context.user_data[
                    "add_step"
                ] = "price"

                await update.message.reply_text(
                    "💰 قیمت محصول را وارد کنید."
                )
                return

            if step == "price":
                try:
                    price = price_number(text)

                    if price <= 0:
                        raise ValueError

                except Exception:
                    await update.message.reply_text(
                        "❌ قیمت نامعتبر است. "
                        "مثلاً: 1500"
                    )
                    return

                context.user_data[
                    "new_product_price"
                ] = price

                context.user_data[
                    "add_step"
                ] = "stock"

                await update.message.reply_text(
                    "📦 تعداد موجودی را وارد کنید."
                )
                return

            if step == "stock":
                try:
                    stock = int(text)

                    if stock < 0:
                        raise ValueError

                except Exception:
                    await update.message.reply_text(
                        "❌ موجودی نامعتبر است."
                    )
                    return

                context.user_data[
                    "new_product_stock"
                ] = stock

                context.user_data[
                    "add_step"
                ] = "description"

                await update.message.reply_text(
                    "📝 توضیحات محصول را وارد کنید."
                )
                return

            if step == "description":
                context.user_data[
                    "new_product_description"
                ] = text

                context.user_data[
                    "add_step"
                ] = "photo"

                await update.message.reply_text(
                    "📸 حالا عکس محصول را ارسال کنید."
                )
                return

        # ----------------------------------------------------
        # CHANGE PRICE
        # ----------------------------------------------------

        if context.user_data.get(
            "admin_action"
        ) == "change_price":

            step = context.user_data.get(
                "change_step"
            )

            if step == "product":
                product = get_product(text)

                if not product:
                    await update.message.reply_text(
                        "❌ شناسه محصول پیدا نشد."
                    )
                    return

                context.user_data[
                    "change_product_id"
                ] = text

                context.user_data[
                    "change_step"
                ] = "value"

                await update.message.reply_text(
                    f"💰 قیمت فعلی: "
                    f"{fmt_money(product['price'])}\n\n"
                    "قیمت جدید را وارد کنید."
                )
                return

            if step == "value":
                try:
                    value = price_number(text)

                    if value <= 0:
                        raise ValueError

                except Exception:
                    await update.message.reply_text(
                        "❌ قیمت نامعتبر است."
                    )
                    return

                products = load_products()

                product_id = context.user_data[
                    "change_product_id"
                ]

                for product in products:
                    if str(product.get("id")) == str(
                        product_id
                    ):
                        product["price"] = value
                        break

                save_products(products)

                context.user_data.clear()

                await update.message.reply_text(
                    "✅ قیمت با موفقیت تغییر کرد.",
                    reply_markup=admin_keyboard(),
                )
                return

        # ----------------------------------------------------
        # CHANGE STOCK
        # ----------------------------------------------------

        if context.user_data.get(
            "admin_action"
        ) == "change_stock":

            step = context.user_data.get(
                "change_step"
            )

            if step == "product":
                product = get_product(text)

                if not product:
                    await update.message.reply_text(
                        "❌ شناسه محصول پیدا نشد."
                    )
                    return

                context.user_data[
                    "change_product_id"
                ] = text

                context.user_data[
                    "change_step"
                ] = "value"

                await update.message.reply_text(
                    f"📦 موجودی فعلی: "
                    f"{product['stock']}\n\n"
                    "موجودی جدید را وارد کنید."
                )
                return

            if step == "value":
                try:
                    value = int(text)

                    if value < 0:
                        raise ValueError

                except Exception:
                    await update.message.reply_text(
                        "❌ موجودی نامعتبر است."
                    )
                    return

                products = load_products()

                product_id = context.user_data[
                    "change_product_id"
                ]

                for product in products:
                    if str(product.get("id")) == str(
                        product_id
                    ):
                        product["stock"] = value
                        break

                save_products(products)

                context.user_data.clear()

                await update.message.reply_text(
                    "✅ موجودی با موفقیت تغییر کرد.",
                    reply_markup=admin_keyboard(),
                )
                return

        # ----------------------------------------------------
        # DELETE PRODUCT
        # ----------------------------------------------------

        if context.user_data.get(
            "admin_action"
        ) == "delete_product":

            products = load_products()

            before = len(products)

            products = [
                p for p in products
                if str(p.get("id")) != str(text)
            ]

            if len(products) == before:
                await update.message.reply_text(
                    "❌ محصول پیدا نشد."
                )
                return

            save_products(products)

            context.user_data.clear()

            await update.message.reply_text(
                "🗑️ محصول حذف شد.",
                reply_markup=admin_keyboard(),
            )
            return

    # ========================================================
    # NORMAL AI FALLBACK
    # ========================================================

    if ai_enabled():
        answer = ai_reply(text)

        await update.message.reply_text(
            answer,
            reply_markup=home_keyboard(
                user.id
            ),
        )
    else:
        await update.message.reply_text(
            "لطفاً از منوی زیر استفاده کنید.",
            reply_markup=home_keyboard(
                user.id
            ),
        )


# ============================================================
# PHOTO
# ============================================================

async def receive_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    photo = update.message.photo[-1]

    file_id = photo.file_id

    # --------------------------------------------------------
    # CUSTOM SEWING PHOTO
    # --------------------------------------------------------

    if context.user_data.get(
        "custom_step"
    ) == "photo":

        description = context.user_data.get(
            "custom_description",
            "",
        )

        await update.message.reply_text(
            "✅ عکس دریافت شد.\n\n"
            "درخواست دوخت سفارشی شما ثبت شد.\n"
            "مدیر با شما تماس خواهد گرفت.",
            reply_markup=home_keyboard(
                user.id
            ),
        )

        if ADMIN_ID:
            try:
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=file_id,
                    caption=(
                        "🧵 دوخت سفارشی جدید\n\n"
                        f"👤 مشتری: {user.first_name or ''}\n"
                        f"🆔 User ID: {user.id}\n\n"
                        f"📝 {description}"
                    ),
                )
            except Exception as e:
                print(
                    f"CUSTOM PHOTO ERROR: {e}"
                )

        context.user_data.pop(
            "custom_step",
            None,
        )

        return

    # --------------------------------------------------------
    # ADMIN ADD PRODUCT PHOTO
    # --------------------------------------------------------

    if (
        is_admin(user.id)
        and context.user_data.get(
            "admin_action"
        ) == "add_product"
        and context.user_data.get(
            "add_step"
        ) == "photo"
    ):

        products = load_products()

        product = {
            "id": next_id(
                products,
                "PRD",
            ),
            "name": context.user_data.get(
                "new_product_name",
                "",
            ),
            "category": context.user_data.get(
                "new_product_category",
                "عمومی",
            ),
            "price": context.user_data.get(
                "new_product_price",
                0,
            ),
            "stock": context.user_data.get(
                "new_product_stock",
                0,
            ),
            "description": context.user_data.get(
                "new_product_description",
                "",
            ),
            "photo": file_id,
            "created_at": now_text(),
        }

        products.append(product)

        save_products(products)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ محصول با موفقیت اضافه شد.\n\n"
            f"🆔 {product['id']}\n"
            f"🛍️ {product['name']}\n"
            f"💰 {fmt_money(product['price'])} افغانی\n"
            f"📦 {product['stock']} عدد",
            reply_markup=admin_keyboard(),
        )

        return

    await update.message.reply_text(
        "📸 عکس دریافت شد."
    )


# ============================================================
# FLASK SERVER
# ============================================================

web_app = Flask(__name__)


@web_app.get("/")
def home_health():
    return jsonify({
        "ok": True,
        "service": "Mohammadi Fashion bot",
        "status": "running",
    })


@web_app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "Mohammadi Fashion bot",
        "status": "healthy",
    })


@web_app.post("/webhooks/hesabpay")
def hesabpay_webhook():

    try:
        if HESABPAY_WEBHOOK_TOKEN:
            received = request.headers.get(
                "X-Webhook-Token",
                "",
            )

            if received != HESABPAY_WEBHOOK_TOKEN:
                return jsonify({
                    "ok": False,
                    "error": "unauthorized",
                }), 401

        data = request.get_json(
            silent=True
        ) or {}

        order_id = (
            data.get("order_id")
            or data.get("reference")
            or data.get("merchant_reference")
        )

        status = (
            data.get("status")
            or data.get("payment_status")
            or "unknown"
        )

        transaction_id = (
            data.get("transaction_id")
            or data.get("transactionId")
            or ""
        )

        if order_id:
            orders = load_orders()

            for order in orders:
                if str(order.get("id")) == str(
                    order_id
                ):
                    order["payment_status"] = status
                    order["transaction_id"] = transaction_id
                    order["updated_at"] = now_text()
                    break

            save_orders(orders)

        return jsonify({
            "ok": True,
        })

    except Exception as e:
        print(
            f"HESABPAY WEBHOOK ERROR: {e}"
        )

        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500


# ============================================================
# WEB SERVER
# ============================================================

def run_web_server():
    print(
        f"Starting web server on "
        f"{WEBHOOK_HOST}:{WEBHOOK_PORT}"
    )

    web_app.run(
        host=WEBHOOK_HOST,
        port=WEBHOOK_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not configured."
        )

    if not ADMIN_ID:
        raise RuntimeError(
            "ADMIN_ID is not configured."
        )

    if HESABPAY_API_KEY:
        if not HESABPAY_SUCCESS_URL:
            print(
                "WARNING: HESABPAY_SUCCESS_URL "
                "is not configured."
            )

        if not HESABPAY_FAILURE_URL:
            print(
                "WARNING: HESABPAY_FAILURE_URL "
                "is not configured."
            )

    if not ai_enabled():
        print(
            "INFO: AI assistant is disabled "
            "until OPENAI_API_KEY is configured."
        )
    else:
        print(
            f"AI assistant enabled: {OPENAI_MODEL}"
        )

    # --------------------------------------------------------
    # START FLASK BEFORE TELEGRAM
    # --------------------------------------------------------

    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True,
    )

    web_thread.start()

    print(
        f"Web server started on port "
        f"{WEBHOOK_PORT}"
    )

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_photo,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_message,
        )
    )
    print(
        "Mohammadi Fashion Smart Bot is running..."
    )
    print(f"Webhook URL: {RENDER_URL}{WEBHOOK_PATH}")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
