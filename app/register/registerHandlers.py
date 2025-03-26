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
    role = await rq.check_role(user_tg_id)
    if role == "ADMIN":
        await admin_account(message, state)
    elif role == "MANAGER":
        await manager_account(message, state)
    elif role == "USER":
        result = await rq.check_user_data(user_tg_id)
        if result == "Нет ФИО":
            await register_user_fullname(message, state)
        else:
            await user_account(message, state)
    else:
        sent_message = await message.answer(
            text="Ошибка при регистрации!"
        )
        user_data['bot_messages'].append(sent_message.message_id)


async def register_user_fullname(message: Message, state: FSMContext):
    tuid = message.chat.id
    if tuid not in sent_message_add_screen_ids:
        sent_message_add_screen_ids[tuid] = {'bot_messages': [], 'user_messages': []}
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    sent_message = await message.answer(
        text="Добро пожаловать!"
             "Для дальнейшей работы введите ФИО"
    )
    await state.set_state(st.UserRegister.write_fullname)
    user_data['bot_messages'].append(sent_message.message_id)

@router.message(st.UserRegister.write_fullname)
async def register_user_number(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    await state.update_data(full_name=message.text)

    sent_message = await message.answer(
        text="Введите номер телефона: "
             "Формат: +996700123456"
    )
    await state.set_state(st.UserRegister.write_fullname)
    user_data['bot_messages'].append(sent_message.message_id)
    await state.set_state(st.UserRegister.write_phone_number)

@router.message(st.UserRegister.write_phone_number)
async def register_finish(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    phone_number = message.text

    # Добавляем валидацию номера телефона по формату: +996XXXXXXXXX (9 цифр после кода)
    if not re.match(r'^\+996\d{9}$', phone_number):
        sent_message = await message.answer(
            text="Неверный формат номера телефона.\n"
                 "Пожалуйста, введите номер в формате: +996700123456"
        )
        user_data['bot_messages'].append(sent_message.message_id)
        return

    data = await state.get_data()
    full_name = data.get("full_name")

    result = await rq.register_user(
        telegram_id=message.from_user.id,
        full_name=full_name,
        phone_number=phone_number
    )

    if result:
        await start(message, state)
    else:
        sent_message = await message.answer(
            text="Ошибка при регистрации!\n"
                 "Попробуйте еще раз, нажав на /start"
        )
        user_data['bot_messages'].append(sent_message.message_id)

