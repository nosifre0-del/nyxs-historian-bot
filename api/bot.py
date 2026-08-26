import os
import sys
import json
import base64
import random
import string
import logging
import time
import hashlib
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any

import requests


# ============================================================
# NYXS AI TELEGRAM BOT - SINGLE FILE / VERCEL
# ============================================================

DEVELOPER_NAME = "NYXS"
DEVELOPER_HANDLE = "@h1_c87"

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

ADMIN_ID = int(
    os.environ.get("ADMIN_ID", "0").strip() or "0"
)

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


# ============================================================
# CHATTIDE SETTINGS
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
# GENERAL SETTINGS
# ============================================================

TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
    if BOT_TOKEN
    else ""
)

MAX_HISTORY_MESSAGES = 16
MAX_TELEGRAM_LENGTH = 4000

FORCE_CHANNEL = os.environ.get(
    "FORCE_CHANNEL",
    ""
).strip()

DEV_CONTACT = os.environ.get(
    "DEV_CONTACT",
    "https://t.me/h1_c87"
).strip()


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

            return response.json().get("result")

        except Exception as exc:
            logger.error("UPSTASH EXCEPTION: %s", exc)
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
                str(ex),
            )

        return Memory.cmd("SET", key, value)

    @staticmethod
    def delete(key):
        return Memory.cmd("DEL", key)

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    @staticmethod
    def get_history(chat_id):

        if not Memory.enabled():
            return []

        raw = Memory.get(f"history:{chat_id}")

        if not raw:
            return []

        try:
            data = json.loads(raw)

            if not isinstance(data, list):
                return []

            return data

        except Exception:
            return []

    @staticmethod
    def save_history(chat_id, history):

        if not Memory.enabled():
            return

        history = history[-MAX_HISTORY_MESSAGES:]

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
            Memory.delete(f"history:{chat_id}")

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

            raw = Memory.get("known_users")

            users = (
                json.loads(raw)
                if raw
                else {}
            )

            users[str(chat_id)] = {
                "first_name": first_name,
                "username": username,
                "full_name": full_name,
                "last_active": datetime.now().isoformat(),
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
                "REGISTER USER ERROR: %s",
                exc,
            )

    @staticmethod
    def get_users():

        if not Memory.enabled():
            return {}

        raw = Memory.get("known_users")

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except Exception:
            return {}

    # --------------------------------------------------------
    # BANNED
    # --------------------------------------------------------

    @staticmethod
    def get_banned():

        if not Memory.enabled():
            return []

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
            json.dumps(banned),
        )

    @staticmethod
    def unban(chat_id):

        banned = Memory.get_banned()

        banned = [
            x for x in banned
            if x != chat_id
        ]

        Memory.set(
            "banned_users",
            json.dumps(banned),
        )

    @staticmethod
    def is_banned(chat_id):
        return chat_id in Memory.get_banned()


# ============================================================
# TELEGRAM API
# ============================================================

def telegram(method, payload=None):

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
        text = "❌ لم يتم الحصول على رد."

    chunks = [
        text[i:i + MAX_TELEGRAM_LENGTH]
        for i in range(
            0,
            len(text),
            MAX_TELEGRAM_LENGTH,
        )
    ]

    result = None

    for index, chunk in enumerate(chunks):

        payload = {
            "chat_id": chat_id,
            "text": chunk,
        }

        if (
            reply_markup is not None
            and index == len(chunks) - 1
        ):
            payload["reply_markup"] = reply_markup

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
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    return telegram(
        "editMessageText",
        payload,
    )


def answer_callback(callback_id):

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
        },
    )


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard(is_admin=False):

    keyboard = [
        [
            {
                "text": "💬 بدء المحادثة"
            }
        ],
        [
            {
                "text": "🚀 محادثة جديدة"
            },
            {
                "text": "📊 معلوماتي"
            }
        ],
        [
            {
                "text": "🌐 التواصل مع المطور"
            }
        ],
    ]

    if is_admin:
        keyboard.append(
            [
                {
                    "text": "⚙️ لوحة التحكم"
                }
            ]
        )

    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "is_persistent": True,
    }


def admin_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "📊 الإحصائيات",
                    "callback_data": "adm_stats",
                }
            ],
            [
                {
                    "text": "📢 إذاعة رسالة",
                    "callback_data": "adm_broad",
                }
            ],
            [
                {
                    "text": "👥 قائمة المستخدمين",
                    "callback_data": "adm_users",
                }
            ],
        ]
    }


def back_keyboard():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🔙 رجوع",
                    "callback_data": "adm_back",
                }
            ]
        ]
    }


# ============================================================
# OPENAI-COMPATIBLE ENGINE
# ============================================================

class OpenAIEngine:

    SYSTEM_PROMPT = f"""
أنت مساعد ذكاء اصطناعي تابع لمشروع NYXS.

مطورك وصانعك هو:
NYXS
Telegram: {DEVELOPER_HANDLE}

إذا سُئلت عن مطورك أو صانعك:
اذكر أن المطور هو NYXS ومعرفه {DEVELOPER_HANDLE}.

لا تخترع معلومات عن المشروع.
أجب بشكل مباشر ومحترف ومفيد.
لا تستخدم مقدمات فارغة.
"""

    @staticmethod
    def ask(messages):

        if not AI_API_KEY:

            return (
                "❌ لم يتم ضبط AI_API_KEY "
                "في Environment Variables."
            )

        url = (
            f"{AI_BASE_URL}/chat/completions"
        )

        headers = {
            "Authorization":
                f"Bearer {AI_API_KEY}",
            "Content-Type":
                "application/json",
        }

        formatted = [
            {
                "role": "system",
                "content":
                    OpenAIEngine.SYSTEM_PROMPT,
            }
        ]

        for message in messages:

            role = message.get("role")

            if role in (
                "user",
                "assistant",
            ):

                formatted.append(
                    {
                        "role": role,
                        "content":
                            str(
                                message.get(
                                    "content",
                                    "",
                                )
                            ),
                    }
                )

        payload = {
            "model": AI_MODEL,
            "messages": formatted,
            "temperature": 0.7,
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=45,
            )

            if not response.ok:

                return (
                    f"❌ AI API Error "
                    f"({response.status_code}): "
                    f"{response.text[:300]}"
                )

            data = response.json()

            return (
                data["choices"][0]
                ["message"]
                ["content"]
                .strip()
            )

        except Exception as exc:

            logger.error(
                "OPENAI ERROR: %s",
                exc,
            )

            return (
                "❌ حدث خطأ أثناء الاتصال "
                "بمزود الذكاء الاصطناعي."
            )


# ============================================================
# CHATTIDE ENGINE
# ============================================================

class ChattideEngine:

    def __init__(self):

        self.url = CHATTIDE_URL

        self.model = CHATTIDE_MODEL

        self.n = int(
            "136236490358183259653189950748359669580190635598405237306311768987156534532312435393317272373703463400839797405683556405633769494895560212863113877037049039352461932992309204029954183762382698647733158589129700438379720646895034736836216527276967880354063143356560735956241651941835057143194078092683552570413"
        )

        self.e = 65537

    def rsa_encrypt(
        self,
        message,
    ):

        try:

            max_length = (
                128
                - len(message)
                - 11
            )

            if max_length <= 0:
                return None

            padding = bytes(
                random.randint(1, 255)
                for _ in range(max_length)
            )

            encoded = (
                b"\x00\x02"
                + padding
                + b"\x00"
                + message.encode()
            )

            integer = int.from_bytes(
                encoded,
                "big",
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

        def random_string(length):

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
            "lang": "ar",
            "vtoken": token or "",
            "source": "web",
            "content-type":
                "application/json",
            "accept":
                "text/event-stream,application/json",
            "referer":
                "https://www.chattide.ai/",
            "user-agent":
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
            "spaceHandle": True,
            "roleId": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                        }
                    ],
                }
            ],
            "conversationId":
                conversation_id,
            "model": self.model,
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
                    "CHATTIDE HTTP %s: %s",
                    response.status_code,
                    response.text[:300],
                )

                return None, conversation_id

            result = ""

            new_conversation = (
                conversation_id
            )

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

                data = line_text[
                    len("data:"):
                ].strip()

                if data == "--@DONE@--":
                    break

                if not data:
                    continue

                data = (
                    data
                    .replace(
                        "-=- --",
                        " ",
                    )
                    .replace(
                        "-=-n-",
                        "\n",
                    )
                )

                result += data

            return (
                result.strip(),
                new_conversation,
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
# AI ROUTER
# ============================================================

class AIEngine:

    @staticmethod
    def ask(
        history,
        conversation_id=None,
    ):

        if AI_PROVIDER == "chattide":

            if not history:
                return (
                    "❌ لم يتم إرسال رسالة.",
                    conversation_id,
                )

            last_user_message = None

            for message in reversed(history):

                if message.get("role") == "user":

                    last_user_message = (
                        message.get(
                            "content",
                            "",
                        )
                    )

                    break

            if not last_user_message:

                return (
                    "❌ لم يتم العثور على الرسالة.",
                    conversation_id,
                )

            return chattide.query(
                last_user_message,
                conversation_id,
            )

        reply = OpenAIEngine.ask(
            history
        )

        return reply, conversation_id


# ============================================================
# USER STATS
# ============================================================

class UserStore:

    @staticmethod
    def get_user(chat_id):

        users = Memory.get_users()

        user = users.get(
            str(chat_id),
            {},
        )

        return user

    @staticmethod
    def message_count(chat_id):

        history = Memory.get_history(
            chat_id
        )

        return sum(
            1
            for x in history
            if x.get("role") == "user"
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
            "مجهول",
        ),
        user.get(
            "username",
            "",
        ),
        user.get(
            "first_name",
            "مجهول",
        ),
    )

    is_admin = (
        ADMIN_ID != 0
        and chat_id == ADMIN_ID
    )

    text = (
        f"👋 أهلاً بك "
        f"{user.get('first_name', 'صديقي')} "
        f"في بوت NYXS الذكي.\n\n"
        f"🤖 النموذج: "
        f"{AI_MODEL}\n\n"
        f"👨‍💻 المطور: "
        f"{DEVELOPER_NAME}\n"
        f"📱 {DEVELOPER_HANDLE}\n\n"
        f"✨ أرسل رسالتك للبدء."
    )

    send_message(
        chat_id,
        text,
        main_keyboard(is_admin),
    )


# ============================================================
# USER INFO
# ============================================================

def handle_user_info(
    chat_id,
    user,
):

    info = UserStore.get_user(
        chat_id
    )

    count = UserStore.message_count(
        chat_id
    )

    username = (
        f"@{user.get('username')}"
        if user.get("username")
        else "غير موجود"
    )

    text = (
        "📋 معلوماتك\n\n"
        f"🆔 المعرف: "
        f"{chat_id}\n"
        f"👤 الاسم: "
        f"{user.get('first_name', 'مجهول')}\n"
        f"🔗 username: "
        f"{username}\n"
        f"💬 رسائلك الحالية: "
        f"{count}\n"
        f"📅 أول تسجيل: "
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
# ADMIN PANEL
# ============================================================

def handle_admin_panel(
    chat_id,
):

    if chat_id != ADMIN_ID:
        send_message(
            chat_id,
            "⛔️ غير مصرح لك بالوصول.",
        )
        return

    send_message(
        chat_id,
        "⚙️ لوحة التحكم الإدارية",
        admin_keyboard(),
    )


# ============================================================
# ADMIN USERS
# ============================================================

def admin_users(chat_id):

    if chat_id != ADMIN_ID:
        return

    users = Memory.get_users()

    if not users:

        send_message(
            chat_id,
            "👥 لا يوجد مستخدمون مسجلون.",
            back_keyboard(),
        )

        return

    banned = set(
        Memory.get_banned()
    )

    lines = [
        f"👥 المستخدمون "
        f"({len(users)})\n"
    ]

    for uid, data in list(
        users.items()
    )[:100]:

        name = (
            data.get("full_name")
            or data.get("first_name")
            or "مجهول"
        )

        status = (
            " 🚫"
            if int(uid) in banned
            else ""
        )

        lines.append(
            f"• {name} — "
            f"{uid}{status}"
        )

    send_message(
        chat_id,
        "\n".join(lines),
        back_keyboard(),
    )


# ============================================================
# ADMIN STATS
# ============================================================

def admin_stats(chat_id):

    if chat_id != ADMIN_ID:
        return

    users = Memory.get_users()
    banned = Memory.get_banned()

    total_messages = 0

    for uid in users:

        total_messages += (
            UserStore.message_count(
                int(uid)
            )
        )

    text = (
        "📊 إحصائيات NYXS\n\n"
        f"👤 إجمالي المستخدمين: "
        f"{len(users)}\n"
        f"💬 إجمالي الرسائل المحفوظة: "
        f"{total_messages}\n"
        f"🚫 المحظورون: "
        f"{len(banned)}\n"
        f"🧠 الذاكرة: "
        f"{'مفعّلة' if Memory.enabled() else 'غير مفعّلة'}\n"
        f"🤖 AI Provider: "
        f"{AI_PROVIDER}\n"
        f"🧩 AI Model: "
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

def broadcast_preview(
    chat_id,
):

    if chat_id != ADMIN_ID:
        return

    text = (
        "📢 نظام الإذاعة\n\n"
        "أرسل الآن الرسالة التي تريد "
        "إرسالها إلى المستخدمين.\n\n"
        "⚠️ استخدم الأمر /cancel "
        "للإلغاء."
    )

    send_message(
        chat_id,
        text,
        back_keyboard(),
    )


def perform_broadcast(
    text,
    users,
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

            time.sleep(0.05)

        except Exception:

            failed += 1

    return sent, failed


# ============================================================
# CALLBACKS
# ============================================================

def handle_callback(
    callback,
):

    callback_id = callback.get(
        "id"
    )

    answer_callback(callback_id)

    data = callback.get(
        "data",
        "",
    )

    message = callback.get(
        "message",
        {},
    )

    chat = message.get(
        "chat",
        {},
    )

    chat_id = chat.get("id")

    if chat_id != ADMIN_ID:
        return

    if data == "adm_stats":

        text = (
            "📊 إحصائيات NYXS\n\n"
            f"👤 المستخدمون: "
            f"{len(Memory.get_users())}\n"
            f"🚫 المحظورون: "
            f"{len(Memory.get_banned())}\n"
            f"🧠 الذاكرة: "
            f"{'مفعّلة' if Memory.enabled() else 'غير مفعّلة'}\n"
            f"🤖 المزود: "
            f"{AI_PROVIDER}\n"
            f"🧩 النموذج: "
            f"{AI_MODEL}"
        )

        edit_message(
            chat_id,
            message.get("message_id"),
            text,
            back_keyboard(),
        )

        return

    if data == "adm_users":

        users = Memory.get_users()

        lines = [
            f"👥 المستخدمون "
            f"({len(users)})\n"
        ]

        for uid, info in list(
            users.items()
        )[:50]:

            name = (
                info.get("full_name")
                or info.get("first_name")
                or "مجهول"
            )

            lines.append(
                f"• {name} — {uid}"
            )

        edit_message(
            chat_id,
            message.get("message_id"),
            "\n".join(lines),
            back_keyboard(),
        )

        return

    if data == "adm_broad":

        edit_message(
            chat_id,
            message.get("message_id"),
            "📢 الإذاعة\n\n"
            "أرسل الرسالة الآن.\n"
            "استخدم /cancel للإلغاء.",
        )

        Memory.set(
            f"broadcast_mode:{chat_id}",
            "1",
            ex=600,
        )

        return

    if data == "adm_back":

        edit_message(
            chat_id,
            message.get("message_id"),
            "⚙️ لوحة التحكم الإدارية",
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
    # BROADCAST MODE
    # --------------------------------------------------------

    if (
        is_admin
        and Memory.get(
            f"broadcast_mode:{chat_id}"
        ) == "1"
    ):

        if text.lower() == "/cancel":

            Memory.delete(
                f"broadcast_mode:{chat_id}"
            )

            send_message(
                chat_id,
                "❌ تم إلغاء الإذاعة.",
                main_keyboard(True),
            )

            return

        Memory.delete(
            f"broadcast_mode:{chat_id}"
        )

        users = Memory.get_users()

        sent, failed = perform_broadcast(
            text,
            users.keys(),
        )

        send_message(
            chat_id,
            "📢 تمت الإذاعة.\n\n"
            f"📤 تم الإرسال: {sent}\n"
            f"❌ فشل الإرسال: {failed}",
            main_keyboard(True),
        )

        return

    # --------------------------------------------------------
    # ADMIN COMMANDS
    # --------------------------------------------------------

    if is_admin:

        if text == "/users":

            admin_users(chat_id)
            return

        if text == "/stats":

            admin_stats(chat_id)
            return

        if text.startswith("/ban "):

            try:

                target = int(
                    text.split(
                        maxsplit=1
                    )[1]
                )

                Memory.ban(target)

                send_message(
                    chat_id,
                    f"🚫 تم حظر "
                    f"{target}.",
                )

            except Exception:

                send_message(
                    chat_id,
                    "الاستخدام:\n"
                    "/ban USER_ID",
                )

            return

        if text.startswith("/unban "):

            try:

                target = int(
                    text.split(
                        maxsplit=1
                    )[1]
                )

                Memory.unban(target)

                send_message(
                    chat_id,
                    f"✅ تم رفع الحظر "
                    f"عن {target}.",
                )

            except Exception:

                send_message(
                    chat_id,
                    "الاستخدام:\n"
                    "/unban USER_ID",
                )

            return

    # --------------------------------------------------------
    # BAN
    # --------------------------------------------------------

    if Memory.is_banned(chat_id):

        return

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    if text in (
        "/clear",
        "/reset",
        "🚀 محادثة جديدة",
    ):

        Memory.clear_history(
            chat_id
        )

        send_message(
            chat_id,
            "✅ تم بدء محادثة جديدة "
            "ومسح سياق المحادثة.",
            main_keyboard(is_admin),
        )

        return

    # --------------------------------------------------------
    # USER INFO
    # --------------------------------------------------------

    if text == "📊 معلوماتي":

        handle_user_info(
            chat_id,
            user,
        )

        return

    # --------------------------------------------------------
    # START CHAT
    # --------------------------------------------------------

    if text == "💬 بدء المحادثة":

        send_message(
            chat_id,
            "✅ أرسل رسالتك الآن.",
            main_keyboard(is_admin),
        )

        return

    # --------------------------------------------------------
    # DEVELOPER
    # --------------------------------------------------------

    if text == "🌐 التواصل مع المطور":

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text":
                            "📩 مراسلة المطور",
                        "url":
                            DEV_CONTACT,
                    }
                ]
            ]
        }

        send_message(
            chat_id,
            "🌐 التواصل مع المطور:",
            keyboard,
        )

        return

    # --------------------------------------------------------
    # ADMIN PANEL
    # --------------------------------------------------------

    if text == "⚙️ لوحة التحكم":

        handle_admin_panel(
            chat_id
        )

        return

    # --------------------------------------------------------
    # REGISTER
    # --------------------------------------------------------

    Memory.register_user(
        chat_id,
        user.get(
            "first_name",
            "مجهول",
        ),
        user.get(
            "username",
            "",
        ),
        user.get(
            "first_name",
            "مجهول",
        ),
    )

    # --------------------------------------------------------
    # ADMIN ACTIVITY
    # --------------------------------------------------------

    if (
        ADMIN_ID
        and chat_id != ADMIN_ID
    ):

        name = user.get(
            "first_name",
            "مجهول",
        )

        send_message(
            ADMIN_ID,
            "📩 نشاط جديد\n\n"
            f"👤 {name}\n"
            f"🆔 {chat_id}\n"
            f"💬 {text[:300]}",
        )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    history = Memory.get_history(
        chat_id
    )

    history.append(
        {
            "role": "user",
            "content": text,
        }
    )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    if AI_PROVIDER == "chattide":

        # Chattide uses its own conversation
        # context, while the bot keeps a lightweight
        # local history as well.

        conversation_key = (
            f"conversation:{chat_id}"
        )

        conversation_id = Memory.get(
            conversation_key
        )

        reply, new_conversation = (
            AIEngine.ask(
                history,
                conversation_id,
            )
        )

        if new_conversation:

            Memory.set(
                conversation_key,
                new_conversation,
                ex=604800,
            )

    else:

        reply, _ = AIEngine.ask(
            history
        )

    if not reply:

        reply = (
            "❌ تعذر الحصول على رد "
            "من الذكاء الاصطناعي."
        )

    history.append(
        {
            "role": "assistant",
            "content": reply,
        }
    )

    Memory.save_history(
        chat_id,
        history,
    )

    send_message(
        chat_id,
        reply,
        main_keyboard(is_admin),
    )


# ============================================================
# WEBHOOK PROCESSOR
# ============================================================

def process_update(update):

    if not update:
        return

    # --------------------------------------------------------
    # CALLBACK
    # --------------------------------------------------------

    if update.get(
        "callback_query"
    ):

        handle_callback(
            update["callback_query"]
        )

        return

    # --------------------------------------------------------
    # MESSAGE
    # --------------------------------------------------------

    message = update.get(
        "message"
    )

    if not message:
        return

    chat = message.get(
        "chat",
        {},
    )

    user = message.get(
        "from",
        {},
    )

    chat_id = chat.get("id")

    if not chat_id:
        return

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    text = message.get(
        "text",
        "",
    ).strip()

    if text.startswith("/start"):

        handle_start(
            chat_id,
            user,
        )

        return

    if text == "/help":

        send_message(
            chat_id,
            "🤖 أوامر NYXS:\n\n"
            "/start — بدء البوت\n"
            "/clear — مسح المحادثة\n"
            "/reset — محادثة جديدة\n"
            "/help — المساعدة",
            main_keyboard(
                chat_id == ADMIN_ID
            ),
        )

        return

    if not text:
        return

    process_text(
        chat_id,
        text,
        user,
    )


# ============================================================
# VERCEL HANDLER
# ============================================================

class handler(
    BaseHTTPRequestHandler
):

    def _headers(self):

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

    def do_GET(self):

        self.send_response(200)

        self._headers()

        self.end_headers()

        memory_status = (
            "ON"
            if Memory.enabled()
            else "OFF"
        )

        self.wfile.write(
            (
                "NYXS AI BOT ONLINE\n"
                f"Memory: {memory_status}\n"
                f"AI Provider: {AI_PROVIDER}\n"
                f"AI Model: {AI_MODEL}\n"
            ).encode(
                "utf-8"
            )
        )

    def do_POST(self):

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            body = self.rfile.read(
                content_length
            )

            if body:

                try:

                    update = json.loads(
                        body.decode(
                            "utf-8"
                        )
                    )

                    process_update(
                        update
                    )

                except Exception as exc:

                    logger.error(
                        "UPDATE ERROR: %s",
                        exc,
                    )

        except Exception as exc:

            logger.error(
                "POST ERROR: %s",
                exc,
            )

        self.send_response(200)

        self._headers()

        self.end_headers()

        self.wfile.write(
            b"OK"
        )


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print(
        "NYXS AI Bot is designed "
        "for Vercel Webhook deployment."
)
