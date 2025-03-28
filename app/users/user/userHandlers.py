import json
import re
import urllib

import pytz
from datetime import datetime

from aiogram.exceptions import TelegramBadRequest
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


# Константы для пагинации
CATEGORIES_PER_PAGE = 5
SUBCATEGORIES_PER_PAGE = 5

async def safe_edit_message(message: Message, text: str, reply_markup):
    if message.text is not None:
        return await message.edit_text(text, reply_markup=reply_markup)
    elif message.caption is not None:
        return await message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        return await message.answer(text, reply_markup=reply_markup)

# Обработчик нажатия на кнопку "🔰 Каталог"
@router.callback_query(F.data == 'user_catalog')
async def show_catalog(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    page = 1
    categories = await rq.catalog_get_categories(page, CATEGORIES_PER_PAGE)
    total_count = await rq.catalog_get_total_categories()
    total_pages = (total_count + CATEGORIES_PER_PAGE - 1) // CATEGORIES_PER_PAGE
    keyboard = kb.get_categories_keyboard(categories, page, total_pages)
    text = "Выберите категорию:"
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)

# Обработчик выбора категории
@router.callback_query(F.data.startswith('select_category:'))
async def select_category(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: select_category:{category_id}:{page}
    data = callback_query.data.split(':')
    category_id = int(data[1])
    page = int(data[2])
    subcategories = await rq.catalog_get_subcategories(category_id, 1, SUBCATEGORIES_PER_PAGE)
    total_count = await rq.catalog_get_total_subcategories(category_id)
    total_pages = (total_count + SUBCATEGORIES_PER_PAGE - 1) // SUBCATEGORIES_PER_PAGE
    keyboard = kb.get_subcategories_keyboard(subcategories, category_id, 1, total_pages)
    text = "Выберите подкатегорию:"
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)

# Пагинация для категорий
@router.callback_query(F.data.startswith('cat_page:'))
async def category_page(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: cat_page:{page}
    data = callback_query.data.split(':')
    page = int(data[1])
    categories = await rq.catalog_get_categories(page, CATEGORIES_PER_PAGE)
    total_count = await rq.catalog_get_total_categories()
    total_pages = (total_count + CATEGORIES_PER_PAGE - 1) // CATEGORIES_PER_PAGE
    keyboard = kb.get_categories_keyboard(categories, page, total_pages)
    text = "Выберите категорию:"
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)

# Пагинация для подкатегорий
@router.callback_query(F.data.startswith('subcat_page:'))
async def subcategory_page(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: subcat_page:{category_id}:{page}
    data = callback_query.data.split(':')
    category_id = int(data[1])
    page = int(data[2])
    subcategories = await rq.catalog_get_subcategories(category_id, page, SUBCATEGORIES_PER_PAGE)
    total_count = await rq.catalog_get_total_subcategories(category_id)
    total_pages = (total_count + SUBCATEGORIES_PER_PAGE - 1) // SUBCATEGORIES_PER_PAGE
    keyboard = kb.get_subcategories_keyboard(subcategories, category_id, page, total_pages)
    text = "Выберите подкатегорию:"
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)

# Обработчик выбора подкатегории – вывод первого товара
@router.callback_query(F.data.startswith('select_subcat:'))
async def select_subcategory(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: select_subcat:{subcategory_id}:{category_id}:{page}
    data = callback_query.data.split(':')
    subcat_id = int(data[1])
    category_id = int(data[2])
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    if not products:
        await safe_edit_message(callback_query.message, "Нет товаров в этой подкатегории, нажмите на /start.", reply_markup=None)
        return
    product_index = 0
    photo_index = 0
    product = products[product_index]
    photos = await rq.catalog_get_product_photos(product.id)
    photo_file = photos[photo_index].file_id if photos else utils.user_second_png
    text = f"Название: {product.name}\nОписание: {product.description}\nЦена: {product.price}"
    # Передаём category_id для кнопки "Назад"
    keyboard = kb.get_product_view_keyboard(category_id, subcat_id, product_index, photo_index,
                                              len(products), (len(photos) if photos else 0))
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

# Обработчик листания фотографий товара
@router.callback_query(F.data.startswith('photo_nav:'))
async def product_photo_navigation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: photo_nav:{direction}:{subcat_id}:{product_index}:{photo_index}:{category_id}
    data = callback_query.data.split(':')
    direction = data[1]
    subcat_id = int(data[2])
    product_index = int(data[3])
    photo_index = int(data[4])
    category_id = int(data[5])
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    if not products:
        await safe_edit_message(callback_query.message, "Нет товаров в этой подкатегории.", reply_markup=None)
        return
    product = products[product_index]
    photos = await rq.catalog_get_product_photos(product.id)
    total_photos = len(photos) if photos else 0
    if total_photos == 0:
        photo_file = utils.user_second_png
        new_photo_index = 0
    else:
        new_photo_index = (photo_index + 1) % total_photos if direction == "next" else (photo_index - 1 + total_photos) % total_photos
        photo_file = photos[new_photo_index].file_id
    text = f"Название: {product.name}\nОписание: {product.description}\nЦена: {product.price}"
    keyboard = kb.get_product_view_keyboard(category_id, subcat_id, product_index, new_photo_index,
                                              len(products), total_photos)
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

# Обработчик навигации по товарам (⏪, ⏩)
@router.callback_query(F.data.startswith('prod_nav:'))
async def product_navigation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: prod_nav:{direction}:{subcat_id}:{product_index}:{category_id}
    data = callback_query.data.split(':')
    direction = data[1]
    subcat_id = int(data[2])
    product_index = int(data[3])
    category_id = int(data[4])
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    total_products = len(products)
    if total_products == 0:
        await safe_edit_message(callback_query.message, "Нет товаров в этой подкатегории.", reply_markup=None)
        return
    new_index = (product_index + 1) % total_products if direction == "next" else (product_index - 1 + total_products) % total_products
    new_photo_index = 0
    product = products[new_index]
    photos = await rq.catalog_get_product_photos(product.id)
    total_photos = len(photos) if photos else 0
    photo_file = photos[new_photo_index].file_id if total_photos > 0 else utils.user_second_png
    text = f"Название: {product.name}\nОписание: {product.description}\nЦена: {product.price}"
    keyboard = kb.get_product_view_keyboard(category_id, subcat_id, new_index, new_photo_index,
                                              total_products, total_photos)
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

# Обработчик кнопки "Назад" в режиме просмотра товара (возврат к подкатегориям)
@router.callback_query(F.data.startswith('prod_back:'))
async def product_back(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: prod_back:{category_id}:{page}
    data = callback_query.data.split(':')
    category_id = int(data[1])
    page = int(data[2])
    subcategories = await rq.catalog_get_subcategories(category_id, page, SUBCATEGORIES_PER_PAGE)
    total_count = await rq.catalog_get_total_subcategories(category_id)
    total_pages = (total_count + SUBCATEGORIES_PER_PAGE - 1) // SUBCATEGORIES_PER_PAGE
    keyboard = kb.get_subcategories_keyboard(subcategories, category_id, page, total_pages)
    text = "Выберите подкатегорию:"
    # Меняем медиа на дефолтное изображение
    await callback_query.message.edit_media(
         media=InputMediaPhoto(media=utils.user_second_png, caption=text),
         reply_markup=keyboard
    )

# Обработчик кнопки "🛒 в корзину" – переход в режим оформления заказа
@router.callback_query(F.data.startswith('to_cart:'))
async def to_cart(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: to_cart:{subcat_id}:{product_index}:{photo_index}:{category_id}
    data = callback_query.data.split(':')
    subcat_id = int(data[1])
    product_index = int(data[2])
    photo_index = int(data[3])
    category_id = int(data[4])
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    product = products[product_index]
    photos = await rq.catalog_get_product_photos(product.id)
    total_photos = len(photos) if photos else 0
    photo_file = photos[photo_index].file_id if total_photos > 0 else utils.user_second_png

    # Получаем списки названий для размеров и цветов
    available_sizes = product.size_ids if product.size_ids else []
    available_colors = product.color_ids if product.color_ids else []
    available_size_names = [await rq.catalog_get_size_name(sid) for sid in available_sizes]
    available_color_names = [await rq.catalog_get_color_name(cid) for cid in available_colors]
    size_index = 0 if available_size_names else -1
    color_index = 0 if available_color_names else -1
    quantity = 1
    text = (f"ПОДРОБНЕЕ О ТОВАРЕ:\nНазвание: {product.name}\nОписание: {product.description}\n{product.usage}\n"
            f"Цена: {product.price}\nМатериал: {product.material}\nОсобенности: {product.features}\n"
            f"Температура: {product.temperature_range}")
    keyboard = kb.get_cart_view_keyboard(category_id, subcat_id, product_index, photo_index,
                                           size_index, color_index, quantity,
                                           available_size_names, available_color_names)
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

# Обработчик изменения выбранного размера
@router.callback_query(F.data.startswith('cart_size:'))
async def cart_size_adjust(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: cart_size:{action}:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}
    data = callback_query.data.split(':')
    action = data[1]
    category_id = int(data[2])
    subcat_id = int(data[3])
    product_index = int(data[4])
    photo_index = int(data[5])
    size_index = int(data[6])
    color_index = int(data[7])
    quantity = int(data[8])
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    product = products[product_index]
    available_sizes = product.size_ids if product.size_ids else []
    if not available_sizes:
        return
    new_size_index = (size_index + 1) % len(available_sizes) if action == "inc" else (size_index - 1 + len(available_sizes)) % len(available_sizes)
    available_size_names = [await rq.catalog_get_size_name(sid) for sid in available_sizes]
    available_color_names = [await rq.catalog_get_color_name(cid) for cid in (product.color_ids if product.color_ids else [])]
    keyboard = kb.get_cart_view_keyboard(category_id, subcat_id, product_index, photo_index,
                                           new_size_index, color_index, quantity,
                                           available_size_names, available_color_names)
    photos = await rq.catalog_get_product_photos(product.id)
    total_photos = len(photos) if photos else 0
    photo_file = photos[photo_index].file_id if total_photos > 0 else utils.user_second_png
    text = (f"ПОДРОБНЕЕ О ТОВАРЕ:\nНазвание: {product.name}\nОписание: {product.description}\n{product.usage}\n"
            f"Цена: {product.price}\nМатериал: {product.material}\nОсобенности: {product.features}\n"
            f"Температура: {product.temperature_range}")
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

# Обработчик изменения выбранного цвета
@router.callback_query(F.data.startswith('cart_color:'))
async def cart_color_adjust(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: cart_color:{action}:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}
    data = callback_query.data.split(':')
    action = data[1]
    category_id = int(data[2])
    subcat_id = int(data[3])
    product_index = int(data[4])
    photo_index = int(data[5])
    size_index = int(data[6])
    color_index = int(data[7])
    quantity = int(data[8])
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    product = products[product_index]
    available_colors = product.color_ids if product.color_ids else []
    if not available_colors:
        return
    new_color_index = (color_index + 1) % len(available_colors) if action == "inc" else (color_index - 1 + len(available_colors)) % len(available_colors)
    available_size_names = [await rq.catalog_get_size_name(sid) for sid in (product.size_ids if product.size_ids else [])]
    available_color_names = [await rq.catalog_get_color_name(cid) for cid in available_colors]
    keyboard = kb.get_cart_view_keyboard(category_id, subcat_id, product_index, photo_index,
                                           size_index, new_color_index, quantity,
                                           available_size_names, available_color_names)
    photos = await rq.catalog_get_product_photos(product.id)
    total_photos = len(photos) if photos else 0
    photo_file = photos[photo_index].file_id if total_photos > 0 else utils.user_second_png
    text = (f"ПОДРОБНЕЕ О ТОВАРЕ:\nНазвание: {product.name}\nОписание: {product.description}\n{product.usage}\n"
            f"Цена: {product.price}\nМатериал: {product.material}\nОсобенности: {product.features}\n"
            f"Температура: {product.temperature_range}")
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

# Обработчик изменения количества товара
@router.callback_query(F.data.startswith('cart_qty:'))
async def cart_quantity_adjust(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: cart_qty:{action}:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}
    data = callback_query.data.split(':')
    action = data[1]
    category_id = int(data[2])
    subcat_id = int(data[3])
    product_index = int(data[4])
    photo_index = int(data[5])
    size_index = int(data[6])
    color_index = int(data[7])
    quantity = int(data[8])
    new_quantity = quantity + 1 if action == "inc" else max(1, quantity - 1)
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    product = products[product_index]
    available_size_names = [await rq.catalog_get_size_name(sid) for sid in (product.size_ids if product.size_ids else [])]
    available_color_names = [await rq.catalog_get_color_name(cid) for cid in (product.color_ids if product.color_ids else [])]
    keyboard = kb.get_cart_view_keyboard(category_id, subcat_id, product_index, photo_index,
                                           size_index, color_index, new_quantity,
                                           available_size_names, available_color_names)
    photos = await rq.catalog_get_product_photos(product.id)
    total_photos = len(photos) if photos else 0
    photo_file = photos[photo_index].file_id if total_photos > 0 else utils.user_second_png
    text = (f"ПОДРОБНЕЕ О ТОВАРЕ:\nНазвание: {product.name}\nОписание: {product.description}\n{product.usage}\n"
            f"Цена: {product.price}\nМатериал: {product.material}\nОсобенности: {product.features}\n"
            f"Температура: {product.temperature_range}")
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

# Обработчик кнопки "Назад" в режиме корзины – возвращает к просмотру товара
@router.callback_query(F.data.startswith('cart_back:'))
async def cart_back(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: cart_back:{category_id}:{subcat_id}:{product_index}:{photo_index}
    data = callback_query.data.split(':')
    category_id = int(data[1])
    subcat_id = int(data[2])
    product_index = int(data[3])
    photo_index = int(data[4])
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    product = products[product_index]
    photos = await rq.catalog_get_product_photos(product.id)
    total_photos = len(photos) if photos else 0
    photo_file = photos[photo_index].file_id if total_photos > 0 else utils.user_second_png
    text = f"Название: {product.name}\nОписание: {product.description}\nЦена: {product.price}"
    keyboard = kb.get_product_view_keyboard(category_id, subcat_id, product_index, photo_index, len(products), total_photos)
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith('cart_confirm:'))
async def cart_confirm(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: cart_confirm:{category_id}:{subcat_id}:{product_index}:{photo_index}:{size_index}:{color_index}:{quantity}
    data = callback_query.data.split(':')
    category_id = int(data[1])
    subcat_id = int(data[2])
    product_index = int(data[3])
    photo_index = int(data[4])
    size_index = int(data[5])
    color_index = int(data[6])
    quantity = int(data[7])
    user_id = callback_query.from_user.id
    products = await rq.catalog_get_products_by_subcategory(subcat_id)
    product = products[product_index]
    available_sizes = product.size_ids if product.size_ids else []
    available_colors = product.color_ids if product.color_ids else []
    # Сохраняем выбранные размеры и цвета как id
    chosen_size = available_sizes[size_index] if available_sizes else None
    chosen_color = available_colors[color_index] if available_colors else None
    user_info = await rq.get_user_info_by_id(str(user_id))
    delivery_method = "доставка" if user_info.get("address") else "Самовывоз"
    order_created = await rq.add_to_cart(user_id, product, quantity, chosen_size, chosen_color, delivery_method)
    if order_created:
        # Возвращаемся в подкатегории, передавая category_id и номер страницы (например, 1)
        keyboard = kb.get_order_success_keyboard(category_id, 1)
        await safe_edit_message(callback_query.message, "Товар успешно добавлен в корзину!", reply_markup=keyboard)
    else:
        await safe_edit_message(callback_query.message, "Ошибка при добавлении товара в корзину. Попробуйте снова.", reply_markup=kb.go_to_user_dashboard)

# Обработчик кнопки "Назад" после успешного оформления заказа – возвращает к списку подкатегорий
@router.callback_query(F.data.startswith('order_success_back:'))
async def order_success_back(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Формат: order_success_back:{category_id}:{page}
    data = callback_query.data.split(':')
    category_id = int(data[1])
    page = int(data[2])  # Например, возвращаем на первую страницу подкатегорий
    subcategories = await rq.catalog_get_subcategories(category_id, page, SUBCATEGORIES_PER_PAGE)
    total_count = await rq.catalog_get_total_subcategories(category_id)
    total_pages = (total_count + SUBCATEGORIES_PER_PAGE - 1) // SUBCATEGORIES_PER_PAGE
    keyboard = kb.get_subcategories_keyboard(subcategories, category_id, page, total_pages)
    text = "Выберите подкатегорию:"
    await callback_query.message.edit_media(
         media=InputMediaPhoto(media=utils.user_second_png, caption=text),
         reply_markup=keyboard
    )


async def safe_edit_message(message: Message, text: str, reply_markup):
    if message.text is not None:
        return await message.edit_text(text, reply_markup=reply_markup)
    elif message.caption is not None:
        return await message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        return await message.answer(text, reply_markup=reply_markup)


# 1. Обработка кнопки "🛒 Корзина"
@router.callback_query(F.data == 'user_cart')
async def cart_main(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    cart_orders = await rq.get_cart_order(str(user_id))
    items = []
    if cart_orders:
        for order in cart_orders:
            items.extend(order.order_items)
    if not items:
        text = "Ваша корзина пуста."
    else:
        lines = []
        total_cost = 0
        for idx, item in enumerate(items, start=1):
            product = await rq.get_product(item.product_id)
            color_name = await rq.catalog_get_color_name(item.chosen_color) if item.chosen_color else "N/A"
            size_name = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size else "N/A"
            line = (f"{idx}. {product.name} ({color_name}, {size_name})\n"
                    f"{item.quantity} шт * {product.price} = {item.quantity * float(product.price)}")
            lines.append(line)
            total_cost += item.quantity * float(product.price)
        text = "\n\n".join(lines)
        text += f"\n\nОбщая стоимость: {total_cost}"
    keyboard = kb.get_cart_main_keyboard()
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=utils.user_second_png, caption=text),
        reply_markup=keyboard
    )


# 2. Очистка корзины — запрос подтверждения
@router.callback_query(F.data == 'cart_clear')
async def cart_clear_confirm(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    keyboard = kb.get_cart_clear_confirmation_keyboard()
    text = "Вы действительно хотите очистить корзину?"
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)


@router.callback_query(F.data == 'cart_clear_yes')
async def cart_clear_yes(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    success = await rq.clear_cart(str(user_id))
    text = "Ваша корзина очищена." if success else "Ошибка при очистке корзины."
    keyboard = kb.get_cart_main_keyboard()
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)


@router.callback_query(F.data == 'cart_clear_no')
async def cart_clear_no(callback_query: CallbackQuery, state: FSMContext):
    await cart_main(callback_query, state)


# 3. Редактирование корзины — вывод списка товаров
@router.callback_query(F.data == 'cart_edit')
async def cart_edit(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    cart_orders = await rq.get_cart_order(str(user_id))
    items = []
    if cart_orders:
        for order in cart_orders:
            items.extend(order.order_items)
    if not items:
        text = "Ваша корзина пуста."
        keyboard = kb.get_cart_main_keyboard()
        await safe_edit_message(callback_query.message, text, reply_markup=keyboard)
        return
    buttons = []
    for item in items:
        product = await rq.get_product(item.product_id)
        color_name = await rq.catalog_get_color_name(item.chosen_color) if item.chosen_color else "N/A"
        size_name = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size else "N/A"
        button_text = f"{product.name} ({color_name}, {size_name}) - {item.quantity} шт"
        callback_data = f"cart_edit_item:{item.id}"
        buttons.append((button_text, callback_data))
    keyboard = kb.get_cart_edit_list_keyboard(buttons)
    text = "Здесь можно редактировать товары:"
    # Если сообщение содержит фото – обновляем через edit_media, иначе через safe_edit_message
    if callback_query.message.photo:
        await callback_query.message.edit_media(
            media=InputMediaPhoto(media=utils.user_second_png, caption=text),
            reply_markup=keyboard
        )
    else:
        await safe_edit_message(callback_query.message, text, reply_markup=keyboard)



# 4. Выбор товара для редактирования
@router.callback_query(F.data.startswith('cart_edit_item:'))
async def cart_edit_item(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = callback_query.data.split(':')
    order_item_id = int(data[1])
    order_item = await rq.get_order_item(order_item_id)
    product = await rq.get_product(order_item.product_id)
    photos = await rq.catalog_get_product_photos(product.id) if hasattr(rq, 'catalog_get_product_photos') else None
    photo_file = photos[0].file_id if photos else utils.user_second_png
    current_size = order_item.chosen_size
    current_color = order_item.chosen_color
    current_qty = order_item.quantity
    current_size_name = await rq.catalog_get_size_name(current_size) if current_size else "N/A"
    current_color_name = await rq.catalog_get_color_name(current_color) if current_color else "N/A"
    available_sizes = product.size_ids if product.size_ids else []
    available_colors = product.color_ids if product.color_ids else []
    available_size_names = [await rq.catalog_get_size_name(sid) for sid in available_sizes]
    available_color_names = [await rq.catalog_get_color_name(cid) for cid in available_colors]
    keyboard = kb.get_cart_item_edit_keyboard(
        order_item_id,
        product.id,
        current_size_name,
        current_color_name,
        current_qty,
        available_size_names,
        available_color_names
    )
    text = f"{product.name}\nОписание: {product.description}\nЦена: {product.price}"
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=text),
        reply_markup=keyboard
    )


# 5. Редактирование параметров выбранного товара
@router.callback_query(F.data.startswith('cart_item_edit:'))
async def cart_item_edit(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = callback_query.data.split(':')
    order_item_id = int(data[1])
    field = data[2]  # может быть "size", "color", "qty", "delete", "confirm", "back"

    if field == "delete":
        keyboard = kb.get_cart_item_delete_confirmation_keyboard(order_item_id)
        text = "Вы уверены, что хотите удалить этот товар из корзины?"
        await safe_edit_message(callback_query.message, text, reply_markup=keyboard)
        return

    if field == "back":
        # При нажатии "Назад" возвращаемся к списку редактирования корзины
        await cart_edit(callback_query, state)
        return

    if field == "confirm":
        # Если нажата кнопка "Подтвердить", можно выполнить логику подтверждения изменений.
        # В данном примере просто возвращаемся к списку редактирования.
        await cart_edit(callback_query, state)
        return

    # Если команда ожидает параметр (например, "inc" или "dec")
    if len(data) < 4:
        await callback_query.message.answer("Ошибка: недостаточно параметров для обновления.")
        return

    action = data[3]  # "inc" или "dec"
    success = await rq.update_cart_item_field(order_item_id, field, action)
    if success:
        order_item = await rq.get_order_item(order_item_id)
        product = await rq.get_product(order_item.product_id)
        photos = await rq.catalog_get_product_photos(product.id) if hasattr(rq, 'catalog_get_product_photos') else None
        photo_file = photos[0].file_id if photos else utils.user_second_png
        current_size = order_item.chosen_size
        current_color = order_item.chosen_color
        current_qty = order_item.quantity
        current_size_name = await rq.catalog_get_size_name(current_size) if current_size else "N/A"
        current_color_name = await rq.catalog_get_color_name(current_color) if current_color else "N/A"
        available_sizes = product.size_ids if product.size_ids else []
        available_colors = product.color_ids if product.color_ids else []
        available_size_names = [await rq.catalog_get_size_name(sid) for sid in available_sizes]
        available_color_names = [await rq.catalog_get_color_name(cid) for cid in available_colors]
        keyboard = kb.get_cart_item_edit_keyboard(
            order_item_id,
            product.id,
            current_size_name,
            current_color_name,
            current_qty,
            available_size_names,
            available_color_names
        )
        text = f"{product.name}\nОписание: {product.description}\nЦена: {product.price}"
        # Используем edit_media, если в сообщении есть фото, иначе safe_edit_message
        if callback_query.message.photo:
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=photo_file, caption=text),
                reply_markup=keyboard
            )
        else:
            await safe_edit_message(callback_query.message, text, reply_markup=keyboard)
    else:
        await callback_query.message.answer("Ошибка при обновлении товара.")



# 6. Подтверждение удаления товара из корзины
@router.callback_query(F.data.startswith('cart_item_delete_confirm:'))
async def cart_item_delete_confirm(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = callback_query.data.split(':')
    order_item_id = int(data[1])
    success = await rq.delete_cart_item(order_item_id)
    text = "Товар удалён из корзины." if success else "Ошибка при удалении товара."
    user_id = callback_query.from_user.id
    cart_orders = await rq.get_cart_order(str(user_id))
    items = []
    if cart_orders:
        for order in cart_orders:
            items.extend(order.order_items)
    if items:
        buttons = []
        for item in items:
            product = await rq.get_product(item.product_id)
            color_name = await rq.catalog_get_color_name(item.chosen_color) if item.chosen_color else "N/A"
            size_name = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size else "N/A"
            button_text = f"{product.name} ({color_name}, {size_name}) - {item.quantity} шт"
            callback_data = f"cart_edit_item:{item.id}"
            buttons.append((button_text, callback_data))
        keyboard = kb.get_cart_edit_list_keyboard(buttons)
    else:
        keyboard = kb.get_cart_main_keyboard()
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)


# 7. Оформление заказа — проверка данных пользователя и сбор информации
async def order_submit_event(event, state: FSMContext):
    # Если event является CallbackQuery, используем его поле message,
    # иначе считаем, что event уже является Message
    if isinstance(event, CallbackQuery):
        base_msg: Message = event.message
        await event.answer()  # Ответ на callback
    else:
        base_msg: Message = event

    tuid = base_msg.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(base_msg.message_id)

    user_id = tuid
    user_info = await rq.get_user_info_by_id(str(user_id))

    # Запрашиваем ФИО, если его нет (с учетом удаления пробелов)
    if user_info.get("full_name", "").strip() == "":
        await state.set_state(st.OrderInfo.waiting_fullname)
        text = "Как вам обращаться? Введите ФИО:"
        await safe_edit_message(base_msg, text, reply_markup=None)
        return

    # Запрашиваем номер телефона, если его нет (аналогично можно добавить .strip())
    if user_info.get("phone_number", "").strip() == "":
        await delete_previous_messages(base_msg, tuid)
        await state.set_state(st.OrderInfo.waiting_phone)
        text = "Как с вами связаться? Введите номер телефона (формат +996XXXXXXXXX):"
        sent_message = await base_msg.answer_photo(
            photo=utils.user_second_png,
            caption=text
        )
        user_data['bot_messages'].append(sent_message.message_id)
        return

    await state.set_state(st.OrderInfo.waiting_address)
    await delete_previous_messages(base_msg, tuid)
    text = ("Напишите адрес, если хотите доставку. "
            "Если не хотите, нажмите 'Нет, не хочу доставку'.")
    keyboard = kb.get_order_address_keyboard()
    sent_message = await base_msg.answer_photo(
        photo=utils.user_second_png,
        caption=text,
        reply_markup=keyboard
    )
    user_data['bot_messages'].append(sent_message.message_id)





@router.callback_query(F.data == 'order_submit')
async def order_submit_callback(callback_query: CallbackQuery, state: FSMContext):
    await order_submit_event(callback_query, state)


@router.message(st.OrderInfo.waiting_fullname)
async def process_fullname(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    fullname = message.text.strip()
    user_id = message.from_user.id
    await rq.update_user_fullname(str(user_id), fullname)
    await state.clear()
    await order_submit_event(message, state)


@router.message(st.OrderInfo.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    new_phone = message.text.strip()
    import re
    if not re.fullmatch(r'\+996\d{9}', new_phone):
        tuid = message.chat.id
        user_data = sent_message_add_screen_ids[tuid]
        user_data['user_messages'].append(message.message_id)
        await delete_previous_messages(message, tuid)
        sent_message = await message.answer_photo(
            photo=utils.user_second_png,
            caption="Неверный формат номера. Попробуйте ещё раз.")
        user_data['bot_messages'].append(sent_message.message_id)
        return
    user_id = message.from_user.id
    await rq.update_user_phone(str(user_id), new_phone)
    await state.clear()
    await order_submit_event(message, state)


@router.callback_query(F.data == 'order_address_skip')
async def order_address_skip(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    await rq.update_user_address(str(user_id), "")
    await state.clear()
    await order_confirmation_summary(callback_query, state)


@router.message(st.OrderInfo.waiting_address)
async def process_address(message: Message, state: FSMContext):
    tuid = message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    address = message.text.strip()
    user_id = message.from_user.id
    await rq.update_user_address(str(user_id), address)
    await state.clear()
    await order_confirmation_summary(message, state)


async def order_confirmation_summary(event, state: FSMContext):
    # Определяем базовое сообщение в зависимости от типа event
    if isinstance(event, CallbackQuery):
        base_message: Message = event.message
    else:
        base_message: Message = event

    # Получаем chat_id и message_id из базового сообщения
    chat_id = base_message.chat.id
    msg_id = base_message.message_id

    # Работа с вашим хранилищем сообщений (пример)
    user_data = sent_message_add_screen_ids[chat_id]
    user_data['user_messages'].append(msg_id)
    await delete_previous_messages(base_message, chat_id)

    user_id = event.from_user.id
    cart_orders = await rq.get_cart_order(str(user_id))
    items = []
    if cart_orders:
        for order in cart_orders:
            items.extend(order.order_items)
    if not items:
        text = "Ваша корзина пуста."
        keyboard = kb.get_cart_main_keyboard()
        msg = event.message if hasattr(event, 'message') else event
        await safe_edit_message(msg, text, reply_markup=keyboard)
        return
    lines = []
    total_cost = 0
    for idx, item in enumerate(items, start=1):
        product = await rq.get_product(item.product_id)
        color_name = await rq.catalog_get_color_name(item.chosen_color) if item.chosen_color else "N/A"
        size_name = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size else "N/A"
        line = (f"{idx}. {product.name} ({color_name}, {size_name}) - {item.quantity} шт * {product.price} = {item.quantity * float(product.price)}")
        lines.append(line)
        total_cost += item.quantity * float(product.price)
    user_info = await rq.get_user_info_by_id(str(user_id))
    order_type = "доставка" if user_info.get("address") else "Самовывоз"
    summary = "\n".join(lines)
    text = (f"{summary}\n\nОбщая стоимость: {total_cost}\n\n"
            f"Адрес: {user_info.get('address', 'N/A')}\n"
            f"Номер: {user_info.get('phone_number', 'N/A')}\n"
            f"ФИО: {user_info.get('full_name', 'N/A')}\n"
            f"Тип заказа: {order_type}")
    keyboard = kb.get_order_confirm_keyboard()
    msg = event.message if hasattr(event, 'message') else event
    await msg.answer_photo(
        photo=utils.user_second_png,
        caption=text,
        reply_markup=keyboard
    )
    # await safe_edit_message(msg, text, reply_markup=keyboard)


# 8. Финальное подтверждение заказа — обновление статуса заказа
@router.callback_query(F.data == 'order_final_confirm')
async def order_final_confirm(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    cart_orders = await rq.get_cart_order(str(user_id))
    if not cart_orders:
        await safe_edit_message(callback_query.message, "Ваша корзина пуста.", reply_markup=kb.get_cart_main_keyboard())
        return
    # Обновляем все заказы пользователя
    success = await rq.submit_all_orders(str(user_id))
    text = "Заказ успешно оформлен! Менеджер скоро свяжется с вами." if success else "Ошибка при оформлении заказа. Попробуйте ещё раз."
    keyboard = kb.get_order_success_final_keyboard()
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)


# 9. Редактирование данных пользователя (ФИО, телефон, адрес)
@router.callback_query(F.data == 'order_edit_data')
async def order_edit_data(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    text = "Измените данные:\nВыберите, что редактировать:"
    keyboard = kb.get_order_edit_data_keyboard()
    await safe_edit_message(callback_query.message, text, reply_markup=keyboard)

@router.callback_query(F.data == 'order_edit_cart')
async def order_edit_data(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await cart_main(callback_query, state)


@router.callback_query(F.data == 'edit_fullname')
async def edit_fullname(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)

    await callback_query.answer()
    await state.set_state(st.UserData.waiting_fullname)
    text = "Введите новое ФИО:"
    sent_message = await callback_query.message.edit_media(
        media=InputMediaPhoto(media=utils.user_second_png, caption=text)
    )
    user_data['bot_messages'].append(sent_message.message_id)


@router.message(st.UserData.waiting_fullname)
async def process_edit_fullname(message: Message, state: FSMContext):
    new_fullname = message.text.strip()
    user_id = message.from_user.id
    await rq.update_user_fullname(str(user_id), new_fullname)
    await state.clear()
    await order_confirmation_summary(message, state)


@router.callback_query(F.data == 'edit_phone')
async def edit_phone(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)

    await callback_query.answer()
    await state.set_state(st.UserData.waiting_phone)

    text = "Введите новый номер телефона (формат +996XXXXXXXXX):"
    sent_message = await callback_query.message.edit_media(
        media=InputMediaPhoto(media=utils.user_second_png, caption=text)
    )
    user_data['bot_messages'].append(sent_message.message_id)


@router.message(st.UserData.waiting_phone)
async def process_edit_phone(message: Message, state: FSMContext):
    new_phone = message.text.strip()
    import re
    if not re.fullmatch(r'\+996\d{9}', new_phone):
        tuid = message.chat.id
        user_data = sent_message_add_screen_ids[tuid]
        user_data['user_messages'].append(message.message_id)
        await delete_previous_messages(message, tuid)
        sent_message = await message.answer_photo(
            photo=utils.user_second_png,
            caption="Неверный формат номера. Попробуйте ещё раз.")
        user_data['bot_messages'].append(sent_message.message_id)
        return
    user_id = message.from_user.id
    await rq.update_user_phone(str(user_id), new_phone)
    await state.clear()
    await order_confirmation_summary(message, state)


@router.callback_query(F.data == 'edit_address')
async def edit_address(callback_query: CallbackQuery, state: FSMContext):
    tuid = callback_query.message.chat.id
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(callback_query.message.message_id)

    await callback_query.answer()
    await state.set_state(st.UserData.waiting_address)
    keyboard = kb.get_address_edit_keyboard()

    text = "Введите новый адрес:"
    sent_message = await callback_query.message.edit_media(
        media=InputMediaPhoto(media=utils.user_second_png, caption=text)
    )
    user_data['bot_messages'].append(sent_message.message_id)


@router.message(st.UserData.waiting_address)
async def process_edit_address(message: Message, state: FSMContext):
    new_address = message.text.strip()
    user_id = message.from_user.id
    await rq.update_user_address(str(user_id), new_address)
    await state.clear()
    await order_confirmation_summary(message, state)


@router.callback_query(F.data == 'address_edit_skip')
async def address_edit_skip(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    await rq.update_user_address(str(user_id), "")
    await state.clear()
    await order_confirmation_summary(callback_query.message, state)


# 10. Кнопка "Назад" в экране подтверждения заказа — возврат в корзину
@router.callback_query(F.data == 'order_confirm_back')
async def order_confirm_back(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await cart_main(callback_query, state)

@router.callback_query(F.data == 'order_confirm_back_in')
async def order_confirm_back(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await order_confirmation_summary(callback_query, state)

@router.callback_query(F.data == 'go_to_user_cart')
async def go_to_user_cart(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Возвращаем пользователя в режим просмотра корзины
    await cart_main(callback_query, state)


# Обработчик кнопки "Мои заказы"
@router.callback_query(F.data == 'user_my_orders')
async def user_my_orders(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = str(callback_query.from_user.id)
    # Получаем последние 10 групп заказов пользователя
    order_groups = await rq.get_user_order_groups(user_id)
    if not order_groups:
        text = "У вас еще нет оформленных заказов."
    else:
        lines = []
        # Для каждой группы берём первый заказ для отображения даты и статуса
        for idx, group in enumerate(order_groups, start=1):
            if group.order_ids:
                order = await rq.get_order_by_id(group.order_ids[0])
                if order:
                    order_date = order.order_datetime.strftime("%Y.%m.%d")
                    status = order.status
                    lines.append(f"Заказ {idx} : {order_date} : {status}")
        orders_info = "\n".join(lines)
        text = f"{orders_info}\n\nМожете посмотреть детально, выберете номер заказа."
    keyboard = kb.get_my_orders_keyboard(order_groups)
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=utils.user_second_png, caption=text),
        reply_markup=keyboard
    )

# Обработчик выбора конкретного заказа из списка (callback_data вида "order_detail:<group_id>")
@router.callback_query(F.data.startswith("order_detail:"))
async def order_detail(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = callback_query.data
    order_group_id = int(data.split(":")[1])
    group = await rq.get_order_group_by_id(order_group_id)
    if not group:
        await safe_edit_message(callback_query.message, "Группа заказа не найдена.", reply_markup=None)
        return

    # Собираем информацию по товарам заказа и считаем сумму
    items_lines = []
    total_cost = 0.0
    index = 1
    first_order = None
    for order_id in group.order_ids:
        order = await rq.get_order_by_id(order_id)
        if not order:
            continue
        if first_order is None:
            first_order = order
        for item in order.order_items:
            product = await rq.get_product(item.product_id)
            color_name = await rq.catalog_get_color_name(item.chosen_color) if item.chosen_color is not None else "N/A"
            size_name = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size is not None else "N/A"
            items_lines.append(f"{index}. {product.name} ({color_name}, {size_name}) - {item.quantity}шт.")
            total_cost += item.quantity * float(product.price)
            index += 1
    items_text = "\n".join(items_lines)

    # Получаем данные пользователя из первого заказа
    user_info = await rq.get_user_info_by_id(str(first_order.user_id))
    fullname = user_info.get("full_name", "N/A")
    phone = user_info.get("phone_number", "N/A")
    address = user_info.get("address", "N/A")

    # Формируем блок информации о заказе согласно требованиям
    details_lines = [items_text, ""]
    if first_order.delivery_method == "доставка":
        details_lines.append(f"адрес: {address}")
    details_lines.append(f"номер: {phone}")
    details_lines.append(f"фИО: {fullname}")
    details_lines.append("")
    details_lines.append(f"тип заказа: {first_order.delivery_method}")
    details_lines.append(f"статус: {first_order.status}")
    details_lines.append(f"Сумма заказа: {total_cost:.2f}")
    details_text = "\n".join(details_lines)

    keyboard = kb.get_order_detail_keyboard(group.id)
    await safe_edit_message(callback_query.message, details_text, reply_markup=keyboard)

# Обработчик нажатия кнопки "Связаться менеджером"
@router.callback_query(F.data.startswith("order_contact:"))
async def order_contact(callback_query: CallbackQuery, state: FSMContext):
    data = callback_query.data
    order_group_id = int(data.split(":")[1])
    group = await rq.get_order_group_by_id(order_group_id)
    if not group or not group.order_ids:
        await callback_query.answer("Заказ не найден.", show_alert=True)
        return
    first_order = await rq.get_order_by_id(group.order_ids[0])
    if not first_order or not first_order.processed_by_id:
        await callback_query.answer("Заказ все еще в обработке.", show_alert=True)
        return
    # Получаем данные менеджера (из таблицы User) по processed_by_id
    manager = await rq.get_user_by_id_user(first_order.processed_by_id)
    if not manager or not manager.telegram_id:
        await callback_query.answer("Менеджер не найден.", show_alert=True)
        return

    # Формируем детали заказа (список товаров, адрес, номер, ФИО, тип, статус, сумма)
    items_lines = []
    total_cost = 0.0
    index = 1
    for order_id in group.order_ids:
        order = await rq.get_order_by_id(order_id)
        if not order:
            continue
        for item in order.order_items:
            product = await rq.get_product(item.product_id)
            color_name = await rq.catalog_get_color_name(item.chosen_color) if item.chosen_color is not None else "N/A"
            size_name = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size is not None else "N/A"
            items_lines.append(f"{index}. {product.name} ({color_name}, {size_name}) - {item.quantity}шт.")
            total_cost += item.quantity * float(product.price)
            index += 1
    items_text = "\n".join(items_lines)

    user_info = await rq.get_user_info_by_id(str(first_order.user_id))
    fullname = user_info.get("full_name", "N/A")
    phone = user_info.get("phone_number", "N/A")
    address = user_info.get("address", "N/A")

    details_lines = [items_text, ""]
    if first_order.delivery_method == "доставка":
        details_lines.append(f"адрес: {address}")
    details_lines.append(f"номер: {phone}")
    details_lines.append(f"фИО: {fullname}")
    details_lines.append("")
    details_lines.append(f"тип заказа: {first_order.delivery_method}")
    details_lines.append(f"статус: {first_order.status}")
    details_lines.append(f"Сумма заказа: {total_cost:.2f}")
    order_details = "\n".join(details_lines)

    # URL-кодируем сформированный текст
    prefilled_text = urllib.parse.quote(order_details)

    # Формируем URL для открытия личного чата с менеджером с предзаполненным текстом.
    # Если у менеджера есть username (например, "@manager123"), используем схему tg://resolve
    # Если username отсутствует и telegram_id является числовым, пробуем использовать tg://user?id=...
    try:
        int(manager.address)
        # Если telegram_id число, используем схему tg://user?id=
        url = f"tg://user?id={manager.address}&text={prefilled_text}"
    except ValueError:
        # Если не число, предполагаем, что это username (возможно с @)
        username = manager.address[1:] if manager.address.startswith("@") else manager.address
        url = f"tg://resolve?domain={username}&text={prefilled_text}"

    # Создаем клавиатуру с кнопкой для открытия чата
    keyboard = kb.get_open_chat_keyboard(url)
    await safe_edit_message(
        callback_query.message,
        "Нажмите кнопку ниже, чтобы открыть личный чат с менеджером. Отредактируйте сообщение по необходимости и отправьте его.",
        reply_markup=keyboard
    )


@router.callback_query(F.data == 'user_support')
async def user_support(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "📞 Поддержка".
    Получает данные менеджера поддержки из БД и формирует ссылки:
      - для Telegram: tg://user?id=<telegram_id>
      - для WhatsApp: https://wa.me/<phone_number> (без символа "+")
    Затем выводит сообщение с фото, текстом и клавиатурой.
    """
    support_details = await rq.get_support_manager_details()

    if support_details:
        telegram_id = support_details.get("telegram_id")
        phone_number = support_details.get("phone_number")

        # Формируем URL для Telegram, используя telegram_id
        telegram_url = f"tg://user?id={telegram_id}"
        # Формируем URL для WhatsApp, убираем лишние символы из номера
        clean_number = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        whatsapp_url = f"https://wa.me/{clean_number}"

        # Получаем фото из utils (например, utils.user_second_png)
        user_png = utils.user_second_png
        # Формируем клавиатуру, передавая сформированные URL
        markup = kb.get_support_keyboard(telegram_url, whatsapp_url)
        text = "Свяжитесь с нашим специалистом поддержки:"

        try:
            if callback_query.message.photo:
                await callback_query.message.edit_caption(caption=text, reply_markup=markup)
            else:
                await callback_query.message.edit_text(text=text, reply_markup=markup)
        except TelegramBadRequest as e:
            if "message to edit not found" in str(e):
                await callback_query.message.answer("Сообщение для редактирования не найдено. Возможно, оно было удалено.")
            else:
                await callback_query.message.answer(f"Произошла ошибка: {e}")
    else:
        await callback_query.message.answer("Специалист поддержки временно недоступен.")
