import json
import re
import pytz
from datetime import datetime

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import CommandStart, Command
from aiogram import F, Router
from app.database import requests as rq
from aiogram.fsm.context import FSMContext
from app.utils import sent_message_add_screen_ids, router
from app.users.manager import managerStates as st
import app.users.manager.managerKeyboards as kb
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
async def manager_account(message: Message, state: FSMContext):
    tuid = message.chat.id
    if tuid not in sent_message_add_screen_ids:
        sent_message_add_screen_ids[tuid] = {'bot_messages': [], 'user_messages': []}
    user_data = sent_message_add_screen_ids[tuid]
    user_data['user_messages'].append(message.message_id)
    await delete_previous_messages(message, tuid)

    await state.clear()

    sent_message = await message.answer_photo(
        photo=utils.manager_png,
        caption="Добро пожаловать в панель менеджера!",
        reply_markup=kb.manager_button
    )

    user_data['bot_messages'].append(sent_message.message_id)


async def safe_edit_message(message: Message, text: str, reply_markup, media: str = None):
    try:
        if media is not None:
            return await message.edit_media(
                media=InputMediaPhoto(media=media, caption=text),
                reply_markup=reply_markup
            )
        if message.text is not None:
            return await message.edit_text(text, reply_markup=reply_markup)
        elif message.caption is not None:
            return await message.edit_caption(caption=text, reply_markup=reply_markup)
        else:
            return await message.answer(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если новое содержимое совпадает с текущим – ничего не делаем
            return
        raise e

# Вспомогательная функция для обновления режима просмотра товаров (список OrderItem)
async def refresh_manager_edit_order_view(callback_query: CallbackQuery, order_group_id: int, page: int = 1):
    group = await rq.get_order_group_by_id(order_group_id)
    if not group:
        await safe_edit_message(callback_query.message, "Группа заказа не найдена.", reply_markup=None)
        return
    # Собираем все OrderItem и дополняем их отображаемыми значениями
    order_items = []
    for order_id in group.order_ids:
        order = await rq.get_order_by_id(order_id)
        if order:
            for item in order.order_items:
                item.display_color = await rq.catalog_get_color_name(item.chosen_color) if item.chosen_color is not None else "N/A"
                item.display_size = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size is not None else "N/A"
                order_items.append(item)
    per_page = 5
    total_pages = (len(order_items) + per_page - 1) // per_page
    paginated_items = order_items[(page-1)*per_page: page*per_page]
    keyboard = kb.get_manager_order_edit_keyboard(order_group_id, paginated_items, page, total_pages)
    caption = "Список товаров данного заказа"
    await safe_edit_message(callback_query.message, caption, reply_markup=keyboard, media=utils.manager_png)

# Обработчик кнопки "Новые заказы"
@router.callback_query(F.data == 'manager_new_orders')
async def manager_new_orders(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    page = 1
    per_page = 10
    new_order_groups = await rq.get_new_order_groups(page, per_page)
    total_orders = await rq.get_total_new_order_groups()
    total_pages = (total_orders + per_page - 1) // per_page
    caption = "Не оформленные заказы, выберите из списка снизу"
    keyboard = kb.get_new_orders_keyboard(new_order_groups, page, total_pages)
    await callback_query.message.edit_media(
        media=InputMediaPhoto(media=utils.manager_png, caption=caption),
        reply_markup=keyboard
    )

# Обработчик смены страницы в списке новых заказов
@router.callback_query(F.data.startswith("manager_new_orders_page:"))
async def manager_new_orders_page(callback_query: CallbackQuery, state: FSMContext):
    data = callback_query.data.split(":")
    page = int(data[1])
    per_page = 10
    new_order_groups = await rq.get_new_order_groups(page, per_page)
    total_orders = await rq.get_total_new_order_groups()
    total_pages = (total_orders + per_page - 1) // per_page
    keyboard = kb.get_new_orders_keyboard(new_order_groups, page, total_pages)
    caption = "Не оформленные заказы, выберите из списка снизу"
    await safe_edit_message(callback_query.message, caption, reply_markup=keyboard)

# Обработчик выбора конкретного заказа (числовая кнопка)
@router.callback_query(F.data.startswith("manager_order_detail:"))
async def manager_order_detail(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    order_group_id = int(callback_query.data.split(":")[1])
    group = await rq.get_order_group_by_id(order_group_id)
    if not group:
        await safe_edit_message(callback_query.message, "Группа заказа не найдена.", reply_markup=None)
        return

    first_order = await rq.get_order_by_id(group.order_ids[0])
    if first_order.status != "В обработке":
        await callback_query.answer("Заказ просматривает другой менеджер.", show_alert=True)
        return

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
    details_text = "\n".join(details_lines)

    keyboard = kb.get_manager_order_detail_keyboard(group.id)
    await safe_edit_message(callback_query.message, details_text, reply_markup=keyboard)

# Обработчик кнопки "Отменить" (начало отмены)
@router.callback_query(F.data.startswith("manager_cancel_order:"))
async def manager_cancel_order(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    order_group_id = int(callback_query.data.split(":")[1])
    keyboard = kb.get_cancel_order_confirmation_keyboard(order_group_id)
    await safe_edit_message(callback_query.message, "Вы действительно хотите отменить заказ?", reply_markup=keyboard)

# Обработчик подтверждения отмены заказа
@router.callback_query(F.data.startswith("manager_cancel_order_confirm:"))
async def manager_cancel_order_confirm(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    order_group_id = int(callback_query.data.split(":")[1])
    group = await rq.get_order_group_by_id(order_group_id)
    if not group:
        await callback_query.answer("Группа заказа не найдена.", show_alert=True)
        return

    # Получаем менеджера по telegram_id
    manager = await rq.get_user_by_telegram_id(str(callback_query.from_user.id))
    if not manager:
        await callback_query.answer("Менеджер не найден.", show_alert=True)
        return

    success = await rq.update_order_status(group.order_ids, "Отменен", manager_id=manager.id)
    if success:
        await safe_edit_message(callback_query.message, "Заказ отменен.", reply_markup=kb.get_manager_main_keyboard())
    else:
        await callback_query.answer("Ошибка при отмене заказа.", show_alert=True)


# Обработчик кнопки "Принять"
@router.callback_query(F.data.startswith("manager_accept_order:"))
async def manager_accept_order(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    order_group_id = int(callback_query.data.split(":")[1])
    keyboard = kb.get_accept_order_confirmation_keyboard(order_group_id)
    await safe_edit_message(callback_query.message, "Вы действительно хотите принять заказ?", reply_markup=keyboard)


@router.callback_query(F.data.startswith("manager_accept_order_confirm:"))
async def manager_accept_order_confirm(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    order_group_id = int(callback_query.data.split(":")[1])
    group = await rq.get_order_group_by_id(order_group_id)
    if not group:
        await callback_query.answer("Группа заказа не найдена.", show_alert=True)
        return

    # Получаем менеджера по telegram_id
    manager = await rq.get_user_by_telegram_id(str(callback_query.from_user.id))
    if not manager:
        await callback_query.answer("Менеджер не найден.", show_alert=True)
        return

    success = await rq.update_order_status(group.order_ids, "Выполнено", manager_id=manager.id)
    if success:
        await safe_edit_message(
            callback_query.message,
            "Заказ принят, вы можете посмотреть в 'Мои заказы'",
            reply_markup=kb.get_manager_main_keyboard(),
            media=utils.manager_png
        )
    else:
        await callback_query.answer("Ошибка при принятии заказа.", show_alert=True)



# Обработчик кнопки "Редактировать заказ" – вывод списка товаров заказа
@router.callback_query(F.data.startswith("manager_edit_order:"))
async def manager_edit_order(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    order_group_id = int(callback_query.data.split(":")[1])
    group = await rq.get_order_group_by_id(order_group_id)
    if not group:
        await safe_edit_message(callback_query.message, "Группа заказа не найдена.", reply_markup=None)
        return
    order_items = []
    for order_id in group.order_ids:
        order = await rq.get_order_by_id(order_id)
        if order:
            order_items.extend(order.order_items)
    # Обновляем каждое OrderItem для отображения реальных названий цвета и размера
    for item in order_items:
        item.display_color = await rq.catalog_get_color_name(
            item.chosen_color) if item.chosen_color is not None else "N/A"
        item.display_size = await rq.catalog_get_size_name(item.chosen_size) if item.chosen_size is not None else "N/A"

    page = 1
    per_page = 5
    total_pages = (len(order_items) + per_page - 1) // per_page
    paginated_items = order_items[(page-1)*per_page: page*per_page]
    keyboard = kb.get_manager_order_edit_keyboard(order_group_id, paginated_items, page, total_pages)
    caption = "Список товаров данного заказа"
    await safe_edit_message(callback_query.message, caption, reply_markup=keyboard, media=utils.manager_png)

# Обработчик выбора товара для редактирования
@router.callback_query(F.data.startswith("manager_edit_product:"))
async def manager_edit_product(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    parts = callback_query.data.split(":")
    order_group_id = int(parts[1])
    order_item_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 1
    order_item = await rq.get_order_item(order_item_id)
    if not order_item:
        await callback_query.answer("Товар не найден.", show_alert=True)
        return
    product = await rq.get_product(order_item.product_id)
    if not product:
        await callback_query.answer("Продукт не найден.", show_alert=True)
        return
    # Получаем реальные названия цвета и размера
    chosen_color = await rq.catalog_get_color_name(order_item.chosen_color) if order_item.chosen_color is not None else "N/A"
    chosen_size = await rq.catalog_get_size_name(order_item.chosen_size) if order_item.chosen_size is not None else "N/A"
    photos = await rq.catalog_get_product_photos(product.id)
    photo_id = photos[0].file_id if photos else None
    desc = (
        f"ПОДРОБНЕЕ О ТОВАРЕ:\n"
        f"Название: {product.name}\n"
        f"Описание: {product.description or 'Нет описания'}\n"
        f"Цена: {product.price:.2f}\n"
        f"Материал: {product.material or 'N/A'}\n"
        f"Особенности: {product.features or 'N/A'}\n"
        f"Температура: {product.temperature_range or 'N/A'}"
    )
    keyboard = kb.get_manager_product_edit_keyboard(order_item_id, product, order_item, order_group_id,
                                                      chosen_color=chosen_color, chosen_size=chosen_size)
    await safe_edit_message(callback_query.message, desc, reply_markup=keyboard, media=photo_id)

# Обработчики для изменения параметров товара без показа alert

@router.callback_query(F.data.startswith("manager_change_size:"))
async def manager_change_size(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    order_item_id = int(parts[1])
    action = parts[2]
    group_id = int(parts[3])
    success = await rq.update_cart_item_field(order_item_id, "size", action)
    await callback_query.answer()  # без текста
    if success:
        order_item = await rq.get_order_item(order_item_id)
        product = await rq.get_product(order_item.product_id)
        chosen_color = await rq.catalog_get_color_name(order_item.chosen_color) if order_item.chosen_color is not None else "N/A"
        chosen_size = await rq.catalog_get_size_name(order_item.chosen_size) if order_item.chosen_size is not None else "N/A"
        desc = (
            f"ПОДРОБНЕЕ О ТОВАРЕ:\n"
            f"Название: {product.name}\n"
            f"Описание: {product.description or 'Нет описания'}\n"
            f"Цена: {product.price:.2f}\n"
            f"Материал: {product.material or 'N/A'}\n"
            f"Особенности: {product.features or 'N/A'}\n"
            f"Температура: {product.temperature_range or 'N/A'}"
        )
        photos = await rq.catalog_get_product_photos(product.id)
        photo_id = photos[0].file_id if photos else None
        keyboard = kb.get_manager_product_edit_keyboard(order_item_id, product, order_item, group_id,
                                                          chosen_color=chosen_color, chosen_size=chosen_size)
        await safe_edit_message(callback_query.message, desc, reply_markup=keyboard, media=photo_id)

@router.callback_query(F.data.startswith("manager_change_color:"))
async def manager_change_color(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    order_item_id = int(parts[1])
    action = parts[2]
    group_id = int(parts[3])
    success = await rq.update_cart_item_field(order_item_id, "color", action)
    await callback_query.answer()
    if success:
        order_item = await rq.get_order_item(order_item_id)
        product = await rq.get_product(order_item.product_id)
        chosen_color = await rq.catalog_get_color_name(order_item.chosen_color) if order_item.chosen_color is not None else "N/A"
        chosen_size = await rq.catalog_get_size_name(order_item.chosen_size) if order_item.chosen_size is not None else "N/A"
        desc = (
            f"ПОДРОБНЕЕ О ТОВАРЕ:\n"
            f"Название: {product.name}\n"
            f"Описание: {product.description or 'Нет описания'}\n"
            f"Цена: {product.price:.2f}\n"
            f"Материал: {product.material or 'N/A'}\n"
            f"Особенности: {product.features or 'N/A'}\n"
            f"Температура: {product.temperature_range or 'N/A'}"
        )
        photos = await rq.catalog_get_product_photos(product.id)
        photo_id = photos[0].file_id if photos else None
        keyboard = kb.get_manager_product_edit_keyboard(order_item_id, product, order_item, group_id,
                                                          chosen_color=chosen_color, chosen_size=chosen_size)
        await safe_edit_message(callback_query.message, desc, reply_markup=keyboard, media=photo_id)

@router.callback_query(F.data.startswith("manager_change_qty:"))
async def manager_change_qty(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    order_item_id = int(parts[1])
    action = parts[2]
    group_id = int(parts[3])
    success = await rq.update_cart_item_field(order_item_id, "qty", action)
    await callback_query.answer()
    if success:
        order_item = await rq.get_order_item(order_item_id)
        product = await rq.get_product(order_item.product_id)
        chosen_color = await rq.catalog_get_color_name(order_item.chosen_color) if order_item.chosen_color is not None else "N/A"
        chosen_size = await rq.catalog_get_size_name(order_item.chosen_size) if order_item.chosen_size is not None else "N/A"
        desc = (
            f"ПОДРОБНЕЕ О ТОВАРЕ:\n"
            f"Название: {product.name}\n"
            f"Описание: {product.description or 'Нет описания'}\n"
            f"Цена: {product.price:.2f}\n"
            f"Материал: {product.material or 'N/A'}\n"
            f"Особенности: {product.features or 'N/A'}\n"
            f"Температура: {product.temperature_range or 'N/A'}"
        )
        photos = await rq.catalog_get_product_photos(product.id)
        photo_id = photos[0].file_id if photos else None
        keyboard = kb.get_manager_product_edit_keyboard(order_item_id, product, order_item, group_id,
                                                          chosen_color=chosen_color, chosen_size=chosen_size)
        await safe_edit_message(callback_query.message, desc, reply_markup=keyboard, media=photo_id)

# Обработчик кнопки "Подтвердить" – возвращает в режим просмотра товаров (без alert)
@router.callback_query(F.data.startswith("manager_update_product:"))
async def manager_update_product(callback_query: CallbackQuery, state: FSMContext):
    # Изменения уже сохранены, просто возвращаемся к просмотру товаров
    parts = callback_query.data.split(":")
    group_id = None
    if len(parts) >= 3:
        group_id = int(parts[2])
    else:
        data = await state.get_data()
        group_id = data.get("order_group_id")
    if group_id is None:
        await callback_query.answer("Ошибка данных.", show_alert=True)
        return
    await callback_query.answer()
    await refresh_manager_edit_order_view(callback_query, group_id)


@router.callback_query(F.data.startswith("manager_delete_product:"))
async def manager_delete_product(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    order_item_id = int(parts[1])
    # Если group_id передан в callback data, используем его; иначе пытаемся взять из FSM
    group_id = int(parts[2]) if len(parts) > 2 else (await state.get_data()).get("order_group_id")
    if group_id is None:
        await callback_query.answer("Ошибка данных.", show_alert=True)
        return
    keyboard = kb.get_delete_product_confirmation_keyboard(order_item_id, group_id)
    await safe_edit_message(callback_query.message, "Вы действительно хотите удалить этот товар?", reply_markup=keyboard)

@router.callback_query(F.data.startswith("manager_delete_product_confirm:"))
async def manager_delete_product_confirm(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    order_item_id = int(parts[1])
    group_id = int(parts[2]) if len(parts) > 2 else None
    if group_id is None:
        await callback_query.answer("Ошибка данных.", show_alert=True)
        return
    # Получаем OrderItem и затем заказ, к которому он принадлежит
    order_item = await rq.get_order_item(order_item_id)
    if not order_item:
        await callback_query.answer("Товар не найден.", show_alert=True)
        return
    order = await rq.get_order_by_id(order_item.order_id)
    if not order:
        await callback_query.answer("Заказ не найден.", show_alert=True)
        return
    # Обновляем статус заказа на "Удален"
    success = await rq.update_order_status([order.id], "Удален")
    if success:
        await refresh_manager_edit_order_view(callback_query, group_id)
    else:
        await callback_query.answer("Ошибка при отмене заказа.", show_alert=True)


@router.callback_query(F.data == 'go_to_manager_dashboard')
async def go_to_dashboard(callback_query: CallbackQuery, state: FSMContext):
    await manager_account(callback_query.message, state)


@router.callback_query(F.data == 'manager_stats')
async def manager_stats(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    # Получаем информацию о менеджере по telegram_id
    manager_info = await rq.get_manager_info(str(callback_query.from_user.id))
    manager_name = manager_info.full_name if manager_info and manager_info.full_name else "N/A"

    # Получаем статистику по заказам (данные из OrderGroup)
    accepted_orders = await rq.get_accepted_order_groups()
    cancelled_orders = await rq.get_cancelled_order_groups()

    stats_text = (
        f"СТАТИСТИКА\n"
        f"ФИО: {manager_name}\n\n"
        f"Заказы({accepted_orders + cancelled_orders}):\n"
        f"    Принятые: {accepted_orders}\n"
        f"    Отмененные: {cancelled_orders}"
    )
    keyboard = kb.go_to_manager_dashboard()
    await safe_edit_message(callback_query.message, stats_text, reply_markup=keyboard, media=utils.manager_png)


async def render_manager_orders_view(source, manager_id: str, status_filter: str, sort_order: str, page: int):
    per_page = 10
    # Получаем список групп заказов: (OrderGroup, fullname, order_datetime)
    order_groups_data = await rq.get_manager_order_groups(manager_id, status_filter, sort_order, page, per_page)
    total_orders = await rq.get_total_manager_order_groups(manager_id, status_filter)
    total_pages = (total_orders + per_page - 1) // per_page if total_orders > 0 else 1

    # Отображаем текст в зависимости от фильтра
    status_text = "Принятые" if status_filter == "accepted" else "Отмененные"
    sort_text = "По возрастанию" if sort_order == "asc" else "По убыванию"
    caption = f"История ваших заказов\nСтатус: {status_text}\nСортировка: {sort_text}"
    keyboard = kb.get_manager_orders_keyboard(order_groups_data, status_filter, sort_order, page, total_pages)

    # Если источник – callback, редактируем сообщение, иначе отправляем новое фото с подписью
    if isinstance(source, CallbackQuery):
        await source.message.edit_media(
            media=InputMediaPhoto(media=utils.manager_png, caption=caption),
            reply_markup=keyboard
        )
    else:
        await source.answer_photo(photo=utils.manager_png, caption=caption, reply_markup=keyboard)

@router.callback_query(F.data == 'manager_my_orders')
async def manager_my_orders(callback_query: CallbackQuery, state: FSMContext):
    manager_id = str(callback_query.message.chat.id)
    status_filter = "accepted"  # по умолчанию – Принятые заказы
    sort_order = "asc"          # по умолчанию – сортировка по возрастанию
    page = 1
    await render_manager_orders_view(callback_query, manager_id, status_filter, sort_order, page)

@router.callback_query(F.data.startswith("manager_my_orders_filter:"))
async def manager_my_orders_filter(callback_query: CallbackQuery, state: FSMContext):
    # Формат callback_data: manager_my_orders_filter:{new_filter}:{sort_order}:{page}
    parts = callback_query.data.split(":")
    new_filter = parts[1]  # "accepted" или "cancelled"
    sort_order = parts[2]
    page = int(parts[3])
    manager_id = str(callback_query.message.chat.id)
    await render_manager_orders_view(callback_query, manager_id, new_filter, sort_order, page)

@router.callback_query(F.data.startswith("manager_my_orders_sort:"))
async def manager_my_orders_sort(callback_query: CallbackQuery, state: FSMContext):
    # Формат callback_data: manager_my_orders_sort:{status_filter}:{new_sort_order}:{page}
    parts = callback_query.data.split(":")
    status_filter = parts[1]
    new_sort_order = parts[2]
    page = int(parts[3])
    manager_id = str(callback_query.message.chat.id)
    await render_manager_orders_view(callback_query, manager_id, status_filter, new_sort_order, page)

@router.callback_query(F.data.startswith("manager_my_orders_page:"))
async def manager_my_orders_page(callback_query: CallbackQuery, state: FSMContext):
    # Формат callback_data: manager_my_orders_page:{status_filter}:{sort_order}:{page}
    parts = callback_query.data.split(":")
    status_filter = parts[1]
    sort_order = parts[2]
    page = int(parts[3])
    manager_id = str(callback_query.message.chat.id)
    await render_manager_orders_view(callback_query, manager_id, status_filter, sort_order, page)

@router.callback_query(F.data.startswith("manager_order_detail_my:"))
async def manager_order_detail_my(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    order_group_id = int(callback_query.data.split(":")[1])
    group = await rq.get_order_group_by_id(order_group_id)
    if not group:
        await safe_edit_message(callback_query.message, "Группа заказа не найдена.", reply_markup=None)
        return

    first_order = await rq.get_order_by_id(group.order_ids[0])
    items_lines = []
    total_cost = 0.0
    index = 1
    # Формируем список товаров по группам заказов
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
    details_text = "\n".join(details_lines)
    keyboard = kb.get_manager_order_detail_keyboard_m(group.id)
    await safe_edit_message(callback_query.message, details_text, reply_markup=keyboard)