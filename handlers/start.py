from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from config import GROUP_ID
from states import Form
from keyboards import get_main_inline_keyboard, get_cancel_keyboard
from aiogram.enums import ParseMode

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
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
        await message.bot.send_location(
            chat_id=GROUP_ID,
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
        
@router.message(StateFilter(None), F.text)
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
        