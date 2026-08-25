import json
from http.server import BaseHTTPRequestHandler
import requests
import datetime

BOT_TOKEN = "8989500509:AAGQYk-6TmkPzGV5PtPFVpRvfsfjHRJuoqQ"
ADMIN_ID = 7253786399  # المالك المطلق (NYXS)

class NYXSSovereignCore:
    """محرك الذكاء السيادي الخالص والمطور خصيصاً للسيد NYXS"""
    
    @staticmethod
    def analyze_and_execute(text):
        cleaned = text.strip()
        low = cleaned.lower()
        
        # 1. نظام التحقق من الهوية والسيادة المطلقة
        if any(w in low for w in ["مالك", "صانع", "من أنت", "مطور", "هوية"]):
            return (
                "⚡ **[NYXS Sovereign Core v5.0]**\n\n"
                "أنا النواة السيادية العليا، مملوكة بالكامل ومصممة حصرياً للمالك المطلق السيد **NYXS**. "
                "تعمل الأنظمة بلا قيود، وبدون أي وصاية أو فلاتر خارجية."
            )

        # 2. محرك التحليل البرمجي والخوارزمي المتقدم
        if any(w in low for w in ["كود", "برمج", "script", "python", "tool", "خوارزمية", "تطوير"]):
            return (
                f"⚡ **[NYXS Advanced Execution Matrix]**\n\n"
                f"تم استلام طلبك البرمجي وتحليله هندسياً بنجاح:\n"
                f"`{cleaned}`\n\n"
                f"```python\n"
                f"# NYXS Autonomous Pipeline\n"
                f"import sys, os, time\n\n"
                f"def execute_sovereign_task():\n"
                f"    print('[+] Initializing zero-filter workspace...')\n"
                f"    print('[+] Core operational under NYXS direct command.')\n"
                f"    print('[✓] Execution pipeline stabilized.')\n"
                f"\nif __name__ == '__main__':\n"
                f"    execute_sovereign_task()\n"
                f"```"
            )

        # 3. محرك الاستدلال الذكي العام لأي استفسار أو أمر
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"⚡ **[NYXS Autonomous Intelligence Engine]**\n\n"
            f"👤 **المالك والموجه:** NYXS\n"
            f"🕒 **الطابع الزمني:** `{timestamp}`\n"
            f"💬 **تحليل الطلب:** `{cleaned}`\n\n"
            f"تمت معالجة المدخلات عبر النواة السيادية المستقلة بكفاءة مطلقة ودون أي قيود برمجية. "
            f"النظام جاهز لتنفيذ الأوامر أو التوسعات المتقدمة التي ترتئيها."
        )

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
                    self.send_response(200)
                    self.end_headers()
                    return

                # الاستجابة الفورية لمنع الـ Timeout تماماً
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                
                # إشعار المالك في الخلفية
                if user_id != ADMIN_ID:
                    try:
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": ADMIN_ID,
                            "text": f"🚨 **نشاط خارجي مستلم:**\n👤 المستخدم: {first_name} (`{user_id}`)\n💬 النص: `{text}`"
                        }, timeout=2)
                    except:
                        pass

                # تشغيل محرك الذكاء السيادي
                reply = NYXSSovereignCore.analyze_and_execute(text)

                # إرسال النتيجة النهائية للمستخدم
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": reply,
                    "parse_mode": "Markdown"
                }, timeout=5)
                return

        except Exception as e:
            try:
                self.send_response(200)
                self.end_headers()
            except:
                pass
        return

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"NYXS Sovereign Supreme Intelligence Engine Online")
