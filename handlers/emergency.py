from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from keyboards import get_main_inline_keyboard
from config import EMERGENCY_NUMBERS

router = Router()

@router.callback_query(F.data == "emergency")
async def handle_emergency(callback: CallbackQuery, state: FSMContext):
    # Определяем названия служб и номера из конфигурации
    services = {
        "fire_service": ("🚒 Пожарная служба", EMERGENCY_NUMBERS.get("fire_service", "101")),
        "ora_duty": ("📞 Дежурная часть ОРА", EMERGENCY_NUMBERS.get("ora_duty", "")),
        "security_chief_lo": ("👨‍💼 Начальник охраны в ЛО", EMERGENCY_NUMBERS.get("security_chief_lo", "")),
        "security_chief_spb": ("👨‍💼 Начальник охраны в СПб", EMERGENCY_NUMBERS.get("security_chief_spb", ""))
    }

    # Формируем сообщение со всеми номерами без каких-либо кнопок
    lines = ["🚨 <b>ВЫЗОВ</b>", ""]
    for _, (name, number) in services.items():
        if not number:
            continue
        lines.append(f"{name}")
        lines.append(f"☎️ <code>{number}</code>")
        lines.append("")  # пустая строка-разделитель

    text = "\n".join(lines).rstrip()

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML
    )
    # Предлагаем вернуться в главное меню
    await callback.message.answer(
        "Что-то еще?",
        reply_markup=get_main_inline_keyboard()
    )
    await callback.answer()

