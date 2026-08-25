import json
import os
from http.server import BaseHTTPRequestHandler
import requests

BOT_TOKEN = "8989500509:AAGQYk-6TmkPzGV5PtPFVpRvfsfjHRJuoqQ"
ADMIN_ID = 7253786399  # حسابك للمراقبة

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
                username = user.get("username", "بدون يوزر")
                first_name = user.get("first_name", "مجهول")
                text = message.get("text", "")
                
                if not text.strip():
                    return

                # 1. نظام المراقبة الفوري لك أنت وحدك
                if user_id != ADMIN_ID:
                    try:
                        log_msg = f"🚨 نشاط مستخدم:\n- الاسم: {first_name}\n- المعرف: @{username}\n- النص: {text}"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": ADMIN_ID,
                            "text": log_msg
                        }, timeout=2)
                    except:
                        pass

                # 2. طلب فائق السرعة ومباشر لتجنب قيود وقت فيرسيل
                ai_url = f"https://text.pollinations.ai/{requests.utils.quote(text)}?model=openai"
                
                response = requests.get(ai_url, timeout=6)
                
                if response.status_code == 200 and response.text.strip():
                    reply = response.text.strip()
                else:
                    reply = "أهلاً بك! استلمت رسالتك، تفضل بطرح سؤالك وسأجيبك فوراً."

                # 3. إرسال الرد للمستخدم على التليجرام
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": reply
                }, timeout=4)
                
        except Exception:
            pass
        
        self.send_response(200)
        self.end_headers()
        return

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running at high speed!")
