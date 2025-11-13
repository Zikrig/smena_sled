from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from config import GROUP_ID
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard
from datetime import datetime

router = Router()

@router.callback_query(F.data == "post_check")
async def handle_post_check(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.post_check_video)
    await callback.message.edit_text(
        "✅ <b>Проверка поста</b>\n\n"
        "Находясь на посту, запишите видео сообщение «Кружок». В кадре отчетливо назовите свое ФИО, текущие время и дату.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(Form.post_check_location, F.data.startswith("loc_"))
async def handle_post_check_location(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split("_", 1)[1]
    if data == "other":
        await state.update_data(expecting_custom_location=True)
        await state.set_state(Form.post_check_video)
        await callback.message.answer(
            "📸 Укажите объект в подписи к кружочку\n\n"
            "Находясь на посту записываем видео сообщение «Кружок», глядя в камеру отчетливо называем свое ФИО, название поста, текущие время и дату.",
            reply_markup=get_cancel_keyboard()
        )
    else:
        await state.update_data(location=data)
        await state.set_state(Form.post_check_video)
        await callback.message.answer(
            f"✅ <b>Проверка поста</b>\n\n"
            f"📍 Объект: {data}\n\n"
            "Находясь на посту записываем видео сообщение «Кружок», глядя в камеру отчетливо называем свое ФИО, название поста, текущие время и дату.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_cancel_keyboard()
        )
    await callback.answer()

@router.message(Form.post_check_video, F.content_type.in_(["video_note"]))
async def handle_post_check_video(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Если ожидается кастомное название объекта, проверяем подпись
    if data.get("expecting_custom_location"):
        if not message.caption:
            await message.answer(
                "❌ Вы не указали объект в подписи к кружочку!\n\n"
                "Запишите видео кружочек с подписью названия объекта:",
                reply_markup=get_cancel_keyboard()
            )
            return
        location = message.caption.strip()
        if len(location) > 100:
            await message.answer(
                "❌ Название объекта слишком длинное. Максимум 100 символов.\n\n"
                "Запишите видео кружочек с подписью названия объекта:",
                reply_markup=get_cancel_keyboard()
            )
            return
        await state.update_data(location=location, expecting_custom_location=False)
    
    # Получаем название объекта
    location = data.get("location", "Не указан")
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Отправляем кружочек в группу
    await message.bot.forward_message(
        chat_id=GROUP_ID,
        from_chat_id=message.from_user.id,
        message_id=message.message_id
    )
    
    # Отправляем информацию о проверке поста
    caption = (
        f"✅ <b>Проверка поста</b>\n"
        f"📍 Объект: {location}\n"
        f"⏰ Время: {current_time}\n"
        f"📅 Дата: {current_date}\n"
        f"🎥 Видео подтверждение: [прикреплено]"
    )
    
    await message.bot.send_message(
        chat_id=GROUP_ID,
        text=caption,
        parse_mode=ParseMode.HTML
    )
    
    await state.clear()
    await message.answer(
        "✅ Проверка поста зафиксирована! Видео отправлено в группу.",
        reply_markup=get_main_inline_keyboard()
    )

