import json
import os
import datetime
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests

# ============================================================
# الإعدادات - تُقرأ من Environment Variables (Vercel Dashboard)
# لا تضع أي مفاتيح أو توكنات هنا مباشرة في الكود أبداً
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# مزود توليد الصور (Pollinations.ai - مجاني، بدون مفتاح)
IMAGE_API_BASE = "https://image.pollinations.ai/prompt"


class ImageEngine:
    """محرك توليد الصور عالية الدقة"""

    STYLES = {
        "واقعي": "photorealistic, highly detailed, 8k, professional photography",
        "انمي": "anime style, vibrant colors, studio quality",
        "رسم": "digital painting, artstation, concept art",
        "سينمائي": "cinematic lighting, dramatic, movie still, 8k",
        "خيال": "fantasy art, epic, magical atmosphere, highly detailed",
    }

    @staticmethod
    def build_url(prompt, width=1024, height=1024, style=None, seed=None, enhance=True):
        full_prompt = prompt
        if style and style in ImageEngine.STYLES:
            full_prompt = f"{prompt}, {ImageEngine.STYLES[style]}"

        encoded_prompt = urllib.parse.quote(full_prompt)
        params = {
            "width": width,
            "height": height,
            "nologo": "true",
            "model": "flux",
        }
        if seed is not None:
            params["seed"] = seed
        if enhance:
            params["enhance"] = "true"

        query = urllib.parse.urlencode(params)
        return f"{IMAGE_API_BASE}/{encoded_prompt}?{query}"

    @staticmethod
    def parse_command(text):
        """
        يدعم صيغ مرنة:
        /image قطة بيضاء تجلس على القمر
        /image قطة بيضاء --style سينمائي --size 1280x720
        """
        parts = text.split()
        args = parts[1:] if parts and parts[0].startswith("/image") else parts

        style = None
        width, height = 1024, 1024
        prompt_words = []

        i = 0
        while i < len(args):
            token = args[i]
            if token == "--style" and i + 1 < len(args):
                style = args[i + 1]
                i += 2
            elif token == "--size" and i + 1 < len(args):
                try:
                    w, h = args[i + 1].lower().split("x")
                    width, height = int(w), int(h)
                except Exception:
                    pass
                i += 2
            else:
                prompt_words.append(token)
                i += 1

        prompt = " ".join(prompt_words).strip()
        return prompt, style, width, height


class BotCore:
    """محرك الردود النصية العام"""

    @staticmethod
    def handle_text(text):
        cleaned = text.strip()
        low = cleaned.lower()

        if any(w in low for w in ["مالك", "صانع", "من أنت", "مطور", "هوية"]):
            return (
                "أنا بوت خاص تم تطويره وتشغيله بواسطة صاحبه.\n"
                "استخدم /help لمعرفة الأوامر المتاحة."
            )

        if any(w in low for w in ["كود", "برمج", "script", "python", "algorithm"]):
            return (
                "تقدر تبعتلي المتطلبات البرمجية بالتفصيل وهساعدك أكتب كود نظيف "
                "وموثق. لو محتاج مثال بسيط أو شرح لغة معينة قولي."
            )

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"استلمت رسالتك: \"{cleaned}\"\n"
            f"الوقت: {timestamp}\n\n"
            f"لو محتاج توليد صورة استخدم:\n/image وصف الصورة"
        )


def send_message(chat_id, text, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=8)
    except Exception:
        pass


def send_photo(chat_id, photo_url, caption=None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    try:
        r = requests.post(f"{TELEGRAM_API}/sendPhoto", json=payload, timeout=25)
        return r.ok
    except Exception:
        return False


def handle_image_command(chat_id, text):
    prompt, style, width, height = ImageEngine.parse_command(text)

    if not prompt:
        send_message(
            chat_id,
            "لازم تكتب وصف للصورة.\n\n"
            "مثال:\n/image منظر جبلي عند الغروب\n\n"
            "خيارات متقدمة:\n"
            "/image قطة --style انمي --size 1280x720\n\n"
            f"الأنماط المتاحة: {', '.join(ImageEngine.STYLES.keys())}",
        )
        return

    width = max(256, min(width, 1536))
    height = max(256, min(height, 1536))

    send_message(chat_id, "⏳ جاري توليد الصورة، لحظات من فضلك...")

    url = ImageEngine.build_url(prompt, width=width, height=height, style=style)
    ok = send_photo(chat_id, url, caption=f"🎨 {prompt}")

    if not ok:
        send_message(chat_id, "حصل خطأ أثناء توليد الصورة. جرب صياغة مختلفة أو حاول مرة أخرى.")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        # الرد الفوري لتيليجرام لمنع الـ timeout
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

        if not BOT_TOKEN:
            return

        try:
            update = json.loads(post_data.decode("utf-8"))
        except Exception:
            return

        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        user = message.get("from", {})
        user_id = user.get("id")
        first_name = user.get("first_name", "مجهول")
        text = message.get("text", "")

        if not text.strip():
            return

        # إشعار المالك بأي نشاط خارجي (اختياري)
        if ADMIN_ID and user_id != ADMIN_ID:
            send_message(
                ADMIN_ID,
                f"نشاط جديد:\nالمستخدم: {first_name} ({user_id})\nالنص: {text}",
            )

        if text.startswith("/image") or text.startswith("/img"):
            handle_image_command(chat_id, text)
            return

        if text.startswith("/help") or text.startswith("/start"):
            send_message(
                chat_id,
                "الأوامر المتاحة:\n"
                "/image [وصف الصورة] - توليد صورة عالية الدقة\n"
                "  خيارات: --style [نمط] --size [عرضxطول]\n"
                "  الأنماط: واقعي، انمي، رسم، سينمائي، خيال\n\n"
                "أي رسالة نصية عادية هترد عليها تلقائياً.",
            )
            return

        reply = BotCore.handle_text(text)
        send_message(chat_id, reply)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is online")
