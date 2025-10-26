from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import GROUP_ID, EMERGENCY_NUMBERS
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard, get_emergency_keyboard
from datetime import datetime

router = Router()

@router.callback_query(F.data == "emergency")
async def handle_emergency(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.emergency_type)
    await callback.message.edit_text(
        "🚨 <b>ЭКСТРЕННЫЙ ВЫЗОВ</b>\n\n"
        "Выберите службу для вызова:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_emergency_keyboard()
    )
    await callback.answer()

@router.callback_query(Form.emergency_type, F.data.in_(["fire_service", "ora_duty", "security_chief"]))
async def handle_emergency_type(callback: CallbackQuery, state: FSMContext):
    emergency_type = callback.data
    service_name = EMERGENCY_NUMBERS[emergency_type]
    
    await state.update_data(emergency_type=service_name)
    await state.set_state(Form.emergency_description)
    
    await callback.message.edit_text(
        f"🚨 <b>ЭКСТРЕННЫЙ ВЫЗОВ</b>\n\n"
        f"Служба: {service_name}\n\n"
        "Опишите ситуацию:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.emergency_description, F.text)
async def handle_emergency_description(message: Message, state: FSMContext):
    data = await state.get_data()
    emergency_type = data["emergency_type"]
    description = message.text
    current_time = datetime.now().strftime("%H:%M")
    
    # Отправляем экстренное сообщение в группу
    emergency_text = (
        f"🚨 <b>ЭКСТРЕННЫЙ ВЫЗОВ!</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📞 Служба: {emergency_type}\n"
        f"📝 Ситуация: {description}\n\n"
    )
    
    await message.bot.send_message(
        chat_id=GROUP_ID,
        text=emergency_text,
        parse_mode=ParseMode.HTML
    )
    
    await state.clear()
    await message.answer(
        f"🚨 ЭКСТРЕННЫЙ ВЫЗОВ ОТПРАВЛЕН!\n\n"
        f"Служба: {emergency_type}\n"
        f"Сообщение передано в группу.",
        reply_markup=get_main_inline_keyboard()
    )

