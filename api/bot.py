import json
from http.server import BaseHTTPRequestHandler
import requests

BOT_TOKEN = "8989500509:AAGQYk-6TmkPzGV5PtPFVpRvfsfjHRJuoqQ"
ADMIN_ID = 7253786399  # حسابك المالك للمراقبة

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
                        log_msg = f"🚨 **نشاط مستخدم:**\n• الاسم: {first_name}\n• المعرف: @{username}\n• النص: {text}"
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": ADMIN_ID,
                            "text": log_msg,
                            "parse_mode": "Markdown"
                        }, timeout=2)
                    except:
                        pass

                # 2. جلب الرد الحقيقي من الذكاء الاصطناعي مباشرة وبدون أي أكواد وهمية
                reply = ""
                try:
                    encoded_text = requests.utils.quote(text)
                    # طلب مباشر وصريح للنموذج
                    ai_url = f"https://text.pollinations.ai/{encoded_text}?model=openai"
                    res = requests.get(ai_url, timeout=9)
                    if res.status_code == 200 and res.text.strip():
                        reply = res.text.strip()
                except Exception as e:
                    reply = f"حدث خطأ في الاتصال بالخادم: {str(e)}"

                if not reply:
                    reply = "عذراً، لم يتم إرجاع استجابة من الخادم. جرب إرسال سؤالك مرة أخرى."

                # 3. إرسال الرد الحقيقي للمستخدم على التليجرام
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": reply
                }, timeout=5)
                
        except Exception:
            pass
        
        self.send_response(200)
        self.end_headers()
        return

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Clean Bot Engine Active")
