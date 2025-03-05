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
            text=f"{admin['full_name']}",
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
            text=f"{manager['full_name']}",
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
            text=f"{employee['full_name']}",
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


manage_products_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🗃️ Категории", callback_data='manage_categories'),
     InlineKeyboardButton(text="📁 Подкатегории", callback_data='manage_subcategories')],
    [InlineKeyboardButton(text="📦 Товары", callback_data='manage_one_product')],
    [InlineKeyboardButton(text="⬅️ В личный кабинет", callback_data='go_to_dashboard')]
])


# Клавиатура для раздела "Категории"
categories_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Редактировать категории", callback_data="edit_categories")],
    [InlineKeyboardButton(text="Добавить категорию", callback_data="add_category")],
    [InlineKeyboardButton(text="Удалить категорию", callback_data="delete_category")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="go_to_dashboard")]
])

def create_category_list_keyboard(categories: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру для отображения списка категорий с пагинацией.
    Каждая кнопка возвращает callback_data формата "category_detail:{category_id}"
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for category in categories:
        button = InlineKeyboardButton(
            text=f"{category['name']}",
            callback_data=f"category_detail:{category['id']}"
        )
        markup.inline_keyboard.append([button])
    pagination_buttons = []
    if has_prev:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"category_page:{page-1}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"category_page:{page+1}"))
    if pagination_buttons:
        markup.inline_keyboard.append(pagination_buttons)
    return markup

def category_detail_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для деталей категории: редактирование, удаление, возврат к списку.
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_category:{category_id}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete_category_detail:{category_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_categories")]
    ])
    return markup

def create_delete_category_list_keyboard(categories: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура для списка категорий при удалении.
    Callback_data каждой кнопки: "delete_category_detail:{category_id}"
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for category in categories:
        button = InlineKeyboardButton(
            text=f"{category['name']}",
            callback_data=f"delete_category_detail:{category['id']}"
        )
        markup.inline_keyboard.append([button])
    pagination_buttons = []
    if has_prev:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"delete_category_page:{page-1}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"delete_category_page:{page+1}"))
    if pagination_buttons:
        markup.inline_keyboard.append(pagination_buttons)
    return markup

def confirm_delete_category_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для подтверждения удаления категории.
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить", callback_data=f"confirm_delete_category:{category_id}:yes"),
            InlineKeyboardButton(text="Отмена", callback_data=f"confirm_delete_category:{category_id}:no")
        ]
    ])
    return markup



# Клавиатура для раздела "Подкатегории"
subcategories_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Редактировать подкатегории", callback_data="edit_subcategories")],
    [InlineKeyboardButton(text="Добавить подкатегорию", callback_data="add_subcategory")],
    [InlineKeyboardButton(text="Удалить подкатегорию", callback_data="delete_subcategory")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="go_to_dashboard")]
])

def create_subcategory_list_keyboard(subcategories: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """
    Формирует клавиатуру для вывода списка подкатегорий с пагинацией.
    Callback_data каждой кнопки: "subcategory_detail:{subcategory_id}"
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for subcat in subcategories:
        button = InlineKeyboardButton(
            text=subcat['name'],
            callback_data=f"subcategory_detail:{subcat['id']}"
        )
        markup.inline_keyboard.append([button])
    pagination_buttons = []
    if has_prev:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"subcategory_page:{page-1}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"subcategory_page:{page+1}"))
    if pagination_buttons:
        markup.inline_keyboard.append(pagination_buttons)
    return markup

def subcategory_detail_keyboard(subcategory_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для деталей подкатегории: редактирование, удаление, возврат.
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_subcategory:{subcategory_id}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"delete_subcategory_detail:{subcategory_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_subcategories")]
    ])
    return markup

def create_delete_subcategory_list_keyboard(subcategories: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура для списка подкатегорий при удалении.
    Callback_data каждой кнопки: "delete_subcategory_detail:{subcategory_id}"
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for subcat in subcategories:
        button = InlineKeyboardButton(
            text=subcat['name'],
            callback_data=f"delete_subcategory_detail:{subcat['id']}"
        )
        markup.inline_keyboard.append([button])
    pagination_buttons = []
    if has_prev:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"delete_subcategory_page:{page-1}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"delete_subcategory_page:{page+1}"))
    if pagination_buttons:
        markup.inline_keyboard.append(pagination_buttons)
    return markup

def confirm_delete_subcategory_keyboard(subcategory_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для подтверждения удаления подкатегории.
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить", callback_data=f"confirm_delete_subcategory:{subcategory_id}:yes"),
            InlineKeyboardButton(text="Отмена", callback_data=f"confirm_delete_subcategory:{subcategory_id}:no")
        ]
    ])
    return markup

def create_parent_category_keyboard(categories: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора родительской категории при редактировании подкатегории.
    Callback_data: "parent_category:{category_id}"
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        button = InlineKeyboardButton(text=cat['name'], callback_data=f"parent_category:{cat['id']}")
        markup.inline_keyboard.append([button])
    pagination_buttons = []
    if has_prev:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"parent_category_page:{page-1}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"parent_category_page:{page+1}"))
    if pagination_buttons:
        markup.inline_keyboard.append(pagination_buttons)
    return markup

def create_parent_category_keyboard_add(categories: list, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора родительской категории при добавлении подкатегории.
    Callback_data: "parent_category_add:{category_id}"
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        button = InlineKeyboardButton(text=cat['name'], callback_data=f"parent_category_add:{cat['id']}")
        markup.inline_keyboard.append([button])
    pagination_buttons = []
    if has_prev:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"parent_category_add_page:{page-1}"))
    if has_next:
        pagination_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"parent_category_add_page:{page+1}"))
    if pagination_buttons:
        markup.inline_keyboard.append(pagination_buttons)
    return markup


# Клавиатура для раздела "Товары"
product_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Добавить товар", callback_data="add_product"),
     InlineKeyboardButton(text="Редактировать товар", callback_data="edit_product")],
    [InlineKeyboardButton(text="Удалить товар", callback_data="delete_product")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="go_to_dashboard")]
])
