# -*- coding: utf-8 -*-

import os
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


# ============================================================
# Mohammadi Fashion Bot
# Render + python-telegram-bot
# ============================================================


TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()

PORT_RAW = os.getenv("PORT", "10000").strip()

DATA_FILE = Path(
    os.getenv("DATA_FILE", "data.json")
)


# ============================================================
# Environment variables
# ============================================================


try:
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW else 0
except ValueError:
    ADMIN_ID = 0


try:
    PORT = int(PORT_RAW)
except ValueError:
    PORT = 10000


# ============================================================
# Logging
# ============================================================


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(
    "mohammadi-fashion"
)


# ============================================================
# Default data
# ============================================================


DEFAULT_DATA = {
    "products": {
        "1": {
            "name": "بخمل نگین دار",
            "price": 700,
            "description": "لباس بخمل نگین دار با کیفیت عالی",
            "photo": "",
            "active": True,
        }
    },
    "orders": []
}


# ============================================================
# Data functions
# ============================================================


def copy_default_data():
    return json.loads(
        json.dumps(
            DEFAULT_DATA,
            ensure_ascii=False
        )
    )


def save_data(data):
    try:
        DATA_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temp_file = DATA_FILE.with_name(
            DATA_FILE.name + ".tmp"
        )

        with temp_file.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

        temp_file.replace(
            DATA_FILE
        )

        return True

    except Exception:
        logger.exception(
            "Could not save data"
        )
        return False


def load_data():
    if not DATA_FILE.exists():
        data = copy_default_data()

        save_data(data)

        return data

    try:
        with DATA_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "data.json must contain an object"
            )

        if not isinstance(
            data.get("products"),
            dict
        ):
            data["products"] = {}

        if not isinstance(
            data.get("orders"),
            list
        ):
            data["orders"] = []

        return data

    except Exception:
        logger.exception(
            "Could not read data.json; "
            "using default data"
        )

        return copy_default_data()


# ============================================================
# Permission
# ============================================================


def is_admin(update: Update):
    user = update.effective_user

    return bool(
        ADMIN_ID
        and user
        and user.id == ADMIN_ID
    )


# ============================================================
# Keyboards
# ============================================================


def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛍 محصولات",
                    callback_data="products"
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 سفارش‌های من",
                    callback_data="my_orders"
                )
            ],
            [
                InlineKeyboardButton(
                    "☎️ تماس با ما",
                    callback_data="contact"
                )
            ],
        ]
    )


def admin_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ افزودن محصول",
                    callback_data="admin_add"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 مدیریت محصولات",
                    callback_data="admin_products"
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 سفارش‌ها",
                    callback_data="admin_orders"
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 فروشگاه",
                    callback_data="home"
                )
            ],
        ]
    )


def back_admin_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ پنل مدیریت",
                    callback_data="admin_home"
                )
            ]
        ]
    )


def products_keyboard(data):
    rows = []

    for product_id, product in data["products"].items():

        if product.get(
            "active",
            True
        ):

            name = str(
                product.get(
                    "name",
                    "محصول"
                )
            )

            price = product.get(
                "price",
                0
            )

            rows.append(
                [
                    InlineKeyboardButton(
                        f"{name} — {price} افغانی",
                        callback_data=f"product:{product_id}"
                    )
                ]
            )

    rows.append(
        [
            InlineKeyboardButton(
                "🏠 برگشت",
                callback_data="home"
            )
        ]
    )

    return InlineKeyboardMarkup(
        rows
    )


# ============================================================
# Product helpers
# ============================================================


def product_text(product):
    return (
        f"🛍 <b>{product.get('name', 'محصول')}</b>\n\n"
        f"💰 قیمت: "
        f"<b>{product.get('price', 0)} افغانی</b>\n"
        f"📝 {product.get('description', '')}"
    )


def next_product_id(products):
    numeric_ids = []

    for product_id in products:

        try:
            numeric_ids.append(
                int(product_id)
            )

        except (
            TypeError,
            ValueError
        ):
            continue

    return str(
        max(
            numeric_ids,
            default=0
        ) + 1
    )


# ============================================================
# /start
# ============================================================


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data.clear()

    if not update.message:
        return

    text = (
        "🌸 <b>به Mohammadi Fashion خوش آمدید</b> 🌸\n\n"
        "فروشگاه لباس زنانه\n"
        "برای دیدن محصولات از دکمه‌های زیر استفاده کنید."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# ============================================================
# /admin
# ============================================================


async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    if not is_admin(update):

        await update.message.reply_text(
            "⛔ این بخش فقط برای مدیر فروشگاه است."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ <b>پنل مدیریت Mohammadi Fashion</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# ============================================================
# /cancel
# ============================================================


async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    context.user_data.clear()

    if update.message:

        await update.message.reply_text(
            "لغو شد.",
            reply_markup=main_keyboard()
        )


# ============================================================
# Callback buttons
# ============================================================


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    data = query.data or ""


    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "home":

        context.user_data.clear()

        await query.edit_message_text(
            "🌸 <b>Mohammadi Fashion</b> 🌸\n\n"
            "به فروشگاه خوش آمدید.",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

        return


    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    if data == "products":

        context.user_data.clear()

        current = load_data()

        active_products = [
            product
            for product in current["products"].values()
            if product.get(
                "active",
                True
            )
        ]

        if not active_products:

            await query.edit_message_text(
                "فعلاً محصولی برای نمایش وجود ندارد.",
                reply_markup=main_keyboard()
            )

            return

        await query.edit_message_text(
            "🛍 <b>محصولات فروشگاه</b>\n\n"
            "یک محصول را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=products_keyboard(
                current
            )
        )

        return


    # --------------------------------------------------------
    # PRODUCT
    # --------------------------------------------------------

    if data.startswith("product:"):

        product_id = data.split(
            ":",
            1
        )[1]

        current = load_data()

        product = current["products"].get(
            product_id
        )

        if (
            not product
            or not product.get(
                "active",
                True
            )
        ):

            await query.edit_message_text(
                "این محصول دیگر موجود نیست.",
                reply_markup=main_keyboard()
            )

            return

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🛒 ثبت سفارش",
                        callback_data=f"order:{product_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ محصولات",
                        callback_data="products"
                    )
                ],
            ]
        )

        await query.edit_message_text(
            product_text(product),
            parse_mode="HTML",
            reply_markup=buttons
        )

        return


    # --------------------------------------------------------
    # ORDER START
    # --------------------------------------------------------

    if data.startswith("order:"):

        product_id = data.split(
            ":",
            1
        )[1]

        current = load_data()

        product = current["products"].get(
            product_id
        )

        if (
            not product
            or not product.get(
                "active",
                True
            )
        ):

            await query.edit_message_text(
                "این محصول دیگر موجود نیست.",
                reply_markup=main_keyboard()
            )

            return

        context.user_data.clear()

        context.user_data[
            "order_product_id"
        ] = product_id

        context.user_data[
            "state"
        ] = "waiting_name"

        await query.edit_message_text(
            f"🛒 سفارش "
            f"<b>{product.get('name', 'محصول')}</b>\n\n"
            "لطفاً نام خود را ارسال کنید:\n\n"
            "برای لغو، /cancel را بزنید.",
            parse_mode="HTML"
        )

        return


    # --------------------------------------------------------
    # MY ORDERS
    # --------------------------------------------------------

    if data == "my_orders":

        context.user_data.clear()

        user = update.effective_user

        if not user:
            return

        current = load_data()

        orders = [
            order
            for order in current["orders"]
            if order.get(
                "user_id"
            ) == user.id
        ]

        if not orders:

            text = (
                "📦 هنوز سفارشی ثبت نکرده‌اید."
            )

        else:

            lines = [
                "📦 <b>سفارش‌های شما</b>\n"
            ]

            for order in orders[-10:]:

                lines.append(
                    f"#{order.get('id', '-')}"
                    f" — {order.get('product_name', '-')}"
                    f" — {order.get('price', 0)} افغانی"
                    f" — {order.get('status', '-')}"
                )

            text = "\n".join(
                lines
            )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

        return


    # --------------------------------------------------------
    # CONTACT
    # --------------------------------------------------------

    if data == "contact":

        context.user_data.clear()

        await query.edit_message_text(
            "☎️ <b>تماس با Mohammadi Fashion</b>\n\n"
            "برای سفارش و هماهنگی، به همین ربات پیام بفرستید.\n"
            "📍 کابل، ده افغانان",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

        return


    # --------------------------------------------------------
    # ADMIN HOME
    # --------------------------------------------------------

    if data == "admin_home":

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        context.user_data.clear()

        await query.edit_message_text(
            "⚙️ <b>پنل مدیریت Mohammadi Fashion</b>",
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )

        return


    # --------------------------------------------------------
    # ADMIN ADD PRODUCT
    # --------------------------------------------------------

    if data == "admin_add":

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        context.user_data.clear()

        context.user_data[
            "state"
        ] = "admin_product_name"

        await query.edit_message_text(
            "➕ <b>افزودن محصول</b>\n\n"
            "نام محصول را ارسال کنید:\n\n"
            "برای لغو، /cancel را بزنید.",
            parse_mode="HTML",
            reply_markup=back_admin_keyboard()
        )

        return


    # --------------------------------------------------------
    # ADMIN PRODUCTS
    # --------------------------------------------------------

    if data == "admin_products":

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        current = load_data()

        rows = []

        for product_id, product in current["products"].items():

            status = (
                "فعال"
                if product.get(
                    "active",
                    True
                )
                else "غیرفعال"
            )

            rows.append(
                [
                    InlineKeyboardButton(
                        f"{product.get('name', 'محصول')} | {status}",
                        callback_data=f"admin_product:{product_id}"
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "⬅️ پنل مدیریت",
                    callback_data="admin_home"
                )
            ]
        )

        if not current["products"]:

            text = (
                "📋 هنوز محصولی ثبت نشده است."
            )

        else:

            text = (
                "📋 <b>مدیریت محصولات</b>\n\n"
                "یک محصول را انتخاب کنید:"
            )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                rows
            )
        )

        return


    # --------------------------------------------------------
    # ADMIN PRODUCT DETAILS
    # --------------------------------------------------------

    if data.startswith("admin_product:"):

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        product_id = data.split(
            ":",
            1
        )[1]

        current = load_data()

        product = current["products"].get(
            product_id
        )

        if not product:

            await query.edit_message_text(
                "محصول پیدا نشد.",
                reply_markup=back_admin_keyboard()
            )

            return

        status = (
            "فعال"
            if product.get(
                "active",
                True
            )
            else "غیرفعال"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 تغییر وضعیت",
                        callback_data=f"toggle_product:{product_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🗑 حذف محصول",
                        callback_data=f"delete_product:{product_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ محصولات",
                        callback_data="admin_products"
                    )
                ],
            ]
        )

        await query.edit_message_text(
            f"🛍 <b>{product.get('name', 'محصول')}</b>\n\n"
            f"💰 قیمت: "
            f"{product.get('price', 0)} افغانی\n"
            f"📌 وضعیت: {status}\n"
            f"📝 {product.get('description', '')}",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        return


    # --------------------------------------------------------
    # TOGGLE PRODUCT
    # --------------------------------------------------------

    if data.startswith("toggle_product:"):

        if not is_admin(update):

            await query.edit_message_text(
                "⛔ دسترسی ندارید."
            )

            return

        product_id = data.split(
            ":",
            1
        )[1]

        current = load_data()

        product = current["products"].get(
            product_id
        )

        if not p
