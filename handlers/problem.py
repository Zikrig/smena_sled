from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import GROUP_ID
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard
from datetime import datetime

router = Router()

@router.callback_query(F.data == "problem")
async def handle_problem(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.problem_description)
    await callback.message.edit_text(
        "⚠️ <b>Сообщение о проблеме</b>\n\n"
        "Опишите проблему или неисправность:\n"
        "• 📹 Камеры наблюдения\n"
        "• 🚧 Шлагбаум\n"
        "• 🖥️ Монитор\n"
        "• 📡 Датчики\n"
        "• 🔧 Другое оборудование",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.problem_description, F.text)
async def handle_problem_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(Form.problem_photo)
    
    await message.answer(
        "📸 Отправьте фото неисправности (или нажмите 'Пропустить'):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(Form.problem_photo, F.photo)
async def handle_problem_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    description = data["description"]
    current_time = datetime.now().strftime("%H:%M")
    
    caption = (
        f"⚠️ <b>ПРОБЛЕМА НА ОБЪЕКТЕ</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📝 Описание: {description}\n"
        f"📸 Фото: [прикреплено]"
    )
    
    await message.bot.send_photo(
        chat_id=GROUP_ID,
        photo=message.photo[-1].file_id,
        caption=caption,
        parse_mode=ParseMode.HTML
    )
    
    await state.clear()
    await message.answer(
        "✅ Сообщение о проблеме отправлено в группу!",
        reply_markup=get_main_inline_keyboard()
    )

@router.message(Form.problem_photo, F.text)
async def handle_problem_no_photo(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Отменено",
            reply_markup=get_main_inline_keyboard()
        )
        return
    
    data = await state.get_data()
    description = data["description"]
    current_time = datetime.now().strftime("%H:%M")
    
    text = (
        f"⚠️ <b>ПРОБЛЕМА НА ОБЪЕКТЕ</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📝 Описание: {description}"
    )
    
    await message.bot.send_message(
        chat_id=GROUP_ID,
        text=text,
        parse_mode=ParseMode.HTML
    )
    
    await state.clear()
    await message.answer(
        "✅ Сообщение о проблеме отправлено в группу!",
        reply_markup=get_main_inline_keyboard()
    )

