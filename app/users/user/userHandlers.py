import json
import re
import pytz
from datetime import datetime
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import CommandStart, Command
from aiogram import F, Router
from app.database import requests as rq
from aiogram.fsm.context import FSMContext
from app.utils import sent_message_add_screen_ids, router
from app.users.user import userStates as st
import app.users.user.userKeyboards as kb
from app import utils
from aiogram.enums import ParseMode


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


# User's personal account
async def user_account(message: Message, state: FSMContext):
    tuid = message.chat.id
    if tuid not in sent_message_add_screen_ids:
        sent_message_add_screen_ids[tuid] = {'bot_messages': [], 'user_messages': []}
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    await state.clear()

    sent_message = await message.answer_photo(
        photo=utils.user_png,
        caption="Добро пожаловать! 🎉",
        reply_markup=kb.user_button
    )

    # Добавляем сообщение бота
    user_data['bot_messages'].append(sent_message.message_id)


@router.callback_query(F.data == 'go_to_user_dashboard')
async def go_to_dashboard(callback_query: CallbackQuery, state: FSMContext):
    await user_account(callback_query.message, state)


@router.callback_query(F.data == 'user_settings')
async def user_settings(callback_query: CallbackQuery, state: FSMContext):
    info = await rq.get_user_info_by_id(str(callback_query.from_user.id))
    print(callback_query.from_user.id)
    # Формируем текст для отображения, учитывая, что info может содержать ключ "answer"
    if "answer" in info:
        caption = f"Ошибка: {info['answer']}"
    else:
        caption = (
            f"👤 ФИО: {info['full_name']}\n"
            f"📍 Адрес: {info['address']}\n"
            f"📞 Телефон: {info['phone_number']}"
        )
    await callback_query.message.edit_media(
        media=InputMediaPhoto(
            media=utils.user_second_png,
            caption=caption
        ),
        reply_markup=kb.user_settings_setting
    )


@router.callback_query(F.data == 'change_fullname')
async def change_fullname(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_media(
        media=InputMediaPhoto(
            media=utils.user_second_png,
            caption="Пожалуйста, напишите ваше ФИО:"
        ),
        reply_markup=kb.go_to_user_dashboard
    )
    await state.set_state(st.ChangeFullname.write_fullname)


@router.message(st.ChangeFullname.write_fullname)
async def change_fullname_second(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    is_updated = await rq.update_user_full_name(str(message.from_user.id), message.text)

    if is_updated:
        await message.answer("Ваше ФИО успешно обновлено!",
                             reply_markup=kb.user_settings)
    else:
        await message.answer("Ошибка: не удалось обновить ФИО",
                             reply_markup=kb.user_settings)


@router.callback_query(F.data == 'change_phone')
async def change_phone(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_media(
        media=InputMediaPhoto(
            media=utils.user_second_png,
            caption="Пожалуйста, введите ваш номер телефона в формате +996XXXXXXXXX:"
        ),
        reply_markup=kb.go_to_user_dashboard
    )
    await state.set_state(st.ChangePhone.write_phone)


@router.message(st.ChangePhone.write_phone)
async def change_phone_second(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    phone = message.text.strip()
    # Валидация номера телефона: формат +996XXXXXXXXX (4 символа + 9 цифр)
    if not re.fullmatch(r'\+996\d{9}', phone):
        sent_message = await message.answer(
            "Ошибка: Неверный формат номера. Пожалуйста, введите номер в формате +996XXXXXXXXX",
            reply_markup=kb.user_settings
        )
        user_data['bot_messages'].append(sent_message.message_id)
        return

    is_updated = await rq.update_user_phone(str(message.from_user.id), phone)
    if is_updated:
        sent_message = await message.answer("Ваш номер телефона успешно обновлен!", reply_markup=kb.user_settings)
        user_data['bot_messages'].append(sent_message.message_id)
    else:
        sent_message = await message.answer("Ошибка: не удалось обновить номер телефона", reply_markup=kb.user_settings)
        user_data['bot_messages'].append(sent_message.message_id)


@router.callback_query(F.data == 'change_delivery')
async def change_address(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_media(
        media=InputMediaPhoto(
            media=utils.user_second_png,
            caption="Пожалуйста, введите ваш адрес:"
        ),
        reply_markup=kb.go_to_user_dashboard
    )
    await state.set_state(st.ChangeAddress.write_address)


@router.message(st.ChangeAddress.write_address)
async def change_address_second(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    is_updated = await rq.update_user_address(str(message.from_user.id), message.text)
    if is_updated:
        await message.answer("Ваш адрес успешно обновлен!", reply_markup=kb.user_settings)
    else:
        await message.answer("Ошибка: не удалось обновить адрес", reply_markup=kb.user_settings)