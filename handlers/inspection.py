from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from storage import get_chat_id_for_user, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_cancel_keyboard, get_main_inline_keyboard, get_inspection_keyboard
from datetime import datetime
from aiogram.types import FSInputFile
from media_utils import stamp_and_send_album
import asyncio

router = Router()

@router.callback_query(F.data == "inspection")
async def handle_inspection(callback: CallbackQuery, state: FSMContext):
    await state.update_data(inspection_photos=[], inspection_times=[], inspection_control_message_id=None)
    await state.set_state(Form.inspection_photos)
    await callback.message.edit_text(
        "🔍 <b>Осмотр/Фотофиксация</b>\n\n"
        "Сделайте фото и отправляйте <b>по одной</b>.\n"
        "Нажмите «Завершить осмотр», когда закончите.\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.inspection_photos, F.photo)
async def handle_inspection_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("inspection_photos", [])
    times = data.get("inspection_times", [])
    control_id = data.get("inspection_control_message_id")

    if len(photos) >= 30:
        await message.answer("Достигнут лимит 30 фото. Нажмите «Завершить осмотр».", reply_markup=get_inspection_keyboard())
        return

    photos.append(message.photo[-1].file_id)
    times.append(datetime.now().strftime("%H:%M"))
    await state.update_data(inspection_photos=photos, inspection_times=times)

    if control_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=control_id)
        except Exception:
            pass

    new_msg = await message.answer(
        f"📸 Получено фото {len(photos)}\n"
        f"Отправьте следующее фото или нажмите «Завершить осмотр».",
        reply_markup=get_inspection_keyboard()
    )
    await state.update_data(inspection_control_message_id=new_msg.message_id)

@router.callback_query(Form.inspection_photos, F.data == "finish_inspection")
async def finish_inspection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("inspection_photos", []) or []
    times = data.get("inspection_times", []) or []
    control_id = data.get("inspection_control_message_id")
    photos_count = len(photos)

    if photos_count == 0:
        try:
            await callback.message.edit_text(
                "❌ Осмотр не может быть завершен без фотографий.\n\n"
                "Сделайте фото и отправьте <b>по одной</b>.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_inspection_keyboard()
            )
        except Exception:
            pass
        await callback.answer()
        return

    chat_id = get_chat_id_for_user(callback.from_user.id)
    if not chat_id:
        await callback.message.edit_text(
            "Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.",
            reply_markup=get_main_inline_keyboard()
        )
        await callback.answer()
        return

    time_lines = "\n".join(f"{idx}. {t}" for idx, t in enumerate(times, start=1)) or "—"
    header = (
        f"🔍 <b>Осмотр/Фотофиксация</b>\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
        f"📸 Количество фото: {photos_count}\n"
        f"📎 Фотофиксация: [альбом]\n"
        f"\n"
        f"🕒 Время:\n{time_lines}"
    )
    sent_message_ids = await stamp_and_send_album(
        bot=callback.message.bot,
        chat_id=chat_id,
        file_ids=photos,
        captions=[None] * photos_count,
        kinds=["photo"] * photos_count,
        header=header,
        parse_mode=ParseMode.HTML
    )

    await state.clear()
    if control_id and control_id != callback.message.message_id:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=control_id)
        except Exception:
            pass
    try:
        await callback.message.edit_text(
            f"✅ Осмотр завершен! Отправлено {photos_count} фото в группу.",
            reply_markup=get_main_inline_keyboard()
        )
    except Exception:
        pass
    await callback.answer()

    short = get_user_group_shortname(callback.from_user.id)
    album_message_id = sent_message_ids[0] if sent_message_ids else None
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Осмотр/Фотофиксация",
            author_full_name=callback.from_user.full_name,
            author_username=callback.from_user.username,
            message_id=album_message_id,
            text=f"Количество фото: {photos_count}"
        )

@router.callback_query(Form.inspection_photos, F.data == "cancel_action")
async def cancel_inspection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    control_id = data.get("inspection_control_message_id")
    await state.clear()
    if control_id and control_id != callback.message.message_id:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=control_id)
        except Exception:
            pass
    try:
        await callback.message.edit_text("❌ Осмотр отменен.", reply_markup=get_main_inline_keyboard())
    except Exception:
        pass
    await callback.answer()

