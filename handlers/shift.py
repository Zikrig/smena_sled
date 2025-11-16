from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_locations_keyboard, get_cancel_keyboard, get_main_inline_keyboard
from datetime import datetime

from aiogram import Router
router = Router()

@router.callback_query(Form.shift_action, F.data.startswith("loc_"))
async def handle_location_selection(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split("_", 1)[1]
    if data == "other":
        await state.update_data(expecting_custom_location=True)
        await state.set_state(Form.waiting_round)
        await callback.message.answer(
            "📸 Укажите объект в подписи к кружочку\n\n"
            "Запишите видео кружочек:"+
                '''Для записи видео кружка:
1. Кнопка начала записи кружка находится справа снизу. Если вы видите там значок диктофона – переключите на запись кружка, нажав на него КОРОТКО.
3. Зажмите кнопку (кружок в квадрате) и записывайте видеокружок.
4. Глядя в камеру сообщите ФИО, дату и время начала смены.
5. Отпустите кнопку – сообщение отправится автоматически.''',
            reply_markup=get_cancel_keyboard()
        )
    else:
        await state.update_data(location=data)
        await state.set_state(Form.waiting_round)
        await callback.message.answer(
            f"📸 Начало смены на объекте: {data}\n\n"
            "Запишите видео кружочек для подтверждения начала смены:"+
            '''Для записи видео кружка:
1. Кнопка начала записи кружка находится справа снизу. Если вы видите там значок диктофона – переключите на запись кружка, нажав на него КОРОТКО.
3. Зажмите кнопку (кружок в квадрате) и записывайте видеокружок.
4. Глядя в камеру сообщите ФИО, дату и время начала смены.
5. Отпустите кнопку – сообщение отправится автоматически.''',
            reply_markup=get_cancel_keyboard()
        )
    await callback.answer()


# Обработчики для кружка (видео-сообщения)
@router.message(Form.waiting_round, F.content_type.in_(["video_note"]))
async def handle_video_note(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Если ожидается кастомное название объекта, проверяем подпись
    if data.get("expecting_custom_location"):
        if not message.caption:
            await message.answer(
                "❌ Вы не указали объект в подписи к кружочку!\n\n"
                "Запишите видео кружочек с подписью названия объекта:"+
                '''Для записи видео кружка:
1. Кнопка начала записи кружка находится справа снизу. Если вы видите там значок диктофона – переключите на запись кружка, нажав на него КОРОТКО.
3. Зажмите кнопку (кружок в квадрате) и записывайте видеокружок.
4. Глядя в камеру сообщите ФИО, дату и время начала смены.
5. Отпустите кнопку – сообщение отправится автоматически.''',
                reply_markup=get_cancel_keyboard()
            )
            return
        location = message.caption.strip()
        if len(location) > 100:
            await message.answer(
                "❌ Название объекта слишком длинное. Максимум 100 символов.\n\n"
                "Запишите видео кружочек с подписью названия объекта:"+
                '''Для записи видео кружка:
1. Кнопка начала записи кружка находится справа снизу. Если вы видите там значок диктофона – переключите на запись кружка, нажав на него КОРОТКО.
3. Зажмите кнопку (кружок в квадрате) и записывайте видеокружок.
4. Глядя в камеру сообщите ФИО, дату и время начала смены.
5. Отпустите кнопку – сообщение отправится автоматически.''',
                reply_markup=get_cancel_keyboard()
            )
            return
        await state.update_data(location=location, expecting_custom_location=False)
    
    # Получаем название объекта
    location = data.get("location", "Не указан")
    
    # Отправляем кружочек в группу
    chat_id = get_chat_id_for_user(message.from_user.id)
    if not chat_id:
        await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
        return
    fwd = await message.bot.forward_message(chat_id=chat_id, from_chat_id=message.from_user.id, message_id=message.message_id)
    
    # Отправляем информацию о начале смены
    current_time = datetime.now().strftime("%H:%M")
    caption = (
        f"📸 <b>Начало смены</b>\n"
        f"📍 Объект: {location}\n"
        f"⏰ Время: {current_time}\n"
        f"🎥 Видео подтверждение: [прикреплено]"
    )
    
    info_msg = await message.bot.send_message(
        chat_id=chat_id,
        text=caption,
        parse_mode=ParseMode.HTML
    )
    
    await state.clear()
    await message.answer(
        "✅ Начало смены зафиксировано! Кружочек отправлен в группу.",
        reply_markup=get_main_inline_keyboard()
    )
    # Log to Google Sheets
    short = get_user_group_shortname(message.from_user.id)
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Начало смены",
            author_full_name=message.from_user.full_name,
            author_username=message.from_user.username,
            message_id=info_msg.message_id,
            text=f"Объект: {location}"
        )
