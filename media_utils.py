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
    kinds: Optional[List[str]] = None,  # 'photo' or 'video' per item; default all 'photo'
) -> None:
    """
    Downloads photos by file_ids, stamps date/time on each, and sends as media groups (chunks of 10).
    Caption is added only to the first item of the first group.
    """
    if not file_ids:
        return
    tmp_dir = tempfile.mkdtemp()
    stamped_paths: List[Optional[str]] = []  # path for photos, None for videos
    try:
        for idx, fid in enumerate(file_ids):
            kind = (kinds[idx] if kinds and idx < len(kinds) else "photo").lower()
            if kind == "video":
                # For videos we don't stamp, keep placeholder
                stamped_paths.append(None)
                continue
            in_path = os.path.join(tmp_dir, f"in_{fid}.jpg")
            out_path = os.path.join(tmp_dir, f"out_{fid}.jpg")
            file = await bot.get_file(fid)
            await bot.download(file, destination=in_path)
            date_text = datetime.now().strftime("%d.%m.%Y %H:%M")
            ImageProcessor.add_text_with_outline(in_path, out_path, date_text)
            stamped_paths.append(out_path)

        # Send in chunks of up to 10
        first = True
        for i in range(0, len(stamped_paths), 10):
            chunk = stamped_paths[i:i + 10]
            media = []
            for idx, p in enumerate(chunk):
                absolute_index = i + idx
                # Determine per-item caption
                item_caption: Optional[str] = None
                if captions and absolute_index < len(captions):
                    item_caption = captions[absolute_index]
                # Apply header to the very first item
                if first and idx == 0:
                    if header and item_caption:
                        item_caption = f"{header}\n{item_caption}"
                    elif header and not item_caption:
                        item_caption = header
                    elif not header and caption:
                        item_caption = caption
                # Select media type
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
            await bot.send_media_group(chat_id=chat_id, media=media)
            first = False
    finally:
        # Cleanup temp files
        try:
            for name in os.listdir(tmp_dir):
                try:
                    os.remove(os.path.join(tmp_dir, name))
                except Exception:
                    pass
            os.rmdir(tmp_dir)
        except Exception:
            pass


# Simple in-memory buffers for incoming Telegram media groups
_ALBUM_BUFFERS: Dict[Tuple[int, str], Dict] = {}


async def queue_album_photo(
    bot,
    chat_id: int,
    media_group_id: str,
    file_id: str,
    photo_caption: Optional[str],
    header_template: str,
    include_date: bool,
    parse_mode: Optional[ParseMode] = None,
    delay_seconds: float = 0.8,
):
    """
    Queue a photo belonging to a Telegram media group; after a short delay,
    all photos with the same media_group_id will be sent as an album with per-photo captions.
    header_template supports {time}, {date}, {count} placeholders.
    """
    key = (chat_id, media_group_id)
    buf = _ALBUM_BUFFERS.get(key)
    if not buf:
        buf = {
            "files": [],
            "captions": [],
            "header_template": header_template,
            "include_date": include_date,
            "parse_mode": parse_mode,
            "bot": bot,
            "chat_id": chat_id,
            "flushing": False,
        }
        _ALBUM_BUFFERS[key] = buf
    buf["files"].append(file_id)
    buf["captions"].append(photo_caption)

    # Schedule flush if not already scheduled
    if not buf["flushing"]:
        buf["flushing"] = True

        async def _flush():
            await asyncio.sleep(delay_seconds)
            current = _ALBUM_BUFFERS.pop(key, None)
            if not current:
                return
            files = current["files"]
            caps = current["captions"]
            now = datetime.now()
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%d.%m.%Y")
            header = current["header_template"].format(
                time=time_str,
                date=date_str if include_date else "",
                count=len(files),
            )
            await stamp_and_send_album(
                bot=current["bot"],
                chat_id=current["chat_id"],
                file_ids=files,
                captions=caps,
                header=header,
                parse_mode=current["parse_mode"],
            )

        asyncio.create_task(_flush())


