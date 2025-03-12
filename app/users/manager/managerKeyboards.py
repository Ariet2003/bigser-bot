from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


manager_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🆕 Новые заказы", callback_data='manager_new_orders'),
     InlineKeyboardButton(text="📊 Статистика", callback_data='manager_stats')],
    [InlineKeyboardButton(text="📦 Мои заказы", callback_data='manager_my_orders'),
     InlineKeyboardButton(text="👤 Профиль", callback_data='manager_profile')]
])

def get_new_orders_keyboard(order_groups: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    for idx, group in enumerate(order_groups, start=1):
        buttons.append(InlineKeyboardButton(text=str(idx), callback_data=f"manager_order_detail:{group.id}"))
    row1 = buttons[:5]
    row2 = buttons[5:10]
    keyboard_buttons = []
    if row1:
        keyboard_buttons.append(row1)
    if row2:
        keyboard_buttons.append(row2)
    # Пагинация
    pagination = []
    if page > 1:
        pagination.append(InlineKeyboardButton(text="<<", callback_data=f"manager_new_orders_page:{page-1}"))
    pagination.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        pagination.append(InlineKeyboardButton(text=">>", callback_data=f"manager_new_orders_page:{page+1}"))
    if pagination:
        keyboard_buttons.append(pagination)
    keyboard_buttons.append([InlineKeyboardButton(text="Назад", callback_data="go_to_manager_dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_manager_order_detail_keyboard(order_group_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Редактировать заказ", callback_data=f"manager_edit_order:{order_group_id}")],
        [InlineKeyboardButton(text="Отменить", callback_data=f"manager_cancel_order:{order_group_id}"),
         InlineKeyboardButton(text="Принять", callback_data=f"manager_accept_order:{order_group_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="manager_new_orders")]
    ])
    return keyboard

def get_cancel_order_confirmation_keyboard(order_group_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data=f"manager_cancel_order_confirm:{order_group_id}")],
        [InlineKeyboardButton(text="Нет", callback_data=f"manager_order_detail:{order_group_id}")]
    ])
    return keyboard

def get_manager_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Новые заказы", callback_data="manager_new_orders"),
         InlineKeyboardButton(text="Мои заказы", callback_data="manager_my_orders")],
        [InlineKeyboardButton(text="На главную", callback_data="go_to_manager_dashboard")]
    ])
    return keyboard

def get_manager_order_edit_keyboard(order_group_id: int, order_items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    for item in order_items:
        btn_text = f"{item.product.name} ({item.display_color}, {item.display_size}) - {item.quantity} шт."
        buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"manager_edit_product:{order_group_id}:{item.id}:{page}"))
    # Каждая кнопка в отдельном ряду
    keyboard_buttons = [[btn] for btn in buttons]
    # Пагинация в одном ряду
    pagination = []
    if page > 1:
        pagination.append(InlineKeyboardButton(text="<<", callback_data=f"manager_order_edit_page:{order_group_id}:{page-1}"))
    pagination.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        pagination.append(InlineKeyboardButton(text=">>", callback_data=f"manager_order_edit_page:{order_group_id}:{page+1}"))
    if pagination:
        keyboard_buttons.append(pagination)
    # Кнопка "Назад" в отдельном ряду
    keyboard_buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"manager_order_detail:{order_group_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_manager_product_edit_keyboard(order_item_id: int, product, order_item, group_id: int,
                                      chosen_color: str, chosen_size: str) -> InlineKeyboardMarkup:
    keyboard_buttons = []
    # Ряд для изменения размера
    row_size = [
        InlineKeyboardButton(text="-", callback_data=f"manager_change_size:{order_item_id}:dec:{group_id}"),
        InlineKeyboardButton(text=f"{chosen_size}", callback_data="ignore"),
        InlineKeyboardButton(text="+", callback_data=f"manager_change_size:{order_item_id}:inc:{group_id}")
    ]
    keyboard_buttons.append(row_size)
    # Ряд для изменения цвета
    row_color = [
        InlineKeyboardButton(text="⬅️", callback_data=f"manager_change_color:{order_item_id}:dec:{group_id}"),
        InlineKeyboardButton(text=f"{chosen_color}", callback_data="ignore"),
        InlineKeyboardButton(text="➡️", callback_data=f"manager_change_color:{order_item_id}:inc:{group_id}")
    ]
    keyboard_buttons.append(row_color)
    # Ряд для изменения количества
    row_qty = [
        InlineKeyboardButton(text="-", callback_data=f"manager_change_qty:{order_item_id}:dec:{group_id}"),
        InlineKeyboardButton(text=f"{order_item.quantity}", callback_data="ignore"),
        InlineKeyboardButton(text="+", callback_data=f"manager_change_qty:{order_item_id}:inc:{group_id}")
    ]
    keyboard_buttons.append(row_qty)
    # Ряд действий: Передаём group_id в обе кнопки
    row_actions = [
        InlineKeyboardButton(text="Удалить", callback_data=f"manager_delete_product:{order_item_id}:{group_id}"),
        InlineKeyboardButton(text="Подтвердить", callback_data=f"manager_update_product:{order_item_id}:{group_id}")
    ]
    keyboard_buttons.append(row_actions)
    # Кнопка "Назад"
    keyboard_buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"manager_edit_order:{group_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_delete_product_confirmation_keyboard(order_item_id: int, group_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data=f"manager_delete_product_confirm:{order_item_id}:{group_id}"),
         InlineKeyboardButton(text="Нет", callback_data=f"manager_edit_product:{group_id}:{order_item_id}")]
    ])
    return keyboard


def get_accept_order_confirmation_keyboard(order_group_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data=f"manager_accept_order_confirm:{order_group_id}"),
         InlineKeyboardButton(text="Нет", callback_data=f"manager_order_detail:{order_group_id}")]
    ])
    return keyboard