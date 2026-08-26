import os
import io
import json
import base64
import requests
from urllib.parse import quote
from http.server import BaseHTTPRequestHandler

# ============================================================
#                    NYXS AI BOT
# ============================================================
# Developer: NYXS
# Telegram: @h1_c87
# Team: PPT
#
# Features:
# - Groq GPT-OSS 120B text intelligence
# - Groq vision for image understanding
# - Pollinations high-quality image generation
# - Persistent memory with Upstash Redis
# - Optional admin conversation viewing
# - User management
# - Ban / Unban
# - Clear conversation
# - Image analysis
# - Image generation
# - No automatic forwarding of user conversations to admin
# ============================================================


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# Groq
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_BASE_URL = os.environ.get(
    "AI_BASE_URL",
    "https://api.groq.com/openai/v1"
).strip().rstrip("/")

AI_MODEL = os.environ.get(
    "AI_MODEL",
    "openai/gpt-oss-120b"
).strip()

# Vision model
VISION_MODEL = os.environ.get(
    "VISION_MODEL",
    "qwen/qwen3.6-27b"
).strip()

# Pollinations
POLLINATIONS_API_KEY = os.environ.get(
    "POLLINATIONS_API_KEY",
    ""
).strip()

IMAGE_MODEL = os.environ.get(
    "IMAGE_MODEL",
    "gpt-image-2"
).strip()

# Admin
ADMIN_ID = int(
    os.environ.get("ADMIN_ID", "0").strip() or "0"
)

# Upstash
UPSTASH_URL = os.environ.get(
    "UPSTASH_REDIS_REST_URL",
    ""
).strip().rstrip("/")

UPSTASH_TOKEN = os.environ.get(
    "UPSTASH_REDIS_REST_TOKEN",
    ""
).strip()

# Limits
MAX_HISTORY_MESSAGES = 20
MAX_TEXT_LENGTH = 12000
MAX_IMAGE_BYTES = 4 * 1024 * 1024

TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
    if BOT_TOKEN
    else ""
)

TELEGRAM_FILE_API = (
    f"https://api.telegram.org/file/bot{BOT_TOKEN}"
    if BOT_TOKEN
    else ""
)


# ============================================================
#                    MEMORY / UPSTASH
# ============================================================

class Memory:

    @staticmethod
    def enabled():
        return bool(UPSTASH_URL and UPSTASH_TOKEN)

    @staticmethod
    def headers():
        return {
            "Authorization": f"Bearer {UPSTASH_TOKEN}",
            "Content-Type": "application/json"
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
                timeout=8
            )

            if not response.ok:
                print(
                    "UPSTASH ERROR:",
                    response.status_code,
                    response.text[:300]
                )
                return None

            return response.json().get("result")

        except Exception as e:
            print("UPSTASH EXCEPTION:", e)
            return None

    @staticmethod
    def get_raw(key):
        return Memory.cmd("GET", key)

    @staticmethod
    def set_raw(key, value, expire=None):
        if expire:
            return Memory.cmd(
                "SET",
                key,
                value,
                "EX",
                str(expire)
            )

        return Memory.cmd("SET", key, value)

    # --------------------------------------------------------
    # Conversation
    # --------------------------------------------------------

    @staticmethod
    def get_history(chat_id):

        raw = Memory.get_raw(
            f"history:{chat_id}"
        )

        if not raw:
            return []

        try:
            return json.loads(raw)
        except Exception:
            return []

    @staticmethod
    def save_history(chat_id, history):

        history = history[-MAX_HISTORY_MESSAGES:]

        Memory.set_raw(
            f"history:{chat_id}",
            json.dumps(
                history,
                ensure_ascii=False
            ),
            expire=604800
        )

    @staticmethod
    def clear_history(chat_id):

        Memory.cmd(
            "DEL",
            f"history:{chat_id}"
        )

    # --------------------------------------------------------
    # Users
    # --------------------------------------------------------

    @staticmethod
    def register_user(
        chat_id,
        first_name,
        username=""
    ):

        users = Memory.get_known_users()

        users[str(chat_id)] = {
            "name": first_name,
            "username": username or "",
        }

        Memory.set_raw(
            "known_users",
            json.dumps(
                users,
                ensure_ascii=False
            )
        )

    @staticmethod
    def get_known_users():

        raw = Memory.get_raw("known_users")

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except Exception:
            return {}

    # --------------------------------------------------------
    # Ban
    # --------------------------------------------------------

    @staticmethod
    def get_banned():

        raw = Memory.get_raw(
            "banned_users"
        )

        if not raw:
            return []

        try:
            return json.loads(raw)
        except Exception:
            return []

    @staticmethod
    def ban_user(chat_id):

        banned = Memory.get_banned()

        if chat_id not in banned:
            banned.append(chat_id)

        Memory.set_raw(
            "banned_users",
            json.dumps(banned)
        )

    @staticmethod
    def unban_user(chat_id):

        banned = Memory.get_banned()

        banned = [
            x for x in banned
            if x != chat_id
        ]

        Memory.set_raw(
            "banned_users",
            json.dumps(banned)
        )

    @staticmethod
    def is_banned(chat_id):

        return chat_id in Memory.get_banned()


# ============================================================
#                    TELEGRAM
# ============================================================

def telegram_request(method, payload=None):

    if not TELEGRAM_API:
        return None

    try:

        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload or {},
            timeout=20
        )

        if not response.ok:
            print(
                "TELEGRAM ERROR:",
                method,
                response.status_code,
                response.text[:300]
            )
            return None

        return response.json()

    except Exception as e:

        print(
            "TELEGRAM EXCEPTION:",
            method,
            e
        )

        return None


def send_message(chat_id, text):

    if not text:
        return False

    text = str(text)

    # Telegram message limit
    chunks = []

    while len(text) > 4000:
        chunks.append(text[:4000])
        text = text[4000:]

    chunks.append(text)

    success = True

    for chunk in chunks:

        result = telegram_request(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk
            }
        )

        if not result or not result.get("ok"):
            success = False

    return success


def send_photo_bytes(
    chat_id,
    image_bytes,
    filename="nyxs.png",
    caption=""
):

    if not TELEGRAM_API:
        return False

    try:

        files = {
            "photo": (
                filename,
                image_bytes,
                "image/png"
            )
        }

        data = {
            "chat_id": str(chat_id)
        }

        if caption:
            data["caption"] = caption[:1024]

        response = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data=data,
            files=files,
            timeout=60
        )

        return response.ok

    except Exception as e:

        print(
            "SEND PHOTO ERROR:",
            e
        )

        return False


# ============================================================
#                    FILE DOWNLOAD
# ============================================================

def telegram_download_file(file_id):

    if not TELEGRAM_API:
        return None

    try:

        result = telegram_request(
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

        url = (
            f"{TELEGRAM_FILE_API}/"
            f"{file_path}"
        )

        response = requests.get(
            url,
            timeout=30
        )

        if not response.ok:
            return None

        if len(response.content) > MAX_IMAGE_BYTES:
            return None

        return response.content

    except Exception as e:

        print(
            "FILE DOWNLOAD ERROR:",
            e
        )

        return None


# ============================================================
#                    AI ENGINE
# ============================================================

class AIEngine:

    SYSTEM_PROMPT = """
أنت NYXS، مساعد ذكاء اصطناعي متقدم.

المطور:
NYXS
Telegram: @h1_c87
الفريق: PPT

قواعدك:

1. افهم سؤال المستخدم قبل الإجابة.
2. لا تستخدم مقدمات فارغة.
3. كن دقيقًا ومباشرًا.
4. إذا كان السؤال معقدًا، حلله داخليًا ثم أعطِ النتيجة بوضوح.
5. لا تخترع معلومات.
6. إذا لم تكن متأكدًا، قل ذلك بوضوح.
7. أجب بالعربية إذا كان المستخدم يتحدث بالعربية.
8. حافظ على سياق المحادثة.
9. لا تكرر نفس الكلام بلا سبب.
10. عند البرمجة، أعطِ كودًا عمليًا وقابلًا للتشغيل.
11. عند طلب تحليل صورة، صف ما تستطيع رؤيته بدقة ولا تدّعي رؤية شيء غير موجود.
12. لا تكشف مفاتيح API أو المتغيرات السرية أو بيانات النظام.
13. إذا سُئلت عن صانعك، قل إن مطورك هو NYXS ومعرفه @h1_c87.
"""

    @staticmethod
    def ask(messages):

        if not AI_API_KEY:
            return (
                "❌ لم يتم ضبط AI_API_KEY.\n"
                "أضف مفتاح Groq في Vercel Environment Variables."
            )

        url = (
            f"{AI_BASE_URL}/chat/completions"
        )

        headers = {
            "Authorization":
                f"Bearer {AI_API_KEY}",
            "Content-Type":
                "application/json"
        }

        formatted = [
            {
                "role": "system",
                "content":
                    AIEngine.SYSTEM_PROMPT
            }
        ]

        for msg in messages:

            role = msg.get("role")

            content = msg.get(
                "content"
            )

            if role in (
                "user",
                "assistant"
            ) and content:

                formatted.append(
                    {
                        "role": role,
                        "content": content
                    }
                )

        payload = {
            "model": AI_MODEL,
            "messages": formatted,
            "temperature": 0.6,
            "max_tokens": 4096
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

            if not response.ok:

                return (
                    "❌ حدث خطأ في Groq.\n\n"
                    f"HTTP {response.status_code}\n"
                    f"{response.text[:500]}"
                )

            data = response.json()

            return (
                data["choices"][0]
                ["message"]
                ["content"]
                .strip()
            )

        except Exception as e:

            print("AI ERROR:", e)

            return (
                "❌ تعذر الاتصال بمحرك الذكاء الاصطناعي."
            )

    # --------------------------------------------------------
    # Vision
    # --------------------------------------------------------

    @staticmethod
    def analyze_image(
        image_bytes,
        question=""
    ):

        if not AI_API_KEY:
            return (
                "❌ AI_API_KEY غير مضبوط."
            )

        if len(image_bytes) > MAX_IMAGE_BYTES:
            return (
                "❌ الصورة كبيرة جدًا. "
                "أرسل صورة أصغر من 4MB."
            )

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        prompt = question.strip()

        if not prompt:
            prompt = (
                "حلل الصورة بدقة. "
                "صف محتواها، العناصر المهمة، "
                "النصوص الظاهرة إن وجدت، "
                "والتفاصيل التي يمكن استنتاجها "
                "بشكل موثوق."
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "أنت نظام رؤية متقدم تابع لـ NYXS. "
                    "حلل الصور بدقة ولا تخترع تفاصيل."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url":
                                "data:image/jpeg;base64,"
                                + encoded
                        }
                    }
                ]
            }
        ]

        url = (
            f"{AI_BASE_URL}/chat/completions"
        )

        headers = {
            "Authorization":
                f"Bearer {AI_API_KEY}",
            "Content-Type":
                "application/json"
        }

        payload = {
            "model": VISION_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4096
        }

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

            if not response.ok:

                return (
                    "❌ خطأ في نموذج الرؤية:\n"
                    f"{response.status_code}\n"
                    f"{response.text[:500]}"
                )

            data = response.json()

            return (
                data["choices"][0]
                ["message"]
                ["content"]
                .strip()
            )

        except Exception as e:

            print("VISION ERROR:", e)

            return (
                "❌ تعذر تحليل الصورة."
            )


# ============================================================
#                    IMAGE GENERATOR
# ============================================================

class ImageGenerator:

    @staticmethod
    def generate(prompt):

        if not prompt:
            return None, (
                "اكتب وصف الصورة بعد الأمر.\n\n"
                "مثال:\n"
                "/image مدينة بغداد المستقبلية ليلًا، "
                "واقعية سينمائية"
            )

        if not POLLINATIONS_API_KEY:
            return None, (
                "❌ لم يتم ضبط POLLINATIONS_API_KEY.\n\n"
                "أضف مفتاح Pollinations إلى "
                "Environment Variables في Vercel."
            )

        # تحسين تلقائي للوصف
        enhanced_prompt = (
            prompt
            + "\n\n"
            "High quality, highly detailed, "
            "professional composition, "
            "cinematic lighting, "
            "sharp details, realistic textures, "
            "excellent anatomy, "
            "high visual fidelity."
        )

        encoded_prompt = quote(
            enhanced_prompt,
            safe=""
        )

        url = (
            "https://gen.pollinations.ai/image/"
            f"{encoded_prompt}"
            f"?model={quote(IMAGE_MODEL)}"
            "&width=1024"
            "&height=1024"
        )

        headers = {
            "Authorization":
                f"Bearer {POLLINATIONS_API_KEY}"
        }

        try:

            response = requests.get(
                url,
                headers=headers,
                timeout=120
            )

            if not response.ok:

                print(
                    "IMAGE ERROR:",
                    response.status_code,
                    response.text[:500]
                )

                return None, (
                    "❌ فشل توليد الصورة.\n"
                    f"HTTP {response.status_code}"
                )

            if not response.content:
                return None, (
                    "❌ خدمة الصور أعادت نتيجة فارغة."
                )

            return response.content, None

        except requests.Timeout:

            return None, (
                "⏳ توليد الصورة استغرق وقتًا أطول "
                "من المتوقع. حاول مرة أخرى."
            )

        except Exception as e:

            print(
                "IMAGE GENERATOR ERROR:",
                e
            )

            return None, (
                "❌ حدث خطأ أثناء صناعة الصورة."
            )


# ============================================================
#                    ADMIN COMMANDS
# ============================================================

def handle_admin_command(
    text,
    admin_chat_id
):

    parts = text.strip().split(
        maxsplit=1
    )

    command = parts[0].lower()

    arg = (
        parts[1].strip()
        if len(parts) > 1
        else ""
    )

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    if command == "/users":

        users = Memory.get_known_users()

        if not users:

            send_message(
                admin_chat_id,
                "👥 لا يوجد مستخدمون مسجلون."
            )

            return

        banned = set(
            Memory.get_banned()
        )

        lines = [
            "👥 قائمة المستخدمين:",
            ""
        ]

        for uid, info in users.items():

            if isinstance(info, dict):

                name = info.get(
                    "name",
                    "مجهول"
                )

                username = info.get(
                    "username",
                    ""
                )

            else:

                name = str(info)
                username = ""

            status = (
                " 🚫"
                if int(uid) in banned
                else ""
            )

            username_text = (
                f" @{username}"
                if username
                else ""
            )

            lines.append(
                f"• {name}{username_text}"
                f" — {uid}{status}"
            )

        send_message(
            admin_chat_id,
            "\n".join(lines)
        )

        return

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    if command == "/view":

        if not arg:

            send_message(
                admin_chat_id,
                "الاستخدام:\n"
                "/view USER_ID"
            )

            return

        try:

            target_id = int(arg)

        except ValueError:

            send_message(
                admin_chat_id,
                "❌ USER_ID غير صحيح."
            )

            return

        history = Memory.get_history(
            target_id
        )

        if not history:

            send_message(
                admin_chat_id,
                "لا توجد محادثة محفوظة لهذا المستخدم."
            )

            return

        lines = [
            f"💬 محادثة المستخدم {target_id}",
            "",
            "هذه المحادثة عُرضت بطلب المالك فقط.",
            ""
        ]

        for msg in history:

            role = (
                "👤 المستخدم"
                if msg.get("role") == "user"
                else "🤖 NYXS"
            )

            content = msg.get(
                "content",
                ""
            )

            lines.append(
                f"{role}:\n{content[:1500]}"
            )

        final_text = "\n\n".join(lines)

        send_message(
            admin_chat_id,
            final_text
        )

        return

    # --------------------------------------------------------
    # DELETE HISTORY
    # --------------------------------------------------------

    if command in (
        "/deletehistory",
        "/delhistory"
    ):

        if not arg:

            send_message(
                admin_chat_id,
                "الاستخدام:\n"
                "/deletehistory USER_ID"
            )

            return

        try:

            target_id = int(arg)

        except ValueError:

            send_message(
                admin_chat_id,
                "❌ USER_ID غير صحيح."
            )

            return

        Memory.clear_history(
            target_id
        )

        send_message(
            admin_chat_id,
            f"🗑 تم حذف ذاكرة المستخدم {target_id}."
        )

        return

    # --------------------------------------------------------
    # BAN
    # --------------------------------------------------------

    if command == "/ban":

        if not arg:

            send_message(
                admin_chat_id,
                "الاستخدام:\n"
                "/ban USER_ID"
            )

            return

        try:

            target_id = int(arg)

        except ValueError:

            send_message(
                admin_chat_id,
                "❌ USER_ID غير صحيح."
            )

            return

        Memory.ban_user(
            target_id
        )

        send_message(
            admin_chat_id,
            f"🚫 تم حظر {target_id}."
        )

        return

    # --------------------------------------------------------
    # UNBAN
    # --------------------------------------------------------

    if command == "/unban":

        if not arg:

            send_message(
                admin_chat_id,
                "الاستخدام:\n"
                "/unban USER_ID"
            )

            return

        try:

            target_id = int(arg)

        except ValueError:

            send_message(
                admin_chat_id,
                "❌ USER_ID غير صحيح."
            )

            return

        Memory.unban_user(
            target_id
        )

        send_message(
            admin_chat_id,
            f"✅ تم رفع الحظر عن {target_id}."
        )

        return

    # --------------------------------------------------------
    # ADMIN HELP
    # --------------------------------------------------------

    if command == "/admin":

        send_message(
            admin_chat_id,
            """
🛡 أوامر NYXS الإدارية:

/users
عرض المستخدمين فقط.

/view USER_ID
عرض محادثة مستخدم محدد عند الطلب.

/deletehistory USER_ID
حذف ذاكرة مستخدم.

/ban USER_ID
حظر مستخدم.

/unban USER_ID
رفع الحظر.

لا يتم إرسال محادثات المستخدمين إليك تلقائيًا.
"""
        )

        return


# ============================================================
#                    USER HELP
# ============================================================

def user_help():

    return """
🤖 NYXS AI

🧠 الذكاء:
أرسل أي سؤال وسأجيبك.

🖼 فهم الصور:
أرسل صورة مع سؤال أو بدون سؤال.

مثال:
"ما الموجود في الصورة؟"

🎨 صناعة الصور:
/image وصف الصورة

مثال:
/image مدينة مستقبلية في بغداد ليلًا، واقعية سينمائية

🧹 مسح الذاكرة:
/clear
أو
/reset

ℹ️ معلومات:
/help

المطور:
NYXS
@h1_c87
"""


# ============================================================
#                    MESSAGE PROCESSOR
# ============================================================

def process_message(update):

    message = update.get(
        "message"
    )

    if not message:
        return

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    user = message.get(
        "from",
        {}
    )

    user_id = user.get("id")

    first_name = user.get(
        "first_name",
        "مجهول"
    )

    username = user.get(
        "username",
        ""
    )

    if not chat_id:
        return

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    text = (
        message.get(
            "text",
            ""
        )
        or ""
    ).strip()

    if (
        ADMIN_ID
        and chat_id == ADMIN_ID
        and text.startswith("/")
    ):

        admin_commands = (
            "/users",
            "/view",
            "/ban",
            "/unban",
            "/deletehistory",
            "/delhistory",
            "/admin"
        )

        if text.lower().startswith(
            admin_commands
        ):

            handle_admin_command(
                text,
                chat_id
            )

            return

    # --------------------------------------------------------
    # BAN
    # --------------------------------------------------------

    if Memory.is_banned(
        chat_id
    ):

        return

    # --------------------------------------------------------
    # REGISTER
    # --------------------------------------------------------

    Memory.register_user(
        chat_id,
        first_name,
        username
    )

    # ========================================================
    # TEXT COMMANDS
    # ========================================================

    if text.lower() in (
        "/start",
        "/help"
    ):

        send_message(
            chat_id,
            user_help()
        )

        return

    if text.lower() in (
        "/clear",
        "/reset"
    ):

        Memory.clear_history(
            chat_id
        )

        send_message(
            chat_id,
            "🧠 تم مسح سياق محادثتك."
        )

        return

    # --------------------------------------------------------
    # IMAGE GENERATION
    # --------------------------------------------------------

    if text.startswith(
        "/image"
    ) or text.startswith(
        "/imagine"
    ):

        parts = text.split(
            maxsplit=1
        )

        prompt = (
            parts[1].strip()
            if len(parts) > 1
            else ""
        )

        send_message(
            chat_id,
            "🎨 جارٍ صناعة الصورة...\n"
            "قد يستغرق الأمر بعض الوقت."
        )

        image, error = (
            ImageGenerator.generate(
                prompt
            )
        )

        if error:

            send_message(
                chat_id,
                error
            )

            return

        send_photo_bytes(
            chat_id,
            image,
            filename="nyxs_generated.png",
            caption="🎨 NYXS AI"
        )

        return

    # ========================================================
    # IMAGE UNDERSTANDING
    # ========================================================

    photo = message.get(
        "photo"
    )

    if photo:

        # Telegram gives several resolutions.
        # Take the largest available.
        largest = photo[-1]

        file_id = largest.get(
            "file_id"
        )

        image_bytes = (
            telegram_download_file(
                file_id
            )
        )

        if not image_bytes:

            send_message(
                chat_id,
                "❌ لم أستطع تحميل الصورة."
            )

            return

        caption = (
            message.get(
                "caption",
                ""
            )
            or ""
        ).strip()

        send_message(
            chat_id,
            "👁️ جارٍ تحليل الصورة..."
        )

        answer = AIEngine.analyze_image(
            image_bytes,
            caption
        )

        # Store only a textual placeholder,
        # NEVER the image itself.
        history = Memory.get_history(
            chat_id
        )

        history.append(
            {
                "role": "user",
                "content":
                    "[أرسل المستخدم صورة]"
                    + (
                        f"\nسؤاله: {caption}"
                        if caption
                        else ""
                    )
            }
        )

        history.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        Memory.save_history(
            chat_id,
            history
        )

        send_message(
            chat_id,
            answer
        )

        return

    # ========================================================
    # EMPTY MESSAGE
    # ========================================================

    if not text:

        return

    # ========================================================
    # NORMAL AI CHAT
    # ========================================================

    if len(text) > MAX_TEXT_LENGTH:

        text = text[
            :MAX_TEXT_LENGTH
        ]

        send_message(
            chat_id,
            "⚠️ الرسالة طويلة جدًا، "
            "تم تقليصها تلقائيًا."
        )

    history = Memory.get_history(
        chat_id
    )

    history.append(
        {
            "role": "user",
            "content": text
        }
    )

    # Keep context manageable
    history = history[
        -MAX_HISTORY_MESSAGES:
    ]

    reply = AIEngine.ask(
        history
    )

    history.append(
        {
            "role": "assistant",
            "content": reply
        }
    )

    Memory.save_history(
        chat_id,
        history
    )

    send_message(
        chat_id,
        reply
    )


# ============================================================
#                    VERCEL HANDLER
# ============================================================

class handler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        memory_status = (
            "ON"
            if Memory.enabled()
            else "OFF"
        )

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        message = (
            "NYXS AI ONLINE\n"
            f"Memory: {memory_status}\n"
            f"Model: {AI_MODEL}\n"
            f"Vision: {VISION_MODEL}\n"
            f"Image: {IMAGE_MODEL}"
        )

        self.wfile.write(
            message.encode(
                "utf-8"
            )
        )

    def do_POST(self):

        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = self.rfile.read(
                length
            )

            if body:

                update = json.loads(
                    body.decode(
                        "utf-8"
                    )
                )

                process_message(
                    update
                )

        except Exception as e:

            print(
                "WEBHOOK ERROR:",
                e
            )

        # Always return 200 to Telegram
        try:

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain"
            )

            self.end_headers()

            self.wfile.write(
                b"OK"
            )

        except Exception:
            pass
