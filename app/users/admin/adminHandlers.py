import re
from datetime import datetime

from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram import F, Router

from app.users.admin import adminKeyboards as kb
from app.users.admin import adminStates as st
from app import utils
from app.database import requests as rq
from aiogram.fsm.context import FSMContext

from app.utils import sent_message_add_screen_ids, router
from app import utils


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


# Administrator's personal account
async def admin_account(message: Message, state: FSMContext):
    tuid = message.chat.id
    if tuid not in sent_message_add_screen_ids:
        sent_message_add_screen_ids[tuid] = {'bot_messages': [], 'user_messages': []}
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    await state.clear()

    sent_message = await message.answer_photo(
        photo=utils.adminka_png,
        caption="Добро пожаловать в панель администратора! Выберите нужный раздел.",
        reply_markup=kb.admin_button
    )

    # Добавляем сообщение бота
    user_data['bot_messages'].append(sent_message.message_id)

# Хендлер для обработки команды "/photo"
@router.message(Command("photo"))
async def request_photo_handler(message: Message):
    await message.answer("Пожалуйста, отправьте фото, чтобы я мог получить его ID.")


# Хендлер для обработки фото от пользователя
@router.message(F.photo)
async def photo_handler(message: Message):
    # Берем фотографию в самом большом разрешении и получаем ее ID
    photo_id = message.photo[-1].file_id
    await message.answer(f"ID вашей картинки: {photo_id}")


@router.callback_query(F.data == 'manage_employees')
async def manage_employees(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)

    await delete_previous_messages(callback_query.message, tuid)
    sent_message = await callback_query.message.answer_photo(photo=utils.adminka_png,
                                                             caption='Выберите нужное действие.',
                                                             reply_markup=kb.manage_employees_button)

    user_data['bot_messages'].append(sent_message.message_id)

@router.callback_query(F.data == 'go_to_dashboard')
async def go_to_dashboard(callback_query: CallbackQuery, state: FSMContext):
    await admin_account(callback_query.message, state)

@router.callback_query(F.data == 'add_employee')
async def add_employee(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    sent_message = await callback_query.message.answer_photo(photo=utils.adminka_png,
                                                             caption='Выберите, какого сотрудника вы хотите добавить.',
                                                             reply_markup=kb.add_employee)

    user_data['bot_messages'].append(sent_message.message_id)

@router.callback_query(F.data == 'add_admin')
async def add_admin(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    sent_message = await callback_query.message.answer(
        text="Напишите telegram id пользователя",
        reply_markup=kb.go_to_dashboard
    )
    await state.set_state(st.AddAdmin.write_telegram_id)

    user_data['bot_messages'].append(sent_message.message_id)

@router.message(st.AddAdmin.write_telegram_id)
async def add_admin_second(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    new_admin_telegram_id = message.text
    await state.update_data(new_admin_telegram_id=new_admin_telegram_id)
    sent_message = await message.answer(
        text="Напишите ФИО пользователя",
        reply_markup=kb.go_to_dashboard
    )

    await state.set_state(st.AddAdmin.write_fullname)
    user_data['bot_messages'].append(sent_message.message_id)


@router.message(st.AddAdmin.write_fullname)
async def add_admin_third(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    state_data = await state.get_data()
    new_admin_telegram_id = state_data.get('new_admin_telegram_id')
    new_admin_fullname = message.text

    print(new_admin_telegram_id)
    print(new_admin_fullname)

    is_added = await rq.add_or_update_user(telegram_id=new_admin_telegram_id,
                                     full_name=new_admin_fullname,
                                     role="ADMIN")

    if is_added:
        sent_message = await message.answer(
            text="Новый администратор успешно добавлен в систему.",
            reply_markup=kb.go_to_dashboard
        )
    else:
        sent_message = await message.answer(
            text="Не удалось добавить администратора. Пожалуйста, попробуйте снова.",
            reply_markup=kb.go_to_dashboard
        )

    user_data['bot_messages'].append(sent_message.message_id)

@router.callback_query(F.data == 'add_manager')
async def add_manager(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    sent_message = await callback_query.message.answer(
        text="Напишите telegram id пользователя",
        reply_markup=kb.go_to_dashboard
    )
    await state.set_state(st.AddManager.write_telegram_id)

    user_data['bot_messages'].append(sent_message.message_id)

@router.message(st.AddManager.write_telegram_id)
async def add_manager_second(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    new_manager_telegram_id = message.text
    await state.update_data(new_manager_telegram_id=new_manager_telegram_id)
    sent_message = await message.answer(
        text="Напишите ФИО пользователя",
        reply_markup=kb.go_to_dashboard
    )

    await state.set_state(st.AddManager.write_fullname)
    user_data['bot_messages'].append(sent_message.message_id)


@router.message(st.AddManager.write_fullname)
async def add_manager_third(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    state_data = await state.get_data()
    new_manager_telegram_id = state_data.get('new_manager_telegram_id')
    new_manager_fullname = message.text

    print(new_manager_telegram_id)
    print(new_manager_fullname)

    is_added = await rq.add_or_update_user(telegram_id=new_manager_telegram_id,
                                     full_name=new_manager_fullname,
                                     role="MANAGER")

    if is_added:
        sent_message = await message.answer(
            text="Новый менеджер успешно добавлен в систему.",
            reply_markup=kb.go_to_dashboard
        )
    else:
        sent_message = await message.answer(
            text="Не удалось добавить менеджера. Пожалуйста, попробуйте снова.",
            reply_markup=kb.go_to_dashboard
        )

    user_data['bot_messages'].append(sent_message.message_id)