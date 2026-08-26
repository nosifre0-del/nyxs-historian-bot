import json
import os
from http.server import BaseHTTPRequestHandler
import requests

# ============================================================
# متغيرات البيئة (تُضبط من Vercel Dashboard > Environment Variables)
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini").strip()
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0").strip() or "0")

UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "").strip()

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""
MAX_HISTORY_MESSAGES = 16


# ============================================================
# طبقة الذاكرة الدائمة (Upstash Redis عبر REST API)
# ============================================================
class Memory:
    @staticmethod
    def _enabled():
        return bool(UPSTASH_URL and UPSTASH_TOKEN)

    @staticmethod
    def _headers():
        return {"Authorization": f"Bearer {UPSTASH_TOKEN}"}

    @staticmethod
    def _get_raw(key):
        try:
            r = requests.get(f"{UPSTASH_URL}/get/{key}", headers=Memory._headers(), timeout=8)
            if not r.ok:
                return None
            return r.json().get("result")
        except Exception as e:
            print("MEMORY GET ERROR:", e)
            return None

    @staticmethod
    def _set_raw(key, value, ex=None):
        try:
            body = {"value": value}
            if ex:
                body["EX"] = ex
            requests.post(f"{UPSTASH_URL}/set/{key}", headers=Memory._headers(), json=body, timeout=8)
        except Exception as e:
            print("MEMORY SET ERROR:", e)

    # ---------- محادثات المستخدمين ----------
    @staticmethod
    def get_history(chat_id):
        if not Memory._enabled():
            return []
        raw = Memory._get_raw(f"history:{chat_id}")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except Exception:
            return []

    @staticmethod
    def save_history(chat_id, history):
        if not Memory._enabled():
            return
        history = history[-MAX_HISTORY_MESSAGES:]
        Memory._set_raw(f"history:{chat_id}", json.dumps(history, ensure_ascii=False), ex=604800)

    @staticmethod
    def clear_history(chat_id):
        if not Memory._enabled():
            return
        try:
            requests.get(f"{UPSTASH_URL}/del/history:{chat_id}", headers=Memory._headers(), timeout=8)
        except Exception as e:
            print("MEMORY CLEAR ERROR:", e)

    # ---------- سجل المستخدمين المعروفين ----------
    @staticmethod
    def register_user(chat_id, first_name):
        if not Memory._enabled():
            return
        try:
            users = Memory._get_raw("known_users")
            users = json.loads(users) if users else {}
            users[str(chat_id)] = first_name
            Memory._set_raw("known_users", json.dumps(users, ensure_ascii=False))
        except Exception as e:
            print("REGISTER USER ERROR:", e)

    @staticmethod
    def get_known_users():
        if not Memory._enabled():
            return {}
        raw = Memory._get_raw("known_users")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    # ---------- الحظر ----------
    @staticmethod
    def get_banned():
        if not Memory._enabled():
            return []
        raw = Memory._get_raw("banned_users")
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
        Memory._set_raw("banned_users", json.dumps(banned))

    @staticmethod
    def unban_user(chat_id):
        banned = Memory.get_banned()
        banned = [b for b in banned if b != chat_id]
        Memory._set_raw("banned_users", json.dumps(banned))

    @staticmethod
    def is_banned(chat_id):
        return chat_id in Memory.get_banned()


# ============================================================
# محرك الذكاء الاصطناعي
# ============================================================
class AIEngine:
    SYSTEM_PROMPT = (
        "أنت مساعد ذكاء اصطناعي. صانعك ومطورك هو NYXS "
        "(معرفه على تيليجرام: @h1_c87). إذا سألك أحد من صنعك أو من طورك، "
        "أجب بهذه المعلومة بوضوح. "
        "أجب بشكل مباشر ومحترف ومفيد، وبدون مقدمات فارغة."
    )

    @staticmethod
    def ask(messages):
        if not AI_API_KEY:
            return "❌ خطأ: لم يتم ضبط مفتاح AI_API_KEY في متغيرات البيئة."

        url = f"{AI_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        }

        formatted = [{"role": "system", "content": AIEngine.SYSTEM_PROMPT}]
        for msg in messages:
            if msg.get("role") in ("user", "assistant"):
                formatted.append({"role": msg["role"], "content": msg["content"]})

        payload = {"model": AI_MODEL, "messages": formatted, "temperature": 0.7}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=28)
            if not response.ok:
                return f"❌ API Error ({response.status_code}): {response.text[:300]}"
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"❌ خطأ في الاتصال بالذكاء الاصطناعي: {str(e)}"


def send_message(chat_id, text):
    if not TELEGRAM_API:
        return False
    try:
        text = text[:4000] if len(text) > 4000 else text
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
        return r.ok
    except Exception as e:
        print("SEND ERROR:", e)
        return False


# ============================================================
# أوامر المالك (Admin Commands)
# ============================================================
def handle_admin_command(text, admin_chat_id):
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/users":
        users = Memory.get_known_users()
        if not users:
            send_message(admin_chat_id, "لا يوجد مستخدمون مسجّلون بعد.")
            return
        banned = set(Memory.get_banned())
        lines = ["👥 قائمة المستخدمين:\n"]
        for uid, name in users.items():
            status = " 🚫 (محظور)" if int(uid) in banned else ""
            lines.append(f"• {name} — `{uid}`{status}")
        send_message(admin_chat_id, "\n".join(lines))
        return

    if cmd == "/view":
        if not arg:
            send_message(admin_chat_id, "الاستخدام: /view <user_id>")
            return
        try:
            target_id = int(arg)
        except ValueError:
            send_message(admin_chat_id, "معرّف المستخدم غير صحيح.")
            return
        history = Memory.get_history(target_id)
        if not history:
            send_message(admin_chat_id, "لا توجد محادثة مسجّلة لهذا المستخدم.")
            return
        lines = [f"💬 آخر محادثة مع `{target_id}`:\n"]
        for msg in history:
            role = "👤 المستخدم" if msg["role"] == "user" else "🤖 البوت"
            lines.append(f"{role}: {msg['content'][:300]}")
        send_message(admin_chat_id, "\n\n".join(lines))
        return

    if cmd == "/ban":
        if not arg:
            send_message(admin_chat_id, "الاستخدام: /ban <user_id>")
            return
        try:
            target_id = int(arg)
        except ValueError:
            send_message(admin_chat_id, "معرّف المستخدم غير صحيح.")
            return
        Memory.ban_user(target_id)
        send_message(admin_chat_id, f"🚫 تم حظر المستخدم `{target_id}`.")
        return

    if cmd == "/unban":
        if not arg:
            send_message(admin_chat_id, "الاستخدام: /unban <user_id>")
            return
        try:
            target_id = int(arg)
        except ValueError:
            send_message(admin_chat_id, "معرّف المستخدم غير صحيح.")
            return
        Memory.unban_user(target_id)
        send_message(admin_chat_id, f"✅ تم رفع الحظر عن `{target_id}`.")
        return

    return  # ليس أمر إداري معروف


# ============================================================
# معالج الطلبات
# ============================================================
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status = "متصلة" if Memory._enabled() else "غير مفعّلة"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"NYXS Bot Online | Memory: {status}".encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            self._process(body)
        except Exception as e:
            print("HANDLER ERROR:", str(e))

        try:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception:
            pass

    def _process(self, body):
        if not body:
            return
        try:
            update = json.loads(body.decode("utf-8"))
        except Exception:
            return

        message = update.get("message")
        if not message:
            return

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        user = message.get("from", {})
        user_id = user.get("id")
        first_name = user.get("first_name", "مجهول")

        if not chat_id or not text:
            return

        # أوامر المالك (تعمل فقط لو المرسل هو ADMIN_ID)
        if ADMIN_ID and chat_id == ADMIN_ID and text.startswith(("/users", "/view", "/ban", "/unban")):
            handle_admin_command(text, chat_id)
            return

        # منع المستخدمين المحظورين
        if Memory.is_banned(chat_id):
            return

        low = text.lower()

        if low in ("/clear", "/reset"):
            Memory.clear_history(chat_id)
            send_message(chat_id, "🧠 تم مسح سياق المحادثة.")
            return

        if text.startswith("/start"):
            Memory.register_user(chat_id, first_name)
            mem_note = "🧠 الذاكرة الدائمة: مفعّلة" if Memory._enabled() else "⚠️ الذاكرة الدائمة: غير مفعّلة"
            send_message(
                chat_id,
                "🤖 البوت متصل ويعمل.\n\n"
                "اكتب أي رسالة وهرد عليك بذكاء اصطناعي.\n"
                "/clear أو /reset لمسح سياق المحادثة.\n\n"
                f"{mem_note}",
            )
            return

        Memory.register_user(chat_id, first_name)

        # إشعار المالك بأي نشاط من مستخدم آخر
        if ADMIN_ID and chat_id != ADMIN_ID:
            send_message(ADMIN_ID, f"نشاط جديد من {first_name} ({chat_id}):\n{text[:200]}")

        history = Memory.get_history(chat_id)
        history.append({"role": "user", "content": text})

        reply = AIEngine.ask(history)

        history.append({"role": "assistant", "content": reply})
        Memory.save_history(chat_id, history)

        send_message(chat_id, reply)
