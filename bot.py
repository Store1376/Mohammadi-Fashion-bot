
import os
import json
import logging
import threading
import time
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify

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


# ============================================================
# MOHAMMADI FASHION
# Stable Telegram Store Bot
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

PORT = int(os.getenv("PORT", "10000"))

DATA_DIR = Path(os.getenv("DATA_DIR", "."))

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(
    "MohammadiFashion"
)

DATA_LOCK = threading.RLock()


# ============================================================
# FLASK / RENDER
# ============================================================

web_app = Flask(__name__)


@web_app.get("/")
def home():

    return jsonify(
        {
            "ok": True,
            "service": "Mohammadi Fashion",
            "status": "running",
        }
    )


@web_app.get("/health")
def health():

    return jsonify(
        {
            "ok": True,
            "service": "Mohammadi Fashion",
            "status": "healthy",
        }
    )


def start_web_server():

    logger.info(
        "Starting Render web server on port %s",
        PORT,
    )

    web_app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


# ============================================================
# JSON DATABASE
# ============================================================

def load_json(
    file_path,
    default,
):

    try:

        with DATA_LOCK:

            if not file_path.exists():

                save_json(
                    file_path,
                    default,
                )

                return default

            content = file_path.read_text(
                encoding="utf-8"
            ).strip()

            if not content:

                return default

            return json.loads(
                content
            )

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
        ValueError,
    ) as error:

        logger.exception(
            "Database read error for %s: %s",
            file_path,
            error,
        )

        return default

    except Exception as error:

        logger.exception(
            "Unexpected database read error for %s: %s",
            file_path,
            error,
        )

        return default


def save_json(
    file_path,
    data,
):

    temp_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    try:

        with DATA_LOCK:

            temp_path.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            temp_path.replace(
                file_path
            )

    except Exception as error:

        logger.exception(
            "Database save error for %s: %s",
            file_path,
            error,
        )

        try:

            if temp_path.exists():

                temp_path.unlink()

        except Exception:

            pass


def get_products():

    return load_json(
        PRODUCTS_FILE,
        [],
    )


def get_orders():

    return load_json(
        ORDERS_FILE,
        [],
    )


# ============================================================
# HELPERS
# ============================================================

def is_admin(
    user_id
):

    if not ADMIN_ID:

        return False

    return str(user_id) == str(
        ADMIN_ID
    )


def get_product(
    product_id
):

    for product in get_products():

        if str(
            product.get("id")
        ) == str(
            product_id
        ):

            return product

    return None


def next_product_id():

    items = get_products()

    if not items:

        return "1"

    numbers = []

    for item in items:

        try:

            numbers.append(
                int(
                    item.get(
                        "id",
                        0,
                    )
                )
            )

        except Exception:

            pass

    if not numbers:

        return "1"

    return str(
        max(numbers) + 1
    )


def next_order_id():

    items = get_orders()

    if not items:

        return 1

    numbers = []

    for item in items:

        try:

            numbers.append(
                int(
                    item.get(
                        "id",
                        0,
                    )
                )
            )

        except Exception:

            pass

    if not numbers:

        return 1

    return max(numbers) + 1


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard(
    user_id
):

    buttons = [

        [

            InlineKeyboardButton(
                "👗 محصولات",
                callback_data="products",
            ),

            InlineKeyboardButton(
                "🛒 سبد خرید",
                callback_data="cart",
            ),

        ],

        [

            InlineKeyboardButton(
                "📦 سفارش‌های من",
                callback_data="my_orders",
            ),

            InlineKeyboardButton(
                "🔎 جستجوی محصول",
                callback_data="search",
            ),

        ],

        [

            InlineKeyboardButton(
                "🧵 دوخت سفارشی",
                callback_data="custom",
            ),

            InlineKeyboardButton(
                "📞 تماس با ما",
                callback_data="contact",
            ),

        ],

    ]

    if is_admin(user_id):

        buttons.append(
            [

                InlineKeyboardButton(
                    "⚙️ مدیریت فروشگاه",
                    callback_data="admin",
                )

            ]
        )

    return InlineKeyboardMarkup(
        buttons
    )


def home_button():

    return InlineKeyboardMarkup(
        [

            [

                InlineKeyboardButton(
                    "🏠 صفحه اصلی",
                    callback_data="home",
                )

            ]

        ]
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

    logger.info(
        "START from user %s",
        user.id,
    )

    await update.message.reply_text(

        f"👋 سلام {user.first_name or 'دوست عزیز'}\n\n"

        "🌸 به فروشگاه\n"
        "Mohammadi Fashion\n"
        "خوش آمدید.\n\n"

        "👗 لباس‌های زنانه\n"
        "🧵 دوخت سفارشی\n"
        "🛒 ثبت سفارش آسان\n\n"

        "یکی از گزینه‌های زیر را انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id
        ),
    )


# ============================================================
# HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(

        "📖 راهنمای Mohammadi Fashion\n\n"

        "/start — صفحه اصلی\n"
        "/products — محصولات\n"
        "/cart — سبد خرید\n"
        "/orders — سفارش‌های من\n"
        "/cancel — لغو عملیات\n\n"

        "برای استفاده آسان‌تر از دکمه‌های فروشگاه استفاده کنید.",

        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# ============================================================
# CANCEL
# ============================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    await update.message.reply_text(

        "❌ عملیات لغو شد.",

        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# ============================================================
# SHOW PRODUCTS
# ============================================================

async def show_products(
    query,
):

    items = get_products()

    if not items:

        await query.edit_message_text(

            "👗 محصولات فروشگاه\n\n"

            "فعلاً محصولی ثبت نشده است.\n"
            "مدیریت می‌تواند از پنل مدیریت محصول اضافه کند.",

            reply_markup=home_button(),
        )

        return

    keyboard = []

    for product in items[:50]:

        name = product.get(
            "name",
            "محصول",
        )

        price = product.get(
            "price",
            0,
        )

        keyboard.append(

            [

                InlineKeyboardButton(
                    f"👗 {name} — {price} افغانی",
                    callback_data=f"product:{product.get('id')}",
                )

            ]

        )

    keyboard.append(

        [

            InlineKeyboardButton(
                "🏠 صفحه اصلی",
                callback_data="home",
            )

        ]

    )

    await query.edit_message_text(

        "👗 محصولات Mohammadi Fashion\n\n"
        "یک محصول را انتخاب کنید:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# SHOW PRODUCT
# ============================================================

async def show_product(
    query,
    product_id,
):

    product = get_product(
        product_id
    )

    if not product:

        await query.edit_message_text(

            "❌ محصول پیدا نشد.",

            reply_markup=home_button(),
        )

        return

    name = product.get(
        "name",
        "محصول",
    )

    price = product.get(
        "price",
        0,
    )

    stock = product.get(
        "stock",
        0,
    )

    description = product.get(
        "description",
        "",
    )

    text = (

        f"👗 {name}\n\n"

        f"💰 قیمت: {price} افغانی\n"

        f"📦 موجودی: {stock}\n\n"

    )

    if description:

        text += (
            f"📝 {description}\n\n"
        )

    keyboard = [

        [

            InlineKeyboardButton(
                "🛒 افزودن به سبد",
                callback_data=f"add:{product_id}",
            )

        ],

        [

            InlineKeyboardButton(
                "⬅️ محصولات",
                callback_data="products",
            ),

            InlineKeyboardButton(
                "🏠 خانه",
                callback_data="home",
            ),

        ],

    ]

    await query.edit_message_text(

        text,

        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# CART
# ============================================================

def get_cart(
    context
):

    return context.user_data.setdefault(
        "cart",
        [],
    )


def cart_total(
    context
):

    total = 0

    for product_id in get_cart(
        context
    ):

        product = get_product(
            product_id
        )

        if product:

            try:

                total += float(
                    product.get(
                        "price",
                        0,
                    )
                )

            except Exception:

                pass

    return total


async def show_cart(
    query,
    context,
):

    cart = get_cart(
        context
    )

    if not cart:

        await query.edit_message_text(

            "🛒 سبد خرید شما خالی است.",

            reply_markup=home_button(),
        )

        return

    lines = [
        "🛒 سبد خرید شما\n"
    ]

    for product_id in cart:

        product = get_product(
            product_id
        )

        if product:

            lines.append(

                f"• {product.get('name')}\n"
                f"  {product.get('price')} افغانی"

            )

    lines.append(

        f"\n💰 مجموع: {cart_total(context):g} افغانی"

    )

    keyboard = [

        [

            InlineKeyboardButton(
                "📱 ثبت سفارش",
                callback_data="checkout",
            )

        ],

        [

            InlineKeyboardButton(
                "🗑 خالی کردن سبد",
                callback_data="clear_cart",
            )

        ],

        [

            InlineKeyboardButton(
                "🏠 صفحه اصلی",
                callback_data="home",
            )

        ],

    ]

    await query.edit_message_text(

        "\n".join(lines),

        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# CREATE ORDER
# ============================================================

def create_order(
    user,
    context,
    phone,
):

    cart = get_cart(
        context
    )

    if not cart:

        return None

    items = []

    total = 0

    for product_id in cart:

        product = get_product(
            product_id
        )

        if not product:

            continue

        try:

            price = float(
                product.get(
                    "price",
                    0,
                )
            )

        except Exception:

            price = 0

        items.append(

            {
                "product_id": product.get("id"),
                "name": product.get("name"),
                "price": price,
            }

        )

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

    data = get_orders()

    data.append(
        order
    )

    save_json(
        ORDERS_FILE,
        data,
    )

    context.user_data.clear()

    return order


# ============================================================
# BUTTON HANDLER
# ============================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    data = query.data

    logger.info(
        "BUTTON %s from %s",
        data,
        user_id,
    )

    # HOME
    if data == "home":

        await query.edit_message_text(

            "🏠 صفحه اصلی Mohammadi Fashion",

            reply_markup=main_keyboard(
                user_id
            ),
        )

        return

    # PRODUCTS
    if data == "products":

        await show_products(
            query
        )

        return

    # PRODUCT
    if data.startswith(
        "product:"
    ):

        product_id = data.split(
            ":",
            1
        )[1]

        await show_product(
            query,
            product_id,
        )

        return

    # ADD CART
    if data.startswith(
        "add:"
    ):

        product_id = data.split(
            ":",
            1
        )[1]

        product = get_product(
            product_id
        )

        if not product:

            await query.edit_message_text(

                "❌ محصول پیدا نشد.",

                reply_markup=home_button(),
            )

            return

        try:

            stock = int(
                product.get(
                    "stock",
                    0,
                )
            )

        except Exception:

            stock = 0

        if stock <= 0:

            await query.edit_message_text(

                "❌ این محصول فعلاً موجود نیست.",

                reply_markup=home_button(),
            )

            return

        cart = get_cart(
            context
        )

        if product_id not in cart:

            cart.append(
                product_id
            )

        await query.edit_message_text(

            f"✅ {product.get('name')}\n"
            "به سبد خرید اضافه شد.",

            reply_markup=InlineKeyboardMarkup(

                [

                    [

                        InlineKeyboardButton(
                            "🛒 سبد خرید",
                            callback_data="cart",
                        )

                    ],

                    [

                        InlineKeyboardButton(
                            "👗 محصولات",
                            callback_data="products",
                        )

                    ],

                    [

                        InlineKeyboardButton(
                            "🏠 خانه",
                            callback_data="home",
                        )

                    ],

                ]

            ),
        )

        return

    # CART
    if data == "cart":

        await show_cart(
            query,
            context,
        )

        return

    # CLEAR CART
    if data == "clear_cart":

        context.user_data[
            "cart"
        ] = []

        await query.edit_message_text(

            "🗑 سبد خرید خالی شد.",

            reply_markup=home_button(),
        )

        return

    # CHECKOUT
    if data == "checkout":

        if not get_cart(
            context
        ):

            await query.edit_message_text(

                "🛒 سبد خرید خالی است.",

                reply_markup=home_button(),
            )

            return

        context.user_data[
            "state"
        ] = "phone"

        await query.edit_message_text(

            "📱 لطفاً شماره تماس خود را ارسال کنید.\n\n"
            "مثال:\n"
            "07XXXXXXXX",

            reply_markup=home_button(),
        )

        return

    # MY ORDERS
    if data == "my_orders":

        user_orders = [

            order

            for order in get_orders()

            if str(
                order.get(
                    "user_id"
                )
            ) == str(
                user_id
            )

        ]

        if not user_orders:

            await query.edit_message_text(

                "📦 شما هنوز سفارشی ثبت نکرده‌اید.",

                reply_markup=home_button(),
            )

            return

        lines = [
            "📦 سفارش‌های شما\n"
        ]

        for order in user_orders[-10:]:

            lines.append(

                f"🧾 سفارش #{order.get('id')}\n"
                f"💰 {order.get('total', 0):g} افغانی\n"
                f"📌 وضعیت: {order.get('status')}\n"

            )

        await query.edit_message_text(

            "\n".join(lines),

            reply_markup=home_button(),
        )

        return

    # SEARCH
    if data == "search":

        context.user_data[
            "state"
        ] = "search"

        await query.edit_message_text(

            "🔎 نام محصول مورد نظر را بنویسید.",

            reply_markup=home_button(),
        )

        return

    # CUSTOM
    if data == "custom":

        context.user_data[
            "state"
        ] = "custom"

        await query.edit_message_text(

            "🧵 دوخت سفارشی\n\n"
            "لطفاً توضیحات لباس مورد نظر خود را ارسال کنید.\n"
            "مثلاً رنگ، مدل و اندازه.",

            reply_markup=home_button(),
        )

        return

    # CONTACT
    if data == "contact":

        await query.edit_message_text(

            "📞 تماس با ما\n\n"
            "Mohammadi Fashion\n\n"
            "برای سفارش و معلومات بیشتر با مدیریت فروشگاه تماس بگیرید.",

            reply_markup=home_button(),
        )

        return

    # ADMIN
    if data == "admin":

        if not is_admin(
            user_id
        ):

            await query.edit_message_text(
                "❌ دسترسی غیرمجاز."
            )

            return

        keyboard = [

            [

                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="admin_stats",
                )

            ],

            [

                InlineKeyboardButton(
                    "📦 سفارش‌ها",
                    callback_data="admin_orders",
                )

            ],

            [

                InlineKeyboardButton(
                    "➕ افزودن محصول",
                    callback_data="admin_add",
                )

            ],

            [

                InlineKeyboardButton(
                    "🗑 حذف محصول",
                    callback_data="admin_delete",
                )

            ],

            [

                InlineKeyboardButton(
                    "🏠 صفحه اصلی",
                    callback_data="home",
                )

            ],

        ]

        await query.edit_message_text(

            "⚙️ پنل مدیریت Mohammadi Fashion",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        return

    # ADMIN STATS
    if data == "admin_stats":

        if not is_admin(
            user_id
        ):

            return

        product_count = len(
            get_products()
        )

        order_count = len(
            get_orders()
        )

        await query.edit_message_text(

            "📊 آمار فروشگاه\n\n"

            f"👗 محصولات: {product_count}\n"
            f"📦 سفارش‌ها: {order_count}",

            reply_markup=home_button(),
        )

        return

    # ADMIN ORDERS
    if data == "admin_orders":

        if not is_admin(
            user_id
        ):

            return

        items = get_orders()

        if not items:

            await query.edit_message_text(

                "📦 هنوز سفارشی وجود ندارد.",

                reply_markup=home_button(),
            )

            return

        lines = [
            "📦 آخرین سفارش‌ها\n"
        ]

        for order in items[-20:]:

            lines.append(

                f"#{order.get('id')} | "
                f"{order.get('name')} | "
                f"{order.get('total', 0):g} افغانی | "
                f"{order.get('status')}"

            )

        await query.edit_message_text(

            "\n".join(lines),

            reply_markup=home_button(),
        )

        return

    # ADMIN ADD
    if data == "admin_add":

        if not is_admin(
            user_id
        ):

            return

        context.user_data[
            "state"
        ] = "admin_name"

        await query.edit_message_text(

            "➕ افزودن محصول\n\n"
            "نام محصول را ارسال کنید.",

            reply_markup=home_button(),
        )

        return

    # ADMIN DELETE
    if data == "admin_delete":

        if not is_admin(
            user_id
        ):

            return

        context.user_data[
            "state"
        ] = "admin_delete"

        await query.edit_message_text(

            "🗑 حذف محصول\n\n"
            "ID محصول را ارسال کنید.",

            reply_markup=home_button(),
        )

        return


# ============================================================
# TEXT HANDLER
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        update.message.text or ""
    ).strip()

    user = update.effective_user

    state = context.user_data.get(
        "state"
    )

    logger.info(
        "MESSAGE from %s: %s",
        user.id,
        text,
    )

    # PHONE
    if state == "phone":

        order = create_order(
            user,
            context,
            text,
        )

        if not order:

            await update.message.reply_text(

                "❌ سفارش ثبت نشد.\n"
                "لطفاً دوباره تلاش کنید.",

                reply_markup=main_keyboard(
                    user.id
                ),
            )

            return

        await update.message.reply_text(

            "✅ سفارش شما ثبت شد.\n\n"

            f"🧾 شماره سفارش: #{order['id']}\n"
            f"💰 مبلغ: {order['total']:g} افغانی\n"
            f"📱 شماره تماس: {order['phone']}\n\n"

            "مدیریت فروشگاه با شما تماس خواهد گرفت.",

            reply_markup=main_keyboard(
                user.id
            ),
        )

        if ADMIN_ID:

            try:

                await context.bot.send_message(

                    chat_id=int(
                        ADMIN_ID
                    ),

                    text=(

                        "🔔 سفارش جدید\n\n"

                        f"🧾 سفارش: #{order['id']}\n"
                        f"👤 مشتری: {order['name']}\n"
                        f"📱 تماس: {order['phone']}\n"
                        f"💰 مبلغ: {order['total']:g} افغانی"

                    ),
                )

            except Exception as error:

                logger.exception(
                    "Admin notification error: %s",
                    error,
                )

        return

    # SEARCH
    if state == "search":

        context.user_data.clear()

        found = []

        for product in get_products():

            name = str(
                product.get(
                    "name",
                    ""
                )
            ).lower()

            if text.lower() in name:

                found.append(
                    product
                )

        if not found:

            await update.message.reply_text(

                "❌ محصولی با این نام پیدا نشد.",

                reply_markup=main_keyboard(
                    user.id
                ),
            )

            return

        keyboard = []

        for product in found[:20]:

            keyboard.append(

                [

                    InlineKeyboardButton(

                        product.get(
                            "name",
                            "محصول"
                        ),

                        callback_data=(
                            f"product:{product.get('id')}"
                        ),

                    )

                ]

            )

        keyboard.append(

            [

                InlineKeyboardButton(
                    "🏠 خانه",
                    callback_data="home",
                )

            ]

        )

        await update.message.reply_text(

            "🔎 نتایج جستجو:",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        return

    # CUSTOM SEWING
    if state == "custom":

        context.user_data.clear()

        await update.message.reply_text(

            "🧵 توضیحات دوخت سفارشی شما دریافت شد ✅\n\n"
            "مدیریت فروشگاه بررسی می‌کند و با شما تماس می‌گیرد.",

            reply_markup=main_keyboard(
                user.id
            ),
        )

        if ADMIN_ID:

            try:

                await context.bot.send_message(

                    chat_id=int(
                        ADMIN_ID
                    ),

                    text=(

                        "🧵 درخواست دوخت سفارشی\n\n"

                        f"👤 مشتری: {user.full_name}\n"
                        f"🆔 User ID: {user.id}\n\n"
                        f"📝 توضیحات:\n{text}"

                    ),
                )

            except Exception as error:

                logger.exception(
                    "Custom sewing notification error: %s",
                    error,
                )

        return

    # ADMIN ADD NAME
    if is_admin(
        user.id
    ) and state == "admin_name":

        context.user_data[
            "new_product"
        ] = {
            "name": text
        }

        context.user_data[
            "state"
        ] = "admin_price"

        await update.message.reply_text(

            "💰 قیمت محصول را به افغانی ارسال کنید."

        )

        return

    # ADMIN PRICE
    if is_admin(
        user.id
    ) and state == "admin_price":

        try:

            price = float(
                text.replace(
                    ",",
                    "",
                )
            )

        except ValueError:

            await update.message.reply_text(
                "❌ لطفاً فقط عدد قیمت را ارسال کنید."
            )

            return

        context.user_data[
            "new_product"
        ][
            "price"
        ] = price

        context.user_data[
            "state"
        ] = "admin_stock"

        await update.message.reply_text(

            "📦 موجودی محصول را ارسال کنید."

        )

        return

    # ADMIN STOCK
    if is_admin(
        user.id
    ) and state == "admin_stock":

        try:

            stock = int(
                text
            )

        except ValueError:

            await update.message.reply_text(
                "❌ لطفاً فقط عدد موجودی را ارسال کنید."
            )

            return

        product = context.user_data[
            "new_product"
        ]

        product[
            "id"
        ] = next_product_id()

        product[
            "stock"
        ] = stock

        product[
            "description"
        ] = ""

        product[
            "photo"
        ] = ""

        data = get_products()

        data.append(
            product
        )

        save_json(
            PRODUCTS_FILE,
            data,
        )

        context.user_data.clear()

        await update.message.reply_text(

            "✅ محصول با موفقیت اضافه شد.",

            reply_markup=main_keyboard(
                user.id
            ),
        )

        return

    # ADMIN DELETE
    if is_admin(
        user.id
    ) and state == "admin_delete":

        data = get_products()

        new_data = [

            product

            for product in data

            if str(
                product.get(
                    "id"
                )
            ) != text

        ]

        if len(
            new_data
        ) == len(
            data
        ):

            await update.message.reply_text(

                "❌ محصولی با این ID پیدا نشد."

            )

            return

        save_json(
            PRODUCTS_FILE,
            new_data,
        )

        context.user_data.clear()

        await update.message.reply_text(

            "✅ محصول حذف شد.",

            reply_markup=main_keyboard(
                user.id
            ),
        )

        return

    # NORMAL MESSAGE
    await update.message.reply_text(

        "سلام 🌸\n\n"
        "پیام شما دریافت شد.\n"
        "برای استفاده از فروشگاه یکی از گزینه‌های زیر را انتخاب کنید.",

        reply_markup=main_keyboard(
            user.id
        ),
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.exception(
        "TELEGRAM ERROR: %s",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================

def build_application():

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    logger.info(
        "Telegram application created."
    )

    # COMMANDS

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel,
        )
    )

    # BUTTONS

    app.add_handler(
        CallbackQueryHandler(
            buttons,
        )
    )

    # TEXT

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_handler,
        )
    )

    # ERROR

    app.add_error_handler(
        error_handler
    )

    return app


def start_web_server_once():

    web_thread = threading.Thread(
        target=start_web_server,
        name="flask-web",
        daemon=True,
    )

    web_thread.start()

    logger.info(
        "Flask web server thread started."
    )


def run_telegram_once():

    app = None

    try:

        app = build_application()

        logger.info(
            "Starting Telegram polling..."
        )

        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
        )

        logger.warning(
            "Telegram polling stopped normally."
        )

    finally:

        logger.info(
            "Telegram polling cycle ended."
        )


def main():

    # TOKEN CHECK

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN is missing. "
            "Add BOT_TOKEN in Render Environment Variables."
        )

    logger.info(
        "BOT TOKEN loaded: True"
    )

    # RENDER WEB SERVER

    start_web_server_once()

    # TELEGRAM SUPERVISOR

    restart_delay = 5
    max_restart_delay = 60

    while True:

        try:

            logger.info(
                "Starting Telegram bot supervisor cycle..."
            )

            run_telegram_once()

            logger.warning(
                "Telegram polling returned. Restarting in %s seconds...",
                restart_delay,
            )

            time.sleep(
                restart_delay
            )

            restart_delay = 5

        except KeyboardInterrupt:

            logger.info(
                "Bot stopped by keyboard interrupt."
            )

            break

        except SystemExit:

            logger.info(
                "Bot received SystemExit."
            )

            break

        except Exception as error:

            logger.exception(
                "FATAL TELEGRAM/POLLING ERROR: %s",
                error,
            )

            logger.warning(
                "Bot will automatically restart in %s seconds.",
                restart_delay,
            )

            time.sleep(
                restart_delay
            )

            restart_delay = min(
                restart_delay * 2,
                max_restart_delay,
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        logger.info(
            "Mohammadi Fashion Bot stopped."
        )

    except Exception as error:

        logger.exception(
            "UNHANDLED STARTUP ERROR: %s",
            error,
        )

        raise
```
