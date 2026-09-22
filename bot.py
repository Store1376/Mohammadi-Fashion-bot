import os
import json
import logging
from datetime import datetime

from flask import Flask
from threading import Thread

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
    ConversationHandler,
)

# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

SHOP_NAME = "Mohammadi Fashion"
SHOP_DESCRIPTION = "عرضه کننده هر نوع لباس های زنانه"

PRODUCTS_FILE = "products.json"
ORDERS_FILE = "orders.json"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# =========================================================
# FLASK FOR RENDER
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Mohammadi Fashion Bot is running."


@app.route("/health")
def health():
    return "OK"


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# =========================================================
# FILE FUNCTIONS
# =========================================================

def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)

            return default

        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        logger.error("JSON LOAD ERROR: %s", e)
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        logger.error("JSON SAVE ERROR: %s", e)


def get_products():
    return load_json(PRODUCTS_FILE, [])


def save_products(products):
    save_json(PRODUCTS_FILE, products)


def get_orders():
    return load_json(ORDERS_FILE, [])


def save_orders(orders):
    save_json(ORDERS_FILE, orders)


# =========================================================
# PRODUCT ID
# =========================================================

def next_product_id():
    products = get_products()

    if not products:
        return 1

    return max(int(p.get("id", 0)) for p in products) + 1


# =========================================================
# USER DATA
# =========================================================

def get_user_data(context):
    if "cart" not in context.user_data:
        context.user_data["cart"] = []

    return context.user_data


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard():

    keyboard = [
        [
            InlineKeyboardButton("🛍 محصولات", callback_data="products"),
            InlineKeyboardButton("🔎 جستجو", callback_data="search"),
        ],
        [
            InlineKeyboardButton("🛒 سبد خرید", callback_data="cart"),
            InlineKeyboardButton("📦 سفارش‌های من", callback_data="my_orders"),
        ],
        [
            InlineKeyboardButton("✂️ دوخت سفارشی", callback_data="custom"),
            InlineKeyboardButton("📞 تماس با ما", callback_data="contact"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    get_user_data(context)

    text = (
        f"👋 سلام و خوش آمدید به {SHOP_NAME}\n\n"
        f"{SHOP_DESCRIPTION}\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=main_keyboard()
        )

    elif update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            reply_markup=main_keyboard()
        )


# =========================================================
# PRODUCTS
# =========================================================

async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query:
        await query.answer()

    product_list = get_products()

    if not product_list:

        text = (
            "🛍 محصولات\n\n"
            "در حال حاضر محصولی ثبت نشده است."
        )

        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ]

        if query:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        return

    keyboard = []

    for product in product_list:

        product_id = product.get("id")
        name = product.get("name", "محصول")
        price = product.get("price", 0)

        keyboard.append([
            InlineKeyboardButton(
                f"{name} — {price}",
                callback_data=f"product_{product_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="home")
    ])

    if query:
        await query.message.reply_text(
            "🛍 لیست محصولات:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# =========================================================
# SHOW PRODUCT
# =========================================================

async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    try:
        product_id = int(query.data.split("_")[1])
    except Exception:
        return

    products_list = get_products()

    product = next(
        (p for p in products_list if int(p.get("id", 0)) == product_id),
        None
    )

    if not product:

        await query.message.reply_text(
            "❌ محصول پیدا نشد."
        )

        return

    name = product.get("name", "محصول")
    price = product.get("price", 0)
    description = product.get("description", "")
    stock = product.get("stock", 0)
    photo_id = product.get("photo_id")

    text = (
        f"👗 {name}\n\n"
        f"💰 قیمت: {price}\n"
        f"📦 موجودی: {stock}\n\n"
        f"📝 توضیحات:\n{description}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "🛒 افزودن به سبد",
                callback_data=f"addcart_{product_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 محصولات",
                callback_data="products"
            )
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    try:

        if photo_id:

            await query.message.reply_photo(
                photo=photo_id,
                caption=text,
                reply_markup=markup
            )

        else:

            await query.message.reply_text(
                text,
                reply_markup=markup
            )

    except Exception as e:

        logger.error("PRODUCT PHOTO ERROR: %s", e)

        await query.message.reply_text(
            text,
            reply_markup=markup
        )


# =========================================================
# ADD TO CART
# =========================================================

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    try:
        product_id = int(query.data.split("_")[1])
    except Exception:
        return

    products_list = get_products()

    product = next(
        (p for p in products_list if int(p.get("id", 0)) == product_id),
        None
    )

    if not product:

        await query.message.reply_text(
            "❌ محصول پیدا نشد."
        )

        return

    stock = int(product.get("stock", 0))

    if stock <= 0:

        await query.message.reply_text(
            "❌ متأسفانه این محصول فعلاً موجود نیست."
        )

        return

    cart = context.user_data.setdefault("cart", [])

    found = False

    for item in cart:

        if item["product_id"] == product_id:

            item["quantity"] += 1
            found = True
            break

    if not found:

        cart.append({
            "product_id": product_id,
            "quantity": 1
        })

    await query.message.reply_text(
        f"✅ «{product.get('name')}» به سبد خرید اضافه شد.\n\n"
        "برای مشاهده سبد خرید روی 🛒 سبد خرید بزنید.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🛒 مشاهده سبد خرید",
                    callback_data="cart"
                )
            ],
            [
                InlineKeyboardButton(
                    "🛍 ادامه خرید",
                    callback_data="products"
                )
            ]
        ])
    )


# =========================================================
# CART
# =========================================================

async def cart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query:
        await query.answer()

    cart_items = context.user_data.setdefault("cart", [])

    if not cart_items:

        await query.message.reply_text(
            "🛒 سبد خرید شما خالی است.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛍 مشاهده محصولات",
                        callback_data="products"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    products_list = get_products()

    text = "🛒 سبد خرید شما:\n\n"

    total = 0

    for item in cart_items:

        product = next(
            (
                p for p in products_list
                if int(p.get("id", 0)) == int(item["product_id"])
            ),
            None
        )

        if not product:
            continue

        quantity = int(item["quantity"])
        price = float(product.get("price", 0))

        subtotal = price * quantity
        total += subtotal

        text += (
            f"👗 {product.get('name')}\n"
            f"تعداد: {quantity}\n"
            f"قیمت: {price}\n"
            f"جمع: {subtotal}\n\n"
        )

    text += f"💰 مجموع سفارش: {total}"

    keyboard = [
        [
            InlineKeyboardButton(
                "🗑 خالی کردن سبد",
                callback_data="clear_cart"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ ثبت سفارش",
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
                "🔙 بازگشت",
                callback_data="home"
            )
        ]
    ]

    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# CLEAR CART
# =========================================================

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["cart"] = []

    await query.message.reply_text(
        "🗑 سبد خرید شما خالی شد.",
        reply_markup=main_keyboard()
    )


# =========================================================
# CHECKOUT
# =========================================================

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    cart_items = context.user_data.setdefault("cart", [])

    if not cart_items:

        await query.message.reply_text(
            "❌ سبد خرید شما خالی است."
        )

        return

    context.user_data["checkout"] = True

    await query.message.reply_text(
        "📞 لطفاً شماره تلفن خود را ارسال کنید.\n\n"
        "مثلاً:\n"
        "0700000000"
    )


# =========================================================
# HANDLE PHONE
# =========================================================

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("checkout"):
        return

    phone = update.message.text.strip()

    if len(phone) < 7:

        await update.message.reply_text(
            "❌ شماره تلفن صحیح نیست.\n"
            "لطفاً دوباره شماره تلفن را ارسال کنید."
        )

        return

    context.user_data["phone"] = phone

    await update.message.reply_text(
        "📍 لطفاً آدرس یا محل تحویل سفارش را ارسال کنید."
    )

    context.user_data["waiting_address"] = True


# =========================================================
# HANDLE ADDRESS
# =========================================================

async def handle_address(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_address"):
        return

    address = update.message.text.strip()

    context.user_data["address"] = address

    await create_order(update, context)


# =========================================================
# CREATE ORDER
# =========================================================

async def create_order(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cart_items = context.user_data.get("cart", [])

    products_list = get_products()

    user = update.effective_user

    items = []
    total = 0

    for item in cart_items:

        product = next(
            (
                p for p in products_list
                if int(p.get("id", 0)) == int(item["product_id"])
            ),
            None
        )

        if not product:
            continue

        quantity = int(item["quantity"])
        price = float(product.get("price", 0))

        total += price * quantity

        items.append({
            "product_id": product.get("id"),
            "name": product.get("name"),
            "price": price,
            "quantity": quantity
        })

    order_id = len(get_orders()) + 1

    order = {
        "id": order_id,
        "user_id": user.id,
        "username": user.username or "",
        "name": user.full_name,
        "phone": context.user_data.get("phone", ""),
        "address": context.user_data.get("address", ""),
        "items": items,
        "total": total,
        "status": "در انتظار بررسی",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    orders = get_orders()
    orders.append(order)

    save_orders(orders)

    context.user_data["cart"] = []
    context.user_data["checkout"] = False
    context.user_data["waiting_address"] = False

    await update.message.reply_text(
        f"✅ سفارش شما با موفقیت ثبت شد.\n\n"
        f"🧾 شماره سفارش: #{order_id}\n"
        f"💰 مبلغ: {total}\n"
        f"📦 وضعیت: در انتظار بررسی\n\n"
        "از خرید شما سپاسگزاریم ❤️",
        reply_markup=main_keyboard()
    )

    # اطلاع به ادمین

    if ADMIN_ID:

        admin_text = (
            f"🔔 سفارش جدید!\n\n"
            f"🧾 سفارش: #{order_id}\n"
            f"👤 مشتری: {user.full_name}\n"
            f"🆔 User ID: {user.id}\n"
            f"📞 تلفن: {order['phone']}\n"
            f"📍 آدرس: {order['address']}\n\n"
        )

        for item in items:

            admin_text += (
                f"👗 {item['name']}\n"
                f"تعداد: {item['quantity']}\n"
                f"قیمت: {item['price']}\n\n"
            )

        admin_text += (
            f"💰 مجموع: {total}\n"
            f"📦 وضعیت: در انتظار بررسی"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text
            )
        except Exception as e:
            logger.error("ADMIN MESSAGE ERROR: %s", e)


# =========================================================
# MY ORDERS
# =========================================================

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    orders = [
        o for o in get_orders()
        if int(o.get("user_id", 0)) == user_id
    ]

    if not orders:

        await query.message.reply_text(
            "📦 شما هنوز سفارشی ثبت نکرده‌اید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🛍 خرید",
                        callback_data="products"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

        return

    text = "📦 سفارش‌های شما:\n\n"

    for order in orders[-10:]:

        text += (
            f"🧾 سفارش #{order.get('id')}\n"
            f"💰 مبلغ: {order.get('total')}\n"
            f"📦 وضعیت: {order.get('status')}\n"
            f"📅 تاریخ: {order.get('date')}\n\n"
        )

    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="home"
                )
            ]
        ])
    )


# =========================================================
# SEARCH
# =========================================================

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    if query:
        await query.answer()

    context.user_data["searching"] = True

    await query.message.reply_text(
        "🔎 نام محصول مورد نظر را بنویسید."
    )


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("searching"):
        return

    keyword = update.message.text.strip().lower()

    context.user_data["searching"] = False

    products_list = get_products()

    results = [
        p for p in products_list
        if keyword in p.get("name", "").lower()
        or keyword in p.get("description", "").lower()
    ]

    if not results:

        await update.message.reply_text(
            "❌ محصولی با این نام پیدا نشد.",
            reply_markup=main_keyboard()
        )

        return

    keyboard = []

    for product in results:

        keyboard.append([
            InlineKeyboardButton(
                f"{product.get('name')} — {product.get('price')}",
                callback_data=f"product_{product.get('id')}"
            )
        ])

    await update.message.reply_text(
        "🔎 نتایج جستجو:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# CUSTOM TAILORING
# =========================================================

async def custom(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["custom"] = True

    await query.message.reply_text(
        "✂️ درخواست دوخت سفارشی\n\n"
        "لطفاً توضیحات لباس مورد نظر خود را بنویسید.\n\n"
        "مثلاً:\n"
        "لباس مجلسی مخمل با نگین، رنگ مشکی، سایز ۴۲"
    )


async def handle_custom(update: Update, context: ContextTypes.DEF
