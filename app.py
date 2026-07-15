import os
import hmac
import hashlib
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import sqlite3
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TERMINAL_SECRET = os.getenv("TERMINAL_SECRET")
DB_PATH = "payments.db"

if not BOT_TOKEN or not TERMINAL_SECRET:
    raise ValueError("Нужны BOT_TOKEN и TERMINAL_SECRET в .env")

app = FastAPI()


def get_telegram_bot_session():
    # Простой HTTP‑клиент для отправки сообщений в Telegram
    import aiohttp
    session = aiohttp.ClientSession()
    return session


async def send_telegram_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()


def verify_tinkoff_signature(payload: dict, signature: str) -> bool:
    """
    Т‑Банк присылает поле Signature.
    Строим строку для подписи: сортируем ключи, делаем key=value, добавляем TERMINAL_SECRET.
    """
    filtered = {k: v for k, v in payload.items() if v is not None and v != ""}
    sorted_keys = sorted(filtered.keys())
    sign_str = "".join(f"{k}={filtered[k]}" for k in sorted_keys)
    sign_str += TERMINAL_SECRET

    expected = hmac.new(
        TERMINAL_SECRET.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def update_order_status_in_db(order_id: str, status: str, delivered: bool = False):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute(
                "UPDATE orders SET status = ?, delivered = ? WHERE order_id = ?",
                (status, 1 if delivered else 0, order_id)
            )
            conn.commit()
            return c.rowcount > 0
        except sqlite3.Error as e:
            print(f"SQLite error при обновлении заказа: {e}")
            return False


@app.post("/webhook/tinkoff")
async def tinkoff_webhook(request: Request):
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    signature = request.headers.get("Signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Signature header")

    # Проверка подписи
    if not verify_tinkoff_signature(payload, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    order_id = payload.get("OrderId")
    status_from_bank = payload.get("Status")  # например: WAITING, AUTHORIZED, REJECTED

    if not order_id:
        return JSONResponse(status_code=200, content={"status": "ok", "message": "No OrderId"})

    print(f"[Webhook] Получен статус для заказа {order_id}: {status_from_bank}")

    delivered = False
    new_status = status_from_bank or "UNKNOWN"

    # Логика статусов Т‑Банка (упрощённо)
    if status_from_bank == "AUTHORIZED":
        delivered = True
        new_status = "PAID"
    elif status_from_bank in ("REJECTED", "CANCELED"):
        new_status = "REJECTED"
    # WAITING и другие — оставляем как есть или ставим PENDING

    updated = update_order_status_in_db(order_id, new_status, delivered=delivered)
    if not updated:
        # Если такого заказа нет — всё равно отвечаем 200, чтобы Т‑Банк не слал повторные вебхуки
        return JSONResponse(status_code=200, content={"status": "ok", "message": "Order not found"})

    # Если оплата успешна — отправляем уведомление пользователю
    if delivered:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT user_id, uc_amount, uid FROM orders WHERE order_id = ?", (order_id,))
            row = c.fetchone()

        if row:
            user_id = row["user_id"]
            uc_amount = row["uc_amount"]
            uid = row["uid"]

            text = (
                f"✅ Оплата подтверждена!\n\n"
                f"Заказ: {uc_amount} UC\n"
                f"UID: {uid}\n\n"
                "Ваш заказ обрабатывается. Ожидайте начисления UC в ближайшее время."
            )
            await send_telegram_message(user_id, text)

    return JSONResponse(status_code=200, content={"status": "ok"})
