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

    except Exception as error:

        logger.error(
            "Database read error: %s",
            error,
        )

        return default


def save_json(
    file_path,
    data,
):

    try:

        file_path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    except Exception as error:

        logger.error(
            "Database save error: %s",
            error,
        )


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

def is_admin(user_id):

    if not ADMIN_ID:

        return False

    return str(user_id) == str(
        ADMIN_ID
    )


def get_product(product_id):

    for product in get_products():

        if str(product.get("id")) == str(
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
                int(item.get("id", 0))
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
                int(item.get("id", 0))
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
                "ًں‘— ظ…ط­طµظˆظ„ط§طھ",
                callback_data="products",
            ),

            InlineKeyboardButton(
                "ًں›’ ط³ط¨ط¯ ط®ط±غŒط¯",
                callback_data="cart",
            ),
        ],

        [
            InlineKeyboardButton(
                "ًں“¦ ط³ظپط§ط±ط´â€Œظ‡ط§غŒ ظ…ظ†",
                callback_data="my_orders",
            ),

            InlineKeyboardButton(
                "ًں”ژ ط¬ط³طھط¬ظˆغŒ ظ…ط­طµظˆظ„",
                callback_data="search",
            ),
        ],

        [
            InlineKeyboardButton(
                "ًں§µ ط¯ظˆط®طھ ط³ظپط§ط±ط´غŒ",
                callback_data="custom",
            ),

            InlineKeyboardButton(
                "ًں“‍ طھظ…ط§ط³ ط¨ط§ ظ…ط§",
                callback_data="contact",
            ),
        ],

    ]

    if is_admin(user_id):

        buttons.append(
            [
                InlineKeyboardButton(
                    "âڑ™ï¸ڈ ظ…ط¯غŒط±غŒطھ ظپط±ظˆط´ع¯ط§ظ‡",
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
                    "ًںڈ  طµظپط­ظ‡ ط§طµظ„غŒ",
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

        f"ًں‘‹ ط³ظ„ط§ظ… {user.first_name or 'ط¯ظˆط³طھ ط¹ط²غŒط²'}\n\n"

        "ًںŒ¸ ط¨ظ‡ ظپط±ظˆط´ع¯ط§ظ‡\n"
        "Mohammadi Fashion\n"
        "ط®ظˆط´ ط¢ظ…ط¯غŒط¯.\n\n"

        "ًں‘— ظ„ط¨ط§ط³â€Œظ‡ط§غŒ ط²ظ†ط§ظ†ظ‡\n"
        "ًں§µ ط¯ظˆط®طھ ط³ظپط§ط±ط´غŒ\n"
        "ًں›’ ط«ط¨طھ ط³ظپط§ط±ط´ ط¢ط³ط§ظ†\n\n"

        "غŒع©غŒ ط§ط² ع¯ط²غŒظ†ظ‡â€Œظ‡ط§غŒ ط²غŒط± ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:",

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

        "ًں“– ط±ط§ظ‡ظ†ظ…ط§غŒ Mohammadi Fashion\n\n"

        "/start â€” طµظپط­ظ‡ ط§طµظ„غŒ\n"
        "/products â€” ظ…ط­طµظˆظ„ط§طھ\n"
        "/cart â€” ط³ط¨ط¯ ط®ط±غŒط¯\n"
        "/orders â€” ط³ظپط§ط±ط´â€Œظ‡ط§غŒ ظ…ظ†\n"
        "/cancel â€” ظ„ط؛ظˆ ط¹ظ…ظ„غŒط§طھ\n\n"

        "ط¨ط±ط§غŒ ط§ط³طھظپط§ط¯ظ‡ ط¢ط³ط§ظ†â€Œطھط± ط§ط² ط¯ع©ظ…ظ‡â€Œظ‡ط§غŒ ظپط±ظˆط´ع¯ط§ظ‡ ط§ط³طھظپط§ط¯ظ‡ ع©ظ†غŒط¯.",

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

        "â‌Œ ط¹ظ…ظ„غŒط§طھ ظ„ط؛ظˆ ط´ط¯.",

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

            "ًں‘— ظ…ط­طµظˆظ„ط§طھ ظپط±ظˆط´ع¯ط§ظ‡\n\n"

            "ظپط¹ظ„ط§ظ‹ ظ…ط­طµظˆظ„غŒ ط«ط¨طھ ظ†ط´ط¯ظ‡ ط§ط³طھ.\n"
            "ظ…ط¯غŒط±غŒطھ ظ…غŒâ€Œطھظˆط§ظ†ط¯ ط§ط² ظ¾ظ†ظ„ ظ…ط¯غŒط±غŒطھ ظ…ط­طµظˆظ„ ط§ط¶ط§ظپظ‡ ع©ظ†ط¯.",

            reply_markup=home_button(),
        )

        return

    keyboard = []

    for product in items[:50]:

        name = product.get(
            "name",
            "ظ…ط­طµظˆظ„",
        )

        price = product.get(
            "price",
            0,
        )

        keyboard.append(

            [
                InlineKeyboardButton(
                    f"ًں‘— {name} â€” {price} ط§ظپط؛ط§ظ†غŒ",
                    callback_data=f"product:{product.get('id')}",
                )
            ]
        )

    keyboard.append(

        [
            InlineKeyboardButton(
                "ًںڈ  طµظپط­ظ‡ ط§طµظ„غŒ",
                callback_data="home",
            )
        ]
    )

    await query.edit_message_text(

        "ًں‘— ظ…ط­طµظˆظ„ط§طھ Mohammadi Fashion\n\n"
        "غŒع© ظ…ط­طµظˆظ„ ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯:",

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
            "â‌Œ ظ…ط­طµظˆظ„ ظ¾غŒط¯ط§ ظ†ط´ط¯.",
            reply_markup=home_button(),
        )

        return

    name = product.get(
        "name",
        "ظ…ط­طµظˆظ„",
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

        f"ًں‘— {name}\n\n"

        f"ًں’° ظ‚غŒظ…طھ: {price} ط§ظپط؛ط§ظ†غŒ\n"

        f"ًں“¦ ظ…ظˆط¬ظˆط¯غŒ: {stock}\n\n"

    )

    if description:

        text += (
            f"ًں“‌ {description}\n\n"
        )

    keyboard = [

        [
            InlineKeyboardButton(
                "ًں›’ ط§ظپط²ظˆط¯ظ† ط¨ظ‡ ط³ط¨ط¯",
                callback_data=f"add:{product_id}",
            )
        ],

        [
            InlineKeyboardButton(
                "â¬…ï¸ڈ ظ…ط­طµظˆظ„ط§طھ",
                callback_data="products",
            ),

            InlineKeyboardButton(
                "ًںڈ  ط®ط§ظ†ظ‡",
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

            "ًں›’ ط³ط¨ط¯ ط®ط±غŒط¯ ط´ظ…ط§ ط®ط§ظ„غŒ ط§ط³طھ.",

            reply_markup=home_button(),
        )

        return

    lines = [
        "ًں›’ ط³ط¨ط¯ ط®ط±غŒط¯ ط´ظ…ط§\n"
    ]

    for product_id in cart:

        product = get_product(
            product_id
        )

        if product:

            lines.append(

                f"â€¢ {product.get('name')}\n"
                f"  {product.get('price')} ط§ظپط؛ط§ظ†غŒ"

            )

    lines.append(

        f"\nًں’° ظ…ط¬ظ…ظˆط¹: {cart_total(context):g} ط§ظپط؛ط§ظ†غŒ"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "ًں“± ط«ط¨طھ ط³ظپط§ط±ط´",
                callback_data="checkout",
            )
        ],

        [
            InlineKeyboardButton(
                "ًں—‘ ط®ط§ظ„غŒ ع©ط±ط¯ظ† ط³ط¨ط¯",
                callback_data="clear_cart",
            )
        ],

        [
            InlineKeyboardButton(
                "ًںڈ  طµظپط­ظ‡ ط§طµظ„غŒ",
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

        "status": "ط¬ط¯غŒط¯",

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

            "ًںڈ  طµظپط­ظ‡ ط§طµظ„غŒ Mohammadi Fashion",

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
                "â‌Œ ظ…ط­طµظˆظ„ ظ¾غŒط¯ط§ ظ†ط´ط¯.",
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

                "â‌Œ ط§غŒظ† ظ…ط­طµظˆظ„ ظپط¹ظ„ط§ظ‹ ظ…ظˆط¬ظˆط¯ ظ†غŒط³طھ.",

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

            f"âœ… {product.get('name')}\n"
            "ط¨ظ‡ ط³ط¨ط¯ ط®ط±غŒط¯ ط§ط¶ط§ظپظ‡ ط´ط¯.",

            reply_markup=InlineKeyboardMarkup(

                [

                    [
                        InlineKeyboardButton(
                            "ًں›’ ط³ط¨ط¯ ط®ط±غŒط¯",
                            callback_data="cart",
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "ًں‘— ظ…ط­طµظˆظ„ط§طھ",
                            callback_data="products",
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "ًںڈ  ط®ط§ظ†ظ‡",
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

            "ًں—‘ ط³ط¨ط¯ ط®ط±غŒط¯ ط®ط§ظ„غŒ ط´ط¯.",

            reply_markup=home_button(),
        )

        return


    # CHECKOUT
    if data == "checkout":

        if not get_cart(
            context
        ):

            await query.edit_message_text(

                "ًں›’ ط³ط¨ط¯ ط®ط±غŒط¯ ط®ط§ظ„غŒ ط§ط³طھ.",

                reply_markup=home_button(),
            )

            return

        context.user_data[
            "state"
        ] = "phone"

        await query.edit_message_text(

            "ًں“± ظ„ط·ظپط§ظ‹ ط´ظ…ط§ط±ظ‡ طھظ…ط§ط³ ط®ظˆط¯ ط±ط§ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯.\n\n"
            "ظ…ط«ط§ظ„:\n"
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

                "ًں“¦ ط´ظ…ط§ ظ‡ظ†ظˆط² ط³ظپط§ط±ط´غŒ ط«ط¨طھ ظ†ع©ط±ط¯ظ‡â€Œط§غŒط¯.",

                reply_markup=home_button(),
            )

            return

        lines = [
            "ًں“¦ ط³ظپط§ط±ط´â€Œظ‡ط§غŒ ط´ظ…ط§\n"
        ]

        for order in user_orders[-10:]:

            lines.append(

                f"ًں§¾ ط³ظپط§ط±ط´ #{order.get('id')}\n"
                f"ًں’° {order.get('total', 0):g} ط§ظپط؛ط§ظ†غŒ\n"
                f"ًں“Œ ظˆط¶ط¹غŒطھ: {order.get('status')}\n"

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

            "ًں”ژ ظ†ط§ظ… ظ…ط­طµظˆظ„ ظ…ظˆط±ط¯ ظ†ط¸ط± ط±ط§ ط¨ظ†ظˆغŒط³غŒط¯.",

            reply_markup=home_button(),
        )

        return


    # CUSTOM
    if data == "custom":

        context.user_data[
            "state"
        ] = "custom"
        
        await query.edit_message_text(

            "ًں§µ ط¯ظˆط®طھ ط³ظپط§ط±ط´غŒ\n\n"
            "ظ„ط·ظپط§ظ‹ طھظˆط¶غŒط­ط§طھ ظ„ط¨ط§ط³ ظ…ظˆط±ط¯ ظ†ط¸ط± ط®ظˆط¯ ط±ط§ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯.\n"
            "ظ…ط«ظ„ط§ظ‹ ط±ظ†ع¯طŒ ظ…ط¯ظ„ ظˆ ط§ظ†ط¯ط§ط²ظ‡.",

            reply_markup=home_button(),
        )

        return


    # CONTACT
    if data == "contact":

        await query.edit_message_text(

            "ًں“‍ طھظ…ط§ط³ ط¨ط§ ظ…ط§\n\n"
            "Mohammadi Fashion\n\n"
            "ط¨ط±ط§غŒ ط³ظپط§ط±ط´ ظˆ ظ…ط¹ظ„ظˆظ…ط§طھ ط¨غŒط´طھط± ط¨ط§ ظ…ط¯غŒط±غŒطھ ظپط±ظˆط´ع¯ط§ظ‡ طھظ…ط§ط³ ط¨ع¯غŒط±غŒط¯.",

            reply_markup=home_button(),
        )

        return


    # ADMIN
    if data == "admin":

        if not is_admin(
            user_id
        ):

            await query.edit_message_text(
                "â‌Œ ط¯ط³طھط±ط³غŒ ط؛غŒط±ظ…ط¬ط§ط²."
            )

            return

        keyboard = [

            [
                InlineKeyboardButton(
                    "ًں“ٹ ط¢ظ…ط§ط±",
                    callback_data="admin_stats",
                )
            ],

            [
                InlineKeyboardButton(
                    "ًں“¦ ط³ظپط§ط±ط´â€Œظ‡ط§",
                    callback_data="admin_orders",
                )
            ],

            [
                InlineKeyboardButton(
                    "â‍• ط§ظپط²ظˆط¯ظ† ظ…ط­طµظˆظ„",
                    callback_data="admin_add",
                )
            ],

            [
                InlineKeyboardButton(
                    "ًں—‘ ط­ط°ظپ ظ…ط­طµظˆظ„",
                    callback_data="admin_delete",
                )
            ],

            [
                InlineKeyboardButton(
                    "ًںڈ  طµظپط­ظ‡ ط§طµظ„غŒ",
                    callback_data="home",
                )
            ],

        ]

        await query.edit_message_text(

            "âڑ™ï¸ڈ ظ¾ظ†ظ„ ظ…ط¯غŒط±غŒطھ Mohammadi Fashion",

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

            "ًں“ٹ ط¢ظ…ط§ط± ظپط±ظˆط´ع¯ط§ظ‡\n\n"

            f"ًں‘— ظ…ط­طµظˆظ„ط§طھ: {product_count}\n"
            f"ًں“¦ ط³ظپط§ط±ط´â€Œظ‡ط§: {order_count}",

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

                "ًں“¦ ظ‡ظ†ظˆط² ط³ظپط§ط±ط´غŒ ظˆط¬ظˆط¯ ظ†ط¯ط§ط±ط¯.",

                reply_markup=home_button(),
            )

            return

        lines = [
            "ًں“¦ ط¢ط®ط±غŒظ† ط³ظپط§ط±ط´â€Œظ‡ط§\n"
        ]

        for order in items[-20:]:

            lines.append(

                f"#{order.get('id')} | "
                f"{order.get('name')} | "
                f"{order.get('total', 0):g} ط§ظپط؛ط§ظ†غŒ | "
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

            "â‍• ط§ظپط²ظˆط¯ظ† ظ…ط­طµظˆظ„\n\n"
            "ظ†ط§ظ… ظ…ط­طµظˆظ„ ط±ط§ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯.",

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

            "ًں—‘ ط­ط°ظپ ظ…ط­طµظˆظ„\n\n"
            "ID ظ…ط­طµظˆظ„ ط±ط§ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯.",

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

                "â‌Œ ط³ظپط§ط±ط´ ط«ط¨طھ ظ†ط´ط¯.\n"
                "ظ„ط·ظپط§ظ‹ ط¯ظˆط¨ط§ط±ظ‡ طھظ„ط§ط´ ع©ظ†غŒط¯.",

                reply_markup=main_keyboard(
                    user.id
                ),
            )

            return

        await update.message.reply_text(

            "âœ… ط³ظپط§ط±ط´ ط´ظ…ط§ ط«ط¨طھ ط´ط¯.\n\n"

            f"ًں§¾ ط´ظ…ط§ط±ظ‡ ط³ظپط§ط±ط´: #{order['id']}\n"
            f"ًں’° ظ…ط¨ظ„ط؛: {order['total']:g} ط§ظپط؛ط§ظ†غŒ\n"
            f"ًں“± ط´ظ…ط§ط±ظ‡ طھظ…ط§ط³: {order['phone']}\n\n"

            "ظ…ط¯غŒط±غŒطھ ظپط±ظˆط´ع¯ط§ظ‡ ط¨ط§ ط´ظ…ط§ طھظ…ط§ط³ ط®ظˆط§ظ‡ط¯ ع¯ط±ظپطھ.",

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

                        "ًں”” ط³ظپط§ط±ط´ ط¬ط¯غŒط¯\n\n"

                        f"ًں§¾ ط³ظپط§ط±ط´: #{order['id']}\n"
                        f"ًں‘¤ ظ…ط´طھط±غŒ: {order['name']}\n"
                        f"ًں“± طھظ…ط§ط³: {order['phone']}\n"
                        f"ًں’° ظ…ط¨ظ„ط؛: {order['total']:g} ط§ظپط؛ط§ظ†غŒ"

                    ),
                )

            except Exception as error:

                logger.error(
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

                "â‌Œ ظ…ط­طµظˆظ„غŒ ط¨ط§ ط§غŒظ† ظ†ط§ظ… ظ¾غŒط¯ط§ ظ†ط´ط¯.",

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
                            "ظ…ط­طµظˆظ„"
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
                    "ًںڈ  ط®ط§ظ†ظ‡",
                    callback_data="home",
                )
            ]
        )

        await update.message.reply_text(

            "ًں”ژ ظ†طھط§غŒط¬ ط¬ط³طھط¬ظˆ:",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

        return


    # CUSTOM SEWING
    if state == "custom":

        context.user_data.clear()

        await update.message.reply_text(

            "ًں§µ طھظˆط¶غŒط­ط§طھ ط¯ظˆط®طھ ط³ظپط§ط±ط´غŒ ط´ظ…ط§ ط¯ط±غŒط§ظپطھ ط´ط¯ âœ…\n\n"
            "ظ…ط¯غŒط±غŒطھ ظپط±ظˆط´ع¯ط§ظ‡ ط¨ط±ط±ط³غŒ ظ…غŒâ€Œع©ظ†ط¯ ظˆ ط¨ط§ ط´ظ…ط§ طھظ…ط§ط³ ظ…غŒâ€Œع¯غŒط±ط¯.",

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

                        "ًں§µ ط¯ط±ط®ظˆط§ط³طھ ط¯ظˆط®طھ ط³ظپط§ط±ط´غŒ\n\n"

                        f"ًں‘¤ ظ…ط´طھط±غŒ: {user.full_name}\n"
                        f"ًں†” User ID: {user.id}\n\n"
                        f"ًں“‌ طھظˆط¶غŒط­ط§طھ:\n{text}"

                    ),
                )

            except Exception as error:

                logger.error(
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

            "ًں’° ظ‚غŒظ…طھ ظ…ط­طµظˆظ„ ط±ط§ ط¨ظ‡ ط§ظپط؛ط§ظ†غŒ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯."

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
                "â‌Œ ظ„ط·ظپط§ظ‹ ظپظ‚ط· ط¹ط¯ط¯ ظ‚غŒظ…طھ ط±ط§ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯."
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

            "ًں“¦ ظ…ظˆط¬ظˆط¯غŒ ظ…ط­طµظˆظ„ ط±ط§ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯."

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
                "â‌Œ ظ„ط·ظپط§ظ‹ ظپظ‚ط· ط¹ط¯ط¯ ظ…ظˆط¬ظˆط¯غŒ ط±ط§ ط§ط±ط³ط§ظ„ ع©ظ†غŒط¯."
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

            "âœ… ظ…ط­طµظˆظ„ ط¨ط§ ظ…ظˆظپظ‚غŒطھ ط§ط¶ط§ظپظ‡ ط´ط¯.",

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

                "â‌Œ ظ…ط­طµظˆظ„غŒ ط¨ط§ ط§غŒظ† ID ظ¾غŒط¯ط§ ظ†ط´ط¯."

            )

            return

        save_json(
            PRODUCTS_FILE,
            new_data,
        )

        context.user_data.clear()

        await update.message.reply_text(

            "âœ… ظ…ط­طµظˆظ„ ط­ط°ظپ ط´ط¯.",

            reply_markup=main_keyboard(
                user.id
            ),
        )

        return


    # NORMAL MESSAGE
    await update.message.reply_text(

        "ط³ظ„ط§ظ… ًںŒ¸\n\n"
        "ظ¾غŒط§ظ… ط´ظ…ط§ ط¯ط±غŒط§ظپطھ ط´ط¯.\n"
        "ط¨ط±ط§غŒ ط§ط³طھظپط§ط¯ظ‡ ط§ط² ظپط±ظˆط´ع¯ط§ظ‡ غŒع©غŒ ط§ط² ع¯ط²غŒظ†ظ‡â€Œظ‡ط§غŒ ط²غŒط± ط±ط§ ط§ظ†طھط®ط§ط¨ ع©ظ†غŒط¯.",

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

    logger.error(
        "TELEGRAM ERROR: %s",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # TOKEN CHECK
    # --------------------------------------------------------

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN is missing. "
            "Add BOT_TOKEN in Render Environment Variables."
        )

    logger.info(
        "BOT TOKEN loaded: True"
    )


    # --------------------------------------------------------
    # RENDER WEB SERVER
    # --------------------------------------------------------

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True,
    )

    web_thread.start()


    # --------------------------------------------------------
    # TELEGRAM APPLICATION
    # --------------------------------------------------------

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    logger.info(
        "Telegram application created."
    )


    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            buttons,
        )
    )


    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    app.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_handler,

        )

    )


    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    app.add_error_handler(
        error_handler
    )


    # --------------------------------------------------------
    # START POLLING
    # --------------------------------------------------------

    logger.info(
        "Mohammadi Fashion Bot is running..."
    )

    logger.info(
        "Starting Telegram polling..."
    )

    app.run_polling(

        drop_pending_updates=True,

        allowed_updates=Update.ALL_TYPES,

    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
