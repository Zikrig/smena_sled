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
    "fire_service": "101",
    "ora_duty": "89213092735",
    "security_chief_lo": "89213173079",
    "security_chief_spb": "89213666399",
    "security_chief_so": "88137961262"
}
