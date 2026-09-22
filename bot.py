# -*- coding: utf-8 -*-
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

# ==========================================
# Mohammadi Fashion Bot (Unicode Safe Version)
# ==========================================

TOKEN = os.getenv("BOT_TOKEN", "8850373531:AAHYa_Fdz4tLlZik8pL8uTBsaYHp8b80U-0").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
PORT = int(os.getenv("PORT", "10000"))
DATA_FILE = Path(os.getenv("DATA_FILE", "data.json"))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("mohammadi-fashion")

# متون یونیکد برای پیش‌فرض‌ها
DEFAULT_PRODUCT_NAME = u"\u0628\u062e\u0645\u0644 \u0646\u06af\u06cc\u0646 \u062f\u0627\u0631"
DEFAULT_PRODUCT_DESC = u"\u0644\u0628\u0627\u0633 \u0628\u062e\u0645\u0644 \u0646\u06af\u06cc\u0646 \u062f\u0627\u0631"

DEFAULT_DATA = {
    "products": {
        "1": {
            "name": DEFAULT_PRODUCT_NAME,
            "price": 700,
            "description": DEFAULT_PRODUCT_DESC,
            "photo": "",
            "active": True,
        }
    },
    "orders": [],
}

def load_data():
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if "products" not in data: data["products"] = {}
        if "orders" not in data: data["orders"] = []
        return data
    except Exception:
        logger.exception("Could not read data file")
        return json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))

def save_data(data):
    temp = DATA_FILE.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp.replace(DATA_FILE)

DATA = load_data()
DATA_LOCK = threading.Lock()

def is_admin(update: Update) -> bool:
    return bool(ADMIN_ID and update.effective_user and update.effective_user.id == ADMIN_ID)

# دکمه‌های اصلی و ادمین با متون یونیکد امن
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(u"\ud83d\udc5d \u0645\u062d\u0635\u0648\u0644\u0627\u062a", callback_data="products")],
        [InlineKeyboardButton(u"\ud83d\udce6 \u0633\u0641\u0627\u0631\u0634\u200c\u0647\u0627\u06cc \u0645\u0646", callback_data="my_orders")],
        [InlineKeyboardButton(u"\u260e\ufe0f \u062a\u0645\u0627\u0633 \u0628\u0627 \u0645\u0627", callback_data="contact")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(u"\u2795 \u0627\u0641\u0632\u0648\u062f\u0646 \u0645\u062d\u0635\u0648\u0644", callback_data="admin_add")],
        [InlineKeyboardButton(u"\ud83d\udccb \u0645\u0622\u06cc\u0631\u06cc\u062a \u0645\u062d\u0635\u0648\u0644\u0627\u062a", callback_data="admin_products")],
        [InlineKeyboardButton(u"\ud83d\udce6 \u0633\u0641\u0627\u0631\u0634\u200c\u0647\u0627", callback_data="admin_orders")],
        [InlineKeyboardButton(u"\ud83c\udfe0 \u0641\u0631\u0648\u0634\u06af\u0627\u0647", callback_data="home")]
    ])

def products_keyboard(data):
    rows = []
    for pid, product in data["products"].items():
        if product.get("active", True):
            name = product.get('name', u'\u0645\u062d\u0635\u0648\u0644')
            price = product.get('price', 0)
            rows.append([InlineKeyboardButton(f"{name} \u2014 {price} \u0627\u0641\u063a\u0627\u0646\u06cc", callback_data=f"product:{pid}")])
    rows.append([InlineKeyboardButton(u"\ud83c\udfe0 \u0628\u0631\u06af\u0634\u062a", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def admin_products_keyboard(data):
    rows = []
    for pid, product in data["products"].items():
        name = product.get('name', u'\u0645\u062d\u0635\u0648\u0644')
        rows.append([InlineKeyboardButton(f"{name} ({pid})", callback_data=f"edit:{pid}")])
    rows.append([InlineKeyboardButton(u"\u2795 \u0627\u0641\u0632\u0648\u062f\u0646", callback_data="admin_add")])
    rows.append([InlineKeyboardButton(u"\ud83c\udfe0 \u0628\u0631\u06af\u0634\u062a", callback_data="admin")])
    return InlineKeyboardMarkup(rows)

def product_text(product):
    return (
        f"\ud83d\udc5d <b>{product.get('name')}</b>\n\n"
        f"\ud83d\udcb0 \u0642\u06cc\u0645\u062a: <b>{product.get('price', 0)} \u0627\u0641\u063a\u0627\u0646\u06cc</b>\n"
        f"\ud83d\udcdd {product.get('description', '')}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = u"\ud83c\udf38 <b>\u0628\u0647 Mohammadi Fashion \u062e\u0648\u0634 \u0622\u0645\u062f\u06cc\u062f</b> \ud83c\udf38\n\n\u0641\u0631\u0648\u0634\u06af\u0627\u0647 \u0644\u0628\u0627\u0633 \u063convenient\u0647\n\u0628\u0631\u0627\u06cc \u062f\u06cc\u062f\u0646 \u0645\u062d\u0635\u0648\u0644\u0627\u062a \u0627\u0632 \u062f\u06a9\u0645\u0647 \u0632\u06cc\u0631 \u0627\u063a\u0627\u0632 \u06a9\u0646\u06cc\u062f."
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(u"\u26d4 \u062a\u0648\u062c\u0647! \u062a\u0646\u0647\u0627 \u0645\u062f\u06cc\u0631 \u062f\u0633\u062a\u0631\u0633\u06cc \u062f\u0627\u0631\u062f.")
        return
    await update.message.reply_text(u"\u2699\ufe0f <b>\u067e\u0646\u0644 \u0645\u062f\u06cc\u0631\u06cc\u062a</b>", parse_mode="HTML", reply_markup=admin_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        await query.edit_message_text(u"\ud83c\udf38 <b>Mohammadi Fashion</b> \ud83c\udf38\n\n\u0628\u0647 \u0641\u0631\u064\u0634\u06af\u0627\u0647 \u062e\u0648\u0634 \u0622\u0645\u062f\u06cc\u062f.", parse_mode="HTML", reply_markup=main_keyboard())
        return

    if data == "products":
        with DATA_LOCK: current = json.loads(json.dumps(DATA, ensure_ascii=False))
        if not any(p.get("active", True) for p in current["products"].values()):
            await query.edit_message_text(u"\u0641\u0639\u0644\u0627\u064b \u0645\u062d\u0635\u0648\u0644\u06cc \u0645\u0648\u062c\u0648\u062f \u0646\u06cc\u0633\u062a.", reply_markup=main_keyboard())
            return
        await query.edit_message_text(u"\ud83d\udc5d <b>\u0645\u062d\u0635\u0648\u0644\u0627\u062a \u0641\u0631\u0648\u0634\u06af\u0627\u0647</b>\n\n\u06cc\u06a9\u062e \u0631\u0627 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f:", parse_mode="HTML", reply_markup=products_keyboard(current))
        return

    if data.startswith("product:"):
        pid = data.split(":", 1)[1]
        with DATA_LOCK:
            product = DATA["products"].get(pid)
            product = dict(product) if product else None
        if not product or not product.get("active", True):
            await query.edit_message_text(u"\u0627\u06cc\u0646 \u0645\u062d\u0635\u0648\u0644 \u0646\u0627\u0645\u0648\u062c\u0648\u062f \u0634\u062f\u0647 \u0627\u0633\u062a.", reply_markup=main_keyboard())
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(u"\ud83d\uded2 \u062b\u0628\u062a \u0633\u0641\u0627\u0631\u0634", callback_data=f"order:{pid}")],
            [InlineKeyboardButton(u"\u2b05\ufe0f \u0645\u062d\u0635\u0648\u0644\u0627\u062a", callback_data="products")]
        ])

        if product.get("photo"):
            try:
                await query.message.reply_photo(photo=product["photo"], caption=product_text(product), parse_mode="HTML", reply_markup=buttons)
                await query.delete_message()
                return
            except Exception:
                logger.exception("Could not send photo")

        await query.edit_message_text(product_text(product), parse_mode="HTML", reply_markup=buttons)
        return

    if data.startswith("order:"):
        pid = data.split(":", 1)[1]
        with DATA_LOCK: product = DATA["products"].get(pid)
        if not product: return
        context.user_data["order_product_id"] = pid
        context.user_data["state"] = "waiting_name"
        await query.edit_message_text(f"\ud83d\uded2 \u0633\u0641\u0627\u0631\u0634 <b>{product.get('name')}</b>\n\n\u0644\u063a\u0641\u0627\u064b \u0646\u0627\u0645 \u062e\u0648\u062f \u0631\u0627 \u0627\u0631\u0633\u0627\u0646 \u06a9\u0646\u06cc\u062f:", parse_mode="HTML")
        return

    if data == "contact":
        await query.edit_message_text(u"\u260e\ufe0f <b>\u062a\u0645\u0627\u0633 \u0628\u0627 \u0641\u0631\u0648\u0634\u06af\u0627\u0647</b>\n\n\u0628\u0631\u0627\u06cc \u0633\u0641\u0627\u0631\u0634 \u0628\u0647 \u0647\u0645\u06cc\u0646 \u0631\u0628\u0627\u062a \u067e\u06cc\u0627\u0645 \u062f\u0647\u06cc\u062f.\n\ud83d\udccd \u06a9\u0627\u0628\u0644\u060c \u062f\u0647 \u0627\u0641\u063a\u0627\u0646\u0627\u0646", parse_mode="HTML", reply_markup=main_keyboard())
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    state = context.user_data.get("state")

    if state == "waiting_name":
        context.user_data["customer_name"] = update.message.text.strip()
        context.user_data["state"] = "waiting_phone"
        await update.message.reply_text(u"\ud83d\udcf1 \u0644\u063a\u0641\u0627\u064b \u0634\u0645\u0627\u0631\u0647 \u062a\u0645\u0627\u0633 \u062e\u0648\u062f \u0631\u0627 \u0627\u0631\u0633\u0627\u0646 \u06a9\u0646\u06cc\u062f:")
        return

    if state == "waiting_phone":
