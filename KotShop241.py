import asyncio
import os
import hashlib
import hmac
import json
from datetime import datetime
    from typing import Optional, Dict, Any, List

import aiohttp
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TERMINAL_KEY = os.getenv("TERMINAL_KEY")
TERMINAL_SECRET = os.getenv("TERMINAL_SECRET")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")
if not TERMINAL_KEY or not TERMINAL_SECRET:
    raise ValueError("Нужны TERMINAL_KEY и TERMINAL_SECRET в .env")

ADMIN_ID = 7309972832

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_PATH = "payments.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER,
                uc_amount INTEGER,
                price_rub INTEGER,
                uid TEXT,
                status TEXT DEFAULT 'pending',
                delivered INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


init_db()


def save_order(order_id: str, user_id: int, uc_amount: int, price: int, uid: str):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute(
                """
                INSERT INTO orders (order_id, user_id, uc_amount, price_rub, uid, status, delivered)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(order_id) DO NOTHING
                """,
                (order_id, user_id, uc_amount, price, uid, "pending")
            )
            conn.commit()
        except Exception as e:
            print(f"Ошибка сохранения заказа: {e}")


def update_order_status(order_id: str, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
        conn.commit()


def mark_delivered(order_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE orders SET delivered = 1 WHERE order_id = ?", (order_id,))
        conn.commit()


def get_pending_paid_orders() -> List[sqlite3.Row]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE status = 'PAID' AND delivered = 0")
        return c.fetchall()


user_cart: Dict[int, Dict[str, int]] = {}
user_awaiting_uid: Dict[int, tuple] = {}
support_waiting_users = set()


def sign_payload(payload: dict) -> str:
    """
    Подписываем payload согласно T‑API: сортируем ключи, склеиваем "key=value", считаем HMAC‑SHA256.
    Важно: в T‑API не должно быть пустых значений, и порядок ключей важен.
    """
    # Убираем None и пустые строки
    filtered = {k: v for k, v in payload.items() if v is not None and v != ""}
    sorted_keys = sorted(filtered.keys())
    sign_str = "".join(f"{k}={filtered[k]}" for k in sorted_keys)
    sign = hmac.new(
        TERMINAL_SECRET.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return sign


async def create_tinkoff_payment(order_id: str, amount_rub: int, description: str) -> Optional[dict]:
    url = "https://securepay.tinkoff.ru/v2/Init"
    payload = {
        "TerminalKey": TERMINAL_KEY,
        "Amount": amount_rub * 100,  # копейки
        "OrderId": order_id,
        "Description": description,
        "SuccessURL": None,  # не обязателен, если используем PaymentURL
        "FailURL": None
    }

    token = sign_payload(payload)
    payload["Token"] = token

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                return data
        except Exception as e:
            print(f"Ошибка при создании платежа: {e}")
            return None


async def check_tinkoff_payment_status(order_id: str) -> Optional[str]:
    url = "https://securepay.tinkoff.ru/v2/GetState"
    payload = {
        "TerminalKey": TERMINAL_KEY,
        "OrderId": order_id
    }

    token = sign_payload(payload)
    payload["Token"] = token

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if data.get("Success") is True:
                    return data.get("Status")
                else:
                    error_code = data.get("ErrorCode")
                    print(f"GetState ошибка: {error_code} — {data.get('Message')}")
                    return None
        except Exception as e:
            print(f"Network error при проверке статуса: {e}")
            return None


# --- Клавиатуры (без изменений, кроме форматирования) ---

def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Меню", callback_data="menu_main")],
        [InlineKeyboardButton(text="Документация магазина", callback_data="docs")]
    ])


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
        [
            InlineKeyboardButton(text="🏆 Турнир", callback_data="tournament"),
            InlineKeyboardButton(text="🔥 Акции", callback_data="promo")
        ],
        [InlineKeyboardButton(text="🎁 Розыгрыш", callback_data="draw")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_start")]
    ])


def get_shop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 PUBG Mobile", callback_data="pubg_shop")],
        [InlineKeyboardButton(text="🖥️ Steam РФ", callback_data="steam_shop")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main")]
    ])


def get_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать через Telegram", callback_data="support_tg")],
        [InlineKeyboardButton(text="📞 Написать менеджеру", url="https://t.me/KotShop2415")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main")]
    ])


def get_tournament_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Правила проведения турнира", callback_data="tournament_rules")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main")]
    ])


def get_pubg_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 UC по ID", callback_data="uc_by_id")],
        [InlineKeyboardButton(text="🛍️ Другие товары", callback_data="other_items")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="shop")]
    ])


UC_PRICES = [
    ("60 UC — 74 ₽", "uc_select_60"),
    ("120 UC — 145 ₽", "uc_select_120"),
    ("180 UC — 221 ₽", "uc_select_180"),
    ("240 UC — 294 ₽", "uc_select_240"),
    ("325 UC — 431 ₽", "uc_select_325"),
    ("385 UC — 442 ₽", "uc_select_385"),
    ("445 UC — 516 ₽", "uc_select_445"),
    ("660 UC — 749 ₽", "uc_select_660"),
    ("720 UC — 824 ₽", "uc_select_720"),
    ("985 UC — 1089 ₽", "uc_select_985"),
    ("1320 UC — 1489 ₽", "uc_select_1320"),
    ("1800 UC — 1799 ₽", "uc_select_1800"),
    ("1920 UC — 1989 ₽", "uc_select_1920"),
    ("2125 UC — 2179 ₽", "uc_select_2125"),
    ("2460 UC — 2587 ₽", "uc_select_2460"),
    ("3850 UC — 3632 ₽", "uc_select_3850"),
    ("4510 UC — 4372 ₽", "uc_select_4510"),
    ("5650 UC — 5452 ₽", "uc_select_5650"),
    ("8100 UC — 7267 ₽", "uc_select_8100"),
    ("9900 UC — 8989 ₽", "uc_select_9900"),
    ("11950 UC — 10914 ₽", "uc_select_11950"),
    ("16200 UC — 14568 ₽", "uc_select_16200"),
    ("24300 UC — 21852 ₽", "uc_select_24300"),
    ("32400 UC — 28753 ₽", "uc_select_32400"),
    ("40500 UC — 35955 ₽", "uc_select_40500"),
    ("81000 UC — 71299 ₽", "uc_select_81000"),
]


def get_uc_amount_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for text, data in UC_PRICES:
        row.append(InlineKeyboardButton(text=text, callback_data=data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="pubg_shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Хендлеры (исправленные) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "Доброго времени суток!\n\n"
        "Бот находится в разработке. Работает с 9:00 до 23:00 по МСК.\n"
        "Покупки, сообщения, розыгрыши доступны."
    )
    await message.answer(text=text, reply_markup=get_start_keyboard())


@dp.message(F.text.lower().in_(["меню"]))
async def handle_menu_keyword(message: types.Message):
    await message.answer("📋 Главное меню KotShop241:\nВыберите нужный раздел:", reply_markup=get_main_menu_keyboard())


@dp.message(F.text.lower().in_(
    ["магазин", "поддержка", "ошибка", "нужна помощь", "турнир", "акции", "акция", "розыгрыш"]
))
async def handle_keywords(message: types.Message):
    t = message.text.lower()
    if t == "магазин":
        await message.answer("🛒 Раздел «Магазин»", reply_markup=get_shop_keyboard())
    elif t in ["поддержка", "ошибка", "нужна помощь"]:
        await message.answer(
            "💬 Опишите вашу ошибку или вопрос.\nПоддержка работает с 9:00 до 23:00 по МСК.",
            reply_markup=get_support_keyboard()
        )
    elif t == "турнир":
        await message.answer("🏆 Раздел «Турнир»", reply_markup=get_tournament_keyboard())
    elif t in ["акции", "акция"]:
        await message.answer("🔥 Раздел «Акции» — в разработке.", reply_markup=get_main_menu_keyboard())
    elif t == "розыгрыш":
        await message.answer("🎁 Раздел «Розыгрыш» — в разработке.", reply_markup=get_main_menu_keyboard())


@dp.message(F.text.lower().in_(["pubg", "пабг", "купить uc", "купить юси"]))
async def handle_pubg_keywords(message: types.Message):
    await message.answer("Выберите интересующий раздел:", reply_markup=get_pubg_main_keyboard())


@dp.message(F.text.lower().in_(["юси", "uc"]))
async def handle_uc_keywords(message: types.Message):
    await message.answer("Выберите нужное количество UC", reply_markup=get_uc_amount_keyboard())


@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    if data == "menu_main":
        await callback.message.edit_text(
            "📋 Главное меню KotShop241:\nВыберите нужный раздел:",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    elif data == "docs":
        text = (
            "Название магазина: ***KotShop241***\n\n"
            "ИНН организации: 661912653571\n\n"
            "Для получения чека напишите в поддержку.\n"
            "Магазин не несёт ответственности за ошибки в данных при оформлении."
        )
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Меню", callback_data="menu_main")]
            ])
        )
        await callback.answer()

    elif data == "shop":
        await callback.message.edit_text("🛒 Раздел «Магазин»", reply_markup=get_shop_keyboard())
        await callback.answer()

    elif data == "pubg_shop":
        await callback.message.edit_text("Выберите интересующий раздел:", reply_markup=get_pubg_main_keyboard())
        await callback.answer()

    elif data == "steam_shop":
        await callback.message.edit_text("🖥️ Этот раздел находится в разработке.")
        await callback.answer()

    elif data == "uc_by_id":
        user_cart.pop(user_id, None)
        user_awaiting_uid.pop(user_id, None)
        await callback.message.edit_text(
            "Выберите нужное количество UC",
            reply_markup=get_uc_amount_keyboard()
        )
        await callback.answer()

    elif data == "other_items":
        await callback.message.edit_text("🛍️ Другие товары — в разработке.")
        await callback.answer()

    elif data.startswith("uc_select_"):
        mapping = {
            "uc_select_60": (60, 74),
            "uc_select_120": (120, 145),
            "uc_select_180": (180, 221),
            "uc_select_240": (240, 294),
            "uc_select_325": (325, 431),
            "uc_select_385": (385, 442),
            "uc_select_445": (445, 516),
            "uc_select_660": (660, 749),
            "uc_select_720": (720, 824),
            "uc_select_985": (985, 1089),
            "uc_select_1320": (1320, 1489),
            "uc_select_1800": (1800, 1799),
            "uc_select_1920": (1920, 1989),
            "uc_select_2125": (2125, 2179),
            "uc_select_2460": (2460, 2587),
            "uc_select_3850": (3850, 3632),
            "uc_select_4510": (4510, 4372),
            "uc_select_5650": (5650, 5452),
            "uc_select_8100": (8100, 7267),
            "uc_select_9900": (9900, 8989),
            "uc_select_11950": (11950, 10914),
            "uc_select_16200": (16200, 14568),
            "uc_select_24300": (24300, 21852),
            "uc_select_32400": (32400, 28753),
            "uc_select_40500": (40500, 35955),
            "uc_select_81000": (81000, 71299),
        }
        uc_amount, price = mapping.get(data, (0, 0))
        if uc_amount == 0:
            await callback.answer("Ошибка выбора товара.", show_alert=True)
            return

        user_cart[user_id] = {"uc_amount": uc_amount, "price": price}
        await callback.message.edit_text(
            f"🛒 Корзина:\nUC — {uc_amount}\nЦена — {price} ₽\n\nНажмите «Продолжить», чтобы указать UID PUBG Mobile:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить", callback_data="confirm_uid")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="uc_by_id")]
            ])
        )
        await callback.answer()

    elif data == "confirm_uid":
        if user_id not in user_cart:
            await callback.answer("Сначала выберите товар.", show_alert=True)
            return
        cart = user_cart[user_id]
        user_awaiting_uid[user_id] = (cart["uc_amount"], cart["price"])
        await callback.message.edit_text(
            "🆔 Укажите UID PUBG Mobile.\nОн должен состоять только из цифр и начинаться на 5."
        )
        await callback.answer()

    elif data == "support":
        await callback.message.edit_text(
            "💬 Опишите вашу ошибку или вопрос.\nПоддержка работает с 9:00 до 23:00 по МСК.",
            reply_markup=get_support_keyboard()
        )
        await callback.answer()

    elif data == "support_tg":
        await callback.message.edit_text(
            "✍️ Опишите ошибку или вопрос:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад", callback_data="support")]
            ])
        )
        support_waiting_users.add(user_id)
        await callback.answer()

    elif data == "tournament":
        await callback.message.edit_text(
            "🏆 Ознакомьтесь с правилами проведения турнира.",
            reply_markup=get_tournament_keyboard()
        )
        await callback.answer()

    elif data == "tournament_rules":
        await callback.message.edit_text("📖 Правила турнира: (в разработке)")
        await callback.answer()

    elif data in ["promo", "draw"]:
        await callback.message.edit_text("🔥 Акции / 🎁 Розыгрыш — в разработке.")
        await callback.answer()

    elif data == "back_to_start":
        await cmd_start(callback.message)
        await callback.answer()

    elif data.startswith("pay_"):
        parts = data.split("_")
        if len(parts) != 4:
            await callback.answer("Ошибка данных заказа.", show_alert=True)
            return
        uc_amount = int(parts[1])
        price = int(parts[2])
        uid_text = parts[3]

        order_id = f"order_{user_id}_{int(datetime.now().timestamp())}"
        save_order(order_id, user_id, uc_amount, price, uid_text)

        payment_result = await create_tinkoff_payment(order_id, price, f"UC для PUBG Mobile, UID: {uid_text}")

        if not payment_result:
            await callback.message.edit_text(
                "⚠️ Ошибка при создании платежа. Попробуйте позже или обратитесь в поддержку.")
            await callback.answer()
            return

        error_code = payment_result.get("ErrorCode")
        if error_code:
            msg = payment_result.get("Message", "Неизвестная ошибка банка.")
            await callback.message.edit_text(f"⚠️ Ошибка банка: {error_code} — {msg}")
            await callback.answer()
            return

        payment_url = payment_result.get("PaymentURL")
        if not payment_url:
            await callback.message.edit_text("⚠️ Не удалось получить ссылку на оплату. Обратитесь в поддержку.")
            await callback.answer()
            return

        await callback.message.edit_text(
            f"UC — {uc_amount}\n"
            f"Цена — {price} ₽\n"
            f"UID — {uid_text}\n\n"
            "Нажмите кнопку ниже, чтобы перейти к оплате.\n"
            "После оплаты нажмите «Проверить статус оплаты», чтобы получить подтверждение:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)],
                [InlineKeyboardButton(text="✅ Проверить статус оплаты", callback_data=f"check_{order_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
            ])
        )
        await callback.answer()

    elif data.startswith("check_"):
        order_id = data.split("_")[1]

        await callback.message.answer("⏳ Проверяю статус платежа в Т‑Банке...")

        status = await check_tinkoff_payment_status(order_id)

        if status is None:
            await callback.message.answer("⚠️ Не удалось получить статус от банка. Попробуйте позже.")
            await callback.answer()
            return

        # Защита от повторной выдачи: если уже delivered, не выдаём снова
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT delivered FROM orders WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        conn.close()

        delivered = row[0] if row else 0

        if status == "CONFIRMED":
            update_order_status(order_id, "PAID")
            if delivered == 0:
                await callback.message.answer(
                    f"✅ Оплата подтверждена!\n\nВаш заказ принят в обработку. Менеджер свяжется с вами в ближайшее время для начисления UC."
                )
                mark_delivered(order_id)

                # Уведомление админу
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"💰 Новый оплаченный заказ!\nOrderID: {order_id}\nСтатус: CONFIRMED"
                    )
                except Exception:
                    pass
            else:
                await callback.message.answer("✅ Оплата подтверждена. Заказ уже в обработке.")

        elif status == "REJECTED":
            update_order_status(order_id, "REJECTED")
            await callback.message.answer("❌ Оплата отклонена банком.")

        else:
            await callback.message.answer(f"ℹ️ Текущий статус: {status}. Оплата ещё не завершена.")

        await callback.answer()

    elif data == "cancel_order":
        user_cart.pop(user_id, None)
        user_awaiting_uid.pop(user_id, None)
        await callback.message.edit_text(
            "❌ Заказ отменён.\nВернитесь в магазин и выберите товар заново:",
            reply_markup=get_uc_amount_keyboard()
        )
        await callback.answer()

    elif data == "change_uid":
        if user_id not in user_cart:
            await callback.answer("Сначала выберите товар.", show_alert=True)
            return
        cart = user_cart[user_id]
        user_awaiting_uid[user_id] = (cart["uc_amount"], cart["price"])
        await callback.message.edit_text(
            "🆔 Пожалуйста, отправьте новый UID PUBG Mobile.\nОн должен начинаться на 5 и состоять только из цифр."
        )
        await callback.answer()
    else:
        await callback.answer("Неизвестная команда.", show_alert=True)

    @dp.message()
    async def handle_messages(message: types.Message):
        user_id = message.from_user.id

        if user_id in support_waiting_users:
            try:
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"📩 Новое сообщение в поддержку от @{message.from_user.username or 'без юзернейма'} (ID: {user_id})\n\n{message.text}"
                )
                await message.answer("✅ Ваше сообщение отправлено в поддержку. Ответ поступит в ближайшее время.")
            except Exception as e:
                await message.answer("⚠️ Произошла ошибка при отправке сообщения. Попробуйте позже.")
            finally:
                support_waiting_users.discard(user_id)
            return

        if user_id in user_awaiting_uid:
            uid_text = message.text.strip()

            if not uid_text.isdigit() or not uid_text.startswith("5"):
                await message.answer(
                    "❌ UID должен состоять только из цифр и начинаться на 5.\n\nПожалуйста, отправьте корректный UID PUBG Mobile."
                )
                return

            uc_amount, price = user_awaiting_uid[user_id]
            user_awaiting_uid.pop(user_id, None)

            text = (
                f"UC — {uc_amount}\n"
                f"Цена — {price} ₽\n"
                f"UID — {uid_text}"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Оплатить", callback_data=f"pay_{uc_amount}_{price}_{uid_text}")],
                [InlineKeyboardButton(text="🔄 Другой UID", callback_data="change_uid")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
            ])
            await message.answer(text, reply_markup=keyboard)
            return

    async def check_and_deliver_orders():
        """
        Фоновая задача: периодически проверяем заказы со статусом 'PAID' и delivered = 0.
        В реальном проекте лучше использовать вебхуки, но это хороший запасной вариант.
        """
        while True:
            rows = get_pending_paid_orders()
            for row in rows:
                order_id = row["order_id"]
                user_id = row["user_id"]
                uc_amount = row["uc_amount"]
                uid = row["uid"]

                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"✅ Оплата подтверждена!\n\n"
                            f"Заказ: {uc_amount} UC\n"
                            f"UID: {uid}\n\n"
                            "Ваш заказ обрабатывается. Ожидайте начисления UC в ближайшее время."
                        )
                    )
                    mark_delivered(order_id)
                except Exception as e:
                    # Пользователь мог заблокировать бота — просто логируем и пропускаем
                    print(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

            await asyncio.sleep(30)

    async def main():
        # Запускаем фоновую проверку заказов
        asyncio.create_task(check_and_deliver_orders())
        await dp.start_polling(bot)

    if __name__ == "__main__":
        asyncio.run(main())
