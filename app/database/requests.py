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