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



