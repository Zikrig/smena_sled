import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import start, shift, tmc_transfer, patrol, inspection, problem, emergency, post_check

# Настройка логирования (отключено)
logging.basicConfig(
    level=logging.CRITICAL,
    handlers=[]
)

# Отключаем логирование aiogram
logging.getLogger("aiogram").setLevel(logging.CRITICAL)
logging.getLogger("aiogram.dispatcher").setLevel(logging.CRITICAL)
logging.getLogger("aiogram.event").setLevel(logging.CRITICAL)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключение роутеров
for router in (start.router, shift.router, tmc_transfer.router, patrol.router, inspection.router, problem.router, emergency.router, post_check.router):
    dp.include_router(router)

if __name__ == "__main__":
    try:
        dp.run_polling(bot)
    except Exception as e:
        pass