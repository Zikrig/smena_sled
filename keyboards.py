from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup
from config import LOCATIONS

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()

def get_locations_keyboard():
    builder = InlineKeyboardBuilder()
    for location in LOCATIONS:
        builder.button(text=location, callback_data=f"loc_{location}")
    builder.button(text="Другой объект", callback_data="loc_other")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_main_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📸 Начать смену", callback_data="start_shift")
    builder.button(text="📋 Передача ТМЦ", callback_data="transfer_tmc")
    builder.button(text="🚶 Обход", callback_data="patrol")
    builder.button(text="🔍 Осмотр", callback_data="inspection")
    builder.button(text="⚠️ Проблема", callback_data="problem")
    builder.button(text="🚨 Экстренный вызов", callback_data="emergency")
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    return builder.as_markup()

def get_confirm_keyboard(action):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data=action)
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()

def get_geo_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить геолокацию", callback_data="confirm_location")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()

def get_emergency_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🚒 Пожарная служба", callback_data="fire_service")
    builder.button(text="📞 Дежурная часть ОРА", callback_data="ora_duty")
    builder.button(text="👨‍💼 Начальник охраны", callback_data="security_chief")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_problem_type_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📹 Камеры наблюдения", callback_data="problem_cameras")
    builder.button(text="🚧 Шлагбаум", callback_data="problem_barrier")
    builder.button(text="🖥️ Монитор", callback_data="problem_monitor")
    builder.button(text="📡 Датчики", callback_data="problem_sensors")
    builder.button(text="🔧 Другое оборудование", callback_data="problem_other")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

# keyboards.py
def get_patrol_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Завершить обход", callback_data="finish_patrol")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()

def get_inspection_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Завершить осмотр", callback_data="finish_inspection")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()