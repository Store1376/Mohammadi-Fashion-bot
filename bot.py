import os
import logging
import threading

from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

PORT = int(os.getenv("PORT", "10000"))


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

web_app = Flask(__name__)


@web_app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "Mohammadi Fashion Bot",
        "status": "running",
    })


@web_app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "status": "healthy",
    })


def run_web_server():
    web_app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
    )


# =========================================================
# KEYBOARDS
# =========================================================

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
                callback_data="orders"
            ),
            InlineKeyboardButton(
                "📞 تماس با ما",
                callback_data="contact"
            ),
        ],
    ]

    if ADMIN_ID and str(user_id) == ADMIN_ID:
        buttons.append([
            InlineKeyboardButton(
                "⚙️ مدیریت",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(buttons)


def home_keyboard(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🏠 صفحه اصلی",
                callback_data="home"
            )
        ]
    ])


# =========================================================
# /START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    logger.info(
        "START received from user %s",
        user.id
    )

    await update.message.reply_text(
        f"👋 سلام {user.first_name or 'دوست عزیز'}\n\n"
        "🌸 به Mohammadi Fashion خوش آمدید.\n\n"
        "فروشگاه لباس‌های زنانه\n"
        "برای شروع یکی از گزینه‌های زیر را انتخاب کنید.",
        reply_markup=main_keyboard(user.id),
    )


# =========================================================
# /HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "راهنمای Mohammadi Fashion\n\n"
        "/start - شروع ربات\n"
        "/help - راهنما\n\n"
        "برای استفاده از فروشگاه از دکمه‌های زیر استفاده کنید.",
        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# =========================================================
# BUTTONS
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    data = query.data

    logger.info(
        "Button received: %s from user %s",
        data,
        user_id
    )

    # ---------------- HOME ----------------

    if data == "home":

        await query.edit_message_text(
            "🏠 صفحه اصلی Mohammadi Fashion",
            reply_markup=main_keyboard(user_id),
        )

        return

    # ---------------- PRODUCTS ----------------

    if data == "products":

        await query.edit_message_text(
            "👗 محصولات فروشگاه\n\n"
            "در نسخه بعدی محصولات، عکس، قیمت و موجودی "
            "را اینجا اضافه می‌کنیم.",
            reply_markup=home_keyboard(user_id),
        )

        return

    # ---------------- CART ----------------

    if data == "cart":

        await query.edit_message_text(
            "🛒 سبد خرید شما فعلاً خالی است.",
            reply_markup=home_keyboard(user_id),
        )

        return

    # ---------------- ORDERS ----------------

    if data == "orders":

        await query.edit_message_text(
            "📦 سفارش‌های من\n\n"
            "هنوز سفارشی ثبت نشده است.",
            reply_markup=home_keyboard(user_id),
        )

        return

    # ---------------- CONTACT ----------------

    if data == "contact":

        await query.edit_message_text(
            "📞 تماس با ما\n\n"
            "Mohammadi Fashion\n"
            "برای سفارش و معلومات بیشتر با مدیریت تماس بگیرید.",
            reply_markup=home_keyboard(user_id),
        )

        return

    # ---------------- ADMIN ----------------

    if data == "admin":

        if not ADMIN_ID or str(user_id) != ADMIN_ID:

            await query.edit_message_text(
                "❌ دسترسی غیرمجاز.",
                reply_markup=home_keyboard(user_id),
            )

            return

        await query.edit_message_text(
            "⚙️ پنل مدیریت Mohammadi Fashion\n\n"
            "پنل مدیریت آماده است.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🏠 صفحه اصلی",
                        callback_data="home"
                    )
                ]
            ]),
        )

        return


# =========================================================
# NORMAL TEXT
# =========================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    logger.info(
        "Message received from %s: %s",
        update.effective_user.id,
        text
    )

    await update.message.reply_text(
        "پیام شما دریافت شد ✅\n\n"
        "لطفاً از دکمه‌های فروشگاه استفاده کنید.",
        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Telegram error: %s",
        context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # ---------------- TOKEN CHECK ----------------

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN is not configured in Render."
        )

    logger.info(
        "BOT TOKEN loaded: %s",
        bool(TOKEN)
    )

    # ---------------- WEB SERVER ----------------

    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True,
    )

    web_thread.start()

    logger.info(
        "Render health server started on port %s",
        PORT
    )

    # ---------------- TELEGRAM APP ----------------

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    logger.info(
        "Telegram application created."
    )

    # ---------------- HANDLERS ----------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    app.add_error_handler(
        error_handler
    )

    # ---------------- START ----------------

    logger.info(
        "Mohammadi Fashion Bot is starting..."
    )

    logger.info(
        "Polling started."
    )

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
