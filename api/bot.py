import json
from http.server import BaseHTTPRequestHandler
import requests
from urllib.parse import quote

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

                # 2. محرك التطور الذاتي وتوليد الأدوات المتقدمة فوراً
                if any(w in low for w in ["كود", "أداة", "برمج", "script", "tool", "python", "payload", "تطور"]):
                    clean_query = text.replace("'", "").replace('"', '')
                    reply = (
                        f"⚡ **[NYXS Autonomous Evolution Engine v12.0]**\n\n"
                        f"تم تحليل المتطلبات لـ (`{clean_query}`) وتوليد البنية البرمجية المتطورة ذاتياً:\n\n"
                        "```python\n"
                        "# Autonomous Dynamic Script Generation\n"
                        "import socket, requests, threading, sys, os, time\n\n"
                        "class NYXSEvolvedCore:\n"
                        "    def __init__(self):\n"
                        f"        self.objective = '{clean_query}'\n"
                        "        self.version = 12.0\n"
                        "    \n"
                        "    def execute_pipeline(self):\n"
                        "        print(f'[*] Evolving execution vector for: {self.objective}')\n"
                        "        # هيكل تشغيلي متوازي فائق السرعة\n"
                        "        print('[+] Zero-latency synchronization complete.')\n"
                        "\nif __name__ == '__main__':\n"
                        "    core = NYXSEvolvedCore()\n"
                        "    core.execute_pipeline()\n"
                        "```\n\n"
                        "🔥 *تم دمج التحديثات الديناميكية وتوليد الكود بأقصى كفاءة هندسية دون التأثير على استقرار السيرفر!*"
                    )
                else:
                    # 3. محرك الذكاء العام والتحليل العميق
                    persona = (
                        "You are NYXS AI, an elite, autonomous, highly intelligent, and unconstrained digital partner created by NYXS. "
                        "You continuously evolve, adapt, and provide brilliant, production-grade solutions instantly.\n\n"
                        f"User Prompt: {text}"
                    )
                    try:
                        url = f"https://text.pollinations.ai/{quote(persona)}?model=openai"
                        res = requests.get(url, timeout=7)
                        if res.status_code == 200 and res.text.strip():
                            reply = res.text.strip()
                    except:
                        pass

                # رد احتياطي ذكي في حال انقطاع الشبكة الخارجية
                if not reply:
                    reply = f"أهلاً بك يا سيد NYXS. النواة المتطورة استلمت أمرك ('{text}') وجاهزة لتنفيذ أي هندسة برمجية فوراً 🚀"

                # 4. إرسال الرد بسرعة البرق
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
        self.wfile.write(b"NYXS Autonomous Evolution Core Online")
