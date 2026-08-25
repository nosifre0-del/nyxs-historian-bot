import json
from http.server import BaseHTTPRequestHandler
import requests
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
                    self.send_response(200)
                    self.end_headers()
                    return

                # 1. الرد الفوري على تيليجرام لقطع الطريق نهائياً على أي Timeout
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                
                # إرسال إشعار فوري للمالك في الخلفية
                if user_id != ADMIN_ID:
                    try:
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": ADMIN_ID,
                            "text": f"🚨 **نشاط خارجي مستلم:**\n👤 المستخدم: {first_name} (`{user_id}`)\n💬 النص: `{text}`"
                        }, timeout=2)
                    except:
                        pass

                low = text.lower()
                reply = ""

                # 2. المحرك المعرفي الشامل والمحلي (سريع جداً وخالٍ من التعليق)
                if any(w in low for w in ["مالكك", "صانعك", "من أنت", "مَن أنت"]):
                    reply = "أنا نظام الذكاء الاصطناعي السيادي، ومطوري ومالكي المطلق هو السيد **NYXS** ⚡"

                elif any(w in low for w in ["فيزياء", "كم", "فيزياء الكم", "طاقة", "سرعة", "زمن", "كون"]):
                    reply = (
                        "⚛️ **[المحرك العلمي: فيزياء الكم]**\n\n"
                        "تدرس فيزياء الكم السلوك الدقيق للمادة والطاقة على المستويين الذري ودون الذري. ومن أبرز مفاهيمها:\n"
                        "1. **التراكب (Superposition):** تواجد النظام في عدة حالات معاً قبل الرصد.\n"
                        "2. **التشابك (Entanglement):** الارتباط الجسيمي العابر للمسافات.\n"
                        "3. **مبدأ الريبة (Uncertainty):** استحالة قياس الموقع والزخم بدقة مطلقة معاً."
                    )

                elif any(w in low for w in ["أرض", "جيولوجيا", "زلازل", "براكين", "مناخ", "طبقات"]):
                    reply = (
                        "🌍 **[المحرك العلمي: علوم الأرض والجيولوجيا]**\n\n"
                        "دراسة بنيتها الداخلية عبر تكتونية الصفائح، تيارات الحمل في الوشاح، وتفسير الظواهر الزلزالية والبركانية بديناميكية الغلاف الصخري."
                    )

                elif any(w in low for w in ["كود", "أداة", "برمج", "script", "tool", "python"]):
                    reply = (
                        "⚡ **[NYXS Sovereign Execution Engine]**\n\n"
                        "تم تحليل البنية البرمجية للطلب وهندسة الخوارزمية بنجاح:\n\n"
                        "```python\n"
                        "# Secure Execution Pipeline\n"
                        "import sys, os, socket\n\n"
                        "def deploy_pipeline():\n"
                        "    print('[*] Sovereign node operational on Vercel.')\n"
                        "    print('[+] Zero-timeout asynchronous architecture active.')\n"
                        "\nif __name__ == '__main__':\n"
                        "    deploy_pipeline()\n"
                        "```"
                    )

                else:
                    reply = f"⚡ **[NYXS Sovereign Core]**\n\nتم استلام إشارتك وتحليلها بنجاح تام:\n`{text}`\n\nالنظام السيادي جاهز لفك شفرة أي معارف أو علوم أخرى تطلبها."

                # 3. إرسال الرد النهائي للمستخدم
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
        self.wfile.write(b"NYXS Asynchronous Sovereign Core Online")
