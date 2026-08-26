# ============================================================
# NYXS AI TELEGRAM BOT
# SINGLE FILE / VERCEL
# DUAL AI + MEMORY + ADMIN + MULTI-PLATFORM OSINT
# ============================================================

import os
import sys
import json
import base64
import random
import string
import logging
import time
import re
import html
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote, unquote, urlparse

import requests


# ============================================================
# NYXS IDENTITY
# ============================================================

DEVELOPER_NAME = "NYXS"
DEVELOPER_HANDLE = "@h1_c87"


# ============================================================
# ENVIRONMENT
# ============================================================

BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    ""
).strip()

try:
    ADMIN_ID = int(
        os.environ.get(
            "ADMIN_ID",
            "0"
        ).strip() or "0"
    )
except Exception:
    ADMIN_ID = 0


# ============================================================
# AI SETTINGS
# ============================================================

AI_PROVIDER = os.environ.get(
    "AI_PROVIDER",
    "openai"
).strip().lower()

AI_API_KEY = os.environ.get(
    "AI_API_KEY",
    ""
).strip()

AI_MODEL = os.environ.get(
    "AI_MODEL",
    "gpt-4o-mini"
).strip()

AI_BASE_URL = os.environ.get(
    "AI_BASE_URL",
    "https://api.openai.com/v1"
).strip().rstrip("/")

AI_FALLBACK_ENABLED = os.environ.get(
    "AI_FALLBACK",
    "true"
).strip().lower() in (
    "true",
    "1",
    "yes",
    "on",
)

AI_FALLBACK_EXPIRY = 1800


# ============================================================
# CHATTIDE
# ============================================================

CHATTIDE_URL = os.environ.get(
    "CHATTIDE_URL",
    "https://api.chattide.ai/aigc/chat/v2/professional/stream"
).strip()

CHATTIDE_MODEL = os.environ.get(
    "CHATTIDE_MODEL",
    "gpt-5.6-luna"
).strip()


# ============================================================
# UPSTASH
# ============================================================

UPSTASH_URL = os.environ.get(
    "UPSTASH_REDIS_REST_URL",
    ""
).strip().rstrip("/")

UPSTASH_TOKEN = os.environ.get(
    "UPSTASH_REDIS_REST_TOKEN",
    ""
).strip()


# ============================================================
# GENERAL
# ============================================================

TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
    if BOT_TOKEN
    else ""
)

MAX_HISTORY_MESSAGES = 16
MAX_TELEGRAM_LENGTH = 4000

DEV_CONTACT = os.environ.get(
    "DEV_CONTACT",
    "https://t.me/h1_c87"
).strip()

WEBHOOK_SECRET = os.environ.get(
    "WEBHOOK_SECRET",
    ""
).strip()


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger("NYXS")
logger.setLevel(logging.INFO)

if not logger.handlers:

    handler = logging.StreamHandler(
        sys.stdout
    )

    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - "
            "%(levelname)s - %(message)s"
        )
    )

    logger.addHandler(handler)


# ============================================================
# UPSTASH MEMORY
# ============================================================

class Memory:

    @staticmethod
    def enabled():

        return bool(
            UPSTASH_URL
            and UPSTASH_TOKEN
        )

    @staticmethod
    def headers():

        return {
            "Authorization":
                f"Bearer {UPSTASH_TOKEN}",
            "Content-Type":
                "application/json",
        }

    @staticmethod
    def cmd(*args):

        if not Memory.enabled():
            return None

        try:

            response = requests.post(
                UPSTASH_URL,
                headers=Memory.headers(),
                json=list(args),
                timeout=8,
            )

            if not response.ok:

                logger.error(
                    "UPSTASH ERROR %s: %s",
                    response.status_code,
                    response.text[:300],
                )

                return None

            data = response.json()

            return data.get(
                "result"
            )

        except Exception as exc:

            logger.error(
                "UPSTASH EXCEPTION: %s",
                exc,
            )

            return None

    @staticmethod
    def get(key):

        return Memory.cmd(
            "GET",
            key
        )

    @staticmethod
    def set(
        key,
        value,
        ex=None,
    ):

        if ex:

            return Memory.cmd(
                "SET",
                key,
                value,
                "EX",
                str(ex),
            )

        return Memory.cmd(
            "SET",
            key,
            value,
        )

    @staticmethod
    def delete(key):

        return Memory.cmd(
            "DEL",
            key,
        )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    @staticmethod
    def get_history(chat_id):

        if not Memory.enabled():
            return []

        raw = Memory.get(
            f"history:{chat_id}"
        )

        if not raw:
            return []

        try:

            data = json.loads(raw)

            if isinstance(
                data,
                list
            ):
                return data

        except Exception:
            pass

        return []

    @staticmethod
    def save_history(
        chat_id,
        history,
    ):

        if not Memory.enabled():
            return

        history = history[
            -MAX_HISTORY_MESSAGES:
        ]

        Memory.set(
            f"history:{chat_id}",
            json.dumps(
                history,
                ensure_ascii=False,
            ),
            ex=604800,
        )

    @staticmethod
    def clear_history(chat_id):

        if Memory.enabled():

            Memory.delete(
                f"history:{chat_id}"
            )

            Memory.delete(
                f"conversation:{chat_id}"
            )

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    @staticmethod
    def register_user(
        chat_id,
        first_name="مجهول",
        username="",
        full_name="",
    ):

        if not Memory.enabled():
            return

        try:

            raw = Memory.get(
                "known_users"
            )

            users = (
                json.loads(raw)
                if raw
                else {}
            )

            users[str(chat_id)] = {
                "first_name":
                    first_name,
                "username":
                    username,
                "full_name":
                    full_name,
                "last_active":
                    datetime.utcnow().isoformat(),
            }

            Memory.set(
                "known_users",
                json.dumps(
                    users,
                    ensure_ascii=False,
                ),
            )

        except Exception as exc:

            logger.error(
                "REGISTER ERROR: %s",
                exc,
            )

    @staticmethod
    def get_users():

        if not Memory.enabled():
            return {}

        raw = Memory.get(
            "known_users"
        )

        if not raw:
            return {}

        try:

            data = json.loads(raw)

            if isinstance(
                data,
                dict
            ):
                return data

        except Exception:
            pass

        return {}

    # --------------------------------------------------------
    # BANNED
    # --------------------------------------------------------

    @staticmethod
    def get_banned():

        if not Memory.enabled():
            return []

        raw = Memory.get(
            "banned_users"
        )

        if not raw:
            return []

        try:

            data = json.loads(raw)

            if isinstance(
                data,
                list
            ):
                return data

        except Exception:
            pass

        return []

    @staticmethod
    def ban(chat_id):

        banned = Memory.get_banned()

        if chat_id not in banned:

            banned.append(
                chat_id
            )

        Memory.set(
            "banned_users",
            json.dumps(
                banned
            ),
        )

    @staticmethod
    def unban(chat_id):

        banned = Memory.get_banned()

        banned = [
            x
            for x in banned
            if x != chat_id
        ]

        Memory.set(
            "banned_users",
            json.dumps(
                banned
            ),
        )

    @staticmethod
    def is_banned(chat_id):

        return (
            chat_id
            in Memory.get_banned()
        )


# ============================================================
# TELEGRAM
# ============================================================

def telegram(
    method,
    payload=None,
):

    if not TELEGRAM_API:
        return None

    try:

        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload or {},
            timeout=20,
        )

        if not response.ok:

            logger.error(
                "TELEGRAM ERROR %s: %s",
                response.status_code,
                response.text[:500],
            )

            return None

        return response.json()

    except Exception as exc:

        logger.error(
            "TELEGRAM EXCEPTION: %s",
            exc,
        )

        return None


def send_message(
    chat_id,
    text,
    reply_markup=None,
):

    if not text:
        text = (
            "❌ لم يتم الحصول على رد."
        )

    chunks = [
        text[i:i + MAX_TELEGRAM_LENGTH]
        for i in range(
            0,
            len(text),
            MAX_TELEGRAM_LENGTH,
        )
    ]

    result = None

    for index, chunk in enumerate(
        chunks
    ):

        payload = {
            "chat_id": chat_id,
            "text": chunk,
        }

        if (
            reply_markup is not None
            and index == len(chunks) - 1
        ):

            payload[
                "reply_markup"
            ] = reply_markup

        result = telegram(
            "sendMessage",
            payload,
        )

    return result


def edit_message(
    chat_id,
    message_id,
    text,
    reply_markup=None,
):

    payload = {
        "chat_id":
            chat_id,
        "message_id":
            message_id,
        "text":
            text,
    }

    if reply_markup is not None:

        payload[
            "reply_markup"
        ] = reply_markup

    return telegram(
        "editMessageText",
        payload,
    )


def answer_callback(
    callback_id
):

    return telegram(
        "answerCallbackQuery",
        {
            "callback_query_id":
                callback_id
        },
    )


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard(
    is_admin=False
):

    keyboard = [

        [
            {
                "text":
                    "💬 بدء المحادثة"
            }
        ],

        [
            {
                "text":
                    "🚀 محادثة جديدة"
            },
            {
                "text":
                    "📊 معلوماتي"
            }
        ],

        [
            {
                "text":
                    "🔍 نبش معلومات"
            }
        ],

        [
            {
                "text":
                    "🌐 التواصل مع المطور"
            }
        ],
    ]

    if is_admin:

        keyboard.append(
            [
                {
                    "text":
                        "⚙️ لوحة التحكم"
                }
            ]
        )

    return {
        "keyboard":
            keyboard,
        "resize_keyboard":
            True,
        "is_persistent":
            True,
    }


def admin_keyboard():

    return {
        "inline_keyboard": [

            [
                {
                    "text":
                        "📊 الإحصائيات",
                    "callback_data":
                        "adm_stats",
                }
            ],

            [
                {
                    "text":
                        "📢 إذاعة",
                    "callback_data":
                        "adm_broadcast",
                }
            ],

            [
                {
                    "text":
                        "👥 المستخدمون",
                    "callback_data":
                        "adm_users",
                }
            ],

            [
                {
                    "text":
                        "🔄 إعادة AI",
                    "callback_data":
                        "adm_reset_ai",
                }
            ],
        ]
    }


def back_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text":
                        "🔙 رجوع",
                    "callback_data":
                        "adm_back",
                }
            ]
        ]
    }


# ============================================================
# OPENAI COMPATIBLE
# ============================================================

class OpenAIEngine:

    SYSTEM_PROMPT = f"""
أنت مساعد الذكاء الاصطناعي التابع لمشروع NYXS.

المطور:
NYXS

Telegram:
{DEVELOPER_HANDLE}

إذا سُئلت عن المطور:
اذكر أن المطور هو NYXS
ومعرفه {DEVELOPER_HANDLE}.

لا تخترع معلومات عن المشروع.

أجب بشكل مباشر ومفيد.
"""

    @staticmethod
    def ask(history):

        if not AI_API_KEY:

            return (
                "❌ AI_API_KEY غير مضبوط."
            )

        formatted = [
            {
                "role":
                    "system",
                "content":
                    OpenAIEngine.SYSTEM_PROMPT,
            }
        ]

        for message in history:

            role = message.get(
                "role"
            )

            if role not in (
                "user",
                "assistant",
            ):
                continue

            content = str(
                message.get(
                    "content",
                    "",
                )
            )

            formatted.append(
                {
                    "role":
                        role,
                    "content":
                        content,
                }
            )

        payload = {
            "model":
                AI_MODEL,
            "messages":
                formatted,
            "temperature":
                0.7,
        }

        try:

            response = requests.post(
                f"{AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization":
                        f"Bearer {AI_API_KEY}",
                    "Content-Type":
                        "application/json",
                },
                json=payload,
                timeout=45,
            )

            if not response.ok:

                logger.error(
                    "OPENAI HTTP %s",
                    response.status_code,
                )

                return None

            data = response.json()

            choices = data.get(
                "choices"
            )

            if not choices:
                return None

            message = choices[0].get(
                "message",
                {}
            )

            content = message.get(
                "content"
            )

            if not content:
                return None

            return str(
                content
            ).strip()

        except Exception as exc:

            logger.error(
                "OPENAI ERROR: %s",
                exc,
            )

            return None


# ============================================================
# CHATTIDE
# ============================================================

class ChattideEngine:

    def __init__(self):

        self.url = (
            CHATTIDE_URL
        )

        self.model = (
            CHATTIDE_MODEL
        )

        self.n = int(
            "136236490358183259653189950748359669580190635598405237306311768987156534532312435393317272373703463400839797405683556405633769494895560212863113877037049039352461932992309204029954183762382698647733158589129700438379720646895034736836216527276967880354063143356560735956241651941835057143194078092683552570413"
        )

        self.e = 65537

    def rsa_encrypt(
        self,
        message,
    ):

        try:

            message_bytes = (
                message.encode(
                    "utf-8"
                )
            )

            max_length = (
                128
                - len(message_bytes)
                - 11
            )

            if max_length <= 0:
                return None

            padding = bytes(
                random.randint(
                    1,
                    255
                )
                for _ in range(
                    max_length
                )
            )

            encoded = (
                b"\x00\x02"
                + padding
                + b"\x00"
                + message_bytes
            )

            integer = int.from_bytes(
                encoded,
                "big"
            )

            encrypted = pow(
                integer,
                self.e,
                self.n,
            )

            return base64.b64encode(
                encrypted.to_bytes(
                    128,
                    "big",
                )
            ).decode()

        except Exception as exc:

            logger.error(
                "RSA ERROR: %s",
                exc,
            )

            return None

    def generate_id(self):

        def random_string(
            length
        ):

            return "".join(
                random.choices(
                    string.ascii_lowercase
                    + string.digits,
                    k=length,
                )
            )

        return (
            f"{random_string(14)}-"
            f"{random_string(15)}-"
            f"3f700d7e-921600-"
            f"{random_string(15)}"
        )

    def headers(self):

        token = self.rsa_encrypt(
            self.generate_id()
        )

        return {
            "lang":
                "ar",

            "vtoken":
                token or "",

            "source":
                "web",

            "Content-Type":
                "application/json",

            "Accept":
                "text/event-stream,"
                "application/json",

            "Referer":
                "https://www.chattide.ai/",

            "User-Agent":
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0.0.0 "
                "Safari/537.36",
        }

    def query(
        self,
        text,
        conversation_id=None,
    ):

        payload = {

            "spaceHandle":
                True,

            "roleId":
                0,

            "messages": [
                {
                    "role":
                        "user",

                    "content": [
                        {
                            "type":
                                "text",

                            "text":
                                text,
                        }
                    ],
                }
            ],

            "conversationId":
                conversation_id,

            "model":
                self.model,
        }

        try:

            response = requests.post(
                self.url,
                headers=self.headers(),
                json=payload,
                stream=True,
                timeout=60,
            )

            if not response.ok:

                logger.error(
                    "CHATTIDE HTTP %s",
                    response.status_code,
                )

                return (
                    None,
                    conversation_id,
                )

            result = ""

            for line in response.iter_lines():

                if not line:
                    continue

                try:

                    line_text = line.decode(
                        "utf-8",
                        errors="ignore",
                    )

                except Exception:

                    continue

                if not line_text.startswith(
                    "data:"
                ):
                    continue

                data = (
                    line_text[
                        len("data:"):
                    ].strip()
                )

                if data == "--@DONE@--":
                    break

                if not data:
                    continue

                data = data.replace(
                    "-=- --",
                    " ",
                )

                data = data.replace(
                    "-=-n-",
                    "\n",
                )

                # بعض SSE responses تكون JSON
                try:

                    parsed = json.loads(
                        data
                    )

                    if isinstance(
                        parsed,
                        dict
                    ):

                        candidate = (
                            parsed.get("content")
                            or parsed.get("text")
                            or parsed.get("delta")
                            or parsed.get("answer")
                        )

                        if candidate:
                            data = str(
                                candidate
                            )

                except Exception:
                    pass

                result += data

            return (
                result.strip()
                or None,
                conversation_id,
            )

        except Exception as exc:

            logger.error(
                "CHATTIDE ERROR: %s",
                exc,
            )

            return (
                None,
                conversation_id,
            )


chattide = ChattideEngine()


# ============================================================
# DUAL AI ROUTER
# ============================================================

class AIEngine:

    FALLBACK_KEY = (
        "nyxs:active_ai"
    )

    @staticmethod
    def primary():

        if AI_PROVIDER in (
            "openai",
            "chattide",
        ):

            return AI_PROVIDER

        return "openai"

    @staticmethod
    def other(provider):

        if provider == "openai":
            return "chattide"

        return "openai"

    @staticmethod
    def active():

        primary = (
            AIEngine.primary()
        )

        if not AI_FALLBACK_ENABLED:
            return primary

        forced = Memory.get(
            AIEngine.FALLBACK_KEY
        )

        if forced in (
            "openai",
            "chattide",
        ):

            return forced

        return primary

    @staticmethod
    def mark_failed(
        provider
    ):

        if not AI_FALLBACK_ENABLED:
            return

        other = (
            AIEngine.other(
                provider
            )
        )

        Memory.set(
            AIEngine.FALLBACK_KEY,
            other,
            ex=AI_FALLBACK_EXPIRY,
        )

        logger.warning(
            "NYXS FAILOVER: %s -> %s",
            provider,
            other,
        )

    @staticmethod
    def reset():

        Memory.delete(
            AIEngine.FALLBACK_KEY
        )

    @staticmethod
    def valid(
        reply
    ):

        return (
            isinstance(
                reply,
                str
            )
            and bool(
                reply.strip()
            )
            and not reply.startswith(
                "❌ AI_API_KEY"
            )
        )

    @staticmethod
    def ask(
        history,
        conversation_id=None,
    ):

        first = (
            AIEngine.active()
        )

        second = (
            AIEngine.other(first)
        )

        for provider in (
            first,
            second,
        ):

            try:

                logger.info(
                    "AI provider: %s",
                    provider,
                )

                if provider == "openai":

                    reply = (
                        OpenAIEngine.ask(
                            history
                        )
                    )

                    new_conversation = (
                        conversation_id
                    )

                else:

                    (
                        reply,
                        new_conversation,
                    ) = chattide.query(
                        AIEngine.last_user_message(
                            history
                        ),
                        conversation_id,
                    )

                if AIEngine.valid(
                    reply
                ):

                    if provider == (
                        AIEngine.primary()
                    ):

                        AIEngine.reset()

                    else:

                        Memory.set(
                            AIEngine.FALLBACK_KEY,
                            provider,
                            ex=AI_FALLBACK_EXPIRY,
                        )

                    return (
                        reply.strip(),
                        new_conversation,
                    )

                AIEngine.mark_failed(
                    provider
                )

            except Exception as exc:

                logger.error(
                    "AI %s ERROR: %s",
                    provider,
                    exc,
                )

                AIEngine.mark_failed(
                    provider
                )

        return (
            "❌ تعذر الاتصال بمزودي الذكاء الاصطناعي.\n"
            "🔄 تم اختبار النظام الأساسي والاحتياطي.",
            conversation_id,
        )

    @staticmethod
    def last_user_message(
        history
    ):

        for message in reversed(
            history
        ):

            if message.get(
                "role"
            ) == "user":

                return str(
                    message.get(
                        "content",
                        ""
                    )
                )

        return ""


# ============================================================
# MULTI-PLATFORM OSINT
# ============================================================

class OSINTEngine:

    PLATFORMS = {

        "Instagram":
            "instagram.com",

        "TikTok":
            "tiktok.com",

        "X / Twitter":
            "x.com",

        "Twitter":
            "twitter.com",

        "Facebook":
            "facebook.com",

        "GitHub":
            "github.com",

        "LinkedIn":
            "linkedin.com",

        "Reddit":
            "reddit.com",

        "YouTube":
            "youtube.com",

        "Pinterest":
            "pinterest.com",

        "Twitch":
            "twitch.tv",

        "Steam":
            "steamcommunity.com",

        "Medium":
            "medium.com",

        "Threads":
            "threads.net",

        "Mastodon":
            "mastodon.social",

    }

    @staticmethod
    def clean(
        value
    ):

        value = html.unescape(
            value
        )

        value = re.sub(
            r"<[^>]+>",
            "",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @staticmethod
    def search(
        query,
        max_results=10,
    ):

        try:

            url = (
                "https://html.duckduckgo.com/html/?q="
                + quote(query)
            )

            response = requests.get(
                url,
                headers={
                    "User-Agent":
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36",
                    "Accept":
                        "text/html",
                },
                timeout=20,
            )

            if not response.ok:
                return []

            pattern = re.compile(
                r'<a[^>]+class="result__a"'
                r'[^>]+href="([^"]+)"'
                r'[^>]*>(.*?)</a>',
                re.DOTALL,
            )

            results = []

            for url_found, title in (
                pattern.findall(
                    response.text
                )[:max_results]
            ):

                title = OSINTEngine.clean(
                    title
                )

                url_found = html.unescape(
                    url_found
                )

                results.append(
                    {
                        "title":
                            title,
                        "url":
                            url_found,
                    }
                )

            return results

        except Exception as exc:

            logger.error(
                "OSINT SEARCH ERROR: %s",
                exc,
            )

            return []

    @staticmethod
    def wayback(
        target,
        max_results=30,
    ):

        try:

            url = (
                "https://web.archive.org/cdx/search/cdx"
                "?url=*"
                + quote(target)
                + "*"
                "&output=json"
                "&fl=timestamp,original"
                "&filter=statuscode:200"
                "&collapse=urlkey"
                f"&limit={max_results}"
            )

            response = requests.get(
                url,
                timeout=25,
            )

            if not response.ok:
                return []

            data = response.json()

            if (
                not isinstance(
                    data,
                    list
                )
                or len(data) <= 1
            ):
                return []

            results = []

            for row in data[1:]:

                if len(row) < 2:
                    continue

                timestamp = row[0]
                original = row[1]

                try:

                    dt = datetime.strptime(
                        timestamp,
                        "%Y%m%d%H%M%S",
                    )

                    date = dt.strftime(
                        "%Y-%m-%d %H:%M"
                    )

                except Exception:

                    date = timestamp

                results.append(
                    {
                        "date":
                            date,
                        "timestamp":
                            timestamp,
                        "original":
                            original,
                        "archive":
                            (
                                "https://web.archive.org/web/"
                                f"{timestamp}/{original}"
                            ),
                    }
                )

            results.sort(
                key=lambda item:
                    item["timestamp"]
            )

            return results[:max_results]

        except Exception as exc:

            logger.error(
                "WAYBACK ERROR: %s",
                exc,
            )

            return []

    @staticmethod
    def normalize_target(
        target
    ):

        target = target.strip()

        if target.startswith("@"):
            target = target[1:]

        target = target.strip()

        return target

    @staticmethod
    def similarity(
        target,
        result_url,
    ):

        target = target.lower().strip(
            "@ "
        )

        parsed = urlparse(
            result_url
        )

        path = unquote(
            parsed.path
        ).lower()

        domain = (
            parsed.netloc
            .lower()
        )

        score = 0

        if target in path:
            score += 60

        if (
            target in domain
            or target in path.replace(
                "/",
                " "
            )
        ):
            score += 20

        # Exact path component
        parts = [
            x for x in path.split("/")
            if x
        ]

        if target in parts:
            score += 20

        return min(
            score,
            100
        )

    @staticmethod
    def platform_search(
        target,
        platform,
        domain,
    ):

        queries = [

            f'site:{domain} "{target}"',

            f'site:{domain} "@{target}"',

        ]

        found = []

        seen = set()

        for query in queries:

            results = (
                OSINTEngine.search(
                    query,
                    5,
                )
            )

            for item in results:

                url = item.get(
                    "url",
                    ""
                )

                if (
                    url
                    and url not in seen
                ):

                    seen.add(url)

                    score = (
                        OSINTEngine.similarity(
                            target,
                            url,
                        )
                    )

                    item["platform"] = (
                        platform
                    )

                    item["score"] = score

                    found.append(
                        item
                    )

            time.sleep(
                0.15
            )

        return found

    @staticmethod
    def perform(
        target
    ):

        target = (
            OSINTEngine.normalize_target(
                target
            )
        )

        if not target:
            return {
                "target":
                    "",
                "results":
                    [],
                "archives":
                    [],
                "platforms":
                    [],
            }

        all_results = []

        seen = set()

        platform_status = {}

        for platform, domain in (
            OSINTEngine.PLATFORMS.items()
        ):

            try:

                results = (
                    OSINTEngine.platform_search(
                        target,
                        platform,
                        domain,
                    )
                )

                if results:

                    platform_status[
                        platform
                    ] = True

                else:

                    platform_status[
                        platform
                    ] = False

                for item in results:

                    url = item.get(
                        "url",
                        ""
                    )

                    if (
                        url
                        and url not in seen
                    ):

                        seen.add(url)

                        all_results.append(
                            item
                        )

            except Exception as exc:

                logger.error(
                    "PLATFORM %s: %s",
                    platform,
                    exc,
                )

                platform_status[
                    platform
                ] = False

        # General web search
        general_queries = [
            f'"{target}"',
            f'"@{target}"',
        ]

        for query in general_queries:

            results = (
                OSINTEngine.search(
                    query,
                    10,
                )
            )

            for item in results:

                url = item.get(
                    "url",
                    ""
                )

                if (
                    url
                    and url not in seen
                ):

                    seen.add(url)

                    item["platform"] = (
                        "Web"
                    )

                    item["score"] = (
                        OSINTEngine.similarity(
                            target,
                            url,
                        )
                    )

                    all_results.append(
                        item
                    )

        # Sort by score
        all_results.sort(
            key=lambda item:
                item.get(
                    "score",
                    0
                ),
            reverse=True,
        )

        # Historical public traces
        archives = (
            OSINTEngine.wayback(
                target,
                30,
            )
        )

        return {
            "target":
                target,

            "results":
                all_results[:50],

            "archives":
                archives,

            "platforms":
                platform_status,
        }


# ============================================================
# OSINT REPORT
# ============================================================

def build_osint_report(
    data
):

    target = data.get(
        "target",
        ""
    )

    results = data.get(
        "results",
        []
    )

    archives = data.get(
        "archives",
        []
    )

    platforms = data.get(
        "platforms",
        {}
    )

    lines = [

        "🔎 NYXS OSINT",

        "",

        f"🎯 الهدف: {target}",

        "",

        "━━━━━━━━━━━━━━━━━━",

        "🌐 المنصات:",
        "",
    ]

    for platform, found in (
        platforms.items()
    ):

        status = (
            "🟢 نتائج"
            if found
            else "⚪ لا توجد نتائج واضحة"
        )

        lines.append(
            f"{status} — {platform}"
        )

    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━",
            "🧩 الحسابات والنتائج المحتملة:",
            "",
        ]
    )

    if not results:

        lines.append(
            "❌ لم يتم العثور على نتائج واضحة."
        )

    else:

        for index, item in enumerate(
            results[:20],
            1,
        ):

            title = item.get(
                "title",
                "بدون عنوان"
            )

            url = item.get(
                "url",
                ""
            )

            platform = item.get(
                "platform",
                "Web"
            )

            score = item.get(
                "score",
                0
            )

            lines.append(
                f"{index}. {platform}"
            )

            lines.append(
                f"👤 {title[:100]}"
            )

            lines.append(
                f"📊 تطابق المؤشرات: {score}%"
            )

            lines.append(
                f"🔗 {url}"
            )

            lines.append("")

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            "🏛️ أقدم الآثار العامة المؤرشفة:",
            "",
        ]
    )

    if not archives:

        lines.append(
            "❌ لا توجد آثار مؤرشفة مطابقة."
        )

    else:

        for index, archive in enumerate(
            archives[:10],
            1,
        ):

            lines.append(
                f"{index}. 📅 "
                f"{archive.get('date', '?')}"
            )

            lines.append(
                f"🔗 {archive.get('archive', '')}"
            )

            lines.append("")

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            "⚠️ ملاحظة:",
            "نسبة التطابق مؤشر تقني مبني على "
            "نتائج عامة، ولا تثبت أن الحساب يعود "
            "للشخص نفسه.",
        ]
    )

    return "\n".join(
        lines
    )


# ============================================================
# USER STORE
# ============================================================

class UserStore:

    @staticmethod
    def get_user(
        chat_id
    ):

        return Memory.get_users().get(
            str(chat_id),
            {}
        )

    @staticmethod
    def message_count(
        chat_id
    ):

        history = (
            Memory.get_history(
                chat_id
            )
        )

        return sum(
            1
            for item in history
            if item.get(
                "role"
            ) == "user"
        )


# ============================================================
# START
# ============================================================

def handle_start(
    chat_id,
    user,
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
        ),
        user.get(
            "first_name",
            "مجهول"
        ),
    )

    is_admin = (
        ADMIN_ID != 0
        and chat_id == ADMIN_ID
    )

    active = (
        AIEngine.active()
    )

    text = (

        f"👋 أهلاً بك "
        f"{user.get('first_name', 'صديقي')} "
        f"في بوت NYXS.\n\n"

        f"🤖 AI الأساسي: "
        f"{AIEngine.primary()}\n"

        f"🔄 AI النشط: "
        f"{active}\n"

        f"🛡️ Failover: "
        f"{'مفعّل' if AI_FALLBACK_ENABLED else 'معطّل'}\n\n"

        f"👨‍💻 المطور: "
        f"{DEVELOPER_NAME}\n"

        f"📱 {DEVELOPER_HANDLE}\n\n"

        "✨ أرسل رسالتك للبدء.\n\n"

        "🔍 استخدم زر «نبش معلومات» "
        "للبحث في المصادر العامة."
    )

    send_message(
        chat_id,
        text,
        main_keyboard(
            is_admin
        ),
    )


# ============================================================
# USER INFO
# ============================================================

def handle_user_info(
    chat_id,
    user,
):

    info = (
        UserStore.get_user(
            chat_id
        )
    )

    count = (
        UserStore.message_count(
            chat_id
        )
    )

    username = (
        f"@{user.get('username')}"
        if user.get("username")
        else "غير موجود"
    )

    text = (

        "📋 معلوماتك\n\n"

        f"🆔 المعرف: {chat_id}\n"

        f"👤 الاسم: "
        f"{user.get('first_name', 'مجهول')}\n"

        f"🔗 Username: "
        f"{username}\n"

        f"💬 الرسائل: "
        f"{count}\n"

        f"📅 آخر نشاط: "
        f"{info.get('last_active', 'غير معروف')}"
    )

    send_message(
        chat_id,
        text,
        main_keyboard(
            chat_id == ADMIN_ID
        ),
    )


# ============================================================
# ADMIN
# ============================================================

def handle_admin_panel(
    chat_id
):

    if chat_id != ADMIN_ID:

        send_message(
            chat_id,
            "⛔️ غير مصرح."
        )

        return

    send_message(
        chat_id,
        "⚙️ لوحة تحكم NYXS",
        admin_keyboard(),
    )


def admin_users(
    chat_id
):

    if chat_id != ADMIN_ID:
        return

    users = (
        Memory.get_users()
    )

    if not users:

        send_message(
            chat_id,
            "👥 لا يوجد مستخدمون.",
            back_keyboard(),
        )

        return

    lines = [
        f"👥 المستخدمون ({len(users)})",
        "",
    ]

    for uid, info in list(
        users.items()
    )[:100]:

        name = (
            info.get("full_name")
            or info.get("first_name")
            or "مجهول"
        )

        lines.append(
            f"• {name} — {uid}"
        )

    send_message(
        chat_id,
        "\n".join(lines),
        back_keyboard(),
    )


def admin_stats(
    chat_id
):

    if chat_id != ADMIN_ID:
        return

    users = (
        Memory.get_users()
    )

    banned = (
        Memory.get_banned()
    )

    total = 0

    for uid in users:

        try:

            total += (
                UserStore.message_count(
                    int(uid)
                )
            )

        except Exception:
            pass

    text = (

        "📊 إحصائيات NYXS\n\n"

        f"👤 المستخدمون: "
        f"{len(users)}\n"

        f"💬 الرسائل المحفوظة: "
        f"{total}\n"

        f"🚫 المحظورون: "
        f"{len(banned)}\n"

        f"🧠 Upstash: "
        f"{'ON' if Memory.enabled() else 'OFF'}\n"

        f"🤖 الأساسي: "
        f"{AIEngine.primary()}\n"

        f"🔄 النشط: "
        f"{AIEngine.active()}\n"

        f"🧩 النموذج: "
        f"{AI_MODEL}"
    )

    send_message(
        chat_id,
        text,
        back_keyboard(),
    )


# ============================================================
# BROADCAST
# ============================================================

def perform_broadcast(
    text,
    users
):

    sent = 0
    failed = 0

    for uid in users:

        try:

            result = send_message(
                int(uid),
                text,
            )

            if result:
                sent += 1
            else:
                failed += 1

            time.sleep(
                0.05
            )

        except Exception:

            failed += 1

    return sent, failed


# ============================================================
# CALLBACKS
# ============================================================

def handle_callback(
    callback
):

    callback_id = (
        callback.get("id")
    )

    if callback_id:
        answer_callback(
            callback_id
        )

    message = (
        callback.get(
            "message",
            {}
        )
    )

    chat = (
        message.get(
            "chat",
            {}
        )
    )

    chat_id = chat.get(
        "id"
    )

    if chat_id != ADMIN_ID:
        return

    data = (
        callback.get(
            "data",
            ""
        )
    )

    message_id = (
        message.get(
            "message_id"
        )
    )

    if data == "adm_stats":

        admin_stats(
            chat_id
        )

        return

    if data == "adm_users":

        admin_users(
            chat_id
        )

        return

    if data == "adm_broadcast":

        Memory.set(
            f"broadcast:{chat_id}",
            "1",
            ex=600,
        )

        edit_message(
            chat_id,
            message_id,
            "📢 الإذاعة\n\n"
            "أرسل الرسالة الآن.\n"
            "للإلغاء: /cancel",
            back_keyboard(),
        )

        return

    if data == "adm_reset_ai":

        AIEngine.reset()

        edit_message(
            chat_id,
            message_id,
            "✅ تم إعادة AI "
            "إلى المزود الأساسي.",
            back_keyboard(),
        )

        return

    if data == "adm_back":

        edit_message(
            chat_id,
            message_id,
            "⚙️ لوحة تحكم NYXS",
            admin_keyboard(),
        )

        return


# ============================================================
# TEXT PROCESSOR
# ============================================================

def process_text(
    chat_id,
    text,
    user,
):

    text = text.strip()

    if not text:
        return

    is_admin = (
        chat_id == ADMIN_ID
    )

    # --------------------------------------------------------
    # BAN
    # --------------------------------------------------------

    if (
        not is_admin
        and Memory.is_banned(
            chat_id
        )
    ):
        return

    # --------------------------------------------------------
    # BROADCAST
    # --------------------------------------------------------

    if (
        is_admin
        and Memory.get(
            f"broadcast:{chat_id}"
        ) == "1"
    ):

        if text.lower() == "/cancel":

            Memory.delete(
                f"broadcast:{chat_id}"
            )

            send_message(
                chat_id,
                "❌ تم إلغاء الإذاعة.",
                main_keyboard(True),
            )

            return

        Memory.delete(
            f"broadcast:{chat_id}"
        )

        users = (
            Memory.get_users()
        )

        sent, failed = (
            perform_broadcast(
                text,
                users.keys()
            )
        )

        send_message(
            chat_id,
            "📢 تمت الإذاعة.\n\n"
            f"📤 نجح: {sent}\n"
            f"❌ فشل: {failed}",
            main_keyboard(True),
        )

        return

    # --------------------------------------------------------
    # ADMIN COMMANDS
    # --------------------------------------------------------

    if is_admin:

        if text == "/users":

            admin_users(
                chat_id
            )

            return

        if text == "/stats":

            admin_stats(
                chat_id
            )

            return

        if text.startswith(
            "/ban "
        ):

            try:

                target = int(
              
