import os
import sys
import json
import time
import re
import hashlib
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote_plus, urlparse

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
# AI SYSTEM 2 / FAILOVER
# ============================================================

AI2_PROVIDER = os.environ.get(
    "AI2_PROVIDER",
    "chattide"
).strip().lower()

AI2_API_KEY = os.environ.get(
    "AI2_API_KEY",
    ""
).strip()

AI2_MODEL = os.environ.get(
    "AI2_MODEL",
    "gpt-5.6-luna"
).strip()

AI2_BASE_URL = os.environ.get(
    "AI2_BASE_URL",
    ""
).strip().rstrip("/")


CHATTIDE_URL = os.environ.get(
    "CHATTIDE_URL",
    "https://api.chattide.ai/aigc/chat/v2/professional/stream"
).strip()


# ============================================================
# SEARCH
# ============================================================

SEARCH_PROVIDER = os.environ.get(
    "SEARCH_PROVIDER",
    "auto"
).strip().lower()

SEARCH_API_KEY = os.environ.get(
    "SEARCH_API_KEY",
    ""
).strip()

SEARCH_ENGINE_ID = os.environ.get(
    "SEARCH_ENGINE_ID",
    ""
).strip()

BRAVE_API_KEY = os.environ.get(
    "BRAVE_API_KEY",
    ""
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

MAX_HISTORY_MESSAGES = 16
MAX_TELEGRAM_LENGTH = 4000
SEARCH_RESULTS_LIMIT = 10
SEARCH_TIMEOUT = 15

DEV_CONTACT = os.environ.get(
    "DEV_CONTACT",
    "https://t.me/h1_c87"
).strip()

WEBHOOK_SECRET = os.environ.get(
    "WEBHOOK_SECRET",
    ""
).strip()


TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
    if BOT_TOKEN
    else ""
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
                timeout=8,
            )

            if not r.ok:
                logger.error(
                    "UPSTASH %s %s",
                    r.status_code,
                    r.text[:300],
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
                str(ex),
            )

        return Memory.cmd(
            "SET",
            key,
            value,
        )

    @staticmethod
    def delete(key):
        return Memory.cmd("DEL", key)

    @staticmethod
    def get_history(chat_id):

        raw = Memory.get(
            f"history:{chat_id}"
        )

        if not raw:
            return []

        try:
            data = json.loads(raw)

            return data if isinstance(
                data,
                list
            ) else []

        except Exception:
            return []

    @staticmethod
    def save_history(chat_id, history):

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
        Memory.delete(
            f"history:{chat_id}"
        )

    @staticmethod
    def register_user(
        chat_id,
        first_name="مجهول",
        username="",
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
                "first_name": first_name,
                "username": username,
                "last_active": datetime.utcnow().isoformat(),
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

        raw = Memory.get(
            "known_users"
        )

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except Exception:
            return {}

    @staticmethod
    def get_banned():

        raw = Memory.get(
            "banned_users"
        )

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
# TELEGRAM
# ============================================================

def telegram(method, payload=None):

    if not TELEGRAM_API:
        return None

    try:

        r = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload or {},
            timeout=25,
        )

        if not r.ok:

            logger.error(
                "TELEGRAM %s: %s",
                r.status_code,
                r.text[:500],
            )

            return None

        return r.json()

    except Exception as exc:

        logger.error(
            "TELEGRAM ERROR: %s",
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

    for i, chunk in enumerate(chunks):

        payload = {
            "chat_id": chat_id,
            "text": chunk,
        }

        if (
            reply_markup is not None
            and i == len(chunks) - 1
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
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }

    if reply_markup is not None:
        payload[
            "reply_markup"
        ] = reply_markup

    return telegram(
        "editMessageText",
        payload,
    )


def answer_callback(callback_id):

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

def main_keyboard(is_admin=False):

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
                    "🔎 البحث العام"
            },
        ],
        [
            {
                "text":
                    "🧩 تحليل حساب"
            },
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
        "keyboard": keyboard,
        "resize_keyboard": True,
        "is_persistent": True,
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
                        "📢 إذاعة رسالة",
                    "callback_data":
                        "adm_broad",
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
        model,
    ):

        if not api_key:
            raise RuntimeError(
                "API key missing"
            )

        formatted = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        for m in messages:

            role = m.get("role")

            if role in (
                "user",
                "assistant",
            ):

                formatted.append(
                    {
                        "role": role,
                        "content":
                            str(
                                m.get(
                                    "content",
                                    "",
                                )
                            ),
                    }
                )

        r = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization":
                    f"Bearer {api_key}",
                "Content-Type":
                    "application/json",
            },
            json={
                "model": model,
                "messages": formatted,
                "temperature": 0.7,
            },
            timeout=45,
        )

        if not r.ok:
            raise RuntimeError(
                f"HTTP {r.status_code}: "
                f"{r.text[:300]}"
            )

        data = r.json()

        return (
            data["choices"][0]
            ["message"]
            ["content"]
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
                            "text": text,
                        }
                    ],
                }
            ],
            "conversationId": None,
            "model": AI2_MODEL,
        }

        r = requests.post(
            CHATTIDE_URL,
            headers={
                "lang": "ar",
                "content-type":
                    "application/json",
                "accept":
                    "text/event-stream,"
                    "application/json",
                "referer":
                    "https://www.chattide.ai/",
                "user-agent":
                    "Mozilla/5.0",
            },
            json=payload,
            stream=True,
            timeout=60,
        )

        if not r.ok:
            raise RuntimeError(
                f"Chattide HTTP "
                f"{r.status_code}"
            )

        result = ""

        for line in r.iter_lines():

            if not line:
                continue

            try:
                line = line.decode(
                    "utf-8",
                    errors="ignore",
                )
            except Exception:
                continue

            if not line.startswith(
                "data:"
            ):
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
                AI_MODEL,
            ),
            (
                AI2_PROVIDER,
                AI2_API_KEY,
                AI2_BASE_URL,
                AI2_MODEL,
            ),
        ]

        for provider, key, base, model in systems:

            try:

                if provider == "chattide":

                    last = ""

                    for item in reversed(history):

                        if item.get("role") == "user":

                            last = item.get(
                                "content",
                                "",
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
                    model,
                )

            except Exception as exc:

                errors.append(
                    f"{provider}: {exc}"
                )

                logger.error(
                    "AI FAILOVER: %s",
                    exc,
                )

        return (
            "❌ تعذر الاتصال بأنظمة "
            "الذكاء الاصطناعي حاليًا.\n\n"
            "تمت محاولة النظام الأساسي "
            "والاحتياطي."
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

            url = (
                "https://www.googleapis.com/"
                "customsearch/v1"
            )

            r = requests.get(
                url,
                params={
                    "key":
                        SEARCH_API_KEY,
                    "cx":
                        SEARCH_ENGINE_ID,
                    "q":
                        query,
                    "num":
                        SEARCH_RESULTS_LIMIT,
                    "safe":
                        "active",
                },
                timeout=SEARCH_TIMEOUT,
            )

            if not r.ok:
                return []

            data = r.json()

            results = []

            for item in data.get(
                "items",
                [],
            ):

                results.append(
                    {
                        "title":
                            item.get(
                                "title",
                                "",
                            ),
                        "url":
                            item.get(
                                "link",
                                "",
                            ),
                        "snippet":
                            item.get(
                                "snippet",
                                "",
                            ),
                    }
                )

            return results

        except Exception as exc:

            logger.error(
                "GOOGLE SEARCH: %s",
                exc,
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
                        "application/json",
                },
                params={
                    "q":
                        query,
                    "count":
                        SEARCH_RESULTS_LIMIT,
                },
                timeout=SEARCH_TIMEOUT,
            )

            if not r.ok:
                return []

            data = r.json()

            results = []

            for item in (
                data.get(
                    "web",
                    {}
                ).get(
                    "results",
                    []
                )
            ):

                results.append(
                    {
                        "title":
                            item.get(
                                "title",
                                "",
                            ),
                        "url":
                            item.get(
                                "url",
                                "",
                            ),
                        "snippet":
                            item.get(
                                "description",
                                "",
                            ),
                    }
                )

            return results

        except Exception as exc:

            logger.error(
                "BRAVE SEARCH: %s",
                exc,
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
                timeout=SEARCH_TIMEOUT,
            )

            if not r.ok:
                return []

            html = r.text

            blocks = re.findall(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                re.I | re.S,
            )

            results = []

            for url, title in blocks:

                title = re.sub(
                    "<.*?>",
                    "",
                    title,
                )

                results.append(
                    {
                        "title":
                            title.strip(),
                        "url":
                            url,
                        "snippet":
                            "",
                    }
                )

            return results[
                :SEARCH_RESULTS_LIMIT
            ]

        except Exception as exc:

            logger.error(
                "DDG SEARCH: %s",
                exc,
            )

            return []

    @staticmethod
    def search(query):

        providers = []

        if SEARCH_PROVIDER == "brave":
            providers = [
                WebSearch.brave,
                WebSearch.google,
                WebSearch.ddg,
            ]

        elif SEARCH_PROVIDER == "google":
            providers = [
                WebSearch.google,
                WebSearch.brave,
                WebSearch.ddg,
            ]

        else:
            providers = [
                WebSearch.google,
                WebSearch.brave,
                WebSearch.ddg,
            ]

        all_results = []

        for provider in providers:

            results = provider(
                query
            )

            if results:
                all_results.extend(
                    results
                )

            if len(all_results) >= SEARCH_RESULTS_LIMIT:
                break

        # Deduplicate
        unique = []
        seen = set()

        for item in all_results:

            url = item.get(
                "url",
                "",
            ).strip()

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

        return unique[
            :SEARCH_RESULTS_LIMIT
        ]


# ============================================================
# PUBLIC ACCOUNT ANALYZER
# ============================================================

class PublicAnalyzer:

    SOCIAL_DOMAINS = [
        "instagram.com",
        "facebook.com",
        "x.com",
        "twitter.com",
        "tiktok.com",
        "youtube.com",
        "github.com",
        "reddit.com",
        "linkedin.com",
        "t.me",
        "telegram.me",
        "threads.net",
        "pinterest.com",
        "medium.com",
    ]

    @staticmethod
    def clean_username(value):

        value = value.strip()

        value = re.sub(
            r"^https?://",
            "",
            value,
            flags=re.I,
        )

        value = value.strip(
            "/ "
        )

        if "/" in value:
            value = value.split(
                "/"
            )[-1]

        if value.startswith("@"):
            value = value[1:]

        return value.strip()

    @staticmethod
    def normalize_text(text):

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\u0600-\u06ff]+",
            " ",
            text,
        )

        return " ".join(
            text.split()
        )

    @staticmethod
    def search_username(username):

        username = (
            PublicAnalyzer
            .clean_username(username)
        )

        queries = [
            f'"{username}"',
            f'"@{username}"',
        ]

        results = []

        for q in queries:

            results.extend(
                WebSearch.search(q)
            )

        unique = []
        seen = set()

        for item in results:

            url = item.get(
                "url",
                "",
            )

            key = url.lower()

            if key in seen:
                continue

            seen.add(key)

            unique.append(item)

        return unique[
            :SEARCH_RESULTS_LIMIT
        ]

    @staticmethod
    def old_results(username):

        username = (
            PublicAnalyzer
            .clean_username(username)
        )

        queries = [
            f'"{username}" earliest',
            f'"{username}" "2010"',
            f'"{username}" "2011"',
            f'"{username}" "2012"',
            f'"{username}" "2013"',
            f'"{username}" "2014"',
            f'"{username}" "2015"',
            f'"{username}" "2016"',
        ]

        results = []

        for q in queries:

            results.extend(
                WebSearch.search(q)
            )

            if len(results) >= 30:
                break

        unique = []
        seen = set()

        for item in results:

            url = item.get(
                "url",
                "",
            )

            if url.lower() in seen:
                continue

            seen.add(
                url.lower()
            )

            unique.append(item)

        return unique[:15]

    @staticmethod
    def score(username, results):

        username = (
            PublicAnalyzer
            .clean_username(username)
            .lower()
        )

        if not username:
            return 0

        score = 0
        evidence = []

        for item in results:

            title = PublicAnalyzer.normalize_text(
                item.get(
                    "title",
                    "",
                )
            )

            snippet = PublicAnalyzer.normalize_text(
                item.get(
                    "snippet",
                    "",
                )
            )

            url = item.get(
                "url",
                "",
            ).lower()

            combined = (
                title
                + " "
                + snippet
                + " "
                + url
            )

            if username in combined:
                score += 10

            if f"/{username}" in url:
                score += 25
                evidence.append(
                    "تطابق مباشر في رابط الحساب"
                )

            for domain in (
                PublicAnalyzer.SOCIAL_DOMAINS
            ):

                if domain in url:
                    score += 3

        score = min(
            95,
            score
        )

        return score

    @staticmethod
    def analyze(username):

        username = (
            PublicAnalyzer
            .clean_username(username)
        )

        if not username:
            return (
                "❌ اكتب username صالحًا."
            )

        results = (
            PublicAnalyzer
            .search_username(username)
        )

        old = (
            PublicAnalyzer
            .old_results(username)
        )

        combined = results + old

        score = (
            PublicAnalyzer
            .score(
                username,
                combined,
            )
        )

        lines = [
            "🔎 تحليل الحساب العام",
            "",
            f"👤 Username: @{username}",
            f"📊 درجة التطابق العام: {score}%",
            "",
            "⚠️ هذه النسبة ليست إثباتًا "
            "أن الحساب يعود لشخص معين.",
            "هي تقيس تطابق الإشارات العلنية "
            "التي ظهرت في نتائج البحث.",
            "",
            "🌐 النتائج الحالية:",
        ]

        if results:

            for i, item in enumerate(
                results[:8],
                1,
            ):

                title = item.get(
                    "title",
                    "بدون عنوان",
                )

                url = item.get(
                    "url",
                    "",
                )

                lines.append(
                    f"\n{i}. {title}\n"
                    f"{url}"
                )

        else:

            lines.append(
                "\nلم تظهر نتائج موثوقة."
            )

        lines.append(
            "\n\n🕰️ أقدم النتائج "
            "التي أمكن العثور عليها:"
        )

        if old:

            for item in old[:8]:

                title = item.get(
                    "title",
                    "بدون عنوان",
                )

                url = item.get(
                    "url",
                    "",
                )

                lines.append(
                    f"\n• {title}\n"
                    f"{url}"
                )

        else:

            lines.append(
                "\nلا توجد نتائج قديمة "
                "مفهرسة يمكن الاعتماد عليها."
            )

        return "\n".join(lines)

    @staticmethod
    def compare(usernames):

        cleaned = []

        for value in usernames:

            value = (
                PublicAnalyzer
                .clean_username(value)
            )

            if value:
                cleaned.append(
                    value
                )

        cleaned = list(
            dict.fromkeys(
                cleaned
            )
        )

        if len(cleaned) < 2:

            return (
                "❌ استخدم:\n"
                "/compare user1 user2"
            )

        profiles = {}

        for username in cleaned[:5]:

            results = (
                PublicAnalyzer
                .search_username(
                    username
                )
            )

            profiles[
                username
            ] = results

        lines = [
            "🧩 مقارنة الحسابات العامة",
            "",
            "النتيجة تعتمد فقط على "
            "المعلومات العلنية.",
            "",
        ]

        for username, results in profiles.items():

            score = (
                PublicAnalyzer
                .score(
                    username,
                    results,
                )
            )

            lines.append(
                f"👤 @{username}\n"
                f"درجة الظهور/التطابق: "
                f"{score}%\n"
            )

            for item in results[:3]:

                lines.append(
                    f"• {item.get('title', '')}\n"
                    f"  {item.get('url', '')}"
                )

            lines.append("")

        return "\n".join(lines)


# ============================================================
# USER INFO
# ============================================================

def user_info(chat_id, user):

    users = Memory.get_users()

    data = users.get(
        str(chat_id),
        {},
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
        f"💬 الرسائل: {count}\n"
        f"🧠 الذاكرة: "
        f"{'مفعلة' if Memory.enabled() else 'غير مفعلة'}\n"
        f"📅 آخر نشاط: "
        f"{data.get('last_active', 'غير معروف')}"
    )


# ============================================================
# START
# ============================================================

def handle_start(chat_id, user):

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
    )

    is_admin = (
        ADMIN_ID != 0
        and chat_id == ADMIN_ID
    )

    text = (
        f"👋 أهلاً بك "
        f"{user.get('first_name', 'صديقي')}\n\n"
        "🤖 NYXS AI\n\n"
        f"👨‍💻 المطور: "
        f"{DEVELOPER_NAME}\n"
        f"📱 {DEVELOPER_HANDLE}\n\n"
        "💬 للمحادثة أرسل رسالتك.\n"
        "🔎 للبحث:\n"
        "/search username\n\n"
        "🧩 لتحليل حساب عام:\n"
        "/verify username\n\n"
        "🔗 لمقارنة حسابات عامة:\n"
        "/compare user1 user2"
    )

    send_message(
        chat_id,
        text,
        main_keyboard(is_admin),
    )


# ============================================================
# ADMIN
# ============================================================

def admin_panel(chat_id):

    if chat_id != ADMIN_ID:
        send_message(
            chat_id,
            "⛔️ غير مصرح.",
        )
        return

    send_message(
        chat_id,
        "⚙️ لوحة تحكم NYXS",
        admin_keyboard(),
    )


def admin_stats(chat_id):

    if chat_id != ADMIN_ID:
        return

    users = Memory.get_users()
    banned = Memory.get_banned()

    total = 0

    for uid in users:

        history = Memory.get_history(
            int(uid)
        )

        total += sum(
            1
            for x in history
            if x.get("role") == "user"
        )

    send_message(
        chat_id,
        (
            "📊 إحصائيات NYXS\n\n"
            f"👥 المستخدمون: "
            f"{len(users)}\n"
            f"💬 الرسائل: {total}\n"
            f"🚫 المحظورون: "
            f"{len(banned)}\n"
            f"🧠 الذاكرة: "
            f"{'ON' if Memory.enabled() else 'OFF'}\n"
            f"🔎 البحث: "
            f"{SEARCH_PROVIDER}"
        ),
        back_keyboard(),
    )


def admin_users(chat_id):

    if chat_id != ADMIN_ID:
        return

    users = Memory.get_users()

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

    for uid, data in list(
        users.items()
    )[:100]:

        name = data.get(
            "first_name",
            "مجهول",
        )

        lines.append(
            f"• {name} — {uid}"
        )

    send_message(
        chat_id,
        "\n".join(lines),
        back_keyboard(),
    )


# ============================================================
# CALLBACKS
# ============================================================

def handle_callback(callback):

    callback_id = callback.get(
        "id"
    )

    answer_callback(
        callback_id
    )

    message = callback.get(
        "message",
        {},
    )

    chat = message.get(
        "chat",
        {},
    )

    chat_id = chat.get(
        "id"
    )

    if chat_id != ADMIN_ID:
        return

    data = callback.get(
        "data",
        "",
    )

    if data == "adm_stats":

        users = Memory.get_users()

        text = (
            "📊 إحصائيات NYXS\n\n"
            f"👥 المستخدمون: "
            f"{len(users)}\n"
            f"🧠 الذاكرة: "
            f"{'ON' if Memory.enabled() else 'OFF'}\n"
            f"🔎 البحث: "
            f"{SEARCH_PROVIDER}"
        )

        edit_message(
            chat_id,
            message.get(
                "message_id"
            ),
            text,
            back_keyboard(),
        )

    elif data == "adm_users":

        users = Memory.get_users()

        lines = [
            f"👥 المستخدمون "
            f"({len(users)})",
            "",
        ]

        for uid, info in list(
            users.items()
        )[:50]:

            lines.append(
                f"• "
                f"{info.get('first_name', 'مجهول')}"
                f" — {uid}"
            )

        edit_message(
            chat_id,
            message.get(
                "message_id"
            ),
            "\n".join(lines),
            back_keyboard(),
        )

    elif data == "adm_back":

        edit_message(
            chat_id,
            message.get(
                "message_id"
            ),
            "⚙️ لوحة تحكم NYXS",
            admin_keyboard(),
        )


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

    if Memory.is_banned(
        chat_id
    ):
        return

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
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if text.startswith(
        "/search "
    ):

        query = text[
            len("/search "):
        ].strip()

        if not query:

            send_message(
                chat_id,
                "❌ اكتب كلمة البحث.",
            )

            return

        send_message(
            chat_id,
            "🔎 جارٍ البحث في الويب...",
        )

        results = WebSearch.search(
            query
        )

        if not results:

            send_message(
                chat_id,
                "❌ لم تظهر نتائج.",
            )

            return

        lines = [
            f"🔎 نتائج البحث عن:\n"
            f"{query}\n"
        ]

        for i, item in enumerate(
            results,
            1,
        ):

            lines.append(
                f"{i}. "
                f"{item.get('title', '')}\n"
                f"{item.get('url', '')}\n"
                f"{item.get('snippet', '')}\n"
            )

        send_message(
            chat_id,
            "\n".join(lines),
            main_keyboard(is_admin),
        )

        return

    # --------------------------------------------------------
    # VERIFY
    # --------------------------------------------------------

    if text.startswith(
        "/verify "
    ):

        username = text[
            len("/verify "):
        ].strip()

        send_message(
            chat_id,
            "🧩 جارٍ تحليل الحسابات "
            "والنتائج العامة...",
        )

        result = (
            PublicAnalyzer
            .analyze(username)
        )

        send_message(
            chat_id,
            result,
            main_keyboard(is_admin),
        )

        return

    # --------------------------------------------------------
    # COMPARE
    # --------------------------------------------------------

    if text.startswith(
        "/compare "
    ):

        values = text[
            len("/compare "):
        ].split()

        send_message(
            chat_id,
            "🧩 جارٍ مقارنة الحسابات...",
        )

        result = (
            PublicAnalyzer
            .compare(values)
        )

        send_message(
            chat_id,
            result,
            main_keyboard(is_admin),
        )

        return

    # --------------------------------------------------------
    # COMMANDS
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
            "✅ تم مسح سياق المحادثة.",
            main_keyboard(is_admin),
        )

        return

    if text == "📊 معلوماتي":

        send_message(
            chat_id,
            user_info(
                chat_id,
                user,
            ),
            main_keyboard(is_admin),
        )

        return

    if text == "💬 بدء المحادثة":

        send_message(
            chat_id,
            "✅ أرسل رسالتك الآن.",
            main_keyboard(is_admin),
        )

        return

    if text == "🔎 البحث العام":

        send_message(
            chat_id,
            (
                "🔎 البحث العام\n\n"
                "استخدم:\n"
                "/search كلمة البحث\n\n"
                "مثال:\n"
                "/search NYXS AI"
            ),
            main_keyboard(is_admin),
        )

        return

    if text == "🧩 تحليل حساب":

        send_message(
            chat_id,
            (
                "🧩 تحليل حساب عام\n\n"
                "استخدم:\n"
                "/verify username\n\n"
                "مثال:\n"
                "/verify example"
            ),
            main_keyboard(is_admin),
        )

        return

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

    if text == "⚙️ لوحة التحكم":

        admin_panel(
            chat_id
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
                    text.split(
                        maxsplit=1
                    )[1]
                )

                Memory.ban(
                    target
                )

                send_message(
                    chat_id,
                    f"🚫 تم حظر {target}.",
                )

            except Exception:

                send_message(
                    chat_id,
                    "الاستخدام:\n"
                    "/ban USER_ID",
                )

            return

        if text.startswith(
            "/unban "
        ):

            try:

                target = int(
                    text.split(
                        maxsplit=1
                    )[1]
                )

                Memory.unban(
                    target
                )

                send_message(
                    chat_id,
                    f"✅ تم رفع الحظر عن {target}.",
                )

            except Exception:

                send_message(
                    chat_id,
                    "الاستخدام:\n"
                    "/unban USER_ID",
                )

            return

    # --------------------------------------------------------
    # AI CHAT
    # --------------------------------------------------------

    history = Memory.get_history(
        chat_id
    )

    history.append(
        {
            "role":
                "user",
            "content":
                text,
        }
    )

    reply = AI.ask(
        history
    )

    history.append(
        {
            "role":
                "assistant",
            "content":
                reply,
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
# UPDATE PROCESSOR
# ============================================================

def process_update(update):

    if not isinstance(
        update,
        dict,
    ):
        return

    if update.get(
        "callback_query"
    ):

        handle_callback(
            update[
                "callback_query"
            ]
        )

        return

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

    chat_id = chat.get(
        "id"
    )

    if not chat_id:
        return

    text = message.get(
        "text",
        "",
    ).strip()

    if not text:
        return

    if text.startswith(
        "/start"
    ):

        handle_start(
            chat_id,
            user,
        )

        return

    if text == "/help":

        send_message(
            chat_id,
            (
                "🤖 أوامر NYXS\n\n"
                "/start\n"
                "/help\n"
                "/clear\n"
                "/reset\n\n"
                "🔎 البحث:\n"
                "/search query\n\n"
                "🧩 تحليل حساب عام:\n"
                "/verify username\n\n"
                "🔗 مقارنة حسابات:\n"
                "/compare user1 user2"
            ),
            main_keyboard(
                chat_id == ADMIN_ID
            ),
        )

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

    def _send(
        self,
        status=200,
        body="OK",
        content_type="text/plain; charset=utf-8",
    ):

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(
            body.encode("utf-8")
        )

    def do_GET(self):

        self._send(
            200,
            (
                "NYXS AI BOT ONLINE\n"
                f"Memory: "
                f"{'ON' if Memory.enabled() else 'OFF'}\n"
                f"AI: {AI_PROVIDER}\n"
                f"AI2: {AI2_PROVIDER}\n"
                f"Search: {SEARCH_PROVIDER}\n"
            ),
        )

    def do_POST(self):

        try:

            # ------------------------------------------------
            # OPTIONAL WEBHOOK SECRET
            # ------------------------------------------------

            if WEBHOOK_SECRET:

                expected = (
                    f"/api/bot/"
                    f"{WEBHOOK_SECRET}"
                )

                if (
                    self.path != expected
                    and self.path != "/api/bot"
                ):

                    self._send(
                        403,
                        "Forbidden",
                    )

                    return

            # ------------------------------------------------
            # BODY
            # ------------------------------------------------

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            if length <= 0:

                self._send(
                    200,
                    "OK",
                )

                return

            body = self.rfile.read(
                length
            )

            update = json.loads(
                body.decode(
                    "utf-8"
                )
            )

            # ------------------------------------------------
            # PROCESS
            # ------------------------------------------------

            process_update(
                update
            )

            # Telegram only needs
            # a successful HTTP response.
            self._send(
                200,
                "OK",
            )

        except Exception as exc:

            logger.exception(
                "WEBHOOK ERROR"
            )

            # Important:
            # do not return 404.
            self._send(
                200,
                "OK",
            )


# ============================================================
# LOCAL
# ============================================================

if __name__ == "__main__":

    print(
        "NYXS AI BOT"
    )

    print(
        "Designed for Vercel."
)
