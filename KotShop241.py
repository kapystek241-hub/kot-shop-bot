import asyncio
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем токен из .env (переменная должна называться BOT_TOKEN)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Токен не найден. Проверьте, что в файле .env есть строка BOT_TOKEN=ваш_токен")

ADMIN_ID = 7309972832  # ID администратора для пересылки сообщений поддержки

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_start_keyboard() -> InlineKeyboardMarkup:
    btn_menu = InlineKeyboardButton(text="Меню", callback_data="menu_main")
    btn_docs = InlineKeyboardButton(text="Документация магазина", callback_data="docs")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn_menu],
        [btn_docs]
    ])


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    btn_shop = InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")
    btn_support = InlineKeyboardButton(text="💬 Поддержка", callback_data="support")
    btn_tournament = InlineKeyboardButton(text="🏆 Турнир", callback_data="tournament")
    btn_promo = InlineKeyboardButton(text="🔥 Акции", callback_data="promo")
    btn_draw = InlineKeyboardButton(text="🎁 Розыгрыш", callback_data="draw")
    btn_back = InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_start")

    return InlineKeyboardMarkup(inline_keyboard=[
        [btn_shop],
        [btn_support],
        [btn_tournament, btn_promo],
        [btn_draw],
        [btn_back]
    ])


def get_shop_keyboard() -> InlineKeyboardMarkup:
    btn_pubg = InlineKeyboardButton(text="🎮 PUBG Mobile", callback_data="pubg_shop")
    btn_steam = InlineKeyboardButton(text="🖥️ Steam РФ", callback_data="steam_shop")
    btn_back = InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn_pubg],
        [btn_steam],
        [btn_back]
    ])


def get_support_keyboard() -> InlineKeyboardMarkup:
    btn_tg = InlineKeyboardButton(text="✍️ Написать через Telegram", callback_data="support_tg")
    btn_manager = InlineKeyboardButton(text="📞 Написать менеджеру", url="https://t.me/KotShop2415")
    btn_back = InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn_tg],
        [btn_manager],
        [btn_back]
    ])


def get_tournament_keyboard() -> InlineKeyboardMarkup:
    btn_rules = InlineKeyboardButton(text="📖 Правила проведения турнира", callback_data="tournament_rules")
    btn_back = InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn_rules],
        [btn_back]
    ])


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "Доброго времени суток,\n\n"
        "Бот постоянно находится в разработке. На данный момент бот работает с 9:00 до 23:00 по мск. "
        "Причина, по которой бот работает определённое время: бот находится на стадии теста функционала.\n\n"
        "Покупки, сообщения, розыгрыши доступны.\n\n"
        "В нашем боте есть возможность ускорить процесс поиска по ключевым словам."
    )
    await message.answer(text=text, reply_markup=get_start_keyboard())


# Обработчик ключевых слов (Магазин, Поддержка и т.д.)
# Используем F.text вместо Text из aiogram.filters
@dp.message(F.text.lower().in_(["магазин", "поддержка", "ошибка", "нужна помощь", "турнир", "акции", "акция", "розыгрыш"]))
async def handle_keywords(message: types.Message):
    text_lower = message.text.lower()
    if text_lower == "магазин":
        await message.answer("🛒 Раздел «Магазин»", reply_markup=get_shop_keyboard())
    elif text_lower in ["поддержка", "ошибка", "нужна помощь"]:
        await message.answer(
            "💬 Опишите вашу ошибку или вопрос.\nПоддержка работает с 9:00 до 23:00 по МСК.",
            reply_markup=get_support_keyboard()
        )
    elif text_lower == "турнир":
        await message.answer("🏆 Раздел «Турнир»", reply_markup=get_tournament_keyboard())
    elif text_lower in ["акции", "акция"]:
        await message.answer("🔥 Раздел «Акции» — в разработке.", reply_markup=get_main_menu_keyboard())
    elif text_lower == "розыгрыш":
        await message.answer("🎁 Раздел «Розыгрыш» — в разработке.", reply_markup=get_main_menu_keyboard())


# Основной обработчик callback-запросов
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data

    # Главное меню
    if data == "menu_main":
        await callback.message.edit_text(
            "📋 Главное меню KotShop241:\nВыберите нужный раздел:",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

    # Документация
    elif data == "docs":
        await callback.message.edit_text(
            "📖 Документация магазина: правила покупок, возвратов, условия розыгрышей и т.д. (в разработке)."
        )
        await callback.answer()

    # Магазин
    elif data == "shop":
        text = (
            "Доброго времени суток!\nМагазин проходит стадию разработки, поэтому возможны ошибки. "
            "В случае возникновения ошибок просьба обратиться в поддержку."
        )
        await callback.message.edit_text(text, reply_markup=get_shop_keyboard())
        await callback.answer()

    elif data in ["pubg_shop", "steam_shop"]:
        await callback.message.edit_text("🛒 Этот раздел находится в разработке.")
        await callback.answer()

    # Поддержка
    elif data == "support":
        text = "💬 Опишите вашу ошибку или вопрос.\nПоддержка работает с 9:00 до 23:00 по МСК."
        await callback.message.edit_text(text, reply_markup=get_support_keyboard())
        await callback.answer()

    elif data == "support_tg":
        await callback.message.edit_text(
            "✍️ Опишите ошибку или вопрос:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад", callback_data="support")]
            ])
        )
        await set_support_wait_state(callback.from_user.id)
        await callback.answer()

    # Турнир
    elif data == "tournament":
        await callback.message.edit_text(
            "🏆 Ознакомьтесь с правилами проведения турнира.",
            reply_markup=get_tournament_keyboard()
        )
        await callback.answer()

    elif data == "tournament_rules":
        await callback.message.edit_text("📖 Правила турнира: (в разработке)")
        await callback.answer()

    # Акции и Розыгрыш (заглушки)
    elif data == "promo":
        await callback.message.edit_text("🔥 Акции — в разработке.")
        await callback.answer()
    elif data == "draw":
        await callback.message.edit_text("🎁 Розыгрыш — в разработке.")
        await callback.answer()

    # Кнопка «Назад»
    elif data == "back_to_start":
        await cmd_start(callback.message)
        await callback.answer()


# Простой механизм ожидания сообщения для поддержки (без полноценного FSM)
support_waiting_users = set()

async def set_support_wait_state(user_id: int):
    support_waiting_users.add(user_id)


@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    # Если пользователь сейчас в режиме «написать в поддержку»
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


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
