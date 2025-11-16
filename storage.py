import json
import os
import logging
from typing import Dict, Optional, Tuple

# Paths
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
USERS_FILE = os.path.join(DATA_DIR, "user_groups.json")

logger = logging.getLogger(__name__)

def _ensure_storage() -> None:
    logger.debug("Ensuring storage directories and files exist")
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(GROUPS_FILE):
        logger.info("Creating missing groups file at %s", GROUPS_FILE)
        _write_json(GROUPS_FILE, {})
    if not os.path.exists(USERS_FILE):
        logger.info("Creating missing users file at %s", USERS_FILE)
        _write_json(USERS_FILE, {})


def _read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("JSON file not found, using default: %s", path)
        return default
    except json.JSONDecodeError:
        # Corrupted file: back up and reset
        try:
            os.replace(path, f"{path}.bak")
        except Exception:
            pass
        logger.error("JSON decode error, backed up and resetting file: %s", path)
        return default


def _write_json(path: str, data) -> None:
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        logger.debug("Wrote JSON file: %s (size=%s)", path, len(json.dumps(data)))
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _load_groups() -> Dict[str, Dict]:
    _ensure_storage()
    return _read_json(GROUPS_FILE, {})


def _save_groups(groups: Dict[str, Dict]) -> None:
    _ensure_storage()
    _write_json(GROUPS_FILE, groups)


def _load_users() -> Dict[str, str]:
    _ensure_storage()
    return _read_json(USERS_FILE, {})


def _save_users(users: Dict[str, str]) -> None:
    _ensure_storage()
    _write_json(USERS_FILE, users)


# Group management
def list_groups() -> Dict[str, Dict]:
    groups = _load_groups()
    logger.debug("Listing groups: %s", list(groups.keys()))
    return groups


def get_group(shortname: str) -> Optional[Dict]:
    groups = _load_groups()
    logger.debug("Get group by shortname: %s found=%s", shortname, shortname in groups)
    return groups.get(shortname)


def set_group(shortname: str, chat_id: int, title: Optional[str] = None) -> None:
    short = shortname.strip()
    groups = _load_groups()
    groups[short] = {"chat_id": int(chat_id), "title": title or ""}
    logger.info("Saving group mapping: %s -> %s (%s)", short, chat_id, title or "")
    _save_groups(groups)


def remove_group(shortname: str) -> bool:
    groups = _load_groups()
    if shortname in groups:
        del groups[shortname]
        _save_groups(groups)
        logger.info("Removed group by shortname: %s", shortname)
        return True
    logger.warning("Attempted to remove non-existing group: %s", shortname)
    return False


def find_group_by_chat_id(chat_id: int) -> Optional[Tuple[str, Dict]]:
    groups = _load_groups()
    for short, meta in groups.items():
        try:
            if int(meta.get("chat_id")) == int(chat_id):
                return short, meta
        except Exception:
            continue
    return None


def remove_group_by_chat_id(chat_id: int) -> bool:
    groups = _load_groups()
    target = None
    for short, meta in groups.items():
        try:
            if int(meta.get("chat_id")) == int(chat_id):
                target = short
                break
        except Exception:
            continue
    if target:
        del groups[target]
        _save_groups(groups)
        return True
    return False


# User to group mapping
def set_user_group(user_id: int, shortname: str) -> bool:
    groups = _load_groups()
    if shortname not in groups:
        logger.warning("User mapping failed, unknown shortname: user_id=%s short=%s", user_id, shortname)
        return False
    users = _load_users()
    users[str(int(user_id))] = shortname
    _save_users(users)
    logger.info("Mapped user to group: user_id=%s short=%s", user_id, shortname)
    return True


def get_user_group_shortname(user_id: int) -> Optional[str]:
    users = _load_users()
    short = users.get(str(int(user_id)))
    logger.debug("Get user group shortname: user_id=%s short=%s", user_id, short)
    return short


def get_user_group_chat_id(user_id: int) -> Optional[int]:
    short = get_user_group_shortname(user_id)
    if not short:
        return None
    groups = _load_groups()
    group = groups.get(short)
    if not group:
        return None
    return int(group.get("chat_id"))


def get_chat_id_for_user(user_id: int) -> Optional[int]:
    chat_id = get_user_group_chat_id(user_id)
    if chat_id is not None:
        return chat_id
    # Fallback to single-group mode if configured
    try:
        from config import GROUP_ID
    except Exception:
        GROUP_ID = None
    if GROUP_ID:
        try:
            return int(GROUP_ID)
        except Exception:
            return None
    return None


