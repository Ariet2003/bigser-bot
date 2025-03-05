from typing import Optional, List, Dict
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import async_session
from app.database.models import Color, Category, User, Product, Subcategory, Size, Order, OrderItem
from app.users.user import userKeyboards as kb
from sqlalchemy.exc import SQLAlchemyError
from bot_instance import bot
from sqlalchemy import select, delete
from datetime import datetime
from sqlalchemy import update
import random
from sqlalchemy import or_
from sqlalchemy.orm import aliased
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
            result = await session.execute(select(Product))
            products = result.scalars().all()
            return [
                {
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
                    "subcategory_id": product.subcategory_id
                }
                for product in products
            ]
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
            # Выполняем join с таблицей Category для получения названия родительской категории
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

async def add_product(product_data: dict) -> bool:
    async with async_session() as session:
        try:
            new_product = Product(**product_data)
            session.add(new_product)
            await session.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении продукта: {e}")
            await session.rollback()
            return False

async def get_product_by_id(product_id: int):
    async with async_session() as session:
        try:
            result = await session.execute(select(Product).where(Product.id == product_id))
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
