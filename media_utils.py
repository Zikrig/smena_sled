import asyncio
import os
import tempfile
from typing import List, Optional, Dict, Tuple

from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo
from datetime import datetime

from image_processor import ImageProcessor


async def stamp_and_send_album(
    bot,
    chat_id: int,
    file_ids: List[str],
    caption: Optional[str] = None,
    parse_mode: Optional[ParseMode] = None,
    captions: Optional[List[Optional[str]]] = None,
    header: Optional[str] = None,
    kinds: Optional[List[str]] = None,  # «photo» или «video» для каждого элемента; по умолчанию все «photo»
) -> List[int]:
    """
    Загружает медиа по file_id, ставит штамп даты/времени и отправляет альбомами (до 10 элементов).
    Общая подпись добавляется только к первому элементу первого альбома.
    Возвращает список message_id отправленных медиа (по порядку).
    """
    if not file_ids:
        return
    tmp_dir = tempfile.mkdtemp()
    stamped_paths: List[Optional[str]] = []  # путь для фото, None для видео
    sent_message_ids: List[int] = []
    try:
        for idx, fid in enumerate(file_ids):
            kind = (kinds[idx] if kinds and idx < len(kinds) else "photo").lower()
            if kind == "video":
                # Видео не штампуем — сохраняем заглушку
                stamped_paths.append(None)
                continue
            in_path = os.path.join(tmp_dir, f"in_{fid}.jpg")
            out_path = os.path.join(tmp_dir, f"out_{fid}.jpg")
            file = await bot.get_file(fid)
            await bot.download(file, destination=in_path)
            date_text = datetime.now().strftime("%d.%m.%Y %H:%M")
            ImageProcessor.add_text_with_outline(in_path, out_path, date_text)
            stamped_paths.append(out_path)

        # Отправляем блоками максимум по 10 элементов
        first = True
        for i in range(0, len(stamped_paths), 10):
            chunk = stamped_paths[i:i + 10]
            media = []
            for idx, p in enumerate(chunk):
                absolute_index = i + idx
                # Определяем подпись для конкретного элемента
                item_caption: Optional[str] = None
                if captions and absolute_index < len(captions):
                    item_caption = captions[absolute_index]
                # Шапку добавляем только к самому первому элементу
                if first and idx == 0:
                    if header and item_caption:
                        item_caption = f"{header}\n{item_caption}"
                    elif header and not item_caption:
                        item_caption = header
                    elif not header and caption:
                        item_caption = caption
                # Определяем тип медиа
                kind = (kinds[absolute_index] if kinds and absolute_index < len(kinds) else "photo").lower()
                if kind == "video":
                    media.append(InputMediaVideo(
                        media=file_ids[absolute_index],
                        caption=item_caption,
                        parse_mode=parse_mode if item_caption else None
                    ))
                else:
                    media.append(InputMediaPhoto(
                        media=FSInputFile(p) if p else file_ids[absolute_index],
                        caption=item_caption,
                        parse_mode=parse_mode if item_caption else None
                    ))
            sent_messages = await bot.send_media_group(chat_id=chat_id, media=media)
            sent_message_ids.extend(msg.message_id for msg in sent_messages)
            first = False
    finally:
        # Удаляем временные файлы
        try:
            for name in os.listdir(tmp_dir):
                try:
                    os.remove(os.path.join(tmp_dir, name))
                except Exception:
                    pass
            os.rmdir(tmp_dir)
        except Exception:
            pass

    return sent_message_ids


# Простые буферы в памяти для входящих альбомов Telegram
_ALBUM_BUFFERS: Dict[Tuple[int, str], Dict] = {}

