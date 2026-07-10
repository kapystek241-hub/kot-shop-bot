import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем токен из .env (переменная должна называться BOT_TOKEN)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Токен не найден. Проверьте, что в файле .env есть строка BOT_TOKEN=ваш_токен")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_start_keyboard() -> InlineKeyboardMarkup:
    btn_menu = InlineKeyboardButton(text="Меню", callback_data="menu")
    btn_docs = InlineKeyboardButton(text="Документация магазина", callback_data="docs")

    # Каждая кнопка на отдельной строке (ряду)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [btn_menu],
        [btn_docs]
    ])
    return keyboard

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

@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    if callback.data == "menu":
        await callback.message.edit_text("📜 Вы открыли меню. Здесь скоро появятся разделы: товары, розыгрыши, турниры и др.")
    elif callback.data == "docs":
        await callback.message.edit_text("📖 Документация магазина: правила покупок, возвратов, условия розыгрышей и т.д. (в разработке).")
    await callback.answer()  # Убираем индикатор загрузки у кнопки

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
