from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
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
        date_text = datetime.now().strftime("%d.%m.%Y %H:%M")
        ImageProcessor.add_text_with_outline(input_path, output_path, date_text)
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            return
        sent = await message.bot.send_photo(
            chat_id=chat_id,
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
    # Log
    short = get_user_group_shortname(message.from_user.id)
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Передача ТМЦ",
            author_full_name=message.from_user.full_name,
            author_username=message.from_user.username,
            message_id=sent.message_id,
            text="Журнал передачи смены"
        )

