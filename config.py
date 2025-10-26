from dotenv import load_dotenv
from os import getenv

load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")
GROUP_ID = getenv("GROUP_ID")

# Объекты охраны
LOCATIONS = [
    "Торговый центр 'Мега'",
    "Бизнес-центр 'Столица'",
    "Жилой комплекс 'Премиум'",
    "Складской комплекс 'Логистик'",
    "Офисное здание 'Деловой'"
]

# Номера экстренных служб
EMERGENCY_NUMBERS = {
    "fire_service": "101 - Пожарная служба",
    "ora_duty": "102 - Дежурная часть ОРА", 
    "security_chief": "103 - Начальник охраны"
}
