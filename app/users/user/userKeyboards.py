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
