from typing import Optional, List
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