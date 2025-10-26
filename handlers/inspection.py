from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import GROUP_ID
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard, get_inspection_keyboard
from datetime import datetime

router = Router()

@router.callback_query(F.data == "inspection")
async def handle_inspection(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photos_received=0, photos=[])
    await state.set_state(Form.inspection_photos)
    await callback.message.edit_text(
        "🔍 <b>Осмотр транспорта</b>\n\n"
        "Сделайте фотофиксацию:\n"
        "• Багажников автомобилей\n"
        "• Кузовов грузовиков\n"
        "• Выносимых ТМЦ при необходимости\n\n"
        "Можно отправить любое количество фото.\n\n"
        "📸 Отправьте фото #1 (или нажмите 'Завершить осмотр'):",
        parse_mode=ParseMode.HTML,
        reply_markup=get_inspection_keyboard()
    )
    await callback.answer()

@router.message(Form.inspection_photos, F.photo)
async def handle_inspection_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos_received = data["photos_received"] + 1
    photos = data["photos"]
    
    photos.append(message.photo[-1].file_id)
    
    await state.update_data(photos_received=photos_received, photos=photos)
    await message.answer(
        f"📸 Фото #{photos_received} получено!\n\n"
        f"Отправьте следующее фото или нажмите 'Завершить осмотр':",
        reply_markup=get_inspection_keyboard()
    )

@router.callback_query(Form.inspection_photos, F.data == "finish_inspection")
async def handle_finish_inspection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data["photos"]
    photos_count = len(photos)
    
    if photos_count == 0:
        await callback.message.edit_text(
            "❌ Осмотр не может быть завершен без фотографий.\n\n"
            "Отправьте хотя бы одно фото:",
            reply_markup=get_inspection_keyboard()
        )
        await callback.answer()
        return
    
    # Отправляем фото в группу
    current_time = datetime.now().strftime("%H:%M")
    caption = (
        f"🔍 <b>Осмотр транспорта</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📸 Количество фото: {photos_count}\n"
        f"📸 Фотофиксация: [прикреплено]"
    )
    
    # Отправляем первое фото с подписью
    await callback.message.bot.send_photo(
        chat_id=GROUP_ID,
        photo=photos[0],
        caption=caption,
        parse_mode=ParseMode.HTML
    )
    
    # Отправляем остальные фото без подписей
    for photo_id in photos[1:]:
        await callback.message.bot.send_photo(
            chat_id=GROUP_ID,
            photo=photo_id
        )
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Осмотр завершен! Отправлено {photos_count} фотографий в группу.",
        reply_markup=get_main_inline_keyboard()
    )
    await callback.answer()

