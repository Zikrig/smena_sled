import logging
import os
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, LOG_LEVEL
from handlers import start, shift, tmc_transfer, patrol, inspection, problem, emergency, post_check, admin

# Настройка логирования
os.makedirs("logs", exist_ok=True)
log_level = getattr(logging, (LOG_LEVEL or "INFO").upper(), logging.INFO)
logger = logging.getLogger()
logger.setLevel(log_level)
# Очистим существующие хэндлеры и добавим свои
for h in list(logger.handlers):
    logger.removeHandler(h)
file_handler = RotatingFileHandler("logs/bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Уровни логирования aiogram
logging.getLogger("aiogram").setLevel(log_level)
logging.getLogger("aiogram.dispatcher").setLevel(log_level)
logging.getLogger("aiogram.event").setLevel(log_level)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключение роутеров
for router in (start.router, shift.router, tmc_transfer.router, patrol.router, inspection.router, problem.router, emergency.router, post_check.router, admin.router):
    dp.include_router(router)

if __name__ == "__main__":
    try:
        logging.getLogger(__name__).info("Starting bot polling")
        dp.run_polling(bot)
    except Exception as e:
        logging.getLogger(__name__).exception("Fatal error in polling loop")