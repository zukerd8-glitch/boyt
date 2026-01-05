import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from config import settings
from logger_setup import setup_logger
from loguru import logger
from db import init_db, save_message, get_last_messages
from ai_client import generate_compliment
from utils import normalize_type
from typing import Optional

logger = setup_logger(settings.LOG_LEVEL)

# Aiogram 3.x
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Keyboard for types
def types_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Внешность", callback_data="type:appearance"),
         InlineKeyboardButton(text="Характер", callback_data="type:character")],
        [InlineKeyboardButton(text="Достижения", callback_data="type:achievements")]
    ])
    return kb

@dp.message(Command(commands=["start"]))
async def cmd_start(message: Message):
    await save_message(str(message.from_user.id), "user", "/start")
    text = ("Привет! Я бот-генератор комплиментов для Оли. Отправь короткое сообщение — опиши ситуацию или настроение, "
            "и выбери тип комплимента, чтобы получить персональный комплимент.")
    await message.answer(text, reply_markup=types_keyboard())

@dp.message()
async def handle_message(message: Message):
    uid = str(message.from_user.id)
    text = message.text or ""
    await save_message(uid, "user", text)
    # Сохраним и предложим выбрать тип комплимента
    await message.answer("Выбери тип комплимента:", reply_markup=types_keyboard())

@dp.callback_query(lambda c: c.data and c.data.startswith("type:"))
async def process_type(callback: types.CallbackQuery):
    await callback.answer()
    uid = str(callback.from_user.id)
    typ = callback.data.split(":", 1)[1]
    typ = normalize_type(typ)
    # Получаем последние 1-2 сообщения пользователя
    context_messages = await get_last_messages(uid, limit=2)
    # Генерируем комплимент
    try:
        await save_message(uid, "system", f"requested_compliment_type:{typ}")
        compliment = await generate_compliment(uid, typ, context_messages)
    except Exception as e:
        logger.exception("Generation failed: {}", e)
        compliment = "Упс, возникла ошибка при генерации комплимента. Попробуйте ещё раз позже."
    # Сохраняем ответ бота
    await save_message(uid, "bot", compliment)
    # Отправляем пользователю
    await bot.send_message(chat_id=uid, text=compliment)
    # Optionally send follow-up actions
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ещё один", callback_data=f"type:{typ}"), InlineKeyboardButton(text="Другой тип", callback_data="type:random")],
    ])
    await bot.send_message(chat_id=uid, text="Хочешь ещё?", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "type:random")
async def random_type(callback: types.CallbackQuery):
    await callback.answer()
    # choose default sequence: character
    typ = "character"
    uid = str(callback.from_user.id)
    context_messages = await get_last_messages(uid, limit=2)
    compliment = await generate_compliment(uid, typ, context_messages)
    await save_message(uid, "bot", compliment)
    await bot.send_message(chat_id=uid, text=compliment)

async def on_startup():
    logger.info("Bot starting...")
    await init_db()
    # any other startup actions

async def main():
    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
