from typing import Optional, List
from sqlalchemy import (
    Integer, String, ForeignKey, JSON, DECIMAL, TIMESTAMP, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_async_engine(url=os.getenv('SQLITE_URL'))
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Связь с подкатегориями (один-ко-многим)
    subcategories: Mapped[List["Subcategory"]] = relationship(
        "Subcategory", back_populates="category", cascade="all, delete"
    )

class Subcategory(Base):
    __tablename__ = 'subcategories'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id', ondelete='CASCADE'))

    # Связь с категорией
    category: Mapped["Category"] = relationship("Category", back_populates="subcategories")
    # Связь с товарами
    products: Mapped[List["Product"]] = relationship(
        "Product", back_populates="subcategory", cascade="all, delete"
    )

class Color(Base):
    __tablename__ = 'colors'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Отношение с товарами удалено, так как теперь товары хранят список цветов в JSON

class Size(Base):
    __tablename__ = 'sizes'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    size: Mapped[str] = mapped_column(String(50), nullable=False)
    # Отношение с товарами удалено, так как теперь товары хранят список размеров в JSON

class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    # Сохраняем списки идентификаторов цветов и размеров в формате JSON
    color_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    size_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    product_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    material: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    features: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    usage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    temperature_range: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subcategory_id: Mapped[Optional[int]] = mapped_column(ForeignKey('subcategories.id', ondelete='SET NULL'), nullable=True)

    # Связь с подкатегорией
    subcategory: Mapped[Optional["Subcategory"]] = relationship("Subcategory", back_populates="products")

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Указываем, что связь orders должна использовать только столбец user_id
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete",
        foreign_keys=lambda: [Order.user_id]
    )

class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    processed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )  # Кто обработал заказ
    order_datetime: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    delivery_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="orders")
    processed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[processed_by_id]
    )  # Отношение к обработчику заказа
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete"
    )


class OrderItem(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete='CASCADE'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="order_items")
    product: Mapped["Product"] = relationship("Product")

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
