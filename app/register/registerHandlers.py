import re
from datetime import datetime
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.database import requests as rq
import app.register.registerKeyboards as kb
import app.register.registerStates as st
from app.users.admin.adminHandlers import admin_account
from app.users.user.userHandlers import user_account
from app.users.manager.managerHandlers import manager_account
from app.utils import sent_message_add_screen_ids, router


# Function to delete previous messages
async def delete_previous_messages(message: Message, telegram_id: str):
    # Проверяем, есть ли записи для этого пользователя
    if telegram_id not in sent_message_add_screen_ids:
        sent_message_add_screen_ids[telegram_id] = {'bot_messages': [], 'user_messages': []}

    user_data = sent_message_add_screen_ids[telegram_id]

    # Удаляем все сообщения пользователя, кроме "/start"
    for msg_id in user_data['user_messages']:
        try:
            if msg_id != message.message_id or message.text != "/start":
                await message.bot.delete_message(chat_id=telegram_id, message_id=msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")
    user_data['user_messages'].clear()

    # Удаляем все сообщения бота
    for msg_id in user_data['bot_messages']:
        try:
            if msg_id != message.message_id:
                await message.bot.delete_message(chat_id=telegram_id, message_id=msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")
    user_data['bot_messages'].clear()


# /Start
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    tuid = message.chat.id
    if tuid not in sent_message_add_screen_ids:
        sent_message_add_screen_ids[tuid] = {'bot_messages': [], 'user_messages': []}
    user_data = sent_message_add_screen_ids[tuid]
    user_tg_id = str(message.from_user.id)
    print(user_tg_id)
    role = await rq.check_role(user_tg_id)
    print(role)
    if role == "ADMIN":
        await admin_account(message, state)
    elif role == "MANAGER":
        await manager_account(message, state)
    elif role == "USER":
        await user_account(message, state)
    else:
        sent_message = await message.answer(
            text="Ошибка при регистрации!"
        )
        user_data['bot_messages'].append(sent_message.message_id)