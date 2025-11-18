from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards import get_main_inline_keyboard
from config import EMERGENCY_NUMBERS

router = Router()

@router.callback_query(F.data == "emergency")
async def handle_emergency(callback: CallbackQuery, state: FSMContext):
    # Определяем названия служб и номера из конфигурации
    services = {
        "fire_service": ("🚒 Общий телефон пожарной службы", EMERGENCY_NUMBERS.get("fire_service", "101")),
        "ora_duty": ("📞 Дежурная часть ОРА", EMERGENCY_NUMBERS.get("ora_duty", "")),
        "security_chief_lo": ("👨‍💼 Начальник охраны в ЛО", EMERGENCY_NUMBERS.get("security_chief_lo", "")),
        "security_chief_spb": ("👨‍💼 Начальник охраны в СПб", EMERGENCY_NUMBERS.get("security_chief_spb", "")),
        "security_chief_so": ("👨‍💼 Пожарная служба в Сосново", EMERGENCY_NUMBERS.get("security_chief_so", ""))
    }

    # Отправляем все контакты карточками
    for _, (name, number) in services.items():
        if not number:
            continue
        await callback.message.answer_contact(phone_number=number, first_name=name)

    # Следующим сообщением — главное меню с подписью "Что-то еще?"
    await callback.message.answer("Что-то еще?", reply_markup=get_main_inline_keyboard())
    await callback.answer()

