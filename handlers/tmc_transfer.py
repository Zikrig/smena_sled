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
from media_utils import stamp_and_send_album
import asyncio

router = Router()

@router.callback_query(F.data == "transfer_tmc")
async def handle_transfer_tmc(callback: CallbackQuery, state: FSMContext):
    await state.update_data(media_files=[], media_captions=[], media_kinds=[], flush_scheduled=False)
    await state.set_state(Form.transfer_tmc_photo)
    await callback.message.edit_text(
        "📋 <b>Передача ТМЦ на посту</b>\n\n"
        "Сделайте одну или несколько фотографий через камеру мобильного телефона (не в приложении Телеграм).\n"
        "Затем через скрепку прикрепите фото журнала передачи смены и отправьте.\n\n"
        "Фото отправятся одним сообщением, если вы прикрепите их сразу альбомом.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.transfer_tmc_photo, F.photo | F.video)
async def handle_tmc_photo(message: Message, state: FSMContext):
    chat_id = get_chat_id_for_user(message.from_user.id)
    if not chat_id:
        await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
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
                    f"📋 <b>Передача ТМЦ на посту</b>\n"
                    f"⏰ Время: {datetime.now().strftime('%H:%M')}\n"
                    f"📝 Журнал передачи смены: [альбом]\n"
                    f"📸 Количество медиа: {len(files2)}"
                )
                await stamp_and_send_album(
                    bot=message.bot,
                    chat_id=chat_id,
                    file_ids=files2,
                    captions=caps2,
                    kinds=kinds2,
                    header=header,
                    parse_mode=ParseMode.HTML
                )
                await state.clear()
                await message.answer(
                    f"✅ Передача ТМЦ завершена! Отправлено {len(files2)} медиа в группу.",
                    reply_markup=get_main_inline_keyboard()
                )
                short = get_user_group_shortname(message.from_user.id)
                if short:
                    await gsheets.log_event(
                        shortname=short,
                        chat_id=chat_id,
                        event_type="Передача ТМЦ",
                        author_full_name=message.from_user.full_name,
                        author_username=message.from_user.username,
                        message_id=None,
                        text=f"Количество медиа: {len(files2)}"
                    )
            asyncio.create_task(_flush())
        return
    # Single media
    header = (
        f"📋 <b>Передача ТМЦ на посту</b>\n"
        f"⏰ Время: {datetime.now().strftime('%H:%M')}\n"
        f"📝 Журнал передачи смены: [альбом]\n"
        f"📸 Количество медиа: 1"
    )
    if message.photo:
        await stamp_and_send_album(
            bot=message.bot,
            chat_id=chat_id,
            file_ids=[message.photo[-1].file_id],
            captions=[message.caption or None],
            kinds=["photo"],
            header=header,
            parse_mode=ParseMode.HTML
        )
    else:
        await stamp_and_send_album(
            bot=message.bot,
            chat_id=chat_id,
            file_ids=[message.video.file_id],
            captions=[message.caption or None],
            kinds=["video"],
            header=header,
            parse_mode=ParseMode.HTML
        )
    await state.clear()
    await message.answer(
        "✅ Передача ТМЦ завершена! Отправлено 1 медиа в группу.",
        reply_markup=get_main_inline_keyboard()
    )
    short = get_user_group_shortname(message.from_user.id)
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Передача ТМЦ",
            author_full_name=message.from_user.full_name,
            author_username=message.from_user.username,
            message_id=None,
            text="Количество фото: 1"
        )

