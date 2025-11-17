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
from media_utils import stamp_and_send_album, queue_album_photo
import asyncio

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

@router.callback_query(F.data == "patrol")
async def handle_patrol(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photos_received=0, photos=[])
    await state.set_state(Form.patrol_photos)
    
    await callback.message.edit_text(
        "🚶 <b>Обход объекта</b>\n\n"
        "Сделайте одну или несколько фотографий через камеру мобильного телефона (не в приложении Телеграм).\n"
        "Затем через скрепку прикрепите нужное количество фотографий и отправьте.\n\n"
        "Фото отправятся одним сообщением, если вы прикрепите их сразу альбомом.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(Form.patrol_photos, F.photo | F.video)
async def handle_patrol_photo(message: Message, state: FSMContext):
    chat_id = get_chat_id_for_user(message.from_user.id)
    if not chat_id:
        await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
        return
    # If album incoming
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
                    f"🚶 <b>Обход объекта</b>\n"
                    f"⏰ Время: {datetime.now().strftime('%H:%M')}\n"
                    f"📸 Количество медиа: {len(files2)}\n"
                    f"📎 Обход территории: [альбом]"
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
                    f"✅ Обход завершен! Отправлено {len(files2)} медиа в группу.",
                    reply_markup=get_main_inline_keyboard()
                )
                # Log
                short = get_user_group_shortname(message.from_user.id)
                if short:
                    await gsheets.log_event(
                        shortname=short,
                        chat_id=chat_id,
                        event_type="Обход",
                        author_full_name=message.from_user.full_name,
                        author_username=message.from_user.username,
                        message_id=None,
                        text=f"Количество медиа: {len(files2)}"
                    )
            asyncio.create_task(_flush())
        return
    # Single media -> send immediately
    header = (
        f"🚶 <b>Обход объекта</b>\n"
        f"⏰ Время: {datetime.now().strftime('%H:%M')}\n"
        f"📸 Количество медиа: 1\n"
        f"📎 Обход территории: [альбом]"
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
        "✅ Обход завершен! Отправлено 1 медиа в группу.",
        reply_markup=get_main_inline_keyboard()
    )
    short = get_user_group_shortname(message.from_user.id)
    if short:
        await gsheets.log_event(
            shortname=short,
            chat_id=chat_id,
            event_type="Обход",
            author_full_name=message.from_user.full_name,
            author_username=message.from_user.username,
            message_id=None,
            text="Количество фото: 1"
        )

@router.callback_query(Form.patrol_photos, F.data == "finish_patrol")
async def handle_finish_patrol(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data["photos"]
    photos_count = len(photos)
    
    if photos_count == 0:
        await callback.message.edit_text(
            "❌ Обход не может быть завершен без фотографий.\n\n"
            "Прикрепите хотя бы одно фото через скрепку:",
            reply_markup=get_patrol_keyboard()
        )
        await callback.answer()
        return
    
    # Отправляем альбом фото в группу
    current_time = datetime.now().strftime("%H:%M")
    caption = (
        f"🚶 <b>Обход объекта</b>\n"
        f"⏰ Время: {current_time}\n"
        f"📸 Количество фото: {photos_count}\n"
        f"📎 Обход территории: [альбом]"
    )
    chat_id = get_chat_id_for_user(callback.from_user.id)
    if not chat_id:
        await callback.message.edit_text(
            "Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.",
            reply_markup=get_main_inline_keyboard()
        )
        await callback.answer()
        return
    await stamp_and_send_album(
        bot=callback.message.bot,
        chat_id=chat_id,
        file_ids=photos,
        caption=caption,
        parse_mode=ParseMode.HTML
    )
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ Обход завершен! Отправлено {photos_count} фото в группу.",
        reply_markup=get_main_inline_keyboard()
    )
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

