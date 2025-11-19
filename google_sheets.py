import os
import asyncio
from typing import Optional, List
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from storage import get_group


class SheetsClient:
    def __init__(self) -> None:
        self.sheet_id: Optional[str] = os.getenv("GOOGLE_SHEET_ID")
        self.credentials_path: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        self.scopes: List[str] = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        self._client: Optional[gspread.Client] = None
        self._spreadsheet = None
        self._worksheets_cache: dict[str, any] = {}

    async def _ensure_client(self) -> bool:
        if not self.sheet_id:
            return False
        if self._client:
            return True
        if not os.path.exists(self.credentials_path):
            return False
        try:
            creds = await asyncio.to_thread(
                Credentials.from_service_account_file,
                self.credentials_path,
                scopes=self.scopes,
            )
            self._client = await asyncio.to_thread(gspread.authorize, creds)
            self._spreadsheet = await asyncio.to_thread(
                self._client.open_by_url, f"https://docs.google.com/spreadsheets/d/{self.sheet_id}"
            )
            return True
        except Exception:
            return False

    async def _ensure_worksheet(self, shortname: str):
        if shortname in self._worksheets_cache:
            return self._worksheets_cache[shortname]

        if not await self._ensure_client():
            return None

        try:
            ws = await asyncio.to_thread(self._spreadsheet.worksheet, shortname)
        except Exception:
            # Создаём лист, если он ещё не существует
            ws = await asyncio.to_thread(self._spreadsheet.add_worksheet, title=shortname, rows=1000, cols=10)
            # Записываем заголовки
            headers = ["Дата", "Время", "Событие", "Автор", "Ссылка на пост", "Текст"]
            await asyncio.to_thread(ws.append_row, headers)

        self._worksheets_cache[shortname] = ws
        return ws

    @staticmethod
    def _format_author(full_name: str, username: Optional[str]) -> str:
        uname = f"@{username}" if username else ""
        return f"{full_name} {uname}".strip()

    @staticmethod
    def build_message_link(chat_id: int, message_id: int) -> str:
        # Работает для закрытых групп без username: https://t.me/c/<id>/<message_id>
        # где <id> — идентификатор канала/группы без префикса -100
        try:
            cid = str(chat_id)
            if cid.startswith("-100"):
                cid = cid[4:]
            return f"https://t.me/c/{cid}/{message_id}"
        except Exception:
            return ""

    async def log_event(
        self,
        shortname: str,
        chat_id: int,
        event_type: str,
        author_full_name: str,
        author_username: Optional[str],
        message_id: Optional[int],
        text: str = "",
    ) -> bool:
        ws = await self._ensure_worksheet(shortname)
        if not ws:
            return False
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        time_str = now.strftime("%H:%M:%S")
        author = self._format_author(author_full_name, author_username)
        link = self.build_message_link(chat_id, message_id) if message_id else ""
        row = [date_str, time_str, event_type, author, link or "Нет ссылки", text or ""]
        try:
            await asyncio.to_thread(ws.append_row, row)
            return True
        except Exception:
            return False


gsheets = SheetsClient()


