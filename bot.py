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
# Mohammadi Fashion Bot (نسخه بدون نیاز به نصب کتابخانه)
# ==========================================

TOKEN = os.getenv("BOT_TOKEN", "8850373531:AAHYa_Fdz4tLlZik8pL8uTBsaYHp8b80U-0").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

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
            "description": "لباس بخمل نگین دار با کیفیت عالی",
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
    try:
        temp = DATA_FILE.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp.replace(DATA_FILE)
    except Exception:
        logger.exception("Could not save data file")

DATA = load_data()

def is_admin(update: Update) -> bool:
    return bool(ADMIN_ID and update.effective_user and update.effective_user.id == ADMIN_ID)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 محصولات", callback_data="products")],
        [InlineKeyboardButton("📦 سفارش‌های من", callback_data="my_orders")],
        [InlineKeyboardButton("☎️ تماس با ما", callback_data="contact")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="admin_add")],
        [InlineKeyboardButton("📋 مدیریت محصولات", callback_data="admin_products")],
        [InlineKeyboardButton("📦 سفارش‌ها", callback_data="admin_orders")],
        [InlineKeyboardButton("🏠 فروشگاه", callback_data="home")]
    ])

def products_keyboard(data):
    rows = []
    for pid, product in data["products"].items():
        if product.get("active", True):
            name = product.get('name', 'محصول')
            price = product.get('price', 0)
            rows.append([InlineKeyboardButton(f"{name} — {price} افغانی", callback_data=f"product:{pid}")])
    rows.append([InlineKeyboardButton("🏠 برگشت", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def product_text(product):
    return (
        f"🛍 <b>{product.get('name')}</b>\n\n"
        f"💰 قیمت: <b>{product.get('price', 0)} افغانی</b>\n"
        f"📝 {product.get('description', '')}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = (
        "🌸 <b>به Mohammadi Fashion خوش آمدید</b> 🌸\n\n"
        "فروشگاه لباس زنانه\n"
        "برای دیدن محصولات از دکمه زیر استفاده کنید."
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_keyboard())

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ این بخش فقط برای مدیر فروشگاه است.")
        return
    await update.message.reply_text("⚙️ <b>پنل مدیریت</b>", parse_mode="HTML", reply_markup=admin_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        await query.edit_message_text("🌸 <b>Mohammadi Fashion</b> 🌸\n\nبه فروشگاه خوش آمدید.", parse_mode="HTML", reply_markup=main_keyboard())
        return

    if data == "products":
        current = load_data()
        if not any(p.get("active", True) for p in current["products"].values()):
            await query.edit_message_text("فعلاً محصولی برای نمایش وجود ندارد.", reply_markup=main_keyboard())
            return
        await query.edit_message_text("🛍 <b>محصولات فروشگاه</b>\n\nیک محصول را انتخاب کنید:", parse_mode="HTML", reply_markup=products_keyboard(current))
        return

    if data.startswith("product:"):
        pid = data.split(":", 1)[1]
        current = load_data()
        product = current["products"].get(pid)
        if not product or not product.get("active", True):
            await query.edit_message_text("این محصول دیگر موجود نیست.", reply_markup=main_keyboard())
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 ثبت سفارش", callback_data=f"order:{pid}")],
            [InlineKeyboardButton("⬅️ محصولات", callback_data="products")]
        ])
        await query.edit_message_text(product_text(product), parse_mode="HTML", reply_markup=buttons)
        return

    if data.startswith("order:"):
        pid = data.split(":", 1)[1]
        current = load_data()
        product = current["products"].get(pid)
        if not product: return
        context.user_data["order_product_id"] = pid
        context.user_data["state"] = "waiting_name"
        await query.edit_message_text(f"🛒 سفارش <b>{product.get('name')}</b>\n\nلطفاً نام خود را ارسال کنید:", parse_mode="HTML")
        return

    if data == "my_orders":
        uid = update.effective_user.id
        current = load_data()
        orders = [o for o in current["orders"] if o.get("user_id") == uid]
        if not orders:
            text = "📦 هنوز سفارشی ثبت نکرده‌اید."
        else:
            lines = ["📦 <b>سفارش‌های شما</b>\n"]
            for o in orders[-10:]:
                lines.append(f"#{o['id']} — {o['product_name']} — {o['price']} افغانی — {o['status']}")
            text = "\n".join(lines)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_keyboard())
        return

    if data == "contact":
        await query.edit_message_text("☎️ <b>تماس با Mohammadi Fashion</b>\n\nبرای سفارش و هماهنگی، به همین ربات پیام بفرستید.\n📍 کابل، ده افغانان", parse_mode="HTML", reply_markup=main_keyboard())
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    state = context.user_data.get("state")

    if state == "waiting_name":
        context.user_data["customer_name"] = update.message.text.strip()
        context.user_data["state"] = "waiting_phone"
        await update.message.reply_text("📱 لطفاً شماره تماس خود را ارسال کنید:")
        return

    if state == "waiting_phone":
        phone = update.message.text.strip()
        pid = context.user_data.get("order_product_id")
        name = context.user_data.get("customer_name", "-")

        current = load_data()
        product = current["products"].get(pid)
        if not product:
            await update.message.reply_text("محصول یافت نشد.")
            return
        order_id = len(current["orders"]) + 1
        order = {
            "id": order_id,
            "user_id": update.effective_user.id,
            "username": update.effective_user.username or "-",
            "customer_name": name,
            "phone": phone,
            "product_id": pid,
            "product_name": product["name"],
            "price": product["price"],
            "status": "در انتظار تماس",
        }
        current["orders"].append(order)
        save_data(current)

        context.user_data.clear()
        success_text = f"✅ سفارش شما با موفقیت ثبت شد.\n\nشماره سفارش: <b>#{order_id}</b>\nمحصول: {order['product_name']}\nقیمت: {order['price']} افغانی\n\nبه‌زودی برای هماهنگی با شما تماس می‌گیریم."
        await update.message.reply_text(success_text, parse_mode="HTML", reply_markup=main_keyboard())
        
        if ADMIN_ID:
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 سفارش جدید #{order_id}\nنام: {name}\nتلفن: {phone}\nمحصول: {order['product_name']}")
            except Exception: pass
        return

# ==========================================
# سیستم وب‌سرور داخلی (بدون احتیاج به کتابخانه خارجی)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args): return

def run_server(port):
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def main():
    if not TOKEN:
        logger.error("No token found!")
        return

    # پیکربندی بات تلگرام
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    if RENDER_EXTERNAL_URL:
        logger.info("Starting with Webhook on URL: " + RENDER_EXTERNAL_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
        
