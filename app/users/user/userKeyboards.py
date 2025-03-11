from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


user_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔰 Каталог", callback_data='user_catalog'),
     InlineKeyboardButton(text="🛒 Корзина", callback_data='user_cart')],
    [InlineKeyboardButton(text="📦 Мои заказы", callback_data='user_my_orders'),
     InlineKeyboardButton(text="🤖 Консультация", callback_data='user_consultation')],
    [InlineKeyboardButton(text="⚙️ Настройки", callback_data='user_settings'),
     InlineKeyboardButton(text="📞 Поддержка", callback_data='user_support')]
])

user_settings_setting = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✏️ Изменить ФИО", callback_data='change_fullname'),
     InlineKeyboardButton(text="📞 Изменить номер", callback_data='change_phone')],
    [InlineKeyboardButton(text="📍 Изменить адрес", callback_data='change_delivery')],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data='go_to_user_dashboard')]
])

go_to_user_dashboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ В личный кабинет", callback_data='go_to_user_dashboard')]
])

user_settings = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ Назад", callback_data='user_settings')]
])


# Клавиатуры для каталога

def get_categories_keyboard(categories, current_page, total_pages):
    """
    Формирует клавиатуру для отображения списка категорий с пагинацией.
    Callback_data: select_category:{category_id}:{current_page}
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=cat.name, callback_data=f"select_category:{cat.id}:{current_page}")
        ])
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"cat_page:{current_page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"cat_page:{current_page + 1}"))
    keyboard.inline_keyboard.append(nav_buttons)
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="go_to_user_dashboard")])
    return keyboard

def get_subcategories_keyboard(subcategories, category_id, current_page, total_pages):
    """
    Формирует клавиатуру для отображения подкатегорий выбранной категории с пагинацией.
    Callback_data: select_subcat:{subcategory_id}:{category_id}:{current_page}
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for subcat in subcategories:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=subcat.name, callback_data=f"select_subcat:{subcat.id}:{category_id}:{current_page}")
        ])
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"subcat_page:{category_id}:{current_page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="ignore"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"subcat_page:{category_id}:{current_page + 1}"))
    keyboard.inline_keyboard.append(nav_buttons)
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat_page:1")])
    return keyboard

def get_product_view_keyboard(category_id, subcat_id, product_index, photo_index, total_products, total_photos):
    """
    Формирует клавиатуру для просмотра товара.
    В callback_data передаётся category_id для корректного возврата в подкатегории.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    nav_row = [
        InlineKeyboardButton(text="⬅️", callback_data=f"photo_nav:prev:{subcat_id}:{product_index}:{photo_index}:{category_id}"),
        InlineKeyboardButton(text="➡️", callback_data=f"photo_nav:next:{subcat_id}:{product_index}:{photo_index}:{category_id}")
    ]
    keyboard.inline_keyboard.append(nav_row)
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🛒 в корзину", callback_data=f"to_cart:{subcat_id}:{product_index}:{photo_index}:{category_id}")
    ])
    prod_nav_row = [
        InlineKeyboardButton(text="⏪", callback_data=f"prod_nav:prev:{subcat_id}:{product_index}:{category_id}"),
        InlineKeyboardButton(text="Назад", callback_data=f"prod_back:{category_id}:1"),
        InlineKeyboardButton(text="⏩", callback_data=f"prod_nav:next:{subcat_id}:{product_index}:{category_id}")
    ]
    keyboard.inline_keyboard.append(prod_nav_row)
    return keyboard

def get_cart_view_keyboard(category_id, subcat_id, product_index, photo_index, size_index, color_index, quantity, available_size_names, available_color_names):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    current_size = available_size_names[size_index] if available_size_names and size_index >= 0 else "N/A"
    size_row = [
        InlineKeyboardButton(text="-", callback_data=f"cart_size:dec:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}"),
        InlineKeyboardButton(text=f"{current_size}", callback_data="ignore"),
        InlineKeyboardButton(text="+", callback_data=f"cart_size:inc:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}")
    ]
    keyboard.inline_keyboard.append(size_row)
    current_color = available_color_names[color_index] if available_color_names and color_index >= 0 else "N/A"
    color_row = [
        InlineKeyboardButton(text="⬅️", callback_data=f"cart_color:dec:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}"),
        InlineKeyboardButton(text=f"{current_color}", callback_data="ignore"),
        InlineKeyboardButton(text="➡️", callback_data=f"cart_color:inc:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}")
    ]
    keyboard.inline_keyboard.append(color_row)
    qty_row = [
        InlineKeyboardButton(text="+", callback_data=f"cart_qty:inc:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}"),
        InlineKeyboardButton(text=f"{quantity}", callback_data="ignore"),
        InlineKeyboardButton(text="-", callback_data=f"cart_qty:dec:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}")
    ]
    keyboard.inline_keyboard.append(qty_row)
    final_row = [
        InlineKeyboardButton(text="Назад", callback_data=f"cart_back:{category_id}:{subcat_id}:{product_index}:{photo_index}"),
        InlineKeyboardButton(text="Подтвердить", callback_data=f"cart_confirm:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}")
    ]
    keyboard.inline_keyboard.append(final_row)
    return keyboard


def get_order_success_keyboard(category_id, page):
    """
    Формирует клавиатуру, которая отображается после успешного оформления заказа.
    Кнопка "⬅️ Назад" возвращает пользователя в список подкатегорий выбранной категории.
    Callback_data: order_success_back:{category_id}:{page}
    """
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"order_success_back:{category_id}:{page}")
    ])
    return keyboard


def get_cart_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Очистить", callback_data="cart_clear"),
            InlineKeyboardButton(text="🛒 Редактировать", callback_data="cart_edit")
        ],
        [InlineKeyboardButton(text="Оформить заказ", callback_data="order_submit")],
        [InlineKeyboardButton(text="Назад", callback_data="go_to_user_dashboard")]
    ])
    return keyboard

def get_cart_clear_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, очистить", callback_data="cart_clear_yes"),
            InlineKeyboardButton(text="Назад", callback_data="cart_clear_no")
        ]
    ])
    return keyboard

def get_cart_edit_list_keyboard(buttons):
    """
    Принимает список кортежей: (текст_кнопки, callback_data)
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for button_text, callback_data in buttons:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=callback_data)
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="go_to_user_cart")])
    return keyboard

def get_cart_item_edit_keyboard(order_item_id, product_id, current_size, current_color, quantity, available_size_names, available_color_names):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    size_row = [
        InlineKeyboardButton(text="-", callback_data=f"cart_item_edit:{order_item_id}:size:dec"),
        InlineKeyboardButton(text=f"Размер: {current_size}", callback_data="ignore"),
        InlineKeyboardButton(text="+", callback_data=f"cart_item_edit:{order_item_id}:size:inc")
    ]
    keyboard.inline_keyboard.append(size_row)
    color_row = [
        InlineKeyboardButton(text="⬅️", callback_data=f"cart_item_edit:{order_item_id}:color:dec"),
        InlineKeyboardButton(text=f"Цвет: {current_color}", callback_data="ignore"),
        InlineKeyboardButton(text="➡️", callback_data=f"cart_item_edit:{order_item_id}:color:inc")
    ]
    keyboard.inline_keyboard.append(color_row)
    qty_row = [
        InlineKeyboardButton(text="-", callback_data=f"cart_item_edit:{order_item_id}:qty:dec"),
        InlineKeyboardButton(text=f"{quantity} шт", callback_data="ignore"),
        InlineKeyboardButton(text="+", callback_data=f"cart_item_edit:{order_item_id}:qty:inc")
    ]
    keyboard.inline_keyboard.append(qty_row)
    final_row = [
        InlineKeyboardButton(text="Удалить", callback_data=f"cart_item_edit:{order_item_id}:delete"),
        InlineKeyboardButton(text="Подтвердить", callback_data=f"cart_item_edit:{order_item_id}:confirm"),
        InlineKeyboardButton(text="Назад", callback_data=f"cart_item_edit:{order_item_id}:back")
    ]
    keyboard.inline_keyboard.append(final_row)
    return keyboard

def get_cart_item_delete_confirmation_keyboard(order_item_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить", callback_data=f"cart_item_delete_confirm:{order_item_id}"),
            InlineKeyboardButton(text="Назад", callback_data=f"cart_item_edit:{order_item_id}:back")
        ]
    ])
    return keyboard

def get_order_confirm_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить, оформить заказ", callback_data="order_final_confirm")],
        [InlineKeyboardButton(text="✏️ Корзину", callback_data="order_edit_cart"),
         InlineKeyboardButton(text="✏️ Данные", callback_data="order_edit_data")],
        [InlineKeyboardButton(text="Назад", callback_data="order_confirm_back")]
    ])
    return keyboard

def get_order_address_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Нет, не хочу доставку", callback_data="order_address_skip")]
    ])
    return keyboard

def get_order_edit_data_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ФИО", callback_data="edit_fullname"),
         InlineKeyboardButton(text="Номер телефона", callback_data="edit_phone")],
        [InlineKeyboardButton(text="Адрес", callback_data="edit_address")],
        [InlineKeyboardButton(text="Назад", callback_data="order_confirm_back_in")]
    ])
    return keyboard

def get_address_edit_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Нет, не хочу доставку", callback_data="address_edit_skip")],
        [InlineKeyboardButton(text="Назад", callback_data="order_edit_data")]
    ])
    return keyboard

def get_order_success_final_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В личный кабинет", callback_data="go_to_user_dashboard")]
    ])
    return keyboard

# Клавиатура для списка заказов (две строки кнопок с номерами)
def get_my_orders_keyboard(order_groups: list) -> InlineKeyboardMarkup:
    buttons = []
    for idx, group in enumerate(order_groups, start=1):
        buttons.append(InlineKeyboardButton(text=str(idx), callback_data=f"order_detail:{group.id}"))
    row1 = buttons[:5]
    row2 = buttons[5:10]
    keyboard_buttons = []
    if row1:
        keyboard_buttons.append(row1)
    if row2:
        keyboard_buttons.append(row2)
    keyboard_buttons.append([InlineKeyboardButton(text="Назад", callback_data="go_to_user_dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_order_detail_keyboard(order_group_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Связаться менеджером", callback_data=f"order_contact:{order_group_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="user_my_orders")]
    ])
    return keyboard

def get_open_chat_keyboard(url: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть личку", url=url)],
        [InlineKeyboardButton(text="Назад", callback_data="user_my_orders")]
    ])
    return keyboard