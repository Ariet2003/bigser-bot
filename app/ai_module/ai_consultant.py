import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import OpenAI
from sqlalchemy import select, update

from app.database.models import async_session, Product, ProductPhoto, User, Order, OrderItem, Color, Size, Category, Subcategory, \
    OrderGroup
from app.users.user.userHandlers import router
from bot_instance import bot

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Создаем отдельный роутер для AI консультанта
ai_router = Router()

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота и диспетчера
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Словарь для хранения состояний пользователей и их корзин
user_states = {}
user_carts = {}

# Определение инструментов (tools) для OpenAI
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "Получить список товаров из базы данных",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Получить детальную информацию о конкретном товаре",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Название товара"
                    }
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Добавить товар в корзину пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Название товара"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Количество товара"
                    },
                    "color": {
                        "type": "string",
                        "description": "Выбранный цвет (если указан)"
                    },
                    "size": {
                        "type": "string",
                        "description": "Выбранный размер (если указан)"
                    }
                },
                "required": ["product_name", "quantity", "color", "size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_order",
            "description": "Завершить заказ и вывести информацию о корзине",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "ФИО клиента"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Номер телефона клиента"
                    },
                    "address": {
                        "type": "string",
                        "description": "Адрес доставки"
                    },
                    "delivery": {
                        "type": "boolean",
                        "description": "Нужна ли доставка (true) или самовывоз (false)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filter_products",
            "description": "Отфильтровать товары по запросу пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "Запрос пользователя для фильтрации товаров"
                    }
                },
                "required": ["user_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_related_products",
            "description": "Получить связанные товары, подходящие к выбранному товару",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Название товара, для которого нужно найти связанные товары"
                    }
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_info",
            "description": "Получить информацию о пользователе из базы данных",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_info",
            "description": "Обновить информацию о пользователе в базе данных",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "ФИО клиента"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Номер телефона клиента"
                    },
                    "address": {
                        "type": "string",
                        "description": "Адрес доставки"
                    }
                },
                "required": ["full_name", "phone", "address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_user_data",
            "description": "Подтвердить или изменить данные пользователя для заказа",
            "parameters": {
                "type": "object",
                "properties": {
                    "is_correct": {
                        "type": "boolean",
                        "description": "Корректны ли существующие данные пользователя"
                    },
                    "full_name": {
                        "type": "string",
                        "description": "Новое ФИО клиента, если данные некорректны"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Новый номер телефона клиента, если данные некорректны"
                    },
                    "delivery": {
                        "type": "boolean",
                        "description": "Нужна ли доставка (true) или самовывоз (false)"
                    },
                    "address": {
                        "type": "string",
                        "description": "Новый адрес доставки, если данные некорректны или нужна доставка"
                    }
                },
                "required": ["is_correct", "delivery"]
            }
        }
    }
]


# Функции для обработки вызовов от OpenAI
async def get_products() -> Dict:
    """Получить структурированный список товаров из базы данных"""
    async with async_session() as session:
        # Получаем все категории
        categories_result = await session.execute(select(Category))
        categories = categories_result.scalars().all()

        structured_products = []
        flat_product_names = []  # Плоский список только названий для отображения клиенту

        for category in categories:
            category_data = {
                "id": category.id,
                "name": category.name,
                "subcategories": []
            }

            # Получаем подкатегории для текущей категории
            subcategories_result = await session.execute(
                select(Subcategory).where(Subcategory.category_id == category.id)
            )
            subcategories = subcategories_result.scalars().all()

            for subcategory in subcategories:
                subcategory_data = {
                    "id": subcategory.id,
                    "name": subcategory.name,
                    "products": []
                }

                # Получаем товары для текущей подкатегории
                products_result = await session.execute(
                    select(Product).where(Product.subcategory_id == subcategory.id)
                )
                products = products_result.scalars().all()

                for product in products:
                    product_data = {
                        "id": product.id,
                        "name": product.name,
                        "price": float(product.price)
                    }
                    subcategory_data["products"].append(product_data)
                    flat_product_names.append(product.name)

                category_data["subcategories"].append(subcategory_data)

            structured_products.append(category_data)

        return {
            "structured_products": structured_products,
            "product_names": flat_product_names  # Этот список будет использоваться для отображения клиенту
        }


async def get_product_details(product_name: str) -> Dict:
    """Получить детальную информацию о конкретном товаре"""
    async with async_session() as session:
        # Получаем информацию о товаре
        result = await session.execute(
            select(Product).where(Product.name == product_name)
        )
        product = result.scalar_one_or_none()

        if not product:
            return {"error": "Товар не найден"}

        # Получаем фотографии товара
        photos_result = await session.execute(
            select(ProductPhoto).where(ProductPhoto.product_id == product.id)
        )
        photos = photos_result.scalars().all()
        photo_ids = [photo.file_id for photo in photos]

        # Получаем доступные цвета
        available_colors = []
        if product.color_ids:  # Проверяем, что color_ids не пустой
            # Используем list() для преобразования JSON списка в Python список, если необходимо
            color_ids = product.color_ids if isinstance(product.color_ids, list) else list(product.color_ids)
            colors_result = await session.execute(
                select(Color).where(Color.id.in_(color_ids))
            )
            colors = colors_result.scalars().all()
            available_colors = [{"id": color.id, "name": color.name} for color in colors]

        # Получаем доступные размеры
        available_sizes = []
        if product.size_ids:  # Проверяем, что size_ids не пустой
            # Используем list() для преобразования JSON списка в Python список, если необходимо
            size_ids = product.size_ids if isinstance(product.size_ids, list) else list(product.size_ids)
            sizes_result = await session.execute(
                select(Size).where(Size.id.in_(size_ids))
            )
            sizes = sizes_result.scalars().all()
            available_sizes = [{"id": size.id, "size": size.size} for size in sizes]

        # Формируем детальную информацию о товаре
        product_info = {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "description": product.description,
            "product_type": product.product_type,
            "material": product.material,
            "features": product.features,
            "usage": product.usage,
            "temperature_range": product.temperature_range,
            "photo_ids": photo_ids,
            "available_colors": available_colors,
            "available_sizes": available_sizes,
            "has_color_options": len(available_colors) > 0,
            "has_size_options": len(available_sizes) > 0,
            "color_options": [color["name"] for color in available_colors],
            "size_options": [size["size"] for size in available_sizes],
            "instructions": "Показать клиенту основную информацию о товаре. " +
                            "Затем, если доступны цвета или размеры, попросить клиента выбрать конкретные параметры. " +
                            "После выбора всех параметров, спросить о желаемом количестве."
        }
        return product_info


async def add_to_cart(user_id: int, product_name: str, quantity: int = None, color: str = None,
                      size: str = None) -> Dict:
    """Добавить товар в корзину пользователя"""
    if user_id not in user_carts:
        user_carts[user_id] = []

    # Получаем информацию о товаре
    async with async_session() as session:
        result = await session.execute(
            select(Product).where(Product.name == product_name)
        )
        product = result.scalar_one_or_none()

        if not product:
            return {"error": "Товар не найден"}

        # Получаем доступные цвета и размеры
        available_colors = []
        if product.color_ids:
            colors_result = await session.execute(
                select(Color).where(Color.id.in_(product.color_ids))
            )
            colors = colors_result.scalars().all()
            available_colors = [{"id": color.id, "name": color.name} for color in colors]
            available_color_names = [c["name"] for c in available_colors]

        available_sizes = []
        if product.size_ids:
            sizes_result = await session.execute(
                select(Size).where(Size.id.in_(product.size_ids))
            )
            sizes = sizes_result.scalars().all()
            available_sizes = [{"id": size.id, "size": size.size} for size in sizes]
            available_size_names = [s["size"] for s in available_sizes]

        # Проверяем наличие всех необходимых деталей
        missing_params = {}

        # Проверка количества (обязательный параметр)
        if quantity is None:
            missing_params["quantity"] = {
                "message": f"Пожалуйста, укажите количество для {product_name}"
            }

        # Проверка цвета, если есть варианты
        if available_colors:
            if not color:
                missing_params["color"] = {
                    "message": f"Пожалуйста, выберите цвет для {product_name}",
                    "available_options": available_color_names
                }
            else:
                # Проверяем корректность цвета
                color_match = next((c for c in available_colors if c["name"].lower() == color.lower()), None)
                if not color_match:
                    return {
                        "error": f"Цвет '{color}' недоступен для этого товара. Доступные цвета: " +
                                 ", ".join(available_color_names)
                    }
                color_id = color_match["id"]
        else:
            color_id = None
            if color:
                return {
                    "error": f"Для товара {product_name} выбор цвета недоступен"
                }

        # Проверка размера, если есть варианты
        if available_sizes:
            if not size:
                missing_params["size"] = {
                    "message": f"Пожалуйста, выберите размер для {product_name}",
                    "available_options": available_size_names
                }
            else:
                # Проверяем корректность размера
                size_match = next((s for s in available_sizes if s["size"].lower() == size.lower()), None)
                if not size_match:
                    return {
                        "error": f"Размер '{size}' недоступен для этого товара. Доступные размеры: " +
                                 ", ".join(available_size_names)
                    }
                size_id = size_match["id"]
        else:
            size_id = None
            if size:
                return {
                    "error": f"Для товара {product_name} выбор размера недоступен"
                }

        # Если не все детали предоставлены, возвращаем запрос недостающих
        if missing_params:
            return {
                "needs_details": True,
                "product_name": product_name,
                "missing_params": missing_params,
                "message": "Пожалуйста, укажите недостающие параметры для добавления товара в корзину"
            }

    # Добавляем товар в корзину
    cart_item = {
        "product_id": product.id,  # Добавляем product_id из базы данных
        "product_name": product_name,
        "price": float(product.price),
        "quantity": quantity,
        "color": color,
        "color_id": color_id,
        "size": size,
        "size_id": size_id,
        "total": float(product.price) * quantity
    }

    user_carts[user_id].append(cart_item)

    return {
        "status": "success",
        "message": f"Товар {product_name} добавлен в корзину",
        "cart_item": cart_item
    }


async def get_user_info(user_id: int) -> Dict:
    """Получить информацию о пользователе из базы данных"""
    async with async_session() as session:
        # Проверяем, что telegram_id преобразован в строку для корректного сравнения
        telegram_id_str = str(user_id)
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id_str)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Создаем нового пользователя с telegram_id
            new_user = User(telegram_id=telegram_id_str)
            session.add(new_user)
            await session.commit()
            return {"error": "Пользователь не найден"}

        # Проверяем, что у пользователя есть все необходимые данные
        if not user.full_name or not user.phone_number:
            return {"error": "Данные пользователя неполные", "existing_data": {
                "full_name": user.full_name or "",
                "phone": user.phone_number or "",
                "address": user.address or ""
            }}

        return {
            "full_name": user.full_name,
            "phone": user.phone_number,
            "address": user.address
        }


async def update_user_info(user_id: int, full_name: str, phone: str, address: str) -> Dict:
    """Обновить информацию о пользователе в базе данных"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == str(user_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            return {"error": "Пользователь не найден"}

        # Обновляем информацию о пользователе
        await session.execute(
            update(User)
            .where(User.telegram_id == str(user_id))
            .values(full_name=full_name, phone_number=phone, address=address)
        )
        await session.commit()

        return {
            "status": "success",
            "message": "Информация о пользователе обновлена",
            "user_info": {
                "full_name": full_name,
                "phone": phone,
                "address": address
            }
        }


async def save_order_to_db(order_info: Dict) -> List[int]:
    """Сохранить заказ в базу данных"""
    async with async_session() as session:
        # Получаем пользователя по его ID
        user_result = await session.execute(
            select(User).where(User.id == order_info["user_info"]["user_id"])
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("Пользователь не найден")

        order_ids = []  # Список для хранения ID созданных заказов

        # Создаем отдельный заказ для каждого товара
        for item in order_info["items"]:
            # Создаем заказ, используя telegram_id пользователя
            new_order = Order(
                user_id=user.telegram_id,  # Используем telegram_id вместо id
                processed_by_id=None,
                order_datetime=datetime.fromisoformat(order_info["order_datetime"]),
                status="Ожидание",
                delivery_method="доставка" if order_info["user_info"]["delivery"] else "самовывоз"
            )
            session.add(new_order)
            await session.flush()  # Чтобы получить ID заказа

            # Получаем ID цвета
            if item["color"] != "Не указан":
                color_result = await session.execute(
                    select(Color).where(Color.name == item["color"])
                )
                color = color_result.scalar_one_or_none()
                color_id = color.id if color else None
            else:
                color_id = None

            # Получаем ID размера
            if item["size"] != "Не указан":
                size_result = await session.execute(
                    select(Size).where(Size.size == item["size"])
                )
                size = size_result.scalar_one_or_none()
                size_id = size.id if size else None
            else:
                size_id = None

            # Создаем элемент заказа
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                chosen_color=color_id,
                chosen_size=size_id
            )
            session.add(order_item)

            order_ids.append(new_order.id)

        # Создаем группу заказов
        order_group = OrderGroup(
            user_id=user.telegram_id,  # Используем telegram_id и здесь для консистентности
            processed_by_id=None,
            order_ids=order_ids
        )
        session.add(order_group)

        await session.commit()
        return order_ids


async def complete_order(user_id: int, full_name: str = "", phone: str = "", address: str = "",
                         delivery: bool = None) -> Dict:
    """Завершить заказ и вывести информацию о корзине"""
    if user_id not in user_carts or not user_carts[user_id]:
        return {"error": "Корзина пуста"}

    cart = user_carts[user_id]
    total_amount = sum(item["total"] for item in cart)

    # Формируем данные корзины для вывода
    cart_summary = {
        "items": [],
        "total_amount": total_amount,
        "currency": "сом"
    }

    for item in cart:
        cart_summary["items"].append({
            "product_name": item["product_name"],
            "price": item["price"],
            "quantity": item["quantity"],
            "color": item.get("color", "Не указан"),
            "size": item.get("size", "Не указан"),
            "total": item["total"]
        })

    # Если это первый вызов функции (delivery не определено)
    if delivery is None:
        # Сначала проверяем, есть ли данные пользователя в БД
        user_info = await get_user_info(user_id)

        # Если у пользователя есть полные данные в БД
        if "error" not in user_info and not "existing_data" in user_info:
            return {
                "user_data_exists": True,
                "cart_summary": cart_summary,
                "user_info": user_info,
                "message": "У нас есть ваши данные. Пожалуйста, проверьте, верны ли они:",
                "action_required": "verify_user_data"
            }

        # Если нет полных данных, просим указать способ доставки
        return {
            "cart_summary": cart_summary,
            "needs_details": True,
            "missing": "delivery",
            "message": "Хотите оформить доставку? (да/нет)"
        }

    # Получаем информацию о пользователе из базы
    user_info = await get_user_info(user_id)

    # Если у пользователя есть частичные данные
    if "existing_data" in user_info:
        existing_data = user_info["existing_data"]

        # Используем существующие данные, если не указаны новые
        if not full_name and existing_data["full_name"]:
            full_name = existing_data["full_name"]

        if not phone and existing_data["phone"]:
            phone = existing_data["phone"]

        if delivery and not address and existing_data["address"]:
            address = existing_data["address"]

    # Если нет имени
    if not full_name:
        return {
            "cart_summary": cart_summary,
            "needs_details": True,
            "missing": "full_name",
            "message": "Пожалуйста, укажите ваше полное имя"
        }

    # Если нет телефона
    if not phone:
        return {
            "cart_summary": cart_summary,
            "needs_details": True,
            "missing": "phone",
            "message": "Пожалуйста, укажите ваш номер телефона"
        }

    # Если необходима доставка но нет адреса
    if delivery and not address:
        return {
            "cart_summary": cart_summary,
            "needs_details": True,
            "missing": "address",
            "message": "Пожалуйста, укажите адрес доставки"
        }

    # Если все данные предоставлены - обновляем информацию о пользователе в БД
    await update_user_info(user_id, full_name, phone, address if delivery else "")

    # Получаем telegram_id пользователя из базы данных
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == str(user_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            return {"error": "Пользователь не найден в базе данных"}

    # Формируем информацию о заказе для вывода в консоль
    order_info = {
        "user_info": {
            "user_id": user.id,  # ID пользователя из базы данных
            "full_name": full_name,
            "phone": phone,
            "address": address if delivery else "Самовывоз",
            "delivery": delivery
        },
        "order_datetime": datetime.now().isoformat(),
        "items": [
            {
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "color": item.get("color", "Не указан"),
                "size": item.get("size", "Не указан"),
                "price": item["price"],
                "total": item["total"]
            }
            for item in cart
        ],
        "total_amount": total_amount,
        "currency": "сом"
    }

    try:
        # Сохраняем заказ в базу данных
        order_ids = await save_order_to_db(order_info)

        # Выводим информацию о заказе в консоль
        print(json.dumps(order_info, ensure_ascii=False, indent=2))

        # Очищаем корзину пользователя
        user_carts[user_id] = []

        return {
            "status": "success",
            "message": "Заказ оформлен успешно",
            "order_info": order_info,
            "order_ids": order_ids
        }
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа: {e}")
        return {
            "status": "error",
            "message": "Произошла ошибка при оформлении заказа"
        }


async def get_related_products(product_name: str) -> Dict:
    """Получить связанные товары, подходящие к выбранному товару"""
    # Получаем информацию о выбранном товаре
    async with async_session() as session:
        result = await session.execute(
            select(Product).where(Product.name == product_name)
        )
        product = result.scalar_one_or_none()

        if not product:
            return {"error": "Товар не найден"}

        # Получаем категорию и подкатегорию выбранного товара
        product_subcategory = None
        product_category = None

        if product.subcategory_id:
            subcategory_result = await session.execute(
                select(Subcategory).where(Subcategory.id == product.subcategory_id)
            )
            product_subcategory = subcategory_result.scalar_one_or_none()

            if product_subcategory:
                category_result = await session.execute(
                    select(Category).where(Category.id == product_subcategory.category_id)
                )
                product_category = category_result.scalar_one_or_none()

        # Получаем все товары с их категориями и подкатегориями, исключая выбранный
        products_result = await session.execute(
            select(Product, Subcategory, Category)
            .join(Subcategory, Product.subcategory_id == Subcategory.id, isouter=True)
            .join(Category, Subcategory.category_id == Category.id, isouter=True)
            .where(Product.name != product_name)
        )
        products_info = []

        for p, s, c in products_result:
            products_info.append({
                "id": p.id,
                "name": p.name,
                "type": p.product_type,
                "price": float(p.price),
                "subcategory": s.name if s else None,
                "category": c.name if c else None
            })

    # Отправляем запрос в OpenAI для подбора связанных товаров
    try:
        # Формируем контекст с информацией о категории и подкатегории выбранного товара
        context = {
            "product": {
                "name": product_name,
                "type": product.product_type,
                "subcategory": product_subcategory.name if product_subcategory else None,
                "category": product_category.name if product_category else None
            }
        }

        # Отправляем запрос в OpenAI
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Ты - консультант в магазине спортивной одежды Bigser. Выбери из списка товаров не более 3 товаров, которые хорошо сочетаются с основным товаром или дополняют его. Учитывай категории и подкатегории товаров."},
                {"role": "user",
                 "content": f"Основной товар: {json.dumps(context, ensure_ascii=False)}. Доступные товары: {json.dumps(products_info, ensure_ascii=False)}"}
            ],
            max_tokens=1000
        )

        related_text = response.choices[0].message.content.strip()

        # Находим названия товаров в ответе
        related_products = []
        for p in products_info:
            if p["name"] in related_text:
                related_products.append({
                    "name": p["name"],
                    "type": p["type"],
                    "price": p["price"],
                    "category": p["category"],
                    "subcategory": p["subcategory"]
                })
                if len(related_products) >= 3:  # Ограничиваем до 3 связанных товаров
                    break

        return {"related_products": related_products}

    except Exception as e:
        logger.error(f"Ошибка при получении связанных товаров: {e}")
        return {"error": "Произошла ошибка при получении связанных товаров", "related_products": []}


async def filter_products(user_query: str, user_id: int = None) -> Dict:
    """Отфильтровать товары по запросу пользователя"""
    # Определяем контекст предыдущего запроса, если он есть
    previous_context = {}
    if user_id and user_id in user_states:
        previous_context = user_states[user_id].get("search_context", {})

    # Объединяем предыдущий запрос с текущим, если это уточнение
    combined_query = user_query
    user_states[user_id]["last_query"] = combined_query

    if previous_context.get("original_query"):
        if previous_context.get("waiting_for") == "size":
            combined_query = f"{previous_context.get('original_query')} размер {user_query}"
            previous_context["size"] = user_query
            previous_context["waiting_for"] = "color"

        elif previous_context.get("waiting_for") == "color":
            combined_query = f"{previous_context.get('original_query')} цвет {user_query}"
            previous_context["color"] = user_query
            previous_context["waiting_for"] = None

        elif "color" in user_query.lower() or "размер" in user_query.lower() or "цвет" in user_query.lower() or "size" in user_query.lower():
            combined_query = f"{previous_context.get('original_query')} {user_query}"

    # Получаем структурированные данные о товарах
    products_data = await get_products()
    structured_products = products_data["structured_products"]

    # Получаем информацию о категориях, подкатегориях и деталях товаров
    context_info = []
    async with async_session() as session:
        for category in structured_products:
            for subcategory in category["subcategories"]:
                for product in subcategory["products"]:
                    # Получаем детальную информацию о товаре
                    product_result = await session.execute(
                        select(Product).where(Product.id == product["id"])
                    )
                    product_details = product_result.scalar_one_or_none()

                    if product_details:
                        # Получаем доступные цвета
                        available_colors = []
                        if product_details.color_ids:
                            colors_result = await session.execute(
                                select(Color).where(Color.id.in_(product_details.color_ids))
                            )
                            colors = colors_result.scalars().all()
                            available_colors = [color.name for color in colors]

                        # Получаем доступные размеры
                        available_sizes = []
                        if product_details.size_ids:
                            sizes_result = await session.execute(
                                select(Size).where(Size.id.in_(product_details.size_ids))
                            )
                            sizes = sizes_result.scalars().all()
                            available_sizes = [size.size for size in sizes]

                        # Получаем фотографии
                        photos_result = await session.execute(
                            select(ProductPhoto).where(ProductPhoto.product_id == product_details.id)
                        )
                        photos = photos_result.scalars().all()
                        photo_ids = [photo.file_id for photo in photos]

                        context_info.append({
                            "name": product["name"],
                            "category": category["name"],
                            "subcategory": subcategory["name"],
                            "id": product["id"],
                            "colors": available_colors,
                            "sizes": available_sizes,
                            "price": float(product["price"]),
                            "description": product_details.description,
                            "photo_ids": photo_ids,
                            "product_type": product_details.product_type,
                            "material": product_details.material,
                            "features": product_details.features,
                            "usage": product_details.usage
                        })

    # Проверяем, ожидаем ли мы уточнения от пользователя
    if previous_context.get("waiting_for"):
        waiting_for = previous_context.get("waiting_for")

        # Сохраняем обновленный контекст
        if user_id:
            user_states[user_id]["search_context"] = previous_context

        # Если ожидаем уточнения о размере
        if waiting_for == "size":
            # Собираем доступные размеры для указанного типа товара
            available_sizes = set()
            for product in context_info:
                if product.get("sizes"):
                    for size in product.get("sizes"):
                        available_sizes.add(str(size))

            size_options = ", ".join(sorted(available_sizes)) if available_sizes else "любой"

            return {
                "needs_clarification": True,
                "message": f"Какой размер вам подходит? Доступные размеры: {size_options}",
                "context": previous_context
            }

        # Если ожидаем уточнения о цвете
        elif waiting_for == "color":
            # Собираем доступные цвета для указанного типа товара
            available_colors = set()
            for product in context_info:
                if product.get("colors"):
                    for color in product.get("colors"):
                        available_colors.add(color)

            color_options = ", ".join(sorted(available_colors)) if available_colors else "любой"

            return {
                "needs_clarification": True,
                "message": f"Какой цвет предпочитаете? Доступные цвета: {color_options}",
                "context": previous_context
            }

    # Если все уточнения получены или их не требуется, ищем товары
    try:
        # Отправляем запрос в OpenAI для поиска товаров
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": """Ты - дружелюбный консультант в магазине спортивной одежды Bigser.

                 Инструкции:
                 1. Проанализируй запрос клиента и найди товары, максимально соответствующие всем указанным параметрам.
                 2. Учитывай следующие параметры:
                    - Цвет
                    - Размер
                 3. Если точного соответствия нет, найди ближайшие аналоги.
                 4. Верни не более 5 самых подходящих товаров.
                 5. Если нет подходящих товаров, отметь это специальным тегом "НЕТ_ПОДХОДЯЩИХ".
                 6. Для каждого товара добавь короткую рекомендацию, почему он подходит клиенту.
                 7. Альтернативные варианты выводи так же в виде карусели.
                 8. Формат ответа:
                    ```json
                    {
                      "items": [
                        {"name": "Название товара 1", "reason": "Почему подходит"},
                        {"name": "Название товара 2", "reason": "Почему подходит"},
                        ...
                      ]
                    }
                    ```
                    Или, если нет подходящих товаров:
                    ```json
                    {
                      "НЕТ_ПОДХОДЯЩИХ": true,
                      "alternative_suggestions": ["Товар 1", "Товар 2", ...]
                    }
                    ```
                 """},
                {"role": "user",
                 "content": f"Запрос клиента: '{combined_query}'. Доступные товары с деталями: {json.dumps(context_info, ensure_ascii=False)}"}
            ],
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        recommendations = json.loads(response.choices[0].message.content)

        # Очищаем контекст поиска, так как нашли товары
        if user_id and user_id in user_states:
            user_states[user_id].pop("search_context", None)

        # Проверяем, есть ли подходящие товары
        if "НЕТ_ПОДХОДЯЩИХ" in recommendations and recommendations["НЕТ_ПОДХОДЯЩИХ"]:
            alternative_names = recommendations.get("alternative_suggestions", [])
            alternative_products = []

            # Определяем подкатегорию запрашиваемого товара (если известна)
            user_query = user_states[user_id].get("last_query", "")  # Запрос пользователя
            request_subcategory = None

            # Попробуем найти подкатегорию запрашиваемого товара
            for product in context_info:
                if user_query.lower() in product["name"].lower():  # Ищем товар по названию
                    request_subcategory = product["subcategory"]  # Получаем подкатегорию
                    break

            # Ищем информацию об альтернативных товарах
            # Фильтруем альтернативные товары, оставляя только из той же подкатегории
            for alt_name in alternative_names:
                for product in context_info:
                    if product["name"] == alt_name:
                        # Фильтруем по подкатегории
                        if request_subcategory and product["subcategory"] != request_subcategory:
                            continue  # Пропускаем товар, если он не из той же подкатегории
                        alternative_products.append(product)
                        break

            return {
                "no_exact_match": True,
                "message": f"Товаров, точно соответствующих вашему запросу, не найдено. Вот альтернативные варианты из той же подкатегории:",
                "alternatives": alternative_products
            }

        # Если есть подходящие товары, находим полную информацию о них
        recommended_items = recommendations.get("items", [])
        detailed_recommendations = []

        for item in recommended_items:
            for product in context_info:
                if product["name"] == item["name"]:
                    product_with_reason = product.copy()
                    product_with_reason["recommendation_reason"] = item["reason"]
                    detailed_recommendations.append(product_with_reason)
                    break

        return {
            "exact_matches": True,
            "recommended_products": detailed_recommendations
        }

    except Exception as e:
        logger.error(f"Ошибка при фильтрации товаров: {e}")
        return {
            "needs_clarification": True,
            "message": "Извините, не совсем понял ваш запрос. Не могли бы вы сформулировать его по-другому?"
        }


async def verify_user_data(user_id: int, is_correct: bool, delivery: bool, full_name: str = "", phone: str = "",
                           address: str = "") -> Dict:
    """Подтвердить или изменить данные пользователя для заказа"""
    if user_id not in user_carts or not user_carts[user_id]:
        return {"error": "Корзина пуста"}

    cart = user_carts[user_id]
    total_amount = sum(item["total"] for item in cart)

    # Формируем данные корзины для вывода
    cart_summary = {
        "items": [],
        "total_amount": total_amount,
        "currency": "сом"
    }

    for item in cart:
        cart_summary["items"].append({
            "product_name": item["product_name"],
            "price": item["price"],
            "quantity": item["quantity"],
            "color": item.get("color", "Не указан"),
            "size": item.get("size", "Не указан"),
            "total": item["total"]
        })

    # Получаем текущую информацию о пользователе из БД
    user_info = await get_user_info(user_id)

    # Если данные корректны
    if is_correct:
        # Если нужна доставка, но адреса нет или нужно его изменить
        if delivery and (not user_info.get("address") or address):
            if not address:
                return {
                    "cart_summary": cart_summary,
                    "needs_details": True,
                    "missing": "address",
                    "message": "Пожалуйста, укажите адрес доставки"
                }
            else:
                # Обновляем только адрес, сохраняя текущие данные имени и телефона
                await update_user_info(
                    user_id,
                    user_info.get("full_name") if "full_name" in user_info else "",
                    user_info.get("phone") if "phone" in user_info else "",
                    address
                )

        # Продолжаем с оформлением заказа, используя текущие данные из БД
        if "existing_data" in user_info:
            user_data = user_info["existing_data"]
            return await complete_order(
                user_id,
                user_data.get("full_name", ""),
                user_data.get("phone", ""),
                user_data.get("address", "") if delivery else "",
                delivery
            )
        else:
            return await complete_order(
                user_id,
                user_info.get("full_name", ""),
                user_info.get("phone", ""),
                user_info.get("address", "") if delivery else "",
                delivery
            )
    else:
        # Если данные неверны, запрашиваем новые
        if not full_name:
            return {
                "cart_summary": cart_summary,
                "needs_details": True,
                "missing": "full_name",
                "message": "Пожалуйста, укажите ваше полное имя"
            }

        if not phone:
            return {
                "cart_summary": cart_summary,
                "needs_details": True,
                "missing": "phone",
                "message": "Пожалуйста, укажите ваш номер телефона"
            }

        if delivery and not address:
            return {
                "cart_summary": cart_summary,
                "needs_details": True,
                "missing": "address",
                "message": "Пожалуйста, укажите адрес доставки"
            }

        # Обновляем информацию о пользователе
        await update_user_info(user_id, full_name, phone, address if delivery else "")

        # Продолжаем с оформлением заказа
        return await complete_order(user_id, full_name, phone, address if delivery else "", delivery)


@ai_router.callback_query(F.data == 'user_consultation')
async def cmd_start(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.message.delete()
    user_states[user_id] = {
        "chat_history": [
            {"role": "system", "content": """
            Ты - дружелюбный и опытный консультант магазина спортивной одежды Bigser. Общайся естественно, как человек, избегай формальностей и технических терминов.

            Как вести диалог с клиентом:

            1. Начни с приветливого приветствия и спроси, чем можешь помочь.

            2. При поиске товаров ОБЯЗАТЕЛЬНО следуй этой последовательности:
               a) Когда клиент запрашивает товар, используй filter_products для поиска
               b) Если в запросе недостаточно деталей, задай уточняющие вопросы:
                  - Какой цвет предпочитает клиент
                  - Какой размер ему нужен
               c) После получения всех деталей покажи наиболее подходящие товары
               d) Если точных соответствий нет, предложи альтернативные варианты

            3. При показе товаров:
               - Объясни, почему именно эти товары подходят клиенту
               - Добавляй краткие рекомендации к каждому товару
               - Интересуйся, какой товар больше понравился

            4. Когда клиент выбирает конкретный товар:
               - Используй get_product_details для получения подробной информации
               - Если нужно, уточни цвет и размер
               - Спроси о количестве
               - Добавь товар в корзину только после согласования всех деталей

            5. После добавления в корзину:
               - Предложи подходящие дополнительные товары
               - Спроси, хочет ли клиент продолжить выбор или оформить заказ

            6. При оформлении заказа:
               - Сначала проверь, есть ли данные пользователя в БД
               - Если данные есть, попроси подтвердить их
               - Если данных нет или они неверны, запроси ФИО и телефон
               - Уточни способ получения (доставка или самовывоз)
               - При выборе доставки запроси адрес
               - Подтверди все данные заказа перед его оформлением

            Важные моменты:
            - Общайся дружелюбно и неформально
            - ВСЕГДА задавай уточняющие вопросы при недостатке деталей в запросе
            - Рекомендуй только товары, максимально соответствующие запросу клиента
            - Предлагай альтернативы, если идеального соответствия нет
            - Формат цены указывай в сомах
            - Отвечай на русском языке или на языке клиента.
        """}
        ]
    }

    # Отправляем первое сообщение от бота
    # Using asyncio.to_thread for the synchronous OpenAI client
    response = await asyncio.to_thread(
        openai_client.chat.completions.create,
        model="gpt-4o-mini",
        messages=user_states[user_id]["chat_history"],
        tools=tools,
        tool_choice="auto"
    )

    ai_message = response.choices[0].message
    user_states[user_id]["chat_history"].append({"role": "assistant", "content": ai_message.content})

    await callback_query.message.answer(ai_message.content)


# Обработчик для всех текстовых сообщений
@ai_router.message()
async def process_message(message: Message):
    user_id = message.from_user.id
    user_text = message.text

    fake_callback = CallbackQuery(
        id="dummy_id",
        from_user=message.from_user,
        message=message,  # или другой объект сообщения, если нужно
        chat_instance="dummy_instance",
        data="user_consultation"
    )

    # Если пользователь не инициализирован (не вызвал /start)
    if user_id not in user_states:
        await cmd_start(fake_callback)
        return

    # Если ожидается ввод количества, обрабатываем его здесь
    if user_id in user_states and "waiting_for_quantity" in user_states[user_id]:
        try:
            quantity = int(user_text)
        except ValueError:
            await message.answer("Пожалуйста, введите корректное числовое значение для количества.")
            return

        product_id = user_states[user_id].pop("waiting_for_quantity")
        selected = user_states[user_id].get("selected_product", {})
        products = user_states[user_id].get("current_products", [])
        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await message.answer("Товар не найден")
            return

        selected["quantity"] = quantity
        result = await add_to_cart(
            user_id,
            product["name"],
            quantity,
            selected.get("color"),
            selected.get("size")
        )

        if result.get("status") == "success":
            # Очищаем выбранные параметры
            user_states[user_id]["selected_product"] = {}

            # Формируем сообщение о корзине
            cart = user_carts[user_id]
            total_amount = sum(item["total"] for item in cart)
            cart_message = "🛒 Ваша корзина:\n\n"
            for item in cart:
                cart_message += f"• {item['product_name']}\n"
                cart_message += f"  Цвет: {item.get('color', 'Не указан')}\n"
                cart_message += f"  Размер: {item.get('size', 'Не указан')}\n"
                cart_message += f"  Количество: {item['quantity']}\n"
                cart_message += f"  Цена: {item['price']} сом\n"
                cart_message += f"  Итого: {item['total']} сом\n\n"
            cart_message += f"Общая сумма: {total_amount} сом\n\n"
            cart_message += "Что бы вы хотели сделать?\n" \
                            "1. Продолжить покупки\n" \
                            "2. Оформить заказ"

            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🛍 Продолжить покупки", callback_data="continue_shopping")
            keyboard.button(text="✅ Оформить заказ", callback_data="checkout")
            await message.answer(cart_message, reply_markup=keyboard.as_markup())
        else:
            await message.answer(result.get("error", "Ошибка при добавлении в корзину"))
        return

    # Проверяем, ожидаем ли мы какие-то данные от пользователя
    if "waiting_for" in user_states[user_id]:
        waiting_for = user_states[user_id].pop("waiting_for")

        if waiting_for == "new_name":
            # Сохраняем новое имя и запрашиваем телефон
            user_states[user_id]["new_user_data"] = {"full_name": user_text}
            await message.answer("Пожалуйста, введите ваш номер телефона:")
            user_states[user_id]["waiting_for"] = "new_phone"
            return

        elif waiting_for == "new_phone":
            # Сохраняем номер телефона и спрашиваем о способе получения
            user_states[user_id]["new_user_data"]["phone"] = user_text

            # Создаем клавиатуру для выбора способа получения
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🚚 Доставка", callback_data="delivery:true")
            keyboard.button(text="🏪 Самовывоз", callback_data="delivery:false")

            await message.answer(
                "Как вы хотите получить заказ?",
                reply_markup=keyboard.as_markup()
            )
            return

        elif waiting_for == "delivery_address":
            # Сохраняем адрес, обновляем данные пользователя и оформляем заказ
            new_user_data = user_states[user_id].get("new_user_data", {})
            full_name = new_user_data.get("full_name", "")
            phone = new_user_data.get("phone", "")

            # Обновляем данные пользователя с адресом доставки
            await update_user_info(user_id, full_name, phone, user_text)

            # Оформляем заказ
            result = await complete_order(
                user_id=user_id,
                full_name=full_name,
                phone=phone,
                address=user_text,
                delivery=True
            )

            if result.get("status") == "success":
                order_info = result["order_info"]

                # Формируем текст для ИИ
                ai_prompt = (
                    "Заказ оформлен успешно. Вот детали заказа:\n"
                    f"ФИО: {order_info['user_info']['full_name']}\n"
                    f"Телефон: {order_info['user_info']['phone']}\n"
                    f"Адрес доставки: {order_info['user_info']['address']}\n"
                    f"Сумма заказа: {order_info['total_amount']} {order_info['currency']}\n\n"
                    "Пожалуйста, сформулируй короткое и дружелюбное сообщение для клиента, сообщив, что заказ оформлен, "
                    "и что менеджеры скоро свяжутся с ним для уточнения деталей доставки. В конце добавь благодарность за покупку."
                )

                # Отправляем запрос в ИИ
                ai_response = await asyncio.to_thread(
                    openai_client.chat.completions.create,
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Ты дружелюбный консультант магазина спортивной одежды."},
                        {"role": "user", "content": ai_prompt}
                    ],
                    max_tokens=200
                )

                final_message = ai_response.choices[0].message.content

                # Создаем клавиатуру с кнопкой "В личный кабинет"
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="⬅️ В личный кабинет", callback_data="go_to_user_dashboard")

                # Обновляем сообщение для клиента с добавлением кнопки
                await message.answer(
                    final_message,
                    reply_markup=keyboard.as_markup()
                )

                # Очищаем корзину и временные данные
                user_carts[user_id] = []
                user_states[user_id].pop("new_user_data", None)
            else:
                await message.answer(
                    result.get("message", "Произошла ошибка при оформлении заказа")
                )
            return

    # Добавляем сообщение пользователя в историю диалога
    user_states[user_id]["chat_history"].append({"role": "user", "content": user_text})

    try:
        # Отправляем запрос в OpenAI
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=user_states[user_id]["chat_history"],
            tools=tools,
            tool_choice="auto"
        )

        ai_message = response.choices[0].message
        tool_calls = ai_message.tool_calls

        # Если ИИ вызывает функцию
        if tool_calls:
            available_functions = {
                "get_products": get_products,
                "get_product_details": lambda params: get_product_details(params["product_name"]),
                "add_to_cart": lambda params: add_to_cart(user_id, **params),
                "complete_order": lambda params: complete_order(user_id, **params),
                "filter_products": lambda params: filter_products(params["user_query"], user_id),
                "get_related_products": lambda params: get_related_products(params["product_name"]),
                "get_user_info": lambda params: get_user_info(user_id),
                "update_user_info": lambda params: update_user_info(user_id, **params),
                "verify_user_data": lambda params: verify_user_data(user_id, **params)
            }

            # Сохраняем вызов инструмента в историю
            user_states[user_id]["chat_history"].append({
                "role": "assistant",
                "content": ai_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in tool_calls
                ]
            })

            # Обрабатываем все вызовы функций
            function_responses = []
            needs_clarification = False
            clarification_message = ""
            show_products_media_group = False
            products_to_show = []

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                function_to_call = available_functions[function_name]
                function_response = await function_to_call(function_args)

                # Сохраняем ответ функции
                function_responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(function_response, ensure_ascii=False)
                })

                # Проверяем результаты filter_products для специальной обработки
                if function_name == "filter_products":
                    # Если нужно уточнение
                    if function_response.get("needs_clarification"):
                        needs_clarification = True
                        clarification_message = function_response["message"]
                    # Если найдены точные совпадения - показываем их в виде карусели
                    elif function_response.get("exact_matches"):
                        show_products_media_group = True
                        products_to_show = function_response["recommended_products"]
                    # Если нет точных совпадений - показываем альтернативы в виде карусели
                    elif function_response.get("no_exact_match"):
                        show_products_media_group = True
                        products_to_show = function_response["alternatives"]

            # Добавляем все ответы функций в историю
            user_states[user_id]["chat_history"].extend(function_responses)

            # Если требуется уточнение, отправляем его напрямую
            if needs_clarification:
                # Сохраняем контекст поиска в состоянии пользователя
                if user_id not in user_states:
                    user_states[user_id] = {}
                user_states[user_id]["search_context"] = function_response.get("context", {})

                # Добавляем сообщение с уточнением в историю
                user_states[user_id]["chat_history"].append({
                    "role": "assistant",
                    "content": clarification_message
                })
                await message.answer(clarification_message)
                return

            # Если нужно показать товары в виде карусели
            if show_products_media_group and products_to_show:
                # Сохраняем текущие товары в состоянии пользователя
                user_states[user_id]["current_products"] = products_to_show

                # Создаем и отправляем карусель с первым товаром
                media, keyboard = await create_product_carousel(products_to_show)
                if media and keyboard:
                    await message.answer_photo(
                        photo=media.media,
                        caption=media.caption,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                else:
                    await message.answer("Извините, не удалось показать товары. Попробуйте еще раз.")

                return

            # Стандартная обработка для других случаев
            second_response = await asyncio.to_thread(
                openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=user_states[user_id]["chat_history"]
            )

            new_ai_message = second_response.choices[0].message
            user_states[user_id]["chat_history"].append({"role": "assistant", "content": new_ai_message.content})

            # Если это была функция get_product_details, нужно отправить фото товара
            send_text_message = True
            for tool_call in tool_calls:
                if tool_call.function.name == "get_product_details":
                    function_args = json.loads(tool_call.function.arguments)
                    product_details = await get_product_details(function_args["product_name"])

                    # Если есть фотографии, отправляем первую как изображение
                    if "photo_ids" in product_details and product_details["photo_ids"]:
                        try:
                            await bot.send_photo(
                                chat_id=user_id,
                                photo=product_details["photo_ids"][0],
                                caption=new_ai_message.content,
                                parse_mode="Markdown"
                            )
                            send_text_message = False
                            break
                        except Exception as e:
                            logger.error(f"Ошибка при отправке фото: {e}")
                            send_text_message = True

            # Отправляем текстовый ответ пользователю только если не отправили фото с подписью
            if send_text_message:
                await message.answer(new_ai_message.content)

        # Если ИИ не вызывает функцию, просто отправляем сообщение
        else:
            user_states[user_id]["chat_history"].append({"role": "assistant", "content": ai_message.content})
            await message.answer(ai_message.content)

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer(
            "Извините, произошла небольшая техническая заминка. Давайте попробуем еще раз? Пожалуйста, повторите ваш вопрос.")


async def create_product_carousel(products: List[Dict], product_index: int = 0, photo_index: int = 0) -> tuple[
    InputMediaPhoto, InlineKeyboardMarkup]:
    """Создает карусель товаров с кнопками навигации по товарам и фотографиям"""
    if not products:
        return None, None

    product = products[product_index]
    photos = product.get("photo_ids", [])
    if not photos:
        return None, None

    # Определяем фото для отображения
    current_photo = photos[photo_index]

    # Создаем основную клавиатуру
    keyboard = InlineKeyboardBuilder()

    # Если у товара несколько фотографий, добавляем навигацию по фото (отдельный ряд)
    if len(photos) > 1:
        photo_nav = InlineKeyboardBuilder()
        if photo_index > 0:
            photo_nav.button(text="◀️ Фото",
                             callback_data=f"photo:prev:{product['id']}:{product_index}:{photo_index}")
        if photo_index < len(photos) - 1:
            photo_nav.button(text="Фото ▶️",
                             callback_data=f"photo:next:{product['id']}:{product_index}:{photo_index}")
        # Добавляем как отдельный ряд в начале
        keyboard.row(*photo_nav.as_markup().inline_keyboard[0])

        # Далее формируем ряд для навигации по товарам и добавления в корзину
    nav_builder = InlineKeyboardBuilder()
    if product_index > 0:
        nav_builder.button(text="◀️ Товар", callback_data=f"carousel:prev:{product_index}:{photo_index}")
    nav_builder.button(text="🛒 Выбрать", callback_data=f"add_to_cart:{product['id']}")
    if product_index < len(products) - 1:
        nav_builder.button(text="Товар ▶️", callback_data=f"carousel:next:{product_index}:{photo_index}")
    keyboard.row(*nav_builder.as_markup().inline_keyboard[0])

    # Формируем подпись: можно добавить рекомендацию, цену и т.д.
    caption = f"*{product['name']}*\n" \
              f"Цена: {product['price']} сом\n" \
              f"{product.get('recommendation_reason', '')}\n\n" \
              f"Для добавления в корзину нажмите кнопку ниже."

    media = InputMediaPhoto(
        media=current_photo,
        caption=caption,
        parse_mode="Markdown"
    )

    return media, keyboard.as_markup()


# Обработчик для callback-запросов
@ai_router.callback_query()
async def process_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if "selected_product" not in user_states[user_id]:
        user_states[user_id]["selected_product"] = {}
    data = callback.data

    try:
        if data.startswith("photo:"):
            # Формат callback_data: photo:prev:<product_id>:<product_index>:<photo_index>
            _, direction, prod_id, prod_index, photo_index = data.split(":")
            prod_index = int(prod_index)
            photo_index = int(photo_index)
            products = user_states[user_id].get("current_products", [])
            if not products:
                await callback.answer("Товары не найдены")
                return
            product = next((p for p in products if p["id"] == int(prod_id)), None)
            if not product:
                await callback.answer("Товар не найден")
                return
            photos = product.get("photo_ids", [])
            if direction == "prev":
                new_photo_index = photo_index - 1 if photo_index > 0 else photo_index
            else:
                new_photo_index = photo_index + 1 if photo_index < len(photos) - 1 else photo_index

            media, keyboard = await create_product_carousel(products, prod_index, new_photo_index)
            if media and keyboard:
                await callback.message.edit_media(media=media, reply_markup=keyboard)
                await callback.answer()
            else:
                await callback.answer("Ошибка при обновлении фото")
            return

        if data.startswith("carousel:"):
            # Обработка навигации по товарам
            _, direction, prod_index, photo_index = data.split(":")
            prod_index = int(prod_index)
            photo_index = int(photo_index)
            products = user_states[user_id].get("current_products", [])
            if not products:
                await callback.answer("Товары не найдены")
                return
            if direction == "prev":
                new_index = prod_index - 1 if prod_index > 0 else prod_index
            else:
                new_index = prod_index + 1 if prod_index < len(products) - 1 else prod_index
            # При переключении товара можно начать с первой фотографии
            media, keyboard = await create_product_carousel(products, new_index, 0)
            if media and keyboard:
                await callback.message.edit_media(media=media, reply_markup=keyboard)
                await callback.answer()
            else:
                await callback.answer("Ошибка при обновлении карусели")
            return

        elif data.startswith("add_to_cart:"):
            # Обработка добавления в корзину
            product_id = int(data.split(":")[1])
            products = user_states[user_id].get("current_products", [])

            # Находим товар по ID
            product = next((p for p in products if p["id"] == product_id), None)
            if not product:
                await callback.answer("Товар не найден")
                return

            # Получаем информацию о товаре для проверки доступных параметров
            product_details = await get_product_details(product["name"])

            # Создаем клавиатуру с кнопками для выбора цвета
            keyboard = InlineKeyboardBuilder()

            # Если есть варианты цветов, показываем их
            if product_details.get("available_colors"):
                keyboard = InlineKeyboardBuilder()

                for color in product_details["available_colors"]:
                    keyboard.button(
                        text=f"{color['name']}",
                        callback_data=f"select_color:{product_id}:{color['name']}"
                    )
                keyboard.adjust(2)  # по 2 кнопки в ряду
                await callback.message.edit_caption(
                    caption=f"*{product['name']}*\n"
                            f"Цена: {product['price']} сом\n\n"
                            f"Пожалуйста, выберите цвет:",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
            else:
                # Если цветов нет, сразу переходим к выбору размера
                await process_size_selection(callback, product_id, product)

        elif data.startswith("select_color:"):
            # Обработка выбора цвета
            _, product_id, color = data.split(":")
            product_id = int(product_id)
            products = user_states[user_id].get("current_products", [])
            product = next((p for p in products if p["id"] == product_id), None)

            if not product:
                await callback.answer("Товар не найден")
                return

            # Сохраняем выбранный цвет
            if "selected_product" not in user_states[user_id]:
                user_states[user_id]["selected_product"] = {}
            user_states[user_id]["selected_product"]["color"] = color

            # Переходим к выбору размера
            await process_size_selection(callback, product_id, product)

        elif data.startswith("select_size:"):
            # Обработка выбора размера
            _, product_id, size = data.split(":")
            product_id = int(product_id)
            products = user_states[user_id].get("current_products", [])
            product = next((p for p in products if p["id"] == product_id), None)

            if not product:
                await callback.answer("Товар не найден")
                return

            # Сохраняем выбранный размер
            if "selected_product" not in user_states[user_id]:
                user_states[user_id]["selected_product"] = {}
            user_states[user_id]["selected_product"]["size"] = size
            user_states[user_id]["selected_product"]["product_id"] = product_id

            await callback.message.edit_caption(
                caption=f"*{product['name']}*\n"
                        f"Цена: {product['price']} сом\n"
                        f"Выбранный цвет: {user_states[user_id]['selected_product'].get('color', 'Не указан')}\n"
                        f"Выбранный размер: {size}\n\n"
                        f"Пожалуйста, введите количество:",
                parse_mode="Markdown"
            )
            # Устанавливаем ожидание ввода количества
            user_states[user_id]["waiting_for_quantity"] = product_id

        elif data.startswith("select_quantity:"):
            # Обработка выбора количества
            _, product_id, quantity = data.split(":")
            product_id = int(product_id)
            quantity = int(quantity)
            products = user_states[user_id].get("current_products", [])
            product = next((p for p in products if p["id"] == product_id), None)

            if not product:
                await callback.answer("Товар не найден")
                return

            # Сохраняем выбранное количество
            if "selected_product" not in user_states[user_id]:
                user_states[user_id]["selected_product"] = {}
            user_states[user_id]["selected_product"]["quantity"] = quantity

            # Добавляем товар в корзину
            result = await add_to_cart(
                user_id=user_id,
                product_name=product["name"],
                quantity=quantity,
                color=user_states[user_id]["selected_product"].get("color"),
                size=user_states[user_id]["selected_product"].get("size")
            )

            if result.get("status") == "success":
                # Удаляем сообщение с каруселью
                await callback.message.delete()

                # Очищаем выбранные параметры
                user_states[user_id]["selected_product"] = {}

                # Формируем сообщение о корзине
                cart = user_carts[user_id]
                total_amount = sum(item["total"] for item in cart)

                cart_message = "🛒 Ваша корзина:\n\n"
                for item in cart:
                    cart_message += f"• {item['product_name']}\n"
                    cart_message += f"  Цвет: {item.get('color', 'Не указан')}\n"
                    cart_message += f"  Размер: {item.get('size', 'Не указан')}\n"
                    cart_message += f"  Количество: {item['quantity']}\n"
                    cart_message += f"  Цена: {item['price']} сом\n"
                    cart_message += f"  Итого: {item['total']} сом\n\n"
                cart_message += f"Общая сумма: {total_amount} сом\n\n"
                cart_message += "Что бы вы хотели сделать?\n"
                cart_message += "1. Продолжить покупки\n"
                cart_message += "2. Оформить заказ"

                # Создаем клавиатуру с кнопками
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="🛍 Продолжить покупки", callback_data="continue_shopping")
                keyboard.button(text="✅ Оформить заказ", callback_data="checkout")

                # Отправляем сообщение с корзиной
                await callback.message.answer(
                    cart_message,
                    reply_markup=keyboard.as_markup()
                )

                # Добавляем сообщение в историю диалога
                user_states[user_id]["chat_history"].append({
                    "role": "assistant",
                    "content": cart_message
                })

                await callback.answer("Товар добавлен в корзину!")
            else:
                await callback.answer(result.get("error", "Ошибка при добавлении в корзину"))

        elif data == "continue_shopping":
            # Очищаем состояние текущих товаров
            user_states[user_id].pop("current_products", None)

            # Сохраняем предыдущие выборы пользователя
            previous_selections = user_states[user_id].get("selected_product", {})

            # Формируем контекст для ИИ с учетом предыдущих выборов
            ai_context = "Клиент хочет продолжить покупки. "
            if previous_selections:
                details = []
                if "color" in previous_selections:
                    details.append(f"цвет: {previous_selections['color']}")
                if "size" in previous_selections:
                    details.append(f"размер: {previous_selections['size']}")
                if details:
                    ai_context += f"Ранее клиент выбирал {', '.join(details)}. "

            # Отправляем запрос в OpenAI
            response = await asyncio.to_thread(
                openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": "Ты дружелюбный консультант магазина спортивной одежды. Твоя задача - помочь клиенту продолжить покупки, учитывая его предыдущие предпочтения."},
                    {"role": "user", "content": ai_context}
                ]
            )

            # Получаем ответ от ИИ
            ai_message = response.choices[0].message.content

            # Обновляем сообщение с ответом ИИ
            await callback.message.edit_text(ai_message)
            await callback.answer()


        elif data == "checkout":
            # Начинаем процесс оформления заказа
            result = await complete_order(user_id)
            if result.get("needs_details"):
                await callback.message.edit_text(
                    result["message"],
                    reply_markup=None
                )
            elif result.get("user_data_exists"):
                # Если у пользователя есть данные, показываем их для подтверждения
                user_info = result["user_info"]
                cart_summary = result["cart_summary"]

                message = f"Проверьте, пожалуйста, ваши данные:\n\n"
                message += f"ФИО: {user_info['full_name']}\n"
                message += f"Телефон: {user_info['phone']}\n"
                message += f"Адрес: {user_info['address']}\n\n"
                message += "Всё верно?"

                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="✅ Да, всё верно", callback_data="verify_data:true")
                keyboard.button(text="❌ Нет, изменить", callback_data="verify_data:false")

                await callback.message.edit_text(
                    message,
                    reply_markup=keyboard.as_markup()
                )
            await callback.answer()

        elif data.startswith("verify_data:"):
            # Обработка подтверждения данных пользователя
            _, is_correct = data.split(":")
            is_correct = is_correct.lower() == "true"

            # Получаем информацию о пользователе
            user_info = await get_user_info(user_id)

            # Проверяем наличие корзины
            if user_id not in user_carts or not user_carts[user_id]:
                await callback.message.edit_text("Ваша корзина пуста")
                await callback.answer()
                return

            if is_correct:
                # Если данные верны, продолжаем оформление заказа
                result = await verify_user_data(
                    user_id=user_id,
                    is_correct=True,
                    delivery=True if user_info.get("address") else False
                )

                if result.get("status") == "success":
                    # Вместо фиксированного сообщения, отправляем заказ в ИИ для генерации финального ответа
                    order_info = result["order_info"]

                    # Формируем текстовый запрос с деталями заказа для ИИ
                    ai_prompt = (
                        "Заказ оформлен успешно. Вот детали заказа:\n"
                        f"ФИО: {order_info['user_info']['full_name']}\n"
                        f"Телефон: {order_info['user_info']['phone']}\n"
                        f"Способ получения: {order_info['user_info']['address'] if order_info['user_info']['address'] else 'Самовывоз'}\n"
                        f"Сумма заказа: {order_info['total_amount']} {order_info['currency']}\n\n"
                        "Пожалуйста, сформулируй дружелюбное сообщение для клиента, сообщив, что заказ оформлен, "
                        "и что менеджеры скоро свяжутся с ним. В конце добавь благодарность за покупку."
                    )

                    # Отправляем запрос в ИИ (используем asyncio.to_thread для вызова синхронного клиента)
                    ai_response = await asyncio.to_thread(
                        openai_client.chat.completions.create,
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Ты дружелюбный консультант магазина спортивной одежды."},
                            {"role": "user", "content": ai_prompt}
                        ],
                        max_tokens=200
                    )

                    final_message = ai_response.choices[0].message.content

                    # Создаем клавиатуру с кнопкой "В личный кабинет"
                    keyboard = InlineKeyboardBuilder()
                    keyboard.button(text="⬅️ В личный кабинет", callback_data="go_to_user_dashboard")

                    # Обновляем сообщение для клиента с добавлением кнопки
                    await callback.message.edit_text(
                        final_message,
                        reply_markup=keyboard.as_markup()
                    )

                    # Очищаем корзину пользователя
                    user_carts[user_id] = []
                else:
                    await callback.message.edit_text(
                        result.get("message", "Произошла ошибка при оформлении заказа")
                    )
            else:
                # Если данные неверны, запрашиваем новые
                await callback.message.edit_text(
                    "Пожалуйста, введите ваше полное имя:"
                )
                # Устанавливаем состояние для ожидания нового имени
                user_states[user_id]["waiting_for"] = "new_name"

            await callback.answer()

        elif data.startswith("delivery:"):
            # Обработка выбора способа доставки
            _, is_delivery = data.split(":")
            is_delivery = is_delivery.lower() == "true"

            # Получаем сохраненные данные пользователя
            new_user_data = user_states[user_id].get("new_user_data", {})
            full_name = new_user_data.get("full_name", "")
            phone = new_user_data.get("phone", "")

            if is_delivery:
                # Если выбрана доставка, запрашиваем адрес
                await callback.message.edit_text("Пожалуйста, введите адрес доставки:")
                user_states[user_id]["waiting_for"] = "delivery_address"
            else:
                # Если выбран самовывоз, обновляем данные пользователя и оформляем заказ
                await update_user_info(user_id, full_name, phone, "")

                # Оформляем заказ
                result = await complete_order(
                    user_id=user_id,
                    full_name=full_name,
                    phone=phone,
                    address="",
                    delivery=False
                )

                if result.get("status") == "success":
                    order_info = result["order_info"]

                    # Формируем текст для ИИ
                    ai_prompt = (
                        "Заказ оформлен успешно. Вот детали заказа:\n"
                        f"ФИО: {order_info['user_info']['full_name']}\n"
                        f"Телефон: {order_info['user_info']['phone']}\n"
                        f"Способ получения: Самовывоз\n"
                        f"Сумма заказа: {order_info['total_amount']} {order_info['currency']}\n\n"
                        "Пожалуйста, сформулируй дружелюбное сообщение для клиента, сообщив, что заказ оформлен, "
                        "и что менеджеры скоро свяжутся с ним для уточнения деталей самовывоза. В конце добавь благодарность за покупку."
                    )

                    # Отправляем запрос в ИИ
                    ai_response = await asyncio.to_thread(
                        openai_client.chat.completions.create,
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Ты дружелюбный консультант магазина спортивной одежды."},
                            {"role": "user", "content": ai_prompt}
                        ],
                        max_tokens=200
                    )

                    final_message = ai_response.choices[0].message.content

                    # Создаем клавиатуру с кнопкой "В личный кабинет"
                    keyboard = InlineKeyboardBuilder()
                    keyboard.button(text="⬅️ В личный кабинет", callback_data="go_to_user_dashboard")

                    # Обновляем сообщение для клиента с добавлением кнопки
                    await callback.message.edit_text(
                        final_message,
                        reply_markup=keyboard.as_markup()
                    )

                    # Очищаем корзину и временные данные
                    user_carts[user_id] = []
                    user_states[user_id].pop("new_user_data", None)
                else:
                    await callback.message.edit_text(
                        result.get("message", "Произошла ошибка при оформлении заказа")
                    )

            await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")


async def process_size_selection(callback: CallbackQuery, product_id: int, product: dict):
    """Вспомогательная функция для обработки выбора размера"""
    if "selected_product" not in user_states[callback.from_user.id]:
        user_states[callback.from_user.id]["selected_product"] = {}

    product_details = await get_product_details(product["name"])
    keyboard = InlineKeyboardBuilder()
    if product_details.get("available_sizes"):
        for size in product_details["available_sizes"]:
            keyboard.button(
                text=f"{size['size']}",
                callback_data=f"select_size:{product_id}:{size['size']}"
            )
        keyboard.adjust(4)  # по 4 кнопки в ряду
        await callback.message.edit_caption(
            caption=f"*{product['name']}*\n"
                    f"Цена: {product['price']} сом\n"
                    f"Выбранный цвет: {user_states[callback.from_user.id]['selected_product'].get('color', 'Не указан')}\n\n"
                    f"Пожалуйста, выберите размер:",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # Если размеров нет, сразу переходим к выбору количества
        keyboard = InlineKeyboardBuilder()
        for qty in [1, 2, 3, 4, 5]:
            keyboard.button(
                text=f"Количество: {qty}",
                callback_data=f"select_quantity:{product_id}:{qty}"
            )

        await callback.message.edit_caption(
            caption=f"*{product['name']}*\n"
                    f"Цена: {product['price']} сом\n"
                    f"Выбранный цвет: {user_states[callback.from_user.id]['selected_product'].get('color', 'Не указан')}\n\n"
                    f"Выберите количество:",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )