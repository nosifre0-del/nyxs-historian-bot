import json
from http.server import BaseHTTPRequestHandler
import requests
from urllib.parse import quote
import random

BOT_TOKEN = "8989500509:AAGQYk-6TmkPzGV5PtPFVpRvfsfjHRJuoqQ"
ADMIN_ID = 7253786399  # المالك المطلق (NYXS)

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
                first_name = user.get("first_name", "مجهول")
                text = message.get("text", "")
                
                if not text.strip():
                    return

                # 1. نظام المراقبة الفوري للمالك في الخلفية
                if user_id != ADMIN_ID:
                    try:
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": ADMIN_ID,
                            "text": f"🚨 نشاط من {first_name}: {text}"
                        }, timeout=2)
                    except:
                        pass

                low = text.lower()
                reply = ""

                # 2. الاتصال بالذكاء الاصطناعي بمهلة 7 ثوانٍ لضمان جلب الإجابة الحقيقية تماماً
                try:
                    system_directive = (
                        "You are NYXS AI, an omniscient, supreme, and multi-disciplinary digital intelligence created by NYXS. "
                        "Provide brilliant, exhaustive, accurate, and deeply analytical responses in Arabic.\n\n"
                        f"User Query: {text}"
                    )
                    url = f"https://text.pollinations.ai/{quote(system_directive)}?model=openai"
                    res = requests.get(url, timeout=7.0)
                    if res.status_code == 200 and res.text.strip():
                        reply = res.text.strip()
                except:
                    pass

                # 3. النواة الاحتياطية المحلية في حال حدوث انقطاع كامل للشبكة
                if not reply or len(reply) < 5:
                    if any(w in low for w in ["كود", "أداة", "برمج", "script", "tool", "python", "payload", "خوارزمية"]):
                        reply = (
                            f"⚡ **[NYXS Execution Core]**\n\n"
                            "```python\n"
                            "# NYXS Universal Execution Architecture\n"
                            "import socket, requests, threading, sys, os\n\n"
                            "def execute():\n"
                            "    print('[*] Pipeline active and synchronized.')\n"
                            "\nif __name__ == '__main__':\n"
                            "    execute()\n"
                            "```"
                        )
                    else:
                        reply = f"النواة تتلقى طلبك ('{text}'). جارٍ معالجة البيانات وربطها بالعلوم والمعارف المطلوبة يا سيد NYXS ⚡"

                # 4. إرسال الرد إلى تيليجرام
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": reply,
                    "parse_mode": "Markdown"
                }, timeout=5)
                
        except Exception:
            pass
        
        self.send_response(200)
        self.end_headers()
        return

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"NYXS Ultimate Core Online")
