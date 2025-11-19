from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard
from datetime import datetime

from aiogram import Router
router = Router()

# Удален шаг выбора/указания объекта


# Обработчики для кружка (видео-сообщения)
@router.message(Form.waiting_round, F.content_type.in_(["video_note"]))
async def handle_video_note(message: Message, state: FSMContext):
    # Удалена проверка и требование указывать название объекта
    data = await state.get_data()
 
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
        f"⏰ Время: {current_time}\n"
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
    # Логируем в Google Таблицу
    short = get_user_group_shortname(message.from_user.id)
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Начало смены",
            author_full_name=message.from_user.full_name,
            author_username=message.from_user.username,
            message_id=info_msg.message_id,
            text=f"-"
        )
