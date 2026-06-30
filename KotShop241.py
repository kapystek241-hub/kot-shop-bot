import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Ошибка: BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРЫ ---

def get_start_keyboard():
    """Клавиатура для команды /start"""
    kb = [
        [
            InlineKeyboardButton(text="���ню", callback_data="menu_main"),
            InlineKeyboardButton(text="���кументы магазина", callback_data="docs_shop")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_menu_keyboard():
    """Клавиатура внутри раздела Меню (пример с пунктом 1.1)"""
    kb = [
        [InlineKeyboardButton(text="1.1 Покупки UC", callback_data="buy_uc")],
        [InlineKeyboardButton(text="❌ Назад", callback_data="back_to_start")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_docs_keyboard():
    """Кнопка Назад внутри раздела Документы"""
    kb = [[InlineKeyboardButton(text="❌ Назад", callback_data="back_to_start")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ТЕКСТЫ СООБЩЕНИЙ ---

MSG_START = (
    "Доброго времени суток!\n\n"
    "Бот постоянно находится в разработке. На данный момент бот работает с 9:00 до 23:00 по МСК. "
    "Причина, по которой бот работает определенное время: бот находится на стадии теста функционала.\n\n"
    "Покупки, сообщения, розыгрыши доступны.\n\n"
    "В нашем боте есть возможность ускорить процесс поиска по ключевым словам."
)

MSG_MENU_INFO = (
    "Доброго времени суток! Для быстрого поиска используйте ключевые слова или используйте меню с кнопками.\n\n"
    f"Пример поиска по ключевым словам (<b>Юси</b>) — по этому слову открывается раздел с покупками UC для PUBG Mobile.\n\n"
    "Бот работает штатно."
)

MSG_DOCS = (
    f"Название магазина: <b><i>KotShop241</i></b>\n\n"
    "Магазин является официальным и использует законные способы предоставления игровой валюты или пополнения сервисов в РФ и других странах.\n\n"
    "ИНН организации: 661912653571\n"
    "Для проверки вы можете использовать ресурс ФНС.\n\n"
    "В целях вашей безопасности сторонние ссылки не будут размещаться, за исключением банковских операций. "
    "Для получения чека требуется написать в поддержку внутри Telegram-бота, раздел находится (Меню -> Поддержка -> Заполнение формы обращения). Чек предоставляется только по просьбе.\n\n"
    "Проект является коммерческим и не несет ответственности в случае неправильно указанных данных при заполнении формы покупки. В случае если ошибка случилась и товар не доставлен, следует написать в поддержку.\n\n"
    "При проведении турниров от магазина KotShop241 участники, которые подтвердили участие, автоматически соглашаются с правилами, которые находятся в разделе (Меню -> Турнир -> Правила участия). Штрафы предусмотрены в том же разделе, в случае нарушения будут использованы санкции, которые указаны.\n\n"
    "Магазин имеет полное право заблокировать использование сервиса в случае возникновения расследования по отношению к покупателю. В случае если вы не согласны с блокировкой, следует написать в поддержку по ссылкам ниже.\n\n"
    "Связь по почте: Kotshop241@gmail.com\n"
    "Связь с поддержкой внутри Telegram: @KotShop2415"
)

# --- ОБРАБОТЧИКИ (HANDLERS) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        text=MSG_START,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML"  # Важно для жирного текста
    )

@dp.callback_query(F.data == "menu_main")
async def cb_menu_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=MSG_MENU_INFO,
        reply_markup=get_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "docs_shop")
async def cb_docs_shop(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=MSG_DOCS,
        reply_markup=get_docs_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def cb_back_start(callback: types.CallbackQuery):
    # Возвращаем стартовое сообщение с кнопками
    await callback.message.edit_text(
        text=MSG_START,
        reply_markup=get_start_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_uc")
async def cb_buy_uc(callback: types.CallbackQuery):
    # Заглушка для пункта меню 1.1
    await callback.answer("Раздел покупок UC находится в разработке или откроется после выбора товара.", show_alert=False)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
