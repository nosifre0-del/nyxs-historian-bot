import os
import sys
import json
import time
import re
import base64
import hashlib
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

import requests


# ============================================================
# NYXS AI TELEGRAM BOT
# VERCEL / SINGLE PYTHON FUNCTION
# ============================================================

DEVELOPER_NAME = "NYXS"
DEVELOPER_HANDLE = "@h1_c87"

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0").strip() or "0")
except Exception:
    ADMIN_ID = 0


# ============================================================
# AI SYSTEM 1
# ============================================================

AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai").strip().lower()
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini").strip()
AI_BASE_URL = os.environ.get(
    "AI_BASE_URL",
    "https://api.openai.com/v1"
).strip().rstrip("/")


# ============================================================
# AI SYSTEM 2 / FAILOVER
# ============================================================

AI2_PROVIDER = os.environ.get("AI2_PROVIDER", "chattide").strip().lower()
AI2_API_KEY = os.environ.get("AI2_API_KEY", "").strip()
AI2_MODEL = os.environ.get("AI2_MODEL", "gpt-5.6-luna").strip()
AI2_BASE_URL = os.environ.get("AI2_BASE_URL", "").strip().rstrip("/")

CHATTIDE_URL = os.environ.get(
    "CHATTIDE_URL",
    "https://api.chattide.ai/aigc/chat/v2/professional/stream"
).strip()


# ============================================================
# IMAGE GENERATION
# ============================================================

IMAGE_PROVIDER = os.environ.get(
    "IMAGE_PROVIDER", "openai"
).strip().lower()

IMAGE_API_KEY = os.environ.get(
    "IMAGE_API_KEY", AI_API_KEY
).strip()

IMAGE_MODEL = os.environ.get(
    "IMAGE_MODEL", "dall-e-3"
).strip()

IMAGE_BASE_URL = os.environ.get(
    "IMAGE_BASE_URL",
    "https://api.openai.com/v1"
).strip().rstrip("/")

IMAGE2_PROVIDER = os.environ.get(
    "IMAGE2_PROVIDER", "stability"
).strip().lower()

IMAGE2_API_KEY = os.environ.get(
    "IMAGE2_API_KEY", ""
).strip()

IMAGE2_MODEL = os.environ.get(
    "IMAGE2_MODEL",
    "stable-diffusion-xl-1024-v1-0"
).strip()

IMAGE2_BASE_URL = os.environ.get(
    "IMAGE2_BASE_URL",
    "https://api.stability.ai"
).strip().rstrip("/")

IMAGE_SIZE = os.environ.get(
    "IMAGE_SIZE", "1024x1024"
).strip()


# ============================================================
# SEARCH
# ============================================================

SEARCH_PROVIDER = os.environ.get(
    "SEARCH_PROVIDER", "auto"
).strip().lower()

SEARCH_API_KEY = os.environ.get(
    "SEARCH_API_KEY", ""
).strip()

SEARCH_ENGINE_ID = os.environ.get(
    "SEARCH_ENGINE_ID", ""
).strip()

BRAVE_API_KEY = os.environ.get(
    "BRAVE_API_KEY", ""
).strip()

SEARCH_CACHE_TTL = 1800

SEARCH_RESULTS_LIMIT = 10
SEARCH_TIMEOUT = 15


# ============================================================
# UPSTASH
# ============================================================

UPSTASH_URL = os.environ.get(
    "UPSTASH_REDIS_REST_URL", ""
).strip().rstrip("/")

UPSTASH_TOKEN = os.environ.get(
    "UPSTASH_REDIS_REST_TOKEN", ""
).strip()


# ============================================================
# GENERAL
# ============================================================

MAX_HISTORY_MESSAGES = 30
SUMMARIZE_TRIGGER = 24
MAX_TELEGRAM_LENGTH = 4000

DEV_CONTACT = os.environ.get(
    "DEV_CONTACT",
    "https://t.me/h1_c87"
).strip()

WEBHOOK_SECRET = os.environ.get(
    "WEBHOOK_SECRET", ""
).strip()


# ============================================================
# RATE LIMITS
# ============================================================

RATE_LIMIT_CHAT = (40, 3600)
RATE_LIMIT_SEARCH = (15, 3600)
RATE_LIMIT_IMAGE = (5, 3600)
RATE_LIMIT_PROFILE = (8, 3600)


TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
    if BOT_TOKEN else ""
)


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger("NYXS")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    )
    logger.addHandler(handler)


# ============================================================
# UPSTASH MEMORY
# ============================================================

class Memory:

    @staticmethod
    def enabled():
        return bool(UPSTASH_URL and UPSTASH_TOKEN)

    @staticmethod
    def headers():
        return {
            "Authorization": f"Bearer {UPSTASH_TOKEN}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def cmd(*args):
        if not Memory.enabled():
            return None

        try:
            r = requests.post(
                UPSTASH_URL,
                headers=Memory.headers(),
                json=list(args),
                timeout=8
            )

            if not r.ok:
                logger.error(
                    "UPSTASH %s %s",
                    r.status_code,
                    r.text[:300]
                )
                return None

            return r.json().get("result")

        except Exception as exc:
            logger.error("UPSTASH ERROR: %s", exc)
            return None

    @staticmethod
    def get(key):
        return Memory.cmd("GET", key)

    @staticmethod
    def set(key, value, ex=None):
        if ex:
            return Memory.cmd(
                "SET",
                key,
                value,
                "EX",
                str(ex)
            )

        return Memory.cmd("SET", key, value)

    @staticmethod
    def delete(key):
        return Memory.cmd("DEL", key)

    @staticmethod
    def get_history(chat_id):
        raw = Memory.get(f"history:{chat_id}")

        if not raw:
            return []

        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @staticmethod
    def save_history(chat_id, history):
        history = history[-MAX_HISTORY_MESSAGES:]

        Memory.set(
            f"history:{chat_id}",
            json.dumps(
                history,
                ensure_ascii=False
            ),
            ex=604800
        )

    @staticmethod
    def clear_history(chat_id):
        Memory.delete(f"history:{chat_id}")

    @staticmethod
    def register_user(
        chat_id,
        first_name="مجهول",
        username=""
    ):
        if not Memory.enabled():
            return

        try:
            raw = Memory.get("known_users")

            users = (
                json.loads(raw)
                if raw else {}
            )

            users[str(chat_id)] = {
                "first_name": first_name,
                "username": username,
                "last_active": datetime.utcnow().isoformat(),
            }

            Memory.set(
                "known_users",
                json.dumps(
                    users,
                    ensure_ascii=False
                )
            )

        except Exception as exc:
            logger.error(
                "REGISTER ERROR: %s",
                exc
            )

    @staticmethod
    def get_users():
        raw = Memory.get("known_users")

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except Exception:
            return {}

    @staticmethod
    def get_banned():
        raw = Memory.get("banned_users")

        if not raw:
            return []

        try:
            data = json.loads(raw)

            if isinstance(data, list):
                return data

        except Exception:
            pass

        return []

    @staticmethod
    def ban(chat_id):
        banned = Memory.get_banned()

        if chat_id not in banned:
            banned.append(chat_id)

        Memory.set(
            "banned_users",
            json.dumps(banned)
        )

    @staticmethod
    def unban(chat_id):
        banned = [
            x for x in Memory.get_banned()
            if x != chat_id
        ]

        Memory.set(
            "banned_users",
            json.dumps(banned)
        )

    @staticmethod
    def is_banned(chat_id):
        return chat_id in Memory.get_banned()


# ============================================================
# RATE LIMITER
# ============================================================

class RateLimiter:

    @staticmethod
    def check(
        chat_id,
        action,
        limit,
        window
    ):
        if not Memory.enabled():
            return True, 0

        key = f"ratelimit:{action}:{chat_id}"

        raw = Memory.get(key)

        now = int(time.time())

        if not raw:
            Memory.set(
                key,
                json.dumps({
                    "count": 1,
                    "start": now
                }),
                ex=window
            )

            return True, 0

        try:
            data = json.loads(raw)

        except Exception:
            Memory.set(
                key,
                json.dumps({
                    "count": 1,
                    "start": now
                }),
                ex=window
            )

            return True, 0

        count = data.get("count", 0)

        start = data.get(
            "start",
            now
        )

        remaining_window = (
            window - (now - start)
        )

        if remaining_window <= 0:

            Memory.set(
                key,
                json.dumps({
                    "count": 1,
                    "start": now
                }),
                ex=window
            )

            return True, 0

        if count >= limit:
            return False, remaining_window

        data["count"] = count + 1

        Memory.set(
            key,
            json.dumps(data),
            ex=remaining_window
        )

        return True, 0


# ============================================================
# DAILY STATS
# ============================================================

class UsageStats:

    @staticmethod
    def today_key():
        return datetime.utcnow().strftime("%Y-%m-%d")

    @staticmethod
    def increment(chat_id, kind):

        if not Memory.enabled():
            return

        key = f"stats:{UsageStats.today_key()}"

        raw = Memory.get(key)

        try:
            data = (
                json.loads(raw)
                if raw else {}
            )
        except Exception:
            data = {}

        data[kind] = (
            data.get(kind, 0) + 1
        )

        users = data.get(
            "users",
            []
        )

        if chat_id not in users:
            users.append(chat_id)

        data["users"] = users

        Memory.set(
            key,
            json.dumps(data),
            ex=2592000
        )

    @staticmethod
    def get(date_str=None):

        date_str = (
            date_str
            or UsageStats.today_key()
        )

        raw = Memory.get(
            f"stats:{date_str}"
        )

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except Exception:
            return {}


# ============================================================
# TELEGRAM
# ============================================================

def telegram(method, payload=None):

    if not TELEGRAM_API:
        return None

    try:
        r = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload or {},
            timeout=25
        )

        if not r.ok:

            logger.error(
                "TELEGRAM %s: %s",
                r.status_code,
                r.text[:500]
            )

            return None

        return r.json()

    except Exception as exc:

        logger.error(
            "TELEGRAM ERROR: %s",
            exc
        )

        return None


def send_message(
    chat_id,
    text,
    reply_markup=None
):

    if not text:
        text = "❌ لم يتم الحصول على رد."

    chunks = [
        text[i:i + MAX_TELEGRAM_LENGTH]
        for i in range(
            0,
            len(text),
            MAX_TELEGRAM_LENGTH
        )
    ]

    result = None

    for i, chunk in enumerate(chunks):

        payload = {
            "chat_id": chat_id,
            "text": chunk
        }

        if (
            reply_markup is not None
            and i == len(chunks) - 1
        ):
            payload["reply_markup"] = reply_markup

        result = telegram(
            "sendMessage",
            payload
        )

    return result


def edit_message(
    chat_id,
    message_id,
    text,
    reply_markup=None
):

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    return telegram(
        "editMessageText",
        payload
    )


def answer_callback(callback_id):

    return telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


def send_photo_url(
    chat_id,
    photo_url,
    caption=""
):

    return telegram(
        "sendPhoto",
        {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024]
        }
    )


def send_photo_bytes(
    chat_id,
    image_bytes,
    caption=""
):

    if not TELEGRAM_API:
        return None

    try:

        r = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={
                "chat_id": chat_id,
                "caption": caption[:1024]
            },
            files={
                "photo": (
                    "image.png",
                    image_bytes,
                    "image/png"
                )
            },
            timeout=60
        )

        if not r.ok:

            logger.error(
                "TELEGRAM PHOTO %s %s",
                r.status_code,
                r.text[:500]
            )

            return None

        return r.json()

    except Exception as exc:

        logger.error(
            "TELEGRAM PHOTO ERROR: %s",
            exc
        )

        return None


def send_document_bytes(
    chat_id,
    file_bytes,
    filename,
    caption=""
):

    if not TELEGRAM_API:
        return None

    try:

        r = requests.post(
            f"{TELEGRAM_API}/sendDocument",
            data={
                "chat_id": chat_id,
                "caption": caption[:1024]
            },
            files={
                "document": (
                    filename,
                    file_bytes,
                    "text/csv"
                )
            },
            timeout=60
        )

        if not r.ok:
            logger.error(
                "TELEGRAM DOC %s %s",
                r.status_code,
                r.text[:500]
            )
            return None

        return r.json()

    except Exception as exc:

        logger.error(
            "TELEGRAM DOC ERROR: %s",
            exc
        )

        return None


def get_file_url(file_id):

    result = telegram(
        "getFile",
        {
            "file_id": file_id
        }
    )

    if not result or not result.get("ok"):
        return None

    file_path = (
        result
        .get("result", {})
        .get("file_path")
    )

    if not file_path:
        return None

    return (
        f"https://api.telegram.org/file/"
        f"bot{BOT_TOKEN}/{file_path}"
    )


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard(is_admin=False):

    keyboard = [
        [{"text": "💬 بدء المحادثة"}],
        [
            {"text": "🚀 محادثة جديدة"},
            {"text": "📊 معلوماتي"}
        ],
        [
            {"text": "🔎 البحث العام"},
            {"text": "👤 فحص حساب عام"}
        ],
        [
            {"text": "🎨 توليد صورة"}
        ],
        [
            {"text": "🌐 التواصل مع المطور"}
        ]
    ]

    if is_admin:
        keyboard.append(
            [{"text": "⚙️ لوحة التحكم"}]
        )

    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "is_persistent": True
    }


def admin_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "📊 الإحصائيات",
                    "callback_data": "adm_stats"
                }
            ],
            [
                {
                    "text": "📈 إحصائيات اليوم",
                    "callback_data": "adm_today"
                }
            ],
            [
                {
                    "text": "📢 إذاعة رسالة",
                    "callback_data": "adm_broad"
                }
            ],
            [
                {
                    "text": "👥 المستخدمون",
                    "callback_data": "adm_users"
                }
            ],
            [
                {
                    "text": "📤 تصدير المستخدمين",
                    "callback_data": "adm_export"
                }
            ]
        ]
    }


def back_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🔙 رجوع",
                    "callback_data": "adm_back"
                }
            ]
        ]
    }


# ============================================================
# AI ENGINE
# ============================================================

SYSTEM_PROMPT = f"""
أنت NYXS AI.

المطور:
NYXS

Telegram:
{DEVELOPER_HANDLE}

إذا سُئلت عن المطور:
المطور هو NYXS ومعرفه {DEVELOPER_HANDLE}.

أجب باللغة التي يستخدمها المستخدم.
كن مباشرًا ودقيقًا.
لا تخترع معلومات.
إذا لم تعرف شيئًا، قل إنك لا تعرف.
"""


class OpenAICompatible:

    @staticmethod
    def ask(
        messages,
        api_key,
        base_url,
        model
    ):

        if not api_key:
            raise RuntimeError(
                "API key missing"
            )

        formatted = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        for m in messages:

            role = m.get("role")

            if role not in (
                "user",
                "assistant"
            ):
                continue

            if (
                role == "user"
                and m.get("image_url")
            ):

                formatted.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": str(
                                m.get(
                                    "content",
                                    ""
                                )
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": m["image_url"]
                            }
                        }
                    ]
                })

            else:

                formatted.append({
                    "role": role,
                    "content": str(
                        m.get(
                            "content",
                            ""
                        )
                    )
                })

        r = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization":
                    f"Bearer {api_key}",
                "Content-Type":
                    "application/json"
            },
            json={
                "model": model,
                "messages": formatted,
                "temperature": 0.7
            },
            timeout=45
        )

        if not r.ok:
            raise RuntimeError(
                f"HTTP {r.status_code}: "
                f"{r.text[:300]}"
            )

        data = r.json()

        return (
            data["choices"][0]
            ["message"]["content"]
            .strip()
        )


class Chattide:

    @staticmethod
    def ask(text):

        payload = {
            "spaceHandle": True,
            "roleId": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
            ],
            "conversationId": None,
            "model": AI2_MODEL
        }

        r = requests.post(
            CHATTIDE_URL,
            headers={
                "lang": "ar",
                "content-type":
                    "application/json",
                "accept":
                    "text/event-stream,application/json",
                "referer":
                    "https://www.chattide.ai/",
                "user-agent":
                    "Mozilla/5.0"
            },
            json=payload,
            stream=True,
            timeout=60
        )

        if not r.ok:
            raise RuntimeError(
                f"Chattide HTTP {r.status_code}"
            )

        result = ""

        for line in r.iter_lines():

            if not line:
                continue

            try:
                line = line.decode(
                    "utf-8",
                    errors="ignore"
                )
            except Exception:
                continue

            if not line.startswith("data:"):
                continue

            data = line[5:].strip()

            if data == "--@DONE@--":
                break

            if not data:
                continue

            data = (
                data
                .replace("-=- --", " ")
                .replace("-=-n-", "\n")
            )

            result += data

        if not result.strip():
            raise RuntimeError(
                "Empty Chattide response"
            )

        return result.strip()


class AI:

    @staticmethod
    def ask(history):

        errors = []

        systems = [
            (
                AI_PROVIDER,
                AI_API_KEY,
                AI_BASE_URL,
                AI_MODEL
            ),
            (
                AI2_PROVIDER,
                AI2_API_KEY,
                AI2_BASE_URL,
                AI2_MODEL
            )
        ]

        for (
            provider,
            key,
            base,
            model
        ) in systems:

            try:

                if provider == "chattide":

                    last = ""

                    for item in reversed(history):

                        if item.get("role") == "user":
                            last = item.get(
                                "content",
                                ""
                            )
                            break

                    if not last:
                        raise RuntimeError(
                            "No user message"
                        )

                    return Chattide.ask(last)

                return OpenAICompatible.ask(
                    history,
                    key,
                    base,
                    model
                )

            except Exception as exc:

                errors.append(
                    f"{provider}: {exc}"
                )

                logger.error(
                    "AI FAILOVER: %s",
                    exc
                )

        return (
            "❌ تعذر الاتصال بأنظمة "
            "الذكاء الاصطناعي حاليًا.\n\n"
            "تمت محاولة النظام الأساسي "
            "والاحتياطي."
        )


def maybe_summarize_history(history):

    if len(history) <= SUMMARIZE_TRIGGER:
        return history

    old_part = history[:-8]
    recent_part = history[-8:]

    convo_text = "\n".join(
        f"{'المستخدم' if m.get('role') == 'user' else 'المساعد'}: "
        f"{m.get('content', '')}"
        for m in old_part
    )

    try:

        summary = OpenAICompatible.ask(
            [
                {
                    "role": "user",
                    "content": (
                        "لخص هذه المحادثة بإيجاز شديد "
                        "مع الحفاظ على المعلومات المهمة فقط:\n\n"
                        f"{convo_text}"
                    )
                }
            ],
            AI_API_KEY,
            AI_BASE_URL,
            AI_MODEL
        )

    except Exception as exc:

        logger.error(
            "SUMMARY ERROR: %s",
            exc
        )

        return history

    summarized = [
        {
            "role": "user",
            "content":
                f"[ملخص المحادثة السابقة]: {summary}"
        }
    ]

    return summarized + recent_part


# ============================================================
# IMAGE GENERATION
# ============================================================

class ImageGen:

    @staticmethod
    def openai_compatible(
        prompt,
        api_key,
        base_url,
        model
    ):

        if not api_key:
            raise RuntimeError(
                "API key missing"
            )

        r = requests.post(
            f"{base_url}/images/generations",
            headers={
                "Authorization":
                    f"Bearer {api_key}",
                "Content-Type":
                    "application/json"
            },
            json={
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": IMAGE_SIZE
            },
            timeout=60
        )

        if not r.ok:
            raise RuntimeError(
                f"HTTP {r.status_code}: "
                f"{r.text[:300]}"
            )

        data = r.json()

        item = data.get(
            "data",
            [{}]
        )[0]

        if item.get("url"):
            return {
                "type": "url",
                "value": item["url"]
            }

        if item.get("b64_json"):
            return {
                "type": "b64",
                "value": item["b64_json"]
            }

        raise RuntimeError(
            "No image in response"
        )

    @staticmethod
    def stability(
        prompt,
        api_key,
        base_url,
        model
    ):

        if not api_key:
            raise RuntimeError(
                "API key missing"
            )

        r = requests.post(
            f"{base_url}/v1/generation/"
            f"{model}/text-to-image",
            headers={
                "Authorization":
                    f"Bearer {api_key}",
                "Content-Type":
                    "application/json",
                "Accept":
                    "application/json"
            },
            json={
                "text_prompts": [
                    {
                        "text": prompt
                    }
                ],
                "samples": 1,
                "steps": 30
            },
            timeout=60
        )

        if not r.ok:
            raise RuntimeError(
                f"HTTP {r.status_code}: "
                f"{r.text[:300]}"
            )

        data = r.json()

        artifacts = data.get(
            "artifacts",
            []
        )

        if not artifacts:
            raise RuntimeError(
                "No image in response"
            )

        return {
            "type": "b64",
            "value": artifacts[0]["base64"]
        }

    @staticmethod
    def generate(prompt):

        systems = [
            (
                IMAGE_PROVIDER,
                IMAGE_API_KEY,
                IMAGE_BASE_URL,
                IMAGE_MODEL
            ),
            (
                IMAGE2_PROVIDER,
                IMAGE2_API_KEY,
                IMAGE2_BASE_URL,
                IMAGE2_MODEL
            )
        ]

        errors = []

        for (
            provider,
            key,
            base,
            model
        ) in systems:

            try:

                if provider == "stability":
                    return ImageGen.stability(
                        prompt,
                        key,
                        base,
                        model
                    )

                return ImageGen.openai_compatible(
                    prompt,
                    key,
                    base,
                    model
                )

            except Exception as exc:

                errors.append(
                    f"{provider}: {exc}"
                )

                logger.error(
                    "IMAGE FAILOVER: %s",
                    exc
                )

        raise RuntimeError(
            " | ".join(errors)
        )


# ============================================================
# REAL WEB SEARCH
# ============================================================

class WebSearch:

    @staticmethod
    def google(query):

        if not SEARCH_API_KEY or not SEARCH_ENGINE_ID:
            return []

        try:

            r = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": SEARCH_API_KEY,
                    "cx": SEARCH_ENGINE_ID,
                    "q": query,
                    "num": SEARCH_RESULTS_LIMIT,
                    "safe": "active"
                },
                timeout=SEARCH_TIMEOUT
            )

            if not r.ok:
                return []

            data = r.json()

            return [
                {
                    "title":
                        item.get(
                            "title",
                            ""
                        ),
                    "url":
                        item.get(
                            "link",
                            ""
                        ),
                    "snippet":
                        item.get(
                            "snippet",
                            ""
                        )
                }
                for item in data.get(
                    "items",
                    []
                )
            ]

        except Exception as exc:

            logger.error(
                "GOOGLE SEARCH: %s",
                exc
            )

            return []

    @staticmethod
    def brave(query):

        if not BRAVE_API_KEY:
            return []

        try:

            r = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "X-Subscription-Token":
                        BRAVE_API_KEY,
                    "Accept":
                        "application/json"
                },
                params={
                    "q": query,
                    "count":
                        SEARCH_RESULTS_LIMIT
                },
                timeout=SEARCH_TIMEOUT
            )

            if not r.ok:
                return []

            data = r.json()

            return [
                {
                    "title":
                        item.get(
                            "title",
                            ""
                        ),
                    "url":
                        item.get(
                            "url",
                            ""
                        ),
                    "snippet":
                        item.get(
                            "description",
                            ""
                        )
                }
                for item in data
                .get("web", {})
                .get("results", [])
            ]

        except Exception as exc:

            logger.error(
                "BRAVE SEARCH: %s",
                exc
            )

            return []

    @staticmethod
    def ddg(query):

        try:

            r = requests.get(
                "https://html.duckduckgo.com/html/",
                params={
                    "q": query
                },
                headers={
                    "User-Agent":
                        "Mozilla/5.0"
                },
                timeout=SEARCH_TIMEOUT
            )

            if not r.ok:
                return []

            html = r.text

            blocks = re.findall(
                r'class="result__a"[^>]*'
                r'href="([^"]+)"[^>]*>'
                r'(.*?)</a>',
                html,
                re.I | re.S
            )

            results = []

            for url, title in blocks:

                title = re.sub(
                    "<.*?>",
                    "",
                    title
                )

                results.append({
                    "title":
                        title.strip(),
                    "url":
                        url,
                    "snippet":
                        ""
                })

            return results[
                :SEARCH_RESULTS_LIMIT
            ]

        except Exception as exc:

            logger.error(
                "DDG SEARCH: %s",
                exc
            )

            return []

    @staticmethod
    def search(query):

        query = query.strip()

        if not query:
            return []

        cache_key = (
            "searchcache:" +
            hashlib.md5(
                query.lower()
                .encode("utf-8")
            ).hexdigest()
        )

        cached = Memory.get(cache_key)

        if cached:

            try:
                return json.loads(cached)
            except Exception:
                pass

        if SEARCH_PROVIDER == "brave":

            providers = [
                WebSearch.brave,
                WebSearch.google,
                WebSearch.ddg
            ]

        elif SEARCH_PROVIDER == "google":

            providers = [
                WebSearch.google,
                WebSearch.brave,
                WebSearch.ddg
            ]

        else:

            providers = [
                WebSearch.google,
                WebSearch.brave,
                WebSearch.ddg
            ]

        all_results = []

        for provider in providers:

            results = provider(query)

            if results:
                all_results.extend(results)

            if len(all_results) >= SEARCH_RESULTS_LIMIT:
                break

        unique = []
        seen = set()

        for item in all_results:

            url = (
                item.get(
                    "url",
                    ""
                )
                .strip()
            )

            if not url:
                continue

            normalized = (
                url.lower()
                .split("#")[0]
                .rstrip("/")
            )

            if normalized in seen:
                continue

            seen.add(normalized)
            unique.append(item)

        final = unique[
            :SEARCH_RESULTS_LIMIT
        ]

        if final:

            Memory.set(
                cache_key,
                json.dumps(
                    final,
                    ensure_ascii=False
                ),
                ex=SEARCH_CACHE_TTL
            )

        return final


# ============================================================
# PUBLIC ACCOUNT SEARCH ENGINE
# ============================================================

class PublicAccountSearch:

    PLATFORMS = {
        "instagram.com": "Instagram",
        "www.instagram.com": "Instagram",

        "tiktok.com": "TikTok",
        "www.tiktok.com": "TikTok",

        "twitter.com": "X",
        "www.twitter.com": "X",
        "x.com": "X",
        "www.x.com": "X",

        "youtube.com": "YouTube",
        "www.youtube.com": "YouTube",

        "reddit.com": "Reddit",
        "www.reddit.com": "Reddit",

        "github.com": "GitHub",
        "www.github.com": "GitHub",

        "t.me": "Telegram",
        "telegram.me": "Telegram",

        "facebook.com": "Facebook",
        "www.facebook.com": "Facebook",

        "linkedin.com": "LinkedIn",
        "www.linkedin.com": "LinkedIn",
    }

    @staticmethod
    def normalize_url(url):

        url = url.strip()

        if not re.match(
            r"^https?://",
            url,
            re.I
        ):
            url = "https://" + url

        parsed = urlparse(url)

        host = (
            parsed.netloc
            .lower()
            .split(":")[0]
        )

        path = (
            parsed.path
            .strip("/")
        )

        return (
            f"https://{host}/{path}"
            if path
            else f"https://{host}"
        )

    @staticmethod
    def detect_platform(url):

        parsed = urlparse(
            PublicAccountSearch.normalize_url(url)
        )

        host = (
            parsed.netloc
            .lower()
            .split(":")[0]
        )

        return PublicAccountSearch.PLATFORMS.get(
            host
        )

    @staticmethod
    def extract_username(url):

        normalized = (
            PublicAccountSearch
            .normalize_url(url)
        )

        parsed = urlparse(normalized)

        parts = [
            unquote(x)
            for x in parsed.path.split("/")
            if x
        ]

        if not parts:
            return ""

        platform = PublicAccountSearch.detect_platform(
            normalized
        )

        if platform == "TikTok":
            return parts[0].lstrip("@")

        if platform == "Instagram":
            return parts[0].lstrip("@")

        if platform == "X":
            return parts[0].lstrip("@")

        if platform == "GitHub":
            return parts[0]

        if platform == "Reddit":
            if parts[0].lower() in (
                "user",
                "u"
            ) and len(parts) > 1:
                return parts[1]

            return parts[0]

        if platform == "YouTube":

            if parts[0].startswith("@"):
                return parts[0][1:]

            return parts[0]

        if platform == "Telegram":

            return parts[-1].lstrip("@")

        if platform == "Facebook":

            return parts[0]

        if platform == "LinkedIn":

            if (
                parts[0].lower()
                in ("in", "company")
                and len(parts) > 1
            ):
                return parts[1]

            return parts[0]

        return parts[0]

    @staticmethod
    def domain_for_platform(platform):

        domains = {
            "Instagram":
                "site:instagram.com",

            "TikTok":
                "site:tiktok.com",

            "X":
                "site:x.com",

            "YouTube":
                "site:youtube.com",

            "Reddit":
                "site:reddit.com",

            "GitHub":
                "site:github.com",

            "Telegram":
                "site:t.me",

            "Facebook":
                "site:facebook.com",

            "LinkedIn":
                "site:linkedin.com",
        }

        return domains.get(
            platform,
            ""
        )

    @staticmethod
    def score_result(
        item,
        profile_url,
        username,
        platform
    ):

        title = (
            item.get("title", "")
            .lower()
        )

        snippet = (
            item.get("snippet", "")
            .lower()
        )

        result_url = (
            item.get("url", "")
            .lower()
        )

        username_l = username.lower()

        score = 0

        if username_l and username_l in title:
            score += 30

        if username_l and username_l in snippet:
            score += 20

        if username_l and username_l in result_url:
            score += 30

        profile_path = (
            urlparse(
                profile_url
            ).path
            .rstrip("/")
            .lower()
        )

        result_path = (
            urlparse(
                result_url
            ).path
            .rstrip("/")
            .lower()
        )

        if profile_path and result_path == profile_path:
            score += 20

        if platform:
            domain = (
                urlparse(
                    profile_url
                ).netloc.lower()
            )

            if domain and domain in result_url:
                score += 5

        return min(score, 100)

    @staticmethod
    def search_queries(
        profile_url,
        platform,
        username
    ):

        domain = (
            PublicAccountSearch
            .domain_for_platform(platform)
        )

        queries = []

        queries.append(
            f'"{profile_url}"'
        )

        if username:
            queries.append(
                f'{domain} "{username}"'
            )

            queries.append(
                f'{domain} "{username}" posts'
            )

            queries.append(
                f'{domain} "{username}" profile'
            )

            queries.append(
                f'{domain} "{username}" repost'
            )

            queries.append(
                f'{domain} "{username}" 2020'
            )

            queries.append(
                f'{domain} "{username}" 2019'
            )

            queries.append(
                f'{domain} "{username}" 2018'
            )

        return queries

    @staticmethod
    def search_profile(profile_url):

        profile_url = (
            PublicAccountSearch
            .normalize_url(profile_url)
        )

        platform = (
            PublicAccountSearch
            .detect_platform(profile_url)
        )

        username = (
            PublicAccountSearch
            .extract_username(profile_url)
        )

        if not platform:
            raise ValueError(
                "المنصة غير مدعومة."
            )

        if not username:
            raise ValueError(
                "تعذر استخراج اسم المستخدم."
            )

        cache_key = (
            "profile-search:" +
            hashlib.sha256(
                profile_url
                .encode("utf-8")
            ).hexdigest()
        )

        cached = Memory.get(cache_key)

        if cached:

            try:
                return json.loads(cached)
            except Exception:
                pass

        queries = (
            PublicAccountSearch
            .search_queries(
                profile_url,
                platform,
                username
            )
        )

        all_results = []

        # لا نرسل كل الاستعلامات إلى مزود واحد فقط.
        # WebSearch لديه fallback داخلي.
        for query in queries:

            results = WebSearch.search(
                query
            )

            all_results.extend(results)

            if len(all_results) >= 40:
                break

        unique = []
        seen = set()

        for item in all_results:

            url = (
                item.get("url", "")
                .strip()
            )

            if not url:
                continue

            normalized = (
                url.lower()
                .split("#")[0]
                .rstrip("/")
            )

            if normalized in seen:
                continue

            seen.add(normalized)

            item["match_score"] = (
                PublicAccountSearch.score_result(
                    item,
                    profile_url,
                    username,
                    platform
                )
            )

            unique.append(item)

        unique.sort(
            key=lambda x:
                x.get(
                    "match_score",
                    0
                ),
            reverse=True
        )

        result = {
            "profile_url": profile_url,
            "platform": platform,
            "username": username,
            "results": unique[:30],
            "searched_at":
                datetime.utcnow().isoformat()
        }

        Memory.set(
            cache_key,
            json.dumps(
                result,
                ensure_ascii=False
            ),
            ex=SEARCH_CACHE_TTL
        )

        return result

    @staticmethod
    def format_report(data):

        profile_url = data[
            "profile_url"
        ]

        platform = data[
            "platform"
        ]

        username = data[
            "username"
        ]

        results = data.get(
            "results",
            []
        )

        lines = [
            "👤 NYXS — فحص حساب عام",
            "",
            f"🌐 المنصة: {platform}",
            f"👤 Username: @{username}",
            f"🔗 الحساب:",
            profile_url,
            "",
            "📊 النتائج العامة المفهرسة:",
            ""
        ]

        if not results:

            lines.extend([
                "❌ لم يتم العثور على نتائج "
                "مفهرسة كافية.",
                "",
                "قد يكون الحساب غير مفهرس "
                "أو أن محركات البحث لا تعرض "
                "محتواه."
            ])

            return "\n".join(lines)

        for index, item in enumerate(
            results[:12],
            1
        ):

            title = (
                item.get(
                    "title",
                    "بدون عنوان"
                )
                .strip()
            )

            url = (
                item.get(
                    "url",
                    ""
                )
                .strip()
            )

            snippet = (
                item.get(
                    "snippet",
                    ""
                )
                .strip()
            )

            score = item.get(
                "match_score",
                0
            )

            lines.append(
                f"{index}️⃣ {title[:180]}"
            )

            lines.append(
                f"📊 تطابق النتيجة: {score}%"
            )

            if snippet:
                lines.append(
                    f"📝 {snippet[:350]}"
                )

            lines.append(
                f"🔗 {url}"
            )

            lines.append("")

        lines.extend([
            "⚠️ ملاحظة:",
            "هذه النتائج مأخوذة من محتوى "
            "عام ومفهرس فقط.",
            "الدرجة هي درجة تطابق نتيجة "
            "البحث مع الحساب المطلوب، "
            "وليست نسبة لإثبات هوية شخص."
        ])

        return "\n".join(lines)


# ============================================================
# USER INFO
# ============================================================

def user_info(
    chat_id,
    user
):

    users = Memory.get_users()

    data = users.get(
        str(chat_id),
        {}
    )

    history = Memory.get_history(
        chat_id
    )

    count = sum(
        1
        for x in history
        if x.get("role") == "user"
    )

    username = user.get(
        "username"
    )

    username = (
        f"@{username}"
        if username
        else "غير موجود"
    )

    return (
        "📋 معلوماتك\n\n"
        f"🆔 ID: {chat_id}\n"
        f"👤 الاسم: "
        f"{user.get('first_name', 'مجهول')}\n"
        f"🔗 Username: {username}\n"
        f"💬 الرسائل المحفوظة: {count}\n"
        f"🧠 الذاكرة: "
        f"{'مفعلة' if Memory.enabled() else 'غير مفعلة'}\n"
        f"📅 آخر نشاط: "
        f"{data.get('last_active', 'غير معروف')}"
    )


# ============================================================
# START
# ============================================================

def handle_start(
    chat_id,
    user
):

    Memory.register_user(
        chat_id,
        user.get(
            "first_name",
            "مجهول"
        ),
        user.get(
            "username",
            ""
        )
    )

    is_admin = (
        ADMIN_ID != 0
        and chat_id == ADMIN_ID
    )

    text = (
        f"👋 أهلاً بك "
        f"{user.get('first_name', 'صديقي')}\n\n"
        "🤖 NYXS AI\n\n"
        f"👨‍💻 المطور: {DEVELOPER_NAME}\n"
        f"📱 {DEVELOPER_HANDLE}\n\n"
        "💬 للمحادثة أرسل رسالتك.\n\n"
        "🔎 البحث العام:\n"
        "/search كلمة البحث\n\n"
        "👤 فحص حساب عام:\n"
        "/find رابط الحساب\n\n"
        "مثال:\n"
        "/find https://www.instagram.com/username/\n\n"
        "🎨 توليد صورة:\n"
        "/image وصف الصورة\n\n"
        "🚀 محادثة جديدة:\n"
        "/clear"
    )

    send_message(
        chat_id,
        text,
        main_keyboard(is_admin)
    )


# ============================================================
# ADMIN
# ============================================================

def admin_panel(chat_id):

    if chat_id != ADMIN_ID:
        send_message(
            chat_id,
            "⛔️ غير مصرح."
        )
        return

    send_message(
        chat_id,
        "⚙️ لوحة تحكم NYXS",
        admin_keyboard()
    )


def admin_stats(chat_id):

    if chat_id != ADMIN_ID:
        return

    users = Memory.get_users()
    banned = Memory.get_banned()
    today = UsageStats.get()

    total = 0

    for uid in users:

        try:
            history = Memory.get_history(
                int(uid)
            )

            total += sum(
                1
                for x in history
                if x.get("role") == "user"
            )

        except Exception:
            pass

    send_message(
        chat_id,
        (
            "📊 إحصائيات NYXS\n\n"
        
