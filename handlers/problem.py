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

@router.callback_query(F.data == "problem")
async def handle_problem(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.problem_description)
    await callback.message.edit_text(
        "💬 <b>Сообщение</b>\n\n"
        "Напишите, запишите голосовое сообщение или пришлите фото, о чем желаете сообщить.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.problem_description)
async def handle_problem_message(message: Message, state: FSMContext):
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Пересылаем сообщение в группу
    if message.photo:
        # Если есть фото, отправляем его с подписью
        caption = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
        )
        if message.caption:
            caption += f"📝 Текст: {message.caption}"
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        sent_photo = await _stamp_and_send_photo(
            bot=message.bot,
            chat_id=chat_id,
            file_id=message.photo[-1].file_id,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    elif message.video:
        # Если есть видео
        caption = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
        )
        if message.caption:
            caption += f"📝 Текст: {message.caption}"
        
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        sent_video = await message.bot.send_video(
            chat_id=chat_id,
            video=message.video.file_id,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    elif message.voice or message.video_note or message.audio:
        # Если голосовое, кружок или аудио - пересылаем оригинал
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        fwd = await message.bot.forward_message(
            chat_id=chat_id,
            from_chat_id=message.from_user.id,
            message_id=message.message_id
        )
        
        # Отправляем информацию
        info_text = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
            f"🎤 Медиа: [прикреплено]"
        )
        info = await message.bot.send_message(
            chat_id=chat_id,
            text=info_text,
            parse_mode=ParseMode.HTML
        )
    elif message.text:
        # Если текст
        if message.text == "❌ Отмена":
            await state.clear()
            await message.answer(
                "❌ Отменено",
                reply_markup=get_main_inline_keyboard()
            )
            return
        
        text = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
            f"📝 Текст: {message.text}"
        )
        
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        sent_text = await message.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
    elif message.document:
        # Если документ
        caption = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
        )
        if message.caption:
            caption += f"📝 Текст: {message.caption}"
        
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        sent_doc = await message.bot.send_document(
            chat_id=chat_id,
            document=message.document.file_id,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        # Для других типов медиа - просто пересылаем
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        fwd_other = await message.bot.forward_message(
            chat_id=chat_id,
            from_chat_id=message.from_user.id,
            message_id=message.message_id
        )
        
        info_text = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
            f"📎 Медиа: [прикреплено]"
        )
        info_other = await message.bot.send_message(
            chat_id=chat_id,
            text=info_text,
            parse_mode=ParseMode.HTML
        )
    
    await state.clear()
    await message.answer(
        "✅ Сообщение отправлено в группу!",
        reply_markup=get_main_inline_keyboard()
    )

    # Log (choose first available message id variable)
    short = get_user_group_shortname(message.from_user.id)
    if short:
        mid = None
        for var in ["sent_photo", "sent_video", "info", "sent_text", "sent_doc", "fwd", "fwd_other", "info_other"]:
            if var in locals() and locals()[var]:
                try:
                    mid = locals()[var].message_id
                    break
                except Exception:
                    pass
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Сообщение",
            author_full_name=message.from_user.full_name,
            author_username=message.from_user.username,
            message_id=mid,
            text=message.caption or (message.text if message.text and message.text != "❌ Отмена" else "")
        )

