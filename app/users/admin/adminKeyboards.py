from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from urllib.parse import quote

from app import utils

admin_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📦 Товары", callback_data='manage_products'),
     InlineKeyboardButton(text="👥 Сотрудники", callback_data='manage_employees')],
    [InlineKeyboardButton(text="📊 Отчёты", callback_data='view_reports'),
     InlineKeyboardButton(text="📢 Рассылка", callback_data='send_notifications')]])

manage_employees_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Добавить сотрудника", callback_data='add_employee')],
    [InlineKeyboardButton(text="✏️ Редактировать сотрудника", callback_data='edit_employee')],
    [InlineKeyboardButton(text="❌ Удалить сотрудника", callback_data='delete_employee')],
    [InlineKeyboardButton(text="⬅️ В личный кабинет", callback_data='go_to_dashboard')]
])

add_employee = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Администратор", callback_data='add_admin')],
    [InlineKeyboardButton(text="➕ Менеджер", callback_data='add_manager')],
    [InlineKeyboardButton(text="⬅️ В личный кабинет", callback_data='go_to_dashboard')]
])

go_to_dashboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ В личный кабинет", callback_data='go_to_dashboard')]
])

edit_employee = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ Администратор", callback_data='edit_admin')],
    [InlineKeyboardButton(text="✏️ Менеджер", callback_data='edit_manager')],
    [InlineKeyboardButton(text="⬅️ В личный кабинет", callback_data='go_to_dashboard')]
])


def create_admin_list_keyboard(admins: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    # Добавляем кнопки для каждого администратора (каждая кнопка в новой строке)
    for admin in admins:
        button = InlineKeyboardButton(
            text=f"ID: {admin['id']}, {admin['full_name']}",
            callback_data=f"admin_detail:{admin['id']}"
        )
        markup.inline_keyboard.append([button])
    # Добавляем строку пагинации
    pagination = admin_pagination_keyboard(page, has_prev, has_next)
    for row in pagination.inline_keyboard:
        markup.inline_keyboard.append(row)
    return markup


def admin_pagination_keyboard(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_prev:
        buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"admin_page:{page-1}"))
    if has_next:
        buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"admin_page:{page+1}"))
    markup = InlineKeyboardMarkup(inline_keyboard=[], row_width=2)
    if buttons:
        markup.inline_keyboard.append(buttons)
    return markup


def admin_detail_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить ФИО", callback_data=f"edit_admin_fullname:{admin_id}")],
        [InlineKeyboardButton(text="Изменить роль", callback_data=f"edit_admin_role:{admin_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_admin")]
    ])
    return markup


def create_manager_list_keyboard(managers: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    # Добавляем кнопки для каждого администратора (каждая кнопка в новой строке)
    for manager in managers:
        button = InlineKeyboardButton(
            text=f"ID: {manager['id']}, {manager['full_name']}",
            callback_data=f"admin_detail:{manager['id']}"
        )
        markup.inline_keyboard.append([button])
    # Добавляем строку пагинации
    pagination = manager_pagination_keyboard(page, has_prev, has_next)
    for row in pagination.inline_keyboard:
        markup.inline_keyboard.append(row)
    return markup


def manager_pagination_keyboard(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_prev:
        buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"manager_page:{page-1}"))
    if has_next:
        buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"manager_page:{page+1}"))
    markup = InlineKeyboardMarkup(inline_keyboard=[], row_width=2)
    if buttons:
        markup.inline_keyboard.append(buttons)
    return markup


def manager_detail_keyboard(manager_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить ФИО", callback_data=f"edit_admin_fullname:{manager_id}")],
        [InlineKeyboardButton(text="Изменить роль", callback_data=f"edit_admin_role:{manager_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_admin")]
    ])
    return markup



# Клавиатура для выбора роли сотрудника для удаления
delete_employee_role_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Удалить администратора", callback_data="delete_admin")],
    [InlineKeyboardButton(text="❌ Удалить менеджера", callback_data="delete_manager")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="go_to_dashboard")]
])

def create_delete_list_keyboard(employees: list, page: int, has_prev: bool, has_next: bool, role: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру со списком сотрудников для удаления с пагинацией.
    Каждая кнопка имеет callback_data формата "delete_detail:{role}:{user_id}".
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for employee in employees:
        button = InlineKeyboardButton(
            text=f"ID: {employee['id']}, {employee['full_name']}",
            callback_data=f"delete_detail:{role}:{employee['id']}"
        )
        markup.inline_keyboard.append([button])
    # Добавляем кнопки пагинации
    pagination_buttons = []
    if has_prev:
        pagination_buttons.append(InlineKeyboardButton(
            text="⬅️ Предыдущая",
            callback_data=f"delete_page:{role}:{page-1}"
        ))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(
            text="Следующая ➡️",
            callback_data=f"delete_page:{role}:{page+1}"
        ))
    if pagination_buttons:
        markup.inline_keyboard.append(pagination_buttons)
    return markup

def confirm_delete_keyboard(employee_id: int, role: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для подтверждения удаления сотрудника.
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить", callback_data=f"confirm_delete:{role}:{employee_id}:yes"),
            InlineKeyboardButton(text="Отмена", callback_data=f"confirm_delete:{role}:{employee_id}:no")
        ]
    ])
    return markup
