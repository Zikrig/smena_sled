from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard, get_confirm_keyboard, get_patrol_keyboard
from datetime import datetime
from aiogram.types import FSInputFile
import tempfile
import os
from image_processor import ImageProcessor

router = Router()

async def _stamp_and_send_photo(bot, chat_id, file_id, caption=None, parse_mode=None):
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, "in.jpg")
    output_path = os.path.join(tmp_dir, "out.jpg")
    try:
        file = await bot.get_file(file_id)
        await bot.download(file, destination=input_path)
        date_text = datetime.now().strftime("%d.%m.%Y %H:%M")
        ImageProcessor.add_text_with_outline(input_path, output_path, date_text)
        await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile(output_path),
            caption=caption,
            parse_mode=parse_mode
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

@router.callback_query(F.data == "patrol")
async def handle_patrol(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photos_received=0, photos=[])
    await state.set_state(Form.patrol_photos)
    
    await callback.message.edit_text(
        "🚶 <b>Обход объекта</b>\n\n"
        "Сделайте фотографии объекта охраны.\n"
        "Можно отправить любое количество фото.\n\n"
        "📸 Отправьте фото #1 (или нажмите 'Завершить обход'):",
        parse_mode=ParseMode.HTML,
        reply_markup=get_patrol_keyboard()
    )
    await callback.answer()

@router.message(Form.patrol_photos, F.photo)
async def handle_patrol_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos_received = data["photos_received"] + 1
    photos = data["photos"]
    
    photos.append(message.photo[-1].file_id)
    
    await state.update_data(photos_received=photos_received, photos=photos)
    await message.answer(
        f"📸 Фото #{photos_received} получено!\n\n"
        f"Отправьте следующее фото или нажмите 'Завершить обход':",
        reply_markup=get_patrol_keyboard()
    )

@router.callback_query(Form.patrol_photos, F.data == "finish_patrol")
async def handle_finish_patrol(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data["photos"]
    photos_count = len(photos)
    
    if photos_count == 0:
        await callback.message.edit_text(
            "❌ Обход не может быть завершен без фотографий.\n\n"
            "Отправьте хотя бы одно фото:",
            reply_markup=get_patrol_keyboard()
        )
        await callback.answer()
        return
    
    # Отправляем фото в группу
    current_time = datetime.now().strftime("%H:%M")
    caption = (
        f"🚶 <b>Обход объекта</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📸 Количество фото: {photos_count}\n"
        f"📍 Обход территории: [прикреплено]"
    )
    
    # Отправляем первое фото с подписью
    chat_id = get_chat_id_for_user(callback.from_user.id)
    if not chat_id:
        await callback.message.edit_text(
            "Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.",
            reply_markup=get_main_inline_keyboard()
        )
        await callback.answer()
        return

    await _stamp_and_send_photo(
        bot=callback.message.bot,
        chat_id=chat_id,
        file_id=photos[0],
        caption=caption,
        parse_mode=ParseMode.HTML
    )
    
    # Отправляем остальные фото без подписей
    for photo_id in photos[1:]:
        await _stamp_and_send_photo(
            bot=callback.message.bot,
            chat_id=chat_id,
            file_id=photo_id
        )
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Обход завершен! Отправлено {photos_count} фотографий в группу.",
        reply_markup=get_main_inline_keyboard()
    )
    await callback.answer()
    # Log
    short = get_user_group_shortname(callback.from_user.id)
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Обход",
            author_full_name=callback.from_user.full_name,
            author_username=callback.from_user.username,
            message_id=None,
            text=f"Количество фото: {photos_count}"
        )

