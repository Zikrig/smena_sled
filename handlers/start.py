from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from storage import set_user_group, get_chat_id_for_user, get_group, get_user_group_shortname
from google_sheets import gsheets
from states import Form
from keyboards import get_main_inline_keyboard, get_cancel_keyboard
from aiogram.enums import ParseMode

router = Router()

@router.message(CommandStart(), F.chat.type.in_(("group", "supergroup")))
async def cmd_start_in_group(message: Message, state: FSMContext):
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("administrator", "creator"):
            await message.reply("❌ У вас нет доступа к этой команде в группе. Используйте бота в личных сообщениях.")
            return
    except Exception:
        # Если не удалось проверить — отвечаем безопасно
        await message.reply("❌ У вас нет доступа к этой команде в группе. Используйте бота в личных сообщениях.")
        return
    # Для админов в группе ничего не делаем (или можно подсказать про /admin)
    # await message.reply("Откройте админ-панель командой /admin")

@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    # Deep-link payload handling: /start <shortname>
    try:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) > 1:
            payload = parts[1].strip()
            group_meta = get_group(payload)
            if group_meta:
                if set_user_group(message.from_user.id, payload):
                    title = group_meta.get("title") or payload
                    await message.answer(f"✅ Вы привязаны к группе: {title}")
            else:
                await message.answer("⚠️ Ссылка недействительна: группа не найдена.")
    except Exception:
        pass
    await message.answer(
        "🛡️ <b>БОТ ПОСТА ОХРАНЫ</b>\n\n"
        "Добро пожаловать! Этот бот предназначен для:\n"
        "• Начала смены с записью видео кружка\n"
        "• Передачи ТМЦ на посту\n"
        "• Фиксации обходов объекта\n"
        "• Осмотра багажников и кузовов\n"
        "• Проверки поста\n"
        "• Отправки сообщений\n"
        "• Вызовов служб\n\n"
        "<b>Выберите действие:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_inline_keyboard()
    )

@router.callback_query(F.data == "cancel_action")
async def handle_inline_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено", reply_markup=get_main_inline_keyboard())
    await callback.answer()

@router.callback_query(F.data == "start_shift")
async def handle_start_shift(callback: CallbackQuery, state: FSMContext):
    await state.update_data(action_type="start")
    await state.set_state(Form.waiting_round)
    await callback.message.edit_text(
        "📸 <b>Начало смены</b>\n\n"
        "Запишите видео кружочек для подтверждения начала смены:"+
        '''Для записи видео кружка:
1. Кнопка начала записи кружка находится справа снизу. Если вы видите там значок диктофона – переключите на запись кружка, нажав на него КОРОТКО.
3. Зажмите кнопку (кружок в квадрате) и записывайте видеокружок.
4. Глядя в камеру сообщите ФИО, дату и время начала смены.
5. Отпустите кнопку – сообщение отправится автоматически.''',
        parse_mode=ParseMode.HTML,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "send_location")
async def ask_location(callback: CallbackQuery, state: FSMContext):
    location_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    # Отправляем новое сообщение с реплай-клавиатурой вместо редактирования старого
    await callback.message.answer(
        "Нажмите кнопку ниже чтобы отправить геолокацию:",
        reply_markup=location_keyboard
    )
    await state.set_state("waiting_location")
    await callback.answer()

@router.message(F.content_type == "location")
async def handle_location(message: Message, state: FSMContext):
    if await state.get_state() == "waiting_location":
        chat_id = get_chat_id_for_user(message.from_user.id)
        if not chat_id:
            await message.answer("Не настроена группа для отправки. Получите ссылку у администратора и запустите бота по ней.")
            return
        sent = await message.bot.send_location(
            chat_id=chat_id,
            latitude=message.location.latitude,
            longitude=message.location.longitude
        )
        await message.answer(
            "✅ Геолокация отправлена в группу!",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await message.answer(
            "Выберите действие:",
            reply_markup=get_main_inline_keyboard()
        )
        # Log to Google Sheets
        short = get_user_group_shortname(message.from_user.id)
        if short:
            coords = f"{message.location.latitude}, {message.location.longitude}"
            await gsheets.log_event(
                shortname=short,
                chat_id=chat_id,
                event_type="Геолокация",
                author_full_name=message.from_user.full_name,
                author_username=message.from_user.username,
                message_id=sent.message_id,
                text=coords
            )
        
@router.message(StateFilter(None), F.text, F.chat.type == "private", ~F.text.startswith("/"))
async def handle_any_text_as_start(message: Message, state: FSMContext):
    await cmd_start(message, state)
@router.message(F.text == "❌ Отмена")
async def handle_cancel(message: Message, state: FSMContext):
    if await state.get_state() == "waiting_location":
        await message.answer(
            "❌ Отменено",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        await message.answer(
            "Выберите действие:",
            reply_markup=get_main_inline_keyboard()
        )
        