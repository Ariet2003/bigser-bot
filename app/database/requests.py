from typing import Optional, List, Dict
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import async_session, BroadcastHistory, ProductPhoto, OrderGroup
from app.database.models import Color, Category, User, Product, Subcategory, Size, Order, OrderItem
from app.users.user import userKeyboards as kb
from sqlalchemy.exc import SQLAlchemyError
from bot_instance import bot
from sqlalchemy import select, delete, cast, String, literal
from datetime import datetime
from sqlalchemy import update
import random
from sqlalchemy import select, func, cast, String, literal
from datetime import date, datetime, timedelta
import calendar
from sqlalchemy import func, distinct
from datetime import datetime, timedelta
from sqlalchemy import Numeric
from sqlalchemy import or_
from sqlalchemy import Float
from sqlalchemy.orm import aliased
from sqlalchemy import select, desc, insert, and_
import pytz
import json


async def check_role(telegram_id: str) -> str:
    async with async_session() as session:
        result = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if result is not None:
            return result.role
        else:
            new_user = User(telegram_id=telegram_id, role="USER")
            session.add(new_user)
            await session.commit()
            return "USER"

async def add_or_update_user(telegram_id: str, full_name: str, role: str) -> bool:
    try:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is not None:
                # Обновляем данные существующего пользователя
                user.full_name = full_name
                user.role = role
            else:
                # Добавляем нового пользователя
                new_user = User(telegram_id=telegram_id, full_name=full_name, role=role)
                session.add(new_user)
            await session.commit()
            return True
    except Exception as e:
        print(f"Ошибка при добавлении/обновлении пользователя: {e}")
        return False

async def get_users_by_role(role: str) -> str:
    async with async_session() as session:
        result = await session.execute(
            select(User.id, User.full_name).where(User.role == role)
        )
        users = [{"id": user_id, "full_name": full_name} for user_id, full_name in result.all()]
        return json.dumps(users, ensure_ascii=False)

async def get_admins_by_page(page: int, per_page: int = 10) -> List[Dict]:
    async with async_session() as session:
        query = select(User.id, User.full_name).where(User.role == "ADMIN")\
                    .limit(per_page).offset((page - 1) * per_page)
        result = await session.execute(query)
        admins = [{"id": admin_id, "full_name": full_name} for admin_id, full_name in result.all()]
        return admins

async def get_total_admins() -> int:
    async with async_session() as session:
        query = select(func.count()).select_from(User).where(User.role == "ADMIN")
        total = await session.scalar(query)
        return total

async def get_admin_by_id(admin_id: int) -> Optional[Dict]:
    async with async_session() as session:
        query = select(User).where(User.id == admin_id)
        admin = await session.scalar(query)
        if admin:
            return {"id": admin.id, "full_name": admin.full_name, "role": admin.role}
        return None

async def update_admin_fullname(admin_id: int, new_fullname: str) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                update(User).where(User.id == admin_id).values(full_name=new_fullname)
            )
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении ФИО: {e}")
            await session.rollback()
            return False

async def update_admin_role(admin_id: int, new_role: str) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                update(User).where(User.id == admin_id).values(role=new_role)
            )
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении роли: {e}")
            await session.rollback()
            return False

async def get_managers_by_page(page: int, per_page: int = 10) -> List[Dict]:
    async with async_session() as session:
        query = select(User.id, User.full_name).where(User.role == "MANAGER")\
                    .limit(per_page).offset((page - 1) * per_page)
        result = await session.execute(query)
        managers = [{"id": manager_id, "full_name": full_name} for manager_id, full_name in result.all()]
        return managers

async def get_total_managers() -> int:
    async with async_session() as session:
        query = select(func.count()).select_from(User).where(User.role == "MANAGER")
        total = await session.scalar(query)
        return total

async def get_manager_by_id(manager_id: int) -> Optional[Dict]:
    async with async_session() as session:
        query = select(User).where(User.id == manager_id)
        manager = await session.scalar(query)
        if manager:
            return {"id": manager.id, "full_name": manager.full_name, "role": manager.role}
        return None

async def update_manager_fullname(manager_id: int, new_fullname: str) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                update(User).where(User.id == manager_id).values(full_name=new_fullname)
            )
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении ФИО: {e}")
            await session.rollback()
            return False

async def update_manager_role(manager_id: int, new_role: str) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                update(User).where(User.id == manager_id).values(role=new_role)
            )
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении роли: {e}")
            await session.rollback()
            return False


async def get_user_by_id(user_id: int) -> Optional[Dict]:
    async with async_session() as session:
        query = select(User).where(User.id == user_id)
        user = await session.scalar(query)
        if user:
            return {"id": user.id, "full_name": user.full_name, "role": user.role}
        return None


async def delete_user_by_id(user_id: int) -> bool:
    async with async_session() as session:
        try:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при удалении сотрудника: {e}")
            await session.rollback()
            return False


async def get_categories_by_page(page: int, per_page: int = 10) -> List[Dict]:
    async with async_session() as session:
        query = select(Category.id, Category.name).limit(per_page).offset((page - 1) * per_page)
        result = await session.execute(query)
        categories = [{"id": cat_id, "name": name} for cat_id, name in result.all()]
        return categories

async def get_total_categories() -> int:
    async with async_session() as session:
        query = select(func.count()).select_from(Category)
        total = await session.scalar(query)
        return total

async def get_category_by_id(category_id: int) -> Optional[Dict]:
    async with async_session() as session:
        query = select(Category).where(Category.id == category_id)
        category = await session.scalar(query)
        if category:
            return {"id": category.id, "name": category.name}
        return None

async def update_category_name(category_id: int, new_name: str) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                update(Category).where(Category.id == category_id).values(name=new_name)
            )
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении названия категории: {e}")
            await session.rollback()
            return False

async def add_category(name: str) -> bool:
    async with async_session() as session:
        try:
            new_category = Category(name=name)
            session.add(new_category)
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении категории: {e}")
            await session.rollback()
            return False

async def delete_category(category_id: int) -> bool:
    async with async_session() as session:
        try:
            await session.execute(delete(Category).where(Category.id == category_id))
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при удалении категории: {e}")
            await session.rollback()
            return False


async def get_subcategories_by_page(page: int, per_page: int = 10) -> List[Dict]:
    async with async_session() as session:
        query = (
            select(Subcategory.id, Subcategory.name, Category.name)
            .join(Category, Subcategory.category_id == Category.id)
            .limit(per_page)
            .offset((page - 1) * per_page)
        )
        result = await session.execute(query)
        subcategories = [
            {"id": s_id, "name": s_name, "category_name": cat_name}
            for s_id, s_name, cat_name in result.all()
        ]
        return subcategories

async def get_total_subcategories() -> int:
    async with async_session() as session:
        query = select(func.count()).select_from(Subcategory)
        total = await session.scalar(query)
        return total

async def get_subcategory_by_id(subcategory_id: int) -> Optional[Dict]:
    async with async_session() as session:
        query = (
            select(Subcategory, Category.name)
            .join(Category, Subcategory.category_id == Category.id)
            .where(Subcategory.id == subcategory_id)
        )
        result = await session.execute(query)
        row = result.first()
        if row:
            subcat, cat_name = row
            return {"id": subcat.id, "name": subcat.name, "category_id": subcat.category_id, "category_name": cat_name}
        return None

async def update_subcategory(subcategory_id: int, new_name: str, parent_category_id: int) -> bool:
    async with async_session() as session:
        try:
            values = {"category_id": parent_category_id}
            if new_name:
                values["name"] = new_name
            await session.execute(
                update(Subcategory).where(Subcategory.id == subcategory_id).values(**values)
            )
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении подкатегории: {e}")
            await session.rollback()
            return False

async def add_subcategory(name: str, parent_category_id: int) -> bool:
    async with async_session() as session:
        try:
            new_subcat = Subcategory(name=name, category_id=parent_category_id)
            session.add(new_subcat)
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении подкатегории: {e}")
            await session.rollback()
            return False

async def delete_subcategory(subcategory_id: int) -> bool:
    async with async_session() as session:
        try:
            await session.execute(delete(Subcategory).where(Subcategory.id == subcategory_id))
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при удалении подкатегории: {e}")
            await session.rollback()
            return False


async def get_all_products() -> list:
    async with async_session() as session:
        try:
            result = await session.execute(
                select(Product).options(selectinload(Product.photos))
            )
            # Не используем await для all(), так как в вашем окружении он уже возвращает список
            products = result.scalars().all()
            result_list = []
            for product in products:
                # Принудительно получаем все связанные объекты, чтобы избежать ленивой загрузки позже
                photos = list(product.photos)
                result_list.append({
                    "id": product.id,
                    "name": product.name,
                    "price": float(product.price),
                    "color_ids": product.color_ids,
                    "size_ids": product.size_ids,
                    "description": product.description,
                    "product_type": product.product_type,
                    "material": product.material,
                    "features": product.features,
                    "usage": product.usage,
                    "temperature_range": product.temperature_range,
                    "subcategory_id": product.subcategory_id,
                    "photo_file_ids": [photo.file_id for photo in photos]
                })
            return result_list
        except Exception as e:
            print(f"Ошибка при получении товаров: {e}")
            return []


async def get_all_colors() -> list:
    async with async_session() as session:
        try:
            result = await session.execute(select(Color))
            colors = result.scalars().all()
            return [{"id": color.id, "name": color.name} for color in colors]
        except Exception as e:
            print(f"Ошибка при получении цветов: {e}")
            return []


async def get_all_sizes() -> list:
    async with async_session() as session:
        try:
            result = await session.execute(select(Size))
            sizes = result.scalars().all()
            return [{"id": size.id, "size": size.size} for size in sizes]
        except Exception as e:
            print(f"Ошибка при получении размеров: {e}")
            return []


async def get_all_subcategories() -> list:
    async with async_session() as session:
        try:
            stmt = select(Subcategory, Category).join(Category, Subcategory.category_id == Category.id)
            result = await session.execute(stmt)
            rows = result.all()
            subcategories = []
            for subcat, cat in rows:
                subcategories.append({
                    "id": subcat.id,
                    "name": subcat.name,
                    "category_id": subcat.category_id,
                    "category_name": cat.name
                })
            return subcategories
        except Exception as e:
            print(f"Ошибка при получении подкатегорий: {e}")
            return []


async def update_product(product_id: int, product_data: dict) -> bool:
    async with async_session() as session:
        try:
            await session.execute(
                update(Product).where(Product.id == product_id).values(**product_data)
            )
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении продукта {product_id}: {e}")
            await session.rollback()
            return False


async def add_product(product_data: dict) -> Optional[int]:
    async with async_session() as session:
        try:
            new_product = Product(**product_data)
            session.add(new_product)
            await session.commit()
            return new_product.id
        except Exception as e:
            print(f"Ошибка при добавлении продукта: {e}")
            await session.rollback()
            return None


async def get_product_by_id(product_id: int):
    async with async_session() as session:
        try:
            result = await session.execute(
                select(Product)
                .options(selectinload(Product.photos))
                .where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()
            return product
        except Exception as e:
            print(f"Ошибка при получении продукта {product_id}: {e}")
            return None


async def delete_product(product_id: int) -> bool:
    async with async_session() as session:
        try:
            await session.execute(delete(Product).where(Product.id == product_id))
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при удалении продукта {product_id}: {e}")
            await session.rollback()
            return False


async def update_product_photos(product_id: int, file_ids: List[str]) -> bool:
    async with async_session() as session:
        try:
            # Удаляем все существующие фото для данного товара
            await session.execute(delete(ProductPhoto).where(ProductPhoto.product_id == product_id))
            # Добавляем новые записи для каждого file_id
            for file_id in file_ids:
                new_photo = ProductPhoto(file_id=file_id, product_id=product_id)
                session.add(new_photo)
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении фотографий для продукта {product_id}: {e}")
            await session.rollback()
            return False


async def get_all_managers() -> list:
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.role == "MANAGER"))
            managers = result.scalars().all()
            return [{"id": manager.id, "name": manager.full_name or "Manager"} for manager in managers]
        except Exception as e:
            print(f"Ошибка при получении менеджеров: {e}")
            return []


async def get_manager_by_id(manager_id: int) -> dict:
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.id == manager_id))
            manager = result.scalars().first()
            if manager:
                return {"id": manager.id, "full_name": manager.full_name, "role": manager.role}
            return None
        except Exception as e:
            print(f"Ошибка при получении менеджера {manager_id}: {e}")
            return None


async def get_report_data(filters: dict) -> dict:
    async with async_session() as session:
        try:
            conditions = []

            # Фильтр по менеджеру (Order.processed_by_id)
            manager_filter = filters.get("manager", "all")
            if manager_filter != "all":
                try:
                    conditions.append(Order.processed_by_id == int(manager_filter))
                except Exception as e:
                    print(f"Ошибка преобразования менеджера: {e}")

            # Фильтр по статусу
            status_filter = filters.get("status", "all")
            if status_filter not in ("all", "все статусы"):
                mapping = {
                    "Принятый": "Принято",
                    "Отмененный": "Отменено"
                }
                status_filter_db = mapping.get(status_filter, status_filter)
                conditions.append(Order.status == status_filter_db)

            # Фильтр по дате (order_datetime)
            date_filter = filters.get("date", "all")
            if date_filter != "all":
                today = date.today()
                if date_filter == "week":
                    start_date = today - timedelta(days=today.weekday())
                    end_date = start_date + timedelta(days=6)
                elif date_filter == "month":
                    start_date = today.replace(day=1)
                    last_day = calendar.monthrange(today.year, today.month)[1]
                    end_date = today.replace(day=last_day)
                elif date_filter == "year":
                    start_date = today.replace(month=1, day=1)
                    end_date = today.replace(month=12, day=31)
                else:
                    try:
                        # Ожидается формат "ДД.ММ.ГГГГ - ДД.ММ.ГГГГ"
                        start_date_str, end_date_str = date_filter.split(" - ")
                        start_date = datetime.strptime(start_date_str.strip(), "%d.%m.%Y").date()
                        end_date = datetime.strptime(end_date_str.strip(), "%d.%m.%Y").date()
                    except Exception as e:
                        print(f"Ошибка при разборе пользовательского периода: {e}")
                        start_date = None
                        end_date = None
                if start_date and end_date:
                    start_dt = datetime.combine(start_date, datetime.min.time())
                    end_dt = datetime.combine(end_date, datetime.max.time())
                    conditions.append(Order.order_datetime.between(start_dt, end_dt))

            # Формирование строки товара: "Product.name || ' (' || OrderItem.quantity || ')'"
            product_text = (
                Product.name
                .op("||")(literal(" ("))
                .op("||")(cast(OrderItem.quantity, String))
                .op("||")(literal(")"))
            )

            stmt = (
                select(
                    Order.id,
                    Order.order_datetime,
                    func.coalesce(User.full_name, "Не назначен").label("manager_name"),
                    Order.status,
                    Order.delivery_method,
                    Order.payment_method,
                    func.coalesce(
                        func.sum(OrderItem.quantity * Product.price),
                        0
                    ).label("total_amount"),
                    func.coalesce(func.group_concat(product_text, literal(", ")), '').label("products")
                )
                .outerjoin(OrderItem, Order.id == OrderItem.order_id)
                .outerjoin(Product, OrderItem.product_id == Product.id)
                .outerjoin(User, Order.processed_by_id == User.id)
                .where(*conditions)
                .group_by(Order.id)
            )

            result = await session.execute(stmt)
            rows = result.all()

            orders_list = []
            for row in rows:
                order_id, order_datetime, manager_name, status, delivery_method, payment_method, total_amount, products = row
                if isinstance(order_datetime, datetime):
                    order_datetime = order_datetime.strftime("%Y-%m-%d %H:%M:%S")
                orders_list.append({
                    "id": order_id,
                    "order_datetime": order_datetime,
                    "manager_name": manager_name,
                    "status": status,
                    "delivery_method": delivery_method,
                    "payment_method": payment_method,
                    "total_amount": float(total_amount),
                    "products": products
                })

            data = {
                "total_orders": len(orders_list),
                "orders": orders_list
            }
            return data

        except Exception as e:
            print(f"Ошибка при получении данных отчёта: {e}")
            return {}


async def get_manager_fullname(manager_filter: str) -> str:
    """
    Получает ФИО менеджера по его id.

    Параметры:
      manager_filter: строковое значение, содержащее id менеджера.

    Возвращает:
      ФИО менеджера, если найдено, иначе "Не назначен" или исходное значение фильтра.
    """
    async with async_session() as session:
        try:
            manager_obj = await session.get(User, int(manager_filter))
            if manager_obj and manager_obj.full_name:
                return manager_obj.full_name
            else:
                return "Не назначен"
        except Exception as e:
            print(f"Ошибка получения ФИО менеджера: {e}")
            return str(manager_filter)


async def update_user_full_name(user_id: str, full_name: str) -> bool:
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalars().first()
            if user:
                user.full_name = full_name
                await session.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка при обновлении ФИО для пользователя {user_id}: {e}")
            return False


async def get_user_info_by_id(user_id: str) -> dict:
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalars().first()
            if user:
                # Если какое-либо поле равно None, возвращаем "Не указано"
                return {
                    "id": user.id,
                    "full_name": user.full_name if user.full_name is not None else "Не указано",
                    "address": user.address if user.address is not None else "Не указано",
                    "phone_number": user.phone_number if user.phone_number is not None else "Не указано"
                }
            return {"answer": "Пользователь не найден"}
        except Exception as e:
            print(f"Ошибка при получении данных пользователя {user_id}: {e}")
            return {"answer": "Ошибка"}


async def update_user_phone(user_id: str, phone: str) -> bool:
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalars().first()
            if user:
                user.phone_number = phone
                await session.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка при обновлении номера телефона для пользователя {user_id}: {e}")
            return False


async def update_user_address(user_id: str, address: str) -> bool:
    async with async_session() as session:
        try:
            result = await session.execute(select(User).where(User.telegram_id == user_id))
            user = result.scalars().first()
            if user:
                user.address = address
                await session.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка при обновлении адреса для пользователя {user_id}: {e}")
            return False


# Запрос всех пользователей для рассылки
async def get_all_users():
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        return [row[0] for row in result.all()]

# Запрос для истории рассылок (с сессией внутри функции)
async def get_broadcast_history():
    async with async_session() as session:
        result = await session.execute(
            select(BroadcastHistory)
            .order_by(desc(BroadcastHistory.created_at))
            .limit(10)
        )
        return result.scalars().all()

# Запрос для отчета о доставке рассылки группам (с сессией внутри функции)
async def get_filtered_users(filter_type):
    async with async_session() as session:
        if filter_type == "managers":
            result = await session.execute(select(User.telegram_id).where(User.role == "MANAGER"))
        elif filter_type == "leads":
            result = await session.execute(
                select(User.telegram_id)
                .where(and_(User.role == "USER", ~select(1).where(Order.user_id == User.id).exists()))
            )
        elif filter_type == "clients":
            result = await session.execute(
                select(User.telegram_id)
                .where(and_(User.role == "USER", select(1).where(Order.user_id == User.id).exists()))
            )
        elif filter_type == "all":
            result = await session.execute(
                select(User.telegram_id)
                .where(User.role == "USER")
            )
        else:
            return []
        return [row[0] for row in result.all()]

# Сохранение истории рассылок (с сессией внутри функции)
async def save_broadcast_history(text: str, media_type: str, media_file_id: str,
                                 total_users: int, delivered: int, failed: int, target_group: str):
    async with async_session() as session:
        await session.execute(insert(BroadcastHistory).values(
            text=text,
            media_type=media_type,
            media_file_id=media_file_id,
            total_users=total_users,
            delivered=delivered,
            failed=failed,
            target_group=target_group
        ))
        await session.commit()


async def catalog_get_categories(page: int, per_page: int) -> List[Category]:
    async with async_session() as session:
        result = await session.scalars(
            select(Category).offset((page - 1) * per_page).limit(per_page)
        )
        return result.all()

async def catalog_get_total_categories() -> int:
    async with async_session() as session:
        count = await session.scalar(select(func.count(Category.id)))
        return count or 0

async def catalog_get_subcategories(category_id: int, page: int, per_page: int) -> List[Subcategory]:
    async with async_session() as session:
        result = await session.scalars(
            select(Subcategory).where(Subcategory.category_id == category_id).offset((page - 1) * per_page).limit(per_page)
        )
        return result.all()

async def catalog_get_total_subcategories(category_id: int) -> int:
    async with async_session() as session:
        count = await session.scalar(
            select(func.count(Subcategory.id)).where(Subcategory.category_id == category_id)
        )
        return count or 0

async def catalog_get_products_by_subcategory(subcategory_id: int) -> List[Product]:
    async with async_session() as session:
        result = await session.scalars(
            select(Product).where(Product.subcategory_id == subcategory_id)
        )
        return result.all()

async def catalog_get_product_photos(product_id: int) -> List[ProductPhoto]:
    async with async_session() as session:
        result = await session.scalars(
            select(ProductPhoto).where(ProductPhoto.product_id == product_id)
        )
        return result.all()

async def catalog_get_user_info_by_id(telegram_id: str) -> dict:
    async with async_session() as session:
        result = await session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        if result:
            return {"full_name": result.full_name, "address": result.address, "phone_number": result.phone_number}
        else:
            return {}

async def add_to_cart(user_id: int, product: Product, quantity: int, chosen_size: Optional[int],
                       chosen_color: Optional[int], delivery_method: str) -> bool:
    async with async_session() as session:
        try:
            new_order = Order(
                user_id=user_id,
                processed_by_id=None,
                order_datetime=datetime.now(),
                status="В корзине",
                delivery_method=delivery_method
            )
            session.add(new_order)
            await session.flush()  # для получения new_order.id
            new_order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=quantity,
                chosen_size=chosen_size,
                chosen_color=chosen_color
            )
            session.add(new_order_item)
            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error creating order: {e}")
            await session.rollback()
            return False

async def catalog_get_size_name(size_id: int) -> str:
    async with async_session() as session:
        result = await session.scalar(select(Size).where(Size.id == size_id))
        return result.size if result else str(size_id)

async def catalog_get_color_name(color_id: int) -> str:
    async with async_session() as session:
        result = await session.scalar(select(Color).where(Color.id == color_id))
        return result.name if result else str(color_id)


# Возвращает заказ (Order) со статусом "В корзине" для пользователя
async def get_cart_order(user_id: str):
    async with async_session() as session:
        results = await session.scalars(
            select(Order)
            .options(selectinload(Order.order_items))
            .where(Order.user_id == user_id, Order.status=="В корзине")
        )
        return results.all()


async def get_product(product_id: int):
    async with async_session() as session:
        return await session.get(Product, product_id)

# Очищает корзину (обновляет статус заказа на "Удален")
async def clear_cart(user_id: str) -> bool:
    async with async_session() as session:
        try:
            stmt = update(Order).where(Order.user_id == user_id, Order.status=="В корзине").values(status="Удален")
            await session.execute(stmt)
            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error clearing cart: {e}")
            await session.rollback()
            return False


async def get_order_item(order_item_id: int):
    async with async_session() as session:
        return await session.get(OrderItem, order_item_id)

# Обновляет поле заказа (размер, цвет, количество) для OrderItem
async def update_cart_item_field(order_item_id: int, field: str, action: str) -> bool:
    async with async_session() as session:
        try:
            order_item = await session.get(OrderItem, order_item_id)
            if not order_item:
                return False
            product = await session.get(Product, order_item.product_id)
            if field == "size":
                available = product.size_ids or []
                if not available:
                    return False
                current = order_item.chosen_size if order_item.chosen_size is not None else available[0]
                try:
                    idx = available.index(current)
                except ValueError:
                    idx = 0
                new_idx = (idx + 1) % len(available) if action=="inc" else (idx - 1 + len(available)) % len(available)
                order_item.chosen_size = available[new_idx]
            elif field == "color":
                available = product.color_ids or []
                if not available:
                    return False
                current = order_item.chosen_color if order_item.chosen_color is not None else available[0]
                try:
                    idx = available.index(current)
                except ValueError:
                    idx = 0
                new_idx = (idx + 1) % len(available) if action=="inc" else (idx - 1 + len(available)) % len(available)
                order_item.chosen_color = available[new_idx]
            elif field == "qty":
                if action=="inc":
                    order_item.quantity += 1
                else:
                    order_item.quantity = max(1, order_item.quantity - 1)
            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error updating cart item field: {e}")
            await session.rollback()
            return False

# Удаляет OrderItem (можно пометить как удалённый)
async def delete_cart_item(order_item_id: int) -> bool:
    async with async_session() as session:
        try:
            # Физически удаляем запись:
            order_item = await session.get(OrderItem, order_item_id)
            if order_item:
                await session.delete(order_item)
                await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error deleting cart item: {e}")
            await session.rollback()
            return False

# Обновляет статус заказа (Order) на "В обработке"
async def submit_order(order_id: int) -> bool:
    async with async_session() as session:
        try:
            stmt = update(Order).where(Order.id == order_id).values(status="В обработке")
            await session.execute(stmt)
            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error submitting order: {e}")
            await session.rollback()
            return False

# Функции для получения имени размера и цвета по id
async def catalog_get_size_name(size_id: int) -> str:
    async with async_session() as session:
        size = await session.get(Size, size_id)
        return size.size if size else str(size_id)

async def catalog_get_color_name(color_id: int) -> str:
    async with async_session() as session:
        color = await session.get(Color, color_id)
        return color.name if color else str(color_id)

async def update_user_fullname(telegram_id: str, fullname: str) -> bool:
    async with async_session() as session:
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = await session.scalar(stmt)
            if not user:
                return False
            user.full_name = fullname
            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error updating user fullname: {e}")
            await session.rollback()
            return False

async def update_user_phone(telegram_id: str, phone: str) -> bool:
    async with async_session() as session:
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = await session.scalar(stmt)
            if not user:
                return False
            user.phone_number = phone
            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error updating user phone: {e}")
            await session.rollback()
            return False

async def update_user_address(telegram_id: str, address: str) -> bool:
    async with async_session() as session:
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = await session.scalar(stmt)
            if not user:
                return False
            user.address = address
            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error updating user address: {e}")
            await session.rollback()
            return False

async def get_user_info_by_id(telegram_id: str) -> dict:
    async with async_session() as session:
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = await session.scalar(stmt)
            if not user:
                return {}
            return {
                "full_name": user.full_name or "",
                "phone_number": user.phone_number or "",
                "address": user.address or ""
            }
        except SQLAlchemyError as e:
            print(f"Error retrieving user info: {e}")
            return {}


async def submit_all_orders(user_id: str) -> bool:
    async with async_session() as session:
        try:
            # Выбираем id заказов, находящихся в корзине
            stmt_select = select(Order.id).where(Order.user_id == user_id, Order.status == "В корзине")
            result = await session.execute(stmt_select)
            order_ids = result.scalars().all()

            if not order_ids:
                return False

            # Обновляем статус заказов на "В обработке"
            stmt_update = update(Order).where(Order.id.in_(order_ids)).values(status="В обработке")
            await session.execute(stmt_update)

            # Создаём запись группы заказов
            new_group = OrderGroup(
                user_id=user_id,
                processed_by_id=None,  # Менеджер ещё не назначен
                order_ids=order_ids
            )
            session.add(new_group)

            await session.commit()
            return True
        except SQLAlchemyError as e:
            print(f"Error submitting orders: {e}")
            await session.rollback()
            return False

async def get_order_by_id(order_id: int) -> Optional[Order]:
    async with async_session() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.order_items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

async def get_order_group_by_id(order_group_id: int) -> Optional[OrderGroup]:
    async with async_session() as session:
        return await session.get(OrderGroup, order_group_id)

async def get_user_order_groups(user_id: str) -> List[OrderGroup]:
    async with async_session() as session:
        result = await session.scalars(
            select(OrderGroup).where(OrderGroup.user_id == user_id).order_by(OrderGroup.id.desc()).limit(10)
        )
        return result.all()

async def get_user_by_id_user(user_id: int) -> Optional[User]:
    async with async_session() as session:
        return await session.get(User, user_id)


