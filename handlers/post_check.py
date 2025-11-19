from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard
from datetime import datetime

router = Router()

@router.callback_query(F.data == "post_check")
async def handle_post_check(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.post_check_video)
    await callback.message.edit_text(
        "✅ <b>Проверка поста</b>\n\n"
        "Находясь на посту, запишите видео сообщение «Кружок». В кадре отчетливо назовите свое ФИО, текущую дату и время." +
        '''Для записи видео кружка:
1. Кнопка начала записи кружка находится справа снизу. Если вы видите там значок диктофона – переключите на запись кружка, нажав на него КОРОТКО.
3. Зажмите кнопку (кружок в квадрате) и записывайте видеокружок.
4. Глядя в камеру сообщите ФИО, текущую дату и время.
5. Отпустите кнопку – сообщение отправится автоматически.''',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

# Удален шаг выбора/указания объекта для проверки поста

@router.message(Form.post_check_video, F.content_type.in_(["video_note"]))
async def handle_post_check_video(message: Message, state: FSMContext):
    # Удалена проверка и требование указывать название объекта
    data = await state.get_data()
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Отправляем кружочек в группу
    chat_id = get_chat_id_for_user(message.from_user.id)
    if not chat_id:
        await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
        return
    fwd = await message.bot.forward_message(
        chat_id=chat_id,
        from_chat_id=message.from_user.id,
        message_id=message.message_id
    )
    
    # Отправляем информацию о проверке поста
    caption = (
        f"✅ <b>Проверка поста</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📅 Дата: {current_date}\n"
    )
    
    info = await message.bot.send_message(
        chat_id=chat_id,
        text=caption,
        parse_mode=ParseMode.HTML
    )
    
    await state.clear()
    await message.answer(
        "✅ Проверка поста зафиксирована! Видео отправлено в группу.",
        reply_markup=get_main_inline_keyboard()
    )
    # Логируем
    short = get_user_group_shortname(message.from_user.id)
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Проверка поста",
            author_full_name=message.from_user.full_name,
            author_username=message.from_user.username,
            message_id=info.message_id,
            text=f"-"
        )

