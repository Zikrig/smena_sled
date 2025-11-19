from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard, get_done_keyboard
from datetime import datetime
from aiogram.types import FSInputFile
from media_utils import stamp_and_send_album
import asyncio

router = Router()

@router.callback_query(F.data == "problem")
async def handle_problem(callback: CallbackQuery, state: FSMContext):
    await state.update_data(media_files=[], media_captions=[], media_kinds=[], flush_scheduled=False)
    await state.set_state(Form.problem_description)
    await callback.message.edit_text(
        "💬 <b>Сообщение</b>\n\n"
        "Напишите текст, запишите голос/видео или пришлите фото.\n"
        "Если нужно отправить несколько фото — прикрепите все через скрепку. Фото уйдут одним сообщением.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.problem_description)
async def handle_problem_message(message: Message, state: FSMContext):
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Фото/Видео: отправка с подписью(ями). Если альбом (media_group_id) — копим и отправляем автоматически.
    if message.photo or message.video:
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        if message.media_group_id:
            data = await state.get_data()
            files = data.get("media_files", [])
            caps = data.get("media_captions", [])
            kinds = data.get("media_kinds", [])
            if message.photo:
                files.append(message.photo[-1].file_id)
                kinds.append("photo")
            else:
                files.append(message.video.file_id)
                kinds.append("video")
            caps.append(message.caption or None)
            await state.update_data(media_files=files, media_captions=caps, media_kinds=kinds, media_group_id=message.media_group_id)
            if not data.get("flush_scheduled"):
                await state.update_data(flush_scheduled=True)
                async def _flush():
                    await asyncio.sleep(1.0)
                    d = await state.get_data()
                    files2 = d.get("media_files", [])
                    caps2 = d.get("media_captions", [])
                    kinds2 = d.get("media_kinds", [])
                    if not files2:
                        return
                    header = (
                        f"💬 <b>СООБЩЕНИЕ</b>\n"
                        f"⏰ Время: {datetime.now().strftime('%H:%M')}\n"
                        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
                        f"📎 Медиа: [альбом]"
                    )
                    sent_ids = await stamp_and_send_album(
                        bot=message.bot,
                        chat_id=chat_id,
                        file_ids=files2,
                        captions=caps2,
                        header=header,
                        kinds=kinds2,
                        parse_mode=ParseMode.HTML
                    )
                    # Отправляем и закрепляем статусное сообщение с кнопкой ГОТОВО
                    status_text = header + "\n\n❌ НЕ ВЫПОЛНЕНО"
                    status_msg = await message.bot.send_message(
                        chat_id=chat_id,
                        text=status_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=get_done_keyboard()
                    )
                    try:
                        await message.bot.pin_chat_message(chat_id=chat_id, message_id=status_msg.message_id)
                    except Exception:
                        pass
                    await state.clear()
                    await message.answer(
                        f"✅ Сообщение с медиа отправлено! Отправлено {len(files2)} элементов.",
                        reply_markup=get_main_inline_keyboard()
                    )
                    short = get_user_group_shortname(message.from_user.id)
                    if short:
                        album_mid = sent_ids[0] if sent_ids else status_msg.message_id
                        await gsheets.log_event(
                            shortname=short,
                            chat_id=chat_id,
                            event_type="Сообщение (альбом)",
                            author_full_name=message.from_user.full_name,
                            author_username=message.from_user.username,
                            message_id=album_mid,
                            text=f"Медиа: {len(files2)}"
                        )
                asyncio.create_task(_flush())
            return
        # Одиночное медиа
        header = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
            f"📎 Медиа: [прикреплено]"
        )
        media_caption = message.caption or None
        if message.photo:
            sent_ids = await stamp_and_send_album(
                bot=message.bot,
                chat_id=chat_id,
                file_ids=[message.photo[-1].file_id],
                captions=[media_caption],
                header=header,
                kinds=["photo"],
                parse_mode=ParseMode.HTML
            )
        else:
            sent_ids = await stamp_and_send_album(
                bot=message.bot,
                chat_id=chat_id,
                file_ids=[message.video.file_id],
                captions=[media_caption],
                header=header,
                kinds=["video"],
                parse_mode=ParseMode.HTML
            )
        # Статусное сообщение с кнопкой и закреплением
        status_text = header + "\n\n❌ НЕ ВЫПОЛНЕНО"
        status_msg = await message.bot.send_message(
            chat_id=chat_id,
            text=status_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_done_keyboard()
        )
        try:
            await message.bot.pin_chat_message(chat_id=chat_id, message_id=status_msg.message_id)
        except Exception:
            pass
        await state.clear()
        await message.answer(
            "✅ Сообщение с медиа отправлено!",
            reply_markup=get_main_inline_keyboard()
        )
        short = get_user_group_shortname(message.from_user.id)
        if short:
            album_mid = sent_ids[0] if sent_ids else status_msg.message_id
            await gsheets.log_event(
                shortname=short,
                chat_id=chat_id,
                event_type="Сообщение (медиа)",
                author_full_name=message.from_user.full_name,
                author_username=message.from_user.username,
                message_id=album_mid,
                text=media_caption or ""
            )
        return
    
    # Пересылаем прочие медиа/текст сразу
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
            f"🎤 Медиа: [прикреплено]\n\n"
            f"❌ НЕ ВЫПОЛНЕНО"
        )
        info = await message.bot.send_message(
            chat_id=chat_id,
            text=info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_done_keyboard()
        )
        try:
            await message.bot.pin_chat_message(chat_id=chat_id, message_id=info.message_id)
        except Exception:
            pass
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
            f"📝 Текст: {message.text}\n\n"
            f"❌ НЕ ВЫПОЛНЕНО"
        )
        
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        sent_text = await message.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_done_keyboard()
        )
        try:
            await message.bot.pin_chat_message(chat_id=chat_id, message_id=sent_text.message_id)
        except Exception:
            pass
    elif message.document:
        # Если документ
        caption = (
            f"💬 <b>СООБЩЕНИЕ</b>\n"
            f"⏰ Время: {current_time}\n"
            f"📅 Дата: {current_date}\n"
        )
        if message.caption:
            caption += f"📝 Текст: {message.caption}\n"
        caption += "\n❌ НЕ ВЫПОЛНЕНО"
        
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            await state.clear()
            return
        sent_doc = await message.bot.send_document(
            chat_id=chat_id,
            document=message.document.file_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=get_done_keyboard()
        )
        try:
            await message.bot.pin_chat_message(chat_id=chat_id, message_id=sent_doc.message_id)
        except Exception:
            pass
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
            f"📎 Медиа: [прикреплено]\n\n"
            f"❌ НЕ ВЫПОЛНЕНО"
        )
        info_other = await message.bot.send_message(
            chat_id=chat_id,
            text=info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_done_keyboard()
        )
        try:
            await message.bot.pin_chat_message(chat_id=chat_id, message_id=info_other.message_id)
        except Exception:
            pass
    
    await state.clear()
    await message.answer(
        "✅ Сообщение отправлено в группу!",
        reply_markup=get_main_inline_keyboard()
    )

    # Логируем (берём первый доступный message_id — предпочитаем исходное медиа)
    short = get_user_group_shortname(message.from_user.id)
    if short:
        mid = None
        for var in ["sent_photo", "sent_video", "sent_text", "sent_doc", "fwd", "fwd_other", "info", "info_other"]:
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

@router.callback_query(F.data == "message_done")
async def handle_message_done(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.bot.unpin_chat_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    except Exception:
        pass
    # Обновим текст/подпись и уберем кнопку
    try:
        if callback.message.text:
            new_text = callback.message.text.replace("❌ НЕ ВЫПОЛНЕНО", "✅ ГОТОВО", 1)
            if new_text == callback.message.text:
                new_text = callback.message.text.replace("НЕ ВЫПОЛНЕНО", "ГОТОВО", 1)
            await callback.message.edit_text(
                text=new_text,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        elif callback.message.caption:
            new_caption = callback.message.caption.replace("❌ НЕ ВЫПОЛНЕНО", "✅ ГОТОВО", 1)
            if new_caption == callback.message.caption:
                new_caption = callback.message.caption.replace("НЕ ВЫПОЛНЕНО", "ГОТОВО", 1)
            await callback.message.edit_caption(
                caption=new_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        else:
            # На всякий случай просто уберем клавиатуру
            await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.answer("Отмечено как ГОТОВО и откреплено")


