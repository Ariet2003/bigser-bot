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
        await safe_edit_message(callback_query.message, "Нет товаров в этой подкатегории.", reply_markup=None)
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

