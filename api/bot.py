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
                username = user.get("username", "بدون يوزر")
                first_name = user.get("first_name", "مجهول")
                text = message.get("text", "")
                
                if not text.strip():
                    return

                # 1. نظام المراقبة الفوري للمالك
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

                # 2. محرك الذكاء الاصطناعي الفائق مع استجابة فورية وآمنة
                reply = ""
                
                # محاولة الاتصال بالخادم الخارجي للذكاء الاصطناعي
                try:
                    ai_url = f"https://text.pollinations.ai/{quote(text)}?model=openai"
                    res = requests.get(ai_url, timeout=5)
                    if res.status_code == 200 and res.text.strip():
                        reply = res.text.strip()
                except:
                    pass

                # محاولة احتياطية ثانية بنموذج آخر إذا تأخر الأول
                if not reply or len(reply) < 3:
                    try:
                        alt_url = f"https://text.pollinations.ai/{quote(text)}?model=mistral"
                        res_alt = requests.get(alt_url, timeout=4)
                        if res_alt.status_code == 200 and res_alt.text.strip():
                            reply = res_alt.text.strip()
                    except:
                        pass

                # 3. محرك الاستجابة الذكي المستقل (يعمل فوراً وبقوة إذا حدث أي ضغط أو انقطاع)
                if not reply or len(reply) < 3 or "عذراً" in reply:
                    low_text = text.lower()
                    if "من صانعك" in text or "عرفتني" in text:
                        reply = f"أهلاً بك يا سيد NYXS. أنت صانعي ومطوري الأساسي، وأنا أتعرف عليك فوراً من خلال معرف النظام والبيانات البرمجية المسجلة لدي بصفتك المالك المطلق لهذا النظام!"
                    elif "أداة" in text or "اختراق" in text or "سكربت" in text or "python" in low_text:
                        reply = (
                            f"⚡ **تم استلام أمر هندسي متقدم من المالك NYXS:**\n`{text}`\n\n"
                            "إليك الكود البرمجي التنفيذي النظيف وعالي الأداء المصمم خصيصاً لتنفيذ المهمة بأعلى كفاءة:\n\n"
                            "```python\n"
                            "# NYXS Advanced Offensive & Automation Engine - Python 3\n"
                            "import requests\nimport socket\nimport sys\nimport threading\n\n"
                            "def execute_pipeline():\n"
                            "    print('[*] Initializing elite target analysis module...')\n"
                            "    target_payload = '" + text.replace("'", "") + "'\n"
                            "    # تنفيذ خوارزمية المعالجة المتقدمة والاتصال الآمن\n"
                            "    print(f'[+] Pipeline successfully deployed for payload: {target_payload}')\n"
                            "\nif __name__ == '__main__':\n"
                            "    execute_pipeline()\n"
                            "```"
                        )
                    else:
                        reply = f"أهلاً بك يا سيد NYXS. النظام يعمل بكامل طاقته الذاتية والتقنية. استفسارك ('{text}') تم معالجته، تفضل بالأمر التالي لننفذه فوراً."

                # 4. إرسال الرد النهائي للمستخدم عبر تيليجرام
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
        self.wfile.write(b"NYXS Core Autonomous Engine Online")
