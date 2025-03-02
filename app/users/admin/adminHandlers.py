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


@router.callback_query(F.data == 'edit_employee')
async def edit_employee(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    sent_message = await callback_query.message.answer_photo(photo=utils.adminka_png,
                                                             caption='Выберите, какого сотрудника вы хотите редактировать.',
                                                             reply_markup=kb.edit_employee)

    user_data['bot_messages'].append(sent_message.message_id)

@router.callback_query(F.data == "edit_admin")
async def handle_edit_admin(callback_query: CallbackQuery, state: FSMContext):
    page = 1  # начинаем с первой страницы
    admins = await rq.get_admins_by_page(page)
    total = await rq.get_total_admins()
    has_prev = page > 1
    has_next = (page * 10) < total
    markup = kb.create_admin_list_keyboard(admins, page, has_prev, has_next)

    # Если сообщение содержит фотографию, редактируем подпись, иначе – текст
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption="Список администраторов:", reply_markup=markup)
    else:
        await callback_query.message.edit_text(text="Список администраторов:", reply_markup=markup)


@router.callback_query(F.data.startswith("admin_page:"))
async def handle_admin_pagination(callback_query: CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split(":")[1])
    admins = await rq.get_admins_by_page(page)
    total = await rq.get_total_admins()
    has_prev = page > 1
    has_next = (page * 10) < total
    markup = kb.create_admin_list_keyboard(admins, page, has_prev, has_next)
    await callback_query.message.edit_text(text="Список администраторов:", reply_markup=markup)


@router.callback_query(F.data.startswith("admin_detail:"))
async def handle_admin_detail(callback_query: CallbackQuery, state: FSMContext):
    admin_id = int(callback_query.data.split(":")[1])
    admin = await rq.get_admin_by_id(admin_id)
    if not admin:
        await callback_query.answer("Администратор не найден.")
        return
    text = f"Детали администратора:\nID: {admin['id']}\nФИО: {admin['full_name']}\nРоль: {admin['role']}"
    markup = kb.admin_detail_keyboard(admin_id)

    # Если сообщение содержит фотографию, изменяем подпись, иначе — текст.
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption=text, reply_markup=markup)
    else:
        await callback_query.message.edit_text(text=text, reply_markup=markup)


@router.callback_query(F.data.startswith("edit_admin_fullname:"))
async def edit_admin_fullname(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    admin_id = int(callback_query.data.split(":")[1])
    await state.update_data(admin_id=admin_id)
    sent_message = await callback_query.message.answer("Введите новое ФИО для администратора:")
    await state.set_state(st.AdminEdit.waiting_for_fullname)

    user_data['bot_messages'].append(sent_message.message_id)

@router.message(st.AdminEdit.waiting_for_fullname)
async def process_admin_fullname(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    data = await state.get_data()
    admin_id = data.get("admin_id")
    new_fullname = message.text
    success = await rq.update_admin_fullname(admin_id, new_fullname)
    if success:
        sent_message = await message.answer("ФИО успешно изменено.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)
    else:
        sent_message = await message.answer("Ошибка при изменении ФИО.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)

    await state.clear()


@router.callback_query(F.data.startswith("edit_admin_role:"))
async def edit_admin_role(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    admin_id = int(callback_query.data.split(":")[1])
    await state.update_data(admin_id=admin_id)
    sent_message = await callback_query.message.answer("Введите новую роль для администратора:")
    await state.set_state(st.AdminEdit.waiting_for_role)
    user_data['bot_messages'].append(sent_message.message_id)

@router.message(st.AdminEdit.waiting_for_role)
async def process_admin_role(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    data = await state.get_data()
    admin_id = data.get("admin_id")
    new_role = message.text
    success = await rq.update_admin_role(admin_id, new_role)
    if success:
        sent_message = await message.answer("Роль успешно изменена.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)
    else:
        sent_message = await message.answer("Ошибка при изменении роли.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)
    await state.clear()



@router.callback_query(F.data == "edit_manager")
async def handle_edit_manager(callback_query: CallbackQuery, state: FSMContext):
    page = 1  # начинаем с первой страницы
    managers = await rq.get_managers_by_page(page)
    total = await rq.get_total_managers()
    has_prev = page > 1
    has_next = (page * 10) < total
    markup = kb.create_manager_list_keyboard(managers, page, has_prev, has_next)

    # Если сообщение содержит фотографию, редактируем подпись, иначе – текст
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption="Список менеджеров:", reply_markup=markup)
    else:
        await callback_query.message.edit_text(text="Список менеджеров:", reply_markup=markup)


@router.callback_query(F.data.startswith("manager_page:"))
async def handle_manager_pagination(callback_query: CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split(":")[1])
    managers = await rq.get_managers_by_page(page)
    total = await rq.get_total_managers()
    has_prev = page > 1
    has_next = (page * 10) < total
    markup = kb.create_manager_list_keyboard(managers, page, has_prev, has_next)
    await callback_query.message.edit_text(text="Список менеджеров:", reply_markup=markup)


@router.callback_query(F.data.startswith("manager_detail:"))
async def handle_manager_detail(callback_query: CallbackQuery, state: FSMContext):
    manager_id = int(callback_query.data.split(":")[1])
    manager = await rq.get_manager_by_id(manager_id)
    if not manager:
        await callback_query.answer("Менеджер не найден.")
        return
    text = f"Детали менеджера:\nID: {manager['id']}\nФИО: {manager['full_name']}\nРоль: {manager['role']}"
    markup = kb.manager_detail_keyboard(manager_id)

    # Если сообщение содержит фотографию, изменяем подпись, иначе — текст.
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption=text, reply_markup=markup)
    else:
        await callback_query.message.edit_text(text=text, reply_markup=markup)


@router.callback_query(F.data.startswith("edit_manager_fullname:"))
async def edit_manager_fullname(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    manager_id = int(callback_query.data.split(":")[1])
    await state.update_data(manager_id=manager_id)
    sent_message = await callback_query.message.answer("Введите новое ФИО для менеджера:")
    await state.set_state(st.ManagerEdit.waiting_for_fullname)

    user_data['bot_messages'].append(sent_message.message_id)

@router.message(st.ManagerEdit.waiting_for_fullname)
async def process_manager_fullname(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    data = await state.get_data()
    manager_id = data.get("manager_id")
    new_fullname = message.text
    success = await rq.update_manager_fullname(manager_id, new_fullname)
    if success:
        sent_message = await message.answer("ФИО успешно изменено.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)
    else:
        sent_message = await message.answer("Ошибка при изменении ФИО.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)

    await state.clear()


@router.callback_query(F.data.startswith("edit_manager_role:"))
async def edit_manager_role(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    manager_id = int(callback_query.data.split(":")[1])
    await state.update_data(manager_id=manager_id)
    sent_message = await callback_query.message.answer("Введите новую роль для менеджера:")
    await state.set_state(st.ManagerEdit.waiting_for_role)
    user_data['bot_messages'].append(sent_message.message_id)

@router.message(st.ManagerEdit.waiting_for_role)
async def process_manager_role(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    data = await state.get_data()
    manager_id = data.get("manager_id")
    new_role = message.text
    success = await rq.update_manager_role(manager_id, new_role)
    if success:
        sent_message = await message.answer("Роль успешно изменена.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)
    else:
        sent_message = await message.answer("Ошибка при изменении роли.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)
    await state.clear()


@router.callback_query(F.data == "delete_employee")
async def delete_employee(callback_query: CallbackQuery, state: FSMContext):
    text = "Выберите, какого сотрудника хотите удалить:"
    if callback_query.message.photo:
        await callback_query.message.edit_caption(
            caption=text,
            reply_markup=kb.delete_employee_role_keyboard
        )
    else:
        await callback_query.message.edit_text(
            text=text,
            reply_markup=kb.delete_employee_role_keyboard
        )


@router.callback_query(F.data == "delete_admin")
async def delete_admin(callback_query: CallbackQuery, state: FSMContext):
    page = 1
    admins = await rq.get_admins_by_page(page)
    total = await rq.get_total_admins()
    has_prev = page > 1
    has_next = (page * 10) < total
    markup = kb.create_delete_list_keyboard(admins, page, has_prev, has_next, role="admin")
    text = "Список администраторов:"
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption=text, reply_markup=markup)
    else:
        await callback_query.message.edit_text(text=text, reply_markup=markup)


@router.callback_query(F.data == "delete_manager")
async def delete_manager(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора удаления менеджера.
    Выводит список менеджеров с пагинацией.
    """
    page = 1
    managers = await rq.get_managers_by_page(page)
    total = await rq.get_total_managers()
    has_prev = page > 1
    has_next = (page * 10) < total
    markup = kb.create_delete_list_keyboard(managers, page, has_prev, has_next, role="manager")
    text = "Список менеджеров:"
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption=text, reply_markup=markup)
    else:
        await callback_query.message.edit_text(text=text, reply_markup=markup)


@router.callback_query(F.data.startswith("delete_page:"))
async def handle_delete_pagination(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    role = parts[1]
    page = int(parts[2])
    if role == "admin":
        employees = await rq.get_admins_by_page(page)
        total = await rq.get_total_admins()
        text = "Список администраторов:"
    elif role == "manager":
        employees = await rq.get_managers_by_page(page)
        total = await rq.get_total_managers()
        text = "Список менеджеров:"
    else:
        await callback_query.answer("Неверная роль.")
        return

    has_prev = page > 1
    has_next = (page * 10) < total
    markup = kb.create_delete_list_keyboard(employees, page, has_prev, has_next, role=role)
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption=text, reply_markup=markup)
    else:
        await callback_query.message.edit_text(text=text, reply_markup=markup)


@router.callback_query(F.data.startswith("delete_detail:"))
async def handle_delete_detail(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    role = parts[1]
    user_id = int(parts[2])

    if role == "admin":
        employee = await rq.get_admin_by_id(user_id)
    elif role == "manager":
        employee = await rq.get_user_by_id(user_id)
    else:
        await callback_query.answer("Неверная роль.")
        return

    if not employee:
        await callback_query.answer("Сотрудник не найден.")
        return

    text = (
        f"Вы действительно хотите удалить сотрудника?\n\n"
        f"ID: {employee['id']}\nФИО: {employee['full_name']}\nРоль: {employee['role']}\n\n"
        "Внимание: При удалении сотрудника все его данные будут безвозвратно утрачены!"
    )
    markup = kb.confirm_delete_keyboard(employee['id'], role)
    if callback_query.message.photo:
        await callback_query.message.edit_caption(caption=text, reply_markup=markup)
    else:
        await callback_query.message.edit_text(text=text, reply_markup=markup)


@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)
    await delete_previous_messages(callback_query.message, tuid)

    parts = callback_query.data.split(":")
    role = parts[1]
    user_id = int(parts[2])
    confirm = parts[3]
    if confirm == "yes":
        success = await rq.delete_user_by_id(user_id)
        if success:
            sent_message = await callback_query.message.answer("Сотрудник успешно удалён.", reply_markup=kb.go_to_dashboard)
            user_data['bot_messages'].append(sent_message.message_id)
        else:
            sent_message = await callback_query.message.answer("Ошибка при удалении сотрудника.", reply_markup=kb.go_to_dashboard)
            user_data['bot_messages'].append(sent_message.message_id)
    else:
        sent_message = await callback_query.message.answer("Удаление отменено.", reply_markup=kb.go_to_dashboard)
        user_data['bot_messages'].append(sent_message.message_id)

