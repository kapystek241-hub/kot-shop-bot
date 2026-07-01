import asyncio
import os
import time
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "KotShop241")
RAFFLE_ENABLED = os.getenv("RAFFLE_ENABLED", "true").lower() == "true"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Тексты (для удобства редактирования) ---

TEXT_START = (
    "Доброго времени суток!\n\n"
    "Бот постоянно находится в разработке. На данный момент бот работает с 9:00 до 23:00 по МСК. "
    "Причина, по которой бот работает определенное время: бот находится на стадии теста функционала.\n\n"
    "Покупки, сообщения, розыгрыши доступны.\n\n"
    "В нашем боте есть возможность ускорить процесс поиска по ключевым словам."
)

TEXT_MENU_INFO = (
    "Доброго времени суток, для быстрого поиска используйте ключевые слова или используйте меню с кнопками.\n\n"
    f"Пример поиска по ключевым словам (<b>Юси</b>) — по этому слову открывается раздел с покупками UC для PUBG Mobile.\n\n"
    "Бот работает штатно."
)

TEXT_DOCS = (
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

TEXT_WAIT = "Ожидайте..."
TEXT_SELECT_ITEM = "Выберите нужный товар"
TEXT_RAFFLE_INFO = "Розыгрыш проходит на каналах в прямом эфире, информация о том где проходит розыгрыш ищите в телеграмм канале."
TEXT_CLAIM_WIN = (
    "Поздравляю с победой! Для получения выигрыша вы должны быть подписаны на телеграмм канал, "
    "отправить ваш UID, который должен начинаться на 5.\n\n"
    "Проверяйте подписку на канал: <a href='https://t.me/KotShop241'>телеграмм канал</a>\n"
    "Отправляйте ответ с цифрами, которые начинаются на 5, в этот чат: 7309972832."
)
TEXT_RAFFLE_DISABLED = (
    "Доброго времени суток, на данный момент розыгрыши не проводились. "
    "Следите за новостями в моем <a href='https://t.me/KotShop241'>телеграмм канале</a>, "
    "там выкладывается актуальная информация по розыгрышам."
)
TEXT_TOURNAMENT_FORM = (
    "Доброго времени суток, заполните форму участия ниже.\n\n"
    "Название команды (Название не должно нести оскорбление, мат, отсылки на наркотические и опьяняющие вещества)\n\n"
    "1) ID Капитана команды\n"
    "2) ID участника 1\n"
    "3) ID участника 2\n"
    "4) ID участника 3\n"
    "5) ID запасного участника 1 (если есть)\n\n"
    "Подтверждение о том, что правила были прочитаны всеми участниками, вы являетесь подписанными на телеграмм канал аккаунтами, "
    "с которыми будет проводиться дальнейшее общение.\n\n"
    "После с капитаном будет происходить связь с помощью аккаунта менеджера @KotShop2415.\n\n"
    "В случае несоблюдения правил будут приняты меры, описанные в разделе «Правила турнира»."
)
TEXT_CONFIRM_REQUEST = "Вы хотите подтвердить участие?"

# --- Клавиатуры ---

def kb_start():
    builder = InlineKeyboardBuilder()
    builder.button(text="Меню", callback_data="menu_main")
    builder.button(text="Документы магазина", callback_data="docs_shop")
    return builder.as_markup()

def kb_menu_level1():
    builder = InlineKeyboardBuilder()
    builder.button(text="1.1 Купить", callback_data="item_buy")
    builder.button(text="1.1 Розыгрыш", callback_data="raffle_main")
    builder.button(text="1.1 Турнир", callback_data="tournament_main")
    builder.button(text="1.1 Акции", callback_data="promo_main")
    builder.button(text="1.1 Поддержка", callback_data="support_main")
    builder.button(text="❌ Назад", callback_data="back_to_start")
    return builder.as_markup()

def kb_back_only():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Назад", callback_data="back_to_menu")
    return builder.as_markup()

def kb_raffle_claim():
    builder = InlineKeyboardBuilder()
    builder.button(text="Забрать выигрыш", callback_data="claim_win")
    builder.button(text="❌ Назад", callback_data="back_to_raffle")
    return builder.as_markup()

def kb_tournament_confirm():
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data="confirm_apply")
    builder.button(text="Отменить", callback_data="cancel_apply")
    return builder.as_markup()

# --- Вспомогательные функции ---

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        # Если бот не админ канала или другая ошибка — считаем, что не подписан
        return False

async def send_to_admin(text: str, caption: str = None):
    try:
        if caption:
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"{text}\n\n{caption}")
        else:
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
    except Exception as e:
        print(f"Не удалось отправить сообщение админу: {e}")

# --- Хендлеры ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        text=TEXT_START,
        reply_markup=kb_start(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "menu_main")
async def cb_menu_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=TEXT_MENU_INFO,
        reply_markup=kb_menu_level1(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "docs_shop")
async def cb_docs_shop(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=TEXT_DOCS,
        reply_markup=kb_back_only(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def cb_back_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=TEXT_START,
        reply_markup=kb_start()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def cb_back_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=TEXT_MENU_INFO,
        reply_markup=kb_menu_level1(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "item_buy")
async def cb_buy(callback: types.CallbackQuery):
    # Имитация задержки 0.5 сек
    await callback.message.edit_text(text=TEXT_WAIT)
    await asyncio.sleep(0.5)
    await callback.message.edit_text(
        text=TEXT_SELECT_ITEM,
        reply_markup=InlineKeyboardBuilder().button(text="Пример товара 1", callback_data="dummy").as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "raffle_main")
async def cb_raffle_main(callback: types.CallbackQuery):
    if not RAFFLE_ENABLED:
        await callback.message.edit_text(
            text=TEXT_RAFFLE_DISABLED,
            reply_markup=kb_back_only(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        text=TEXT_RAFFLE_INFO,
        reply_markup=kb_raffle_claim(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "claim_win")
async def cb_claim_win(callback: types.CallbackQuery):
    is_sub = await check_subscription(callback.from_user.id)
    if not is_sub:
        await callback.answer("❌ Сначала подпишитесь на канал!", show_alert=True)
        return

    await callback.message.edit_text(
        text=TEXT_CLAIM_WIN,
        reply_markup=kb_back_only(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_raffle")
async def cb_back_raffle(callback: types.CallbackQuery):
    await cb_raffle_main(callback)

@dp.callback_query(F.data == "tournament_main")
async def cb_tournament_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text="Выберите интересующий раздел",
        reply_markup=InlineKeyboardBuilder()
        .button(text="1.4 Принять участие", callback_data="apply_tournament")
        .button(text="❌ Назад", callback_data="back_to_menu")
        .as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "apply_tournament")
async def cb_apply_tournament(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=TEXT_TOURNAMENT_FORM,
        reply_markup=InlineKeyboardBuilder()
        .button(text="Я заполнил форму", callback_data="ready_form")
        .button(text="❌ Назад", callback_data="back_to_tournament")
        .as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "ready_form")
async def cb_ready_form(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text=TEXT_CONFIRM_REQUEST,
        reply_markup=kb_tournament_confirm(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "confirm_apply")
async def cb_confirm_apply(callback: types.CallbackQuery):
    user = callback.from_user
    report = (
        f"Турнирная заявка\n"
        f"Пользователь: {user.full_name} (@{user.username or 'нет юзернейма'})\n"
        f"ID: {user.id}\n"
        f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await send_to_admin(report)
    await callback.message.edit_text("✅ Заявка отправлена! Ожидайте связи с менеджером.")
    await callback.answer()

@dp.callback_query(F.data == "cancel_apply")
async def cb_cancel_apply(callback: types.CallbackQuery):
    await callback.message.edit_text("Заявка отменена.")
    await callback.answer()

@dp.callback_query(F.data == "back_to_tournament")
async def cb_back_tournament(callback: types.CallbackQuery):
    await cb_tournament_main(callback)

# Заглушки для остальных кнопок (Акции, Поддержка)
@dp.callback_query(F.data.in_({"promo_main", "support_main"}))
async def cb_placeholders(callback: types.CallbackQuery):
    await callback.answer("Раздел в разработке", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
