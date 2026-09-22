import os
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# Mohammadi Fashion Bot
# =========================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
PORT = int(os.getenv("PORT", "10000"))

DATA_FILE = Path(os.getenv("DATA_FILE", "data.json"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("mohammadi-fashion")


DEFAULT_DATA = {
    "products": {
        "1": {
            "name": "بخمل نگین دار",
            "price": 700,
            "description": "لباس بخمل نگین دار",
            "photo": "",
            "active": True,
        }
    },
    "orders": [],
}


def load_data():
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA)
        return json.loads(
            json.dumps(DEFAULT_DATA, ensure_ascii=False)
        )

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if "products" not in data:
            data["products"] = {}

        if "orders" not in data:
            data["orders"] = []

        return data

    except Exception:
        logger.exception("Could not read data file")

        return json.loads(
            json.dumps(DEFAULT_DATA, ensure_ascii=False)
        )


def save_data(data):
    temp = DATA_FILE.with_suffix(".tmp")

    with temp.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    temp.replace(DATA_FILE)


DATA = load_data()
DATA_LOCK = threading.Lock()


def is_admin(update: Update) -> bool:
    return bool(
        ADMIN_ID
        and update.effective_user
        and update.effective_user.id == ADMIN_ID
    )


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛍 محصولات",
                callback_data="products",
            )
        ],
        [
            InlineKeyboardButton(
                "📦 سفارش‌های من",
                callback_data="my_orders",
            )
        ],
        [
            InlineKeyboardButton(
                "☎️ تماس با ما",
                callback_data="contact",
            )
        ],
    ])


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="admin_add",
            )
        ],
        [
            InlineKeyboardButton(
                "📋 مدیریت محصولات",
                callback_data="admin_products",
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
                "🏠 فروشگاه",
                callback_data="home",
            )
        ],
    ])


def products_keyboard(data):
    rows = []

    for pid, product in data["products"].items():

        if product.get("active", True):

            rows.append([
                InlineKeyboardButton(
                    f"{product.get('name', 'محصول')} — "
                    f"{product.get('price', 0)} افغانی",
                    callback_data=f"product:{pid}",
                )
            ])

    rows.append([
        InlineKeyboardButton(
            "🏠 برگشت",
            callback_data="home",
        )
    ])

    return InlineKeyboardMarkup(rows)


def admin_products_keyboard(data):
    rows = []

    for pid, product in data["products"].items():

        rows.append([
            InlineKeyboardButton(
                f"{product.get('name', 'محصول')} ({pid})",
                callback_data=f"edit:{pid}",
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "➕ افزودن",
            callback_data="admin_add",
        )
    ])

    rows.append([
        InlineKeyboardButton(
            "🏠 برگشت",
            callback_data="admin",
        )
    ])

    return InlineKeyboardMarkup(rows)


def next_product_id(data):

    ids = []

    for key in data["products"]:

        try:
            ids.append(int(key))
        except ValueError:
            pass

    return str(max(ids, default=0) + 1)


def product_text(product):

    return (
        f"🛍 <b>{product.get('name', 'محصول')}</b>\n\n"
        f"💰 قیمت: <b>{product.get('price', 0)} افغانی</b>\n"
        f"📝 {product.get('description', '')}"
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    text = (
        "🌸 <b>به Mohammadi Fashion خوش آمدید</b> 🌸\n\n"
        "فروشگاه لباس زنانه\n"
        "برای دیدن محصولات از دکمه زیر استفاده کنید."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(update):

        await update.message.reply_text(
            "⛔ این بخش فقط برای مدیر فروشگاه است."
        )

        return

    await update.message.reply_text(
        "⚙️ <b>پنل مدیریت</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # -------------------------
    # HOME
    # -------------------------

    if data == "home":

        await query.edit_message_text(
            "🌸 <b>Mohammadi Fashion</b> 🌸\n\n"
            "به فروشگاه خوش آمدید.",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

        return

    # -------------------------
    # PRODUCTS
    # -------------------------

    if data == "products":

        with DATA_LOCK:

            current = json.loads(
                json.dumps(
                    DATA,
                    ensure_ascii=False,
                )
            )

        if not any(
            p.get("active", True)
            for p in current["products"].values()
        ):

            await query.edit_message_text(
                "فعلاً محصولی برای نمایش وجود ندارد.",
                reply_markup=main_keyboard(),
            )

            return

        await query.edit_message_text(
            "🛍 <b>محصولات فروشگاه</b>\n\n"
            "یک محصول را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=products_keyboard(current),
        )

        return

    # -------------------------
    # PRODUCT
    # -------------------------

    if data.startswith("product:"):

        pid = data.split(":", 1)[1]

        with DATA_LOCK:

            product = DATA["products"].get(pid)

            product = (
                dict(product)
                if product
                else None
            )

        if not product or not product.get(
            "active",
            True,
        ):

            await query.edit_message_text(
                "این محصول دیگر موجود نیست.",
                reply_markup=main_keyboard(),
            )

            return

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🛒 ثبت سفارش",
                    callback_data=f"order:{pid}",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ محصولات",
                    callback_data="products",
                )
            ],
        ])

        if product.get("photo"):

            try:

                await query.message.reply_photo(
                    photo=product["photo"],
                    caption=product_text(product),
                    parse_mode="HTML",
                    reply_markup=buttons,
                )

                await query.delete_message()

                return

            except Exception:

                logger.exception(
                    "Could not send product photo"
                )

        await query.edit_message_text(
            product_text(product),
            parse_mode="HTML",
            reply_markup=buttons,
        )

        return

    # -------------------------
    # ORDER
    # -------------------------

    if data.startswith("order:"):

        pid = data.split(":", 1)[1]

        with DATA_LOCK:

            product = DATA["products"].get(pid)

            product = (
                dict(product)
                if product
                else None
            )

        if not product or not product.get(
            "active",
            True,
        ):

            await query.edit_message_text(
                "این محصول دیگر موجود نیست.",
                reply_markup=main_keyboard(),
            )

            return

        context.user_data[
            "order_product_id"
        ] = pid

        context.user_data[
            "state"
        ] = "waiting_name"

        await query.edit_message_text(
            f"🛒 سفارش <b>{product.get('name')}</b>\n\n"
            "لطفاً نام خود را ارسال کنید:",
            parse_mode="HTML",
        )

        return

    # -------------------------
    # MY ORDERS
    # -------------------------

    if data == "my_orders":

        uid = update.effective_user.id

        with DATA_LOCK:

            orders = [
                o
                for o in DATA["orders"]
                if o.get("user_id") == uid
            ]

        if not orders:

            text = "📦 هنوز سفارشی ثبت نکرده‌اید."

        else:

            lines = [
                "📦 <b>سفارش‌های شما</b>\n"
            ]

            for o in orders[-10:]:

                lines.append(
                    f"#{o['id']} — "
                    f"{o['product_name']} — "
                    f"{o['price']} افغانی — "
                    f"{o['status']}"
                )

            text = "\n".join(lines)

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

        return

    # -------------------------
    # CONTACT
    # -------------------------

    if data == "contact":

        await query.edit_message_text(
            "☎️ <b>تماس با Mohammadi Fashion</b>\n\n"
            "برای سفارش و هماهنگی، همین ربات پیام بفرستید.\n"
            "📍 کابل، ده افغانان",
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

        return

    # -------------------------
    # ADMIN
    # -------------------------

    if data == "admin":

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        await query.edit_message_text(
            "⚙️ <b>پنل مدیریت</b>",
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )

        return

    # -------------------------
    # ADD PRODUCT
    # -------------------------

    if data == "admin_add":

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        context.user_data.clear()

        context.user_data[
            "state"
        ] = "admin_name"

        await query.edit_message_text(
            "➕ نام محصول را بفرستید:"
        )

        return

    # -------------------------
    # ADMIN PRODUCTS
    # -------------------------

    if data == "admin_products":

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        with DATA_LOCK:

            current = json.loads(
                json.dumps(
                    DATA,
                    ensure_ascii=False,
                )
            )

        await query.edit_message_text(
            "📋 <b>مدیریت محصولات</b>",
            parse_mode="HTML",
            reply_markup=admin_products_keyboard(
                current
            ),
        )

        return

    # -------------------------
    # EDIT PRODUCT
    # -------------------------

    if data.startswith("edit:"):

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        pid = data.split(":", 1)[1]

        with DATA_LOCK:

            product = DATA["products"].get(pid)

        if not product:

            await query.edit_message_text(
                "محصول پیدا نشد.",
                reply_markup=admin_products_keyboard(
                    DATA
                ),
            )

            return

        context.user_data[
            "edit_pid"
        ] = pid

        await query.edit_message_text(

            f"🛠 <b>{product['name']}</b>\n\n"
            "چه کاری انجام شود؟",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💰 تغییر قیمت",
                        callback_data=f"price:{pid}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🖼 تغییر عکس",
                        callback_data=f"photo:{pid}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📝 تغییر نام",
                        callback_data=f"name:{pid}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🗑 حذف محصول",
                        callback_data=f"delete:{pid}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ برگشت",
                        callback_data="admin_products",
                    )
                ],
            ]),
        )

        return

    # -------------------------
    # EDIT ACTION
    # -------------------------

    if data.startswith(
        ("price:", "photo:", "name:")
    ):

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        action, pid = data.split(":", 1)

        context.user_data[
            "edit_pid"
        ] = pid

        context.user_data[
            "state"
        ] = {
            "price": "edit_price",
            "photo": "edit_photo",
            "name": "edit_name",
        }[action]

        prompts = {

            "price":
                "💰 قیمت جدید را فقط به عدد بفرستید:",

            "photo":
                "🖼 عکس جدید محصول را به صورت عکس ارسال کنید:",

            "name":
                "📝 نام جدید محصول را بفرستید:",
        }

        await query.edit_message_text(
            prompts[action]
        )

        return

    # -------------------------
    # DELETE
    # -------------------------

    if data.startswith("delete:"):

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        pid = data.split(":", 1)[1]

        with DATA_LOCK:

            DATA["products"].pop(
                pid,
                None,
            )

            save_data(DATA)

        await query.edit_message_text(
            "✅ محصول حذف شد.",
            reply_markup=admin_products_keyboard(
                DATA
            ),
        )

        return

    # -------------------------
    # ADMIN ORDERS
    # -------------------------

    if data == "admin_orders":

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        with DATA_LOCK:

            orders = list(
                DATA["orders"][-20:]
            )

        if not orders:

            text = (
                "📦 هنوز سفارشی ثبت نشده است."
            )

        else:

            lines = [
                "📦 <b>آخرین سفارش‌ها</b>\n"
            ]

            for o in orders:

                lines.append(
                    f"#{o['id']} | "
                    f"{o['product_name']} | "
                    f"{o['price']} افغانی\n"
                    f"👤 {o['customer_name']} | "
                    f"@{o.get('username', '-')} | "
                    f"{o['status']}"
                )

            text = "\n\n".join(lines)

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )

        return


async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    state = context.user_data.get("state")

    # =========================
    # CUSTOMER ORDER
    # =========================

    if state == "waiting_name":

        context.user_data[
            "customer_name"
        ] = update.message.text.strip()

        context.user_data[
            "state"
        ] = "waiting_phone"

        await update.message.reply_text(
            "📱 لطفاً شماره تماس خود را ارسال کنید:"
        )

        return

    if state == "waiting_phone":

        phone = update.message.text.strip()

        pid = context.user_data.get(
            "order_product_id"
        )

        name = context.user_data.get(
            "customer_name",
            "-",
        )

        with DATA_LOCK:

            product = DATA["products"].get(pid)

            if not product:

                await update.message.reply_text(
                    "این محصول دیگر موجود نیست.",
                    reply_markup=main_keyboard(),
                )

                context.user_data.clear()

                return

            order_id = (
                len(DATA["orders"]) + 1
            )

            order = {

                "id": order_id,

                "user_id":
                    update.effective_user.id,

                "username":
                    update.effective_user.username
                    or "-",

                "customer_name":
                    name,

                "phone":
                    phone,

                "product_id":
                    pid,

                "product_name":
                    product["name"],

                "price":
                    product["price"],

                "status":
                    "در انتظار تماس",
            }

            DATA["orders"].append(
                order
            )

            save_data(DATA)

        context.user_data.clear()

        await update.message.reply_text(

            f"✅ سفارش شما با موفقیت ثبت شد.\n\n"
            f"شماره سفارش: <b>#{order_id}</b>\n"
            f"محصول: {order['product_name']}\n"
            f"قیمت: {order['price']} افغانی\n\n"
            "به‌زودی برای هماهنگی با شما تماس می‌گیریم.",

            parse_mode="HTML",

            reply_markup=main_keyboard(),
        )

        if ADMIN_ID:

            try:

                await context.bot.send_message(

                    chat_id=ADMIN_ID,

                    text=(

                        f"🔔 <b>سفارش جدید #{order_id}</b>\n"
                        f"محصول: {order['product_name']}\n"
                        f"قیمت: {order['price']} افغانی\n"
                        f"نام: {name}\n"
                        f"شماره: {phone}\n"
                        f"کاربر: @{order['username']}"
                    ),

                    parse_mode="HTML",
              
