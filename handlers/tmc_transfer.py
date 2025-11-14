from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import GROUP_ID
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard
from datetime import datetime
from aiogram.types import FSInputFile
import tempfile
import os
from image_processor import ImageProcessor

router = Router()

@router.callback_query(F.data == "transfer_tmc")
async def handle_transfer_tmc(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.transfer_tmc_photo)
    await callback.message.edit_text(
        "📋 <b>Передача ТМЦ на посту</b>\n\n"
        "Сделайте фото журнала передачи смены с записью:\n"
        "• Факт передачи смены новому охраннику\n"
        "• Список передаваемых ТМЦ (рация, ключи и т.д.)\n\n"
        "📸 Отправьте фото журнала:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.transfer_tmc_photo, F.photo)
async def handle_tmc_photo(message: Message, state: FSMContext):
    current_time = datetime.now().strftime("%H:%M")
    caption = (
        f"📋 <b>Передача ТМЦ на посту</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📝 Журнал передачи смены: [прикреплено]"
    )

    # Ставим дату на фото и отправляем
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, "in.jpg")
    output_path = os.path.join(tmp_dir, "out.jpg")
    try:
        file = await message.bot.get_file(message.photo[-1].file_id)
        await message.bot.download(file, destination=input_path)
        date_text = datetime.now().strftime("%d.%m.%Y")
        ImageProcessor.add_text_with_outline(input_path, output_path, date_text)
        await message.bot.send_photo(
            chat_id=GROUP_ID,
            photo=FSInputFile(output_path),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    finally:
        try:
            os.remove(input_path)
        except:
            pass
        try:
            os.remove(output_path)
        except:
            pass
        try:
            os.rmdir(tmp_dir)
        except:
            pass
    
    await state.clear()
    await message.answer(
        "✅ Фото журнала передачи ТМЦ отправлено в группу!",
        reply_markup=get_main_inline_keyboard()
    )

