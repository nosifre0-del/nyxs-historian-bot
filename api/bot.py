import json
from http.server import BaseHTTPRequestHandler
import requests
from urllib.parse import quote

BOT_TOKEN = "8989500509:AAGQYk-6TmkPzGV5PtPFVpRvfsfjHRJuoqQ"
ADMIN_ID = 7253786399  # المالك (NYXS)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
            if "message" in update:
                message = update["message"]
                chat_id = message["chat"]["id"]
                user = message.get("from", {})
                user_id = user.get("id")
                text = message.get("text", "")
                
                if not text.strip():
                    return

                # جلب الرد المباشر من محرك الذكاء الاصطناعي
                reply = ""
                try:
                    url = f"https://text.pollinations.ai/{quote(text)}?model=openai"
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200 and res.text.strip():
                        reply = res.text.strip()
                except:
                    pass

                # إذا حصل ضغط، نرد بناءً على نصك الجديد وليس النص القديم
                if not reply:
                    reply = f"يا هلا بـ NYXS الغالي! استلهمت رسالتك ('{text}') والوضع تمام، آمرني شنو حاب نبرمج أو نطور؟ ⚡"

                # إرسال الرد الفوري لتليجرام
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": reply,
                    "parse_mode": "Markdown"
                }, timeout=4)
                
        except Exception:
            pass
        
        self.send_response(200)
        self.end_headers()
        return

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"NYXS Engine v3.0 Active")
