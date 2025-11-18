from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard, get_patrol_keyboard
from datetime import datetime
from aiogram.types import FSInputFile
from media_utils import stamp_and_send_album, queue_album_photo
import asyncio

router = Router()

@router.callback_query(F.data == "patrol")
async def handle_patrol(callback: CallbackQuery, state: FSMContext):
    await state.update_data(patrol_photos=[], patrol_times=[], patrol_control_message_id=None)
    await state.set_state(Form.patrol_photos)
    
    await callback.message.edit_text(
        "🚶 <b>Обход объекта</b>\n\n"
        "Сделайте фото камерой телефона и отправляйте <b>по одной</b>.\n"
        "Нажмите «Завершить обход», когда закончите.\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.patrol_photos, F.photo)
async def handle_patrol_photo(message: Message, state: FSMContext):
    # Копим фото и показываем нижнее сообщение с кнопками (одно актуальное)
    data = await state.get_data()
    photos = data.get("patrol_photos", [])
    times = data.get("patrol_times", [])
    control_id = data.get("patrol_control_message_id")

    if len(photos) >= 30:
        await message.answer("Достигнут лимит 30 фото. Нажмите «Завершить обход».", reply_markup=get_patrol_keyboard())
        return

    photos.append(message.photo[-1].file_id)
    times.append(datetime.now().strftime("%H:%M"))
    await state.update_data(patrol_photos=photos, patrol_times=times)

    # Удалим предыдущее управление, если было
    if control_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=control_id)
        except Exception:
            pass

    # Показать новое управление внизу
    new_msg = await message.answer(
        f"📸 Получено фото {len(photos)}\n"
        f"Отправьте следующее фото или нажмите «Завершить обход».",
        reply_markup=get_patrol_keyboard()
    )
    await state.update_data(patrol_control_message_id=new_msg.message_id)

@router.callback_query(Form.patrol_photos, F.data == "finish_patrol")
async def handle_finish_patrol(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("patrol_photos", []) or []
    times = data.get("patrol_times", []) or []
    control_id = data.get("patrol_control_message_id")
    photos_count = len(photos)
    
    if photos_count == 0:
        try:
            await callback.message.edit_text(
                "❌ Обход не может быть завершен без фотографий.\n\n"
                "Сделайте фото и отправьте <b>по одной</b>.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_patrol_keyboard()
            )
        except Exception:
            pass
        await callback.answer()
        return
    
    # Отправляем фото в группу (альбомами по 10), затем резюме со временем
    chat_id = get_chat_id_for_user(callback.from_user.id)
    if not chat_id:
        await callback.message.edit_text(
            "Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.",
            reply_markup=get_main_inline_keyboard()
        )
        await callback.answer()
        return

    header = (
        f"🚶 <b>Обход объекта</b>\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
        f"📸 Количество фото: {photos_count}\n"
        f"📎 Обход территории: [альбом]\n"
        f"\n"
        f"🕒 Время:\n" + "\n".join(times)
    )
    await stamp_and_send_album(
        bot=callback.message.bot,
        chat_id=chat_id,
        file_ids=photos,
        captions=[None] * photos_count,
        kinds=["photo"] * photos_count,
        header=header,
        parse_mode=ParseMode.HTML
    )

    
    await state.clear()

    # Удалим предыдущее управление, если есть, и покажем финальный ответ
    if control_id and control_id != callback.message.message_id:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=control_id)
        except Exception:
            pass
    try:
        await callback.message.edit_text(
            f"✅ Обход завершен! Отправлено {photos_count} фото в группу.",
            reply_markup=get_main_inline_keyboard()
        )
    except Exception:
        pass
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

@router.callback_query(Form.patrol_photos, F.data == "cancel_action")
async def handle_patrol_cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    control_id = data.get("patrol_control_message_id")
    await state.clear()
    # Удалить контрольное сообщение, если это не он сам
    if control_id and control_id != callback.message.message_id:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=control_id)
        except Exception:
            pass
    try:
        await callback.message.edit_text("❌ Обход отменен.", reply_markup=get_main_inline_keyboard())
    except Exception:
        pass
    await callback.answer()

