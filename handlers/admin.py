from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_IDS
from storage import (
    set_group,
    list_groups,
    remove_group,
    find_group_by_chat_id,
    remove_group_by_chat_id,
)
from states import AdminStates
import re
import logging

router = Router()
logger = logging.getLogger(__name__)


def _admin_main_menu_private():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Список групп", callback_data="admin_list_groups")
    kb.button(text="ℹ️ Инструкция по привязке", callback_data="admin_help")
    kb.adjust(1, 1)
    return kb.as_markup()


def _admin_group_menu(is_bound: bool, shortname: str | None):
    kb = InlineKeyboardBuilder()
    if not is_bound:
        kb.button(text="🔗 Привязать эту группу", callback_data="admin_bind_here")
    else:
        kb.button(text=f"🔁 Перепривязать (сейчас: {shortname})", callback_data="admin_bind_here")
        kb.button(text="❌ Отвязать эту группу", callback_data="admin_unbind_here")
        kb.button(text="🔗 Ссылка для старта", callback_data="admin_show_link_here")
    kb.adjust(1)
    return kb.as_markup()


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext):
    logger.info("Admin entry: chat_type=%s user_id=%s chat_id=%s", message.chat.type, message.from_user.id, message.chat.id)
    await state.clear()
    # Private admin panel
    if message.chat.type == "private":
        if ADMIN_IDS and message.from_user.id not in ADMIN_IDS:
            logger.warning("Admin denied in private: user_id=%s", message.from_user.id)
            await message.answer("Доступ запрещён.")
            return
        logger.info("Show private admin menu to user_id=%s", message.from_user.id)
        await message.answer("Админ-панель", reply_markup=_admin_main_menu_private())
        return

    # Group context: only group admins can manage; bot must be admin
    if message.chat.type in ("group", "supergroup"):
        logger.info("Admin panel in group: chat_id=%s user_id=%s", message.chat.id, message.from_user.id)
        user_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if user_member.status not in ("administrator", "creator"):
            logger.warning("User is not admin of group: user_id=%s", message.from_user.id)
            return
        me = await message.bot.get_me()
        bot_member = await message.bot.get_chat_member(message.chat.id, me.id)
        if bot_member.status not in ("administrator", "creator"):
            logger.warning("Bot is not admin in group chat_id=%s", message.chat.id)
            await message.answer("Дайте боту права администратора для управления этой группой.")
            return

        found = find_group_by_chat_id(message.chat.id)
        short = found[0] if found else None
        logger.info("Group binding state: chat_id=%s bound=%s short=%s", message.chat.id, bool(found), short)
        await message.answer(
            "Управление этой группой:",
            reply_markup=_admin_group_menu(is_bound=bool(found), shortname=short)
        )


@router.callback_query(F.data == "admin_help")
async def admin_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "Чтобы привязать группу:\n"
        "1) Добавьте бота в группу и выдайте ему права администратора.\n"
        "2) В этой группе выполните /admin и нажмите «Привязать эту группу».\n"
        "3) Введите короткое имя (латиница/цифры/-/_), до 32 символов.\n"
        "После этого получите ссылку /start с коротким именем.",
        reply_markup=_admin_main_menu_private()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_list_groups")
async def admin_list_groups(callback: CallbackQuery):
    if callback.message.chat.type != "private":
        await callback.answer()
        return
    if ADMIN_IDS and callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("Доступ запрещён.")
        await callback.answer()
        return
    groups = list_groups()
    me = await callback.message.bot.get_me()
    username = me.username or ""

    if not groups:
        await callback.message.edit_text("Список групп пуст.", reply_markup=_admin_main_menu_private())
        await callback.answer()
        return

    kb = InlineKeyboardBuilder()
    lines = ["Зарегистрированные группы:", ""]
    for short, meta in groups.items():
        title = meta.get("title") or ""
        link = f"https://t.me/{username}?start={short}" if username else f"/start {short}"
        lines.append(f"• {short} — {title}")
        lines.append(f"  {link}")
        kb.button(text=f"Удалить: {short}", callback_data=f"admin_remove::{short}")
    kb.button(text="⬅️ Назад", callback_data="admin_back")
    kb.adjust(1, 1)
    await callback.message.edit_text("\n".join(lines), reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.edit_text("Админ-панель", reply_markup=_admin_main_menu_private())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_remove::"))
async def admin_remove_group(callback: CallbackQuery):
    if callback.message.chat.type != "private":
        await callback.answer()
        return
    if ADMIN_IDS and callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return
    short = callback.data.split("::", 1)[1]
    remove_group(short)
    await admin_list_groups(callback)


@router.callback_query(F.data == "admin_bind_here")
async def admin_bind_here(callback: CallbackQuery, state: FSMContext):
    logger.info("Bind request via menu: chat_id=%s user_id=%s", callback.message.chat.id, callback.from_user.id)
    # Must be from group admin, in group/supergroup, and bot admin
    if callback.message.chat.type not in ("group", "supergroup"):
        logger.warning("Bind requested not from group: chat_type=%s", callback.message.chat.type)
        await callback.answer()
        return
    user_member = await callback.message.bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if user_member.status not in ("administrator", "creator"):
        logger.warning("Bind denied: user not admin user_id=%s", callback.from_user.id)
        await callback.answer()
        return
    me = await callback.message.bot.get_me()
    bot_member = await callback.message.bot.get_chat_member(callback.message.chat.id, me.id)
    if bot_member.status not in ("administrator", "creator"):
        logger.warning("Bind denied: bot not admin chat_id=%s", callback.message.chat.id)
        await callback.message.answer("Дайте боту права администратора для управления этой группой.")
        await callback.answer()
        return
    await state.set_state(AdminStates.awaiting_group_shortname)
    await callback.message.answer("Введите короткое имя для этой группы (латиница/цифры/-/_), до 32 символов:")
    await callback.answer()


@router.message(AdminStates.awaiting_group_shortname)
async def admin_receive_shortname(message: Message, state: FSMContext):
    shortname = (message.text or "").strip()
    logger.info("Received shortname input: '%s' chat_id=%s user_id=%s", shortname, message.chat.id, message.from_user.id)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", shortname):
        logger.warning("Shortname validation failed: '%s'", shortname)
        await message.answer("Некорректное короткое имя. Разрешены латиница, цифры, '-', '_', до 32 символов.")
        return
    try:
        set_group(shortname, message.chat.id, message.chat.title)
        logger.info("Group set: short=%s chat_id=%s title=%s", shortname, message.chat.id, message.chat.title)
    except Exception as e:
        logger.exception("Failed to set group: short=%s chat_id=%s", shortname, message.chat.id)
        await message.answer("❌ Не удалось привязать группу. Проверьте логи на сервере.")
        return
    me = await message.bot.get_me()
    if me.username:
        deep_link = f"https://t.me/{me.username}?start={shortname}"
    else:
        deep_link = f"/start {shortname}"
    await state.clear()
    await message.answer(f"✅ Группа привязана как '{shortname}'.\nСсылка для старта: {deep_link}")


@router.callback_query(F.data == "admin_unbind_here")
async def admin_unbind_here(callback: CallbackQuery):
    logger.info("Unbind request: chat_id=%s user_id=%s", callback.message.chat.id, callback.from_user.id)
    if callback.message.chat.type not in ("group", "supergroup"):
        await callback.answer()
        return
    user_member = await callback.message.bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if user_member.status not in ("administrator", "creator"):
        await callback.answer()
        return
    ok = False
    try:
        ok = remove_group_by_chat_id(callback.message.chat.id)
    except Exception:
        logger.exception("Failed to unbind group chat_id=%s", callback.message.chat.id)
    if ok:
        await callback.message.answer("✅ Группа отвязана.")
    else:
        await callback.message.answer("Группа не была привязана.")
    await callback.answer()


@router.callback_query(F.data == "admin_show_link_here")
async def admin_show_link_here(callback: CallbackQuery):
    found = find_group_by_chat_id(callback.message.chat.id)
    if not found:
        await callback.message.answer("Группа не привязана.")
        await callback.answer()
        return
    short, _ = found
    me = await callback.message.bot.get_me()
    if me.username:
        deep_link = f"https://t.me/{me.username}?start={short}"
    else:
        deep_link = f"/start {short}"
    await callback.message.answer(f"Ссылка для старта: {deep_link}")
    await callback.answer()


