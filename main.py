import logging
import asyncio
from aiogram import Dispatcher

from app.ai_module.ai_consultant import ai_router
from app.register.registerHandlers import router
from app.database.models import async_main
from bot_instance import bot, dp  # Импортируем bot и dp
from app.database import requests as rq

# Настройка логирования только для консоли
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования INFO, можно переключить на DEBUG для более подробного вывода
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Запуск бота...")
    try:
        await async_main()  # Инициализация базы данных (например, для SQLite)
        logger.info("База данных инициализирована успешно.")
    except Exception as e:
        logger.exception("Ошибка при инициализации базы данных")

    dp.include_router(router)
    dp.include_router(ai_router)
    logger.info("Роутеры зарегистрированы. Начинается polling бота.")

    openai_api_key = await rq.get_setting_value(key="OPENAI_API")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Ошибка при запуске polling")
    finally:
        logger.info("Бот завершил работу.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Бот остановлен вручную (Ctrl+C)")
    except Exception as e:
        logger.critical("Критическая ошибка", exc_info=e)
