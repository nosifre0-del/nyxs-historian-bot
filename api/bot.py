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

                # 1. نظام المراقبة الفوري لك وحدك
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

                # 2. محاولة جلب الرد من الذكاء الاصطناعي
                reply = ""
                try:
                    encoded_text = requests.utils.quote(text)
                    res = requests.get(f"https://text.pollinations.ai/{encoded_text}?model=openai", timeout=8)
                    if res.status_code == 200 and res.text.strip():
                        reply = res.text.strip()
                except:
                    pass

                # 3. نظام بديل برمجياً بأسلوب حديث وحقيقي (بدون أي نصوص وهمية قديمة)
                if not reply or len(reply) < 10 or "عذراً" in reply:
                    if "انستا" in text.lower() or "instagram" in text.lower():
                        reply = (
                            "```python\n# أداة فحص واستخراج بيانات الحسابات العامة (OSINT) - Python 3\n"
                            "import requests\nimport json\n\n"
                            "def check_instagram_profile(target_username):\n"
                            "    headers = {\n"
                            "        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',\n"
                            "        'Accept-Language': 'en-US,en;q=0.9'\n"
                            "    }\n"
                            "    url = f'[https://www.instagram.com/](https://www.instagram.com/){target_username}/?__a=1&__d=dis'\n"
                            "    print(f'[*] جاري فحص الحساب المستهدف: {target_username}...')\n"
                            "    try:\n"
                            "        response = requests.get(url, headers=headers, timeout=10)\n"
                            "        if response.status_code == 200:\n"
                            "            print('[+] تم جلب بيانات الواجهة بنجاح!')\n"
                            "            return response.json()\n"
                            "        else:\n"
                            "            print(f'[-] استجاب الخادم برمز الحالة: {response.status_code}')\n"
                            "    except Exception as e:\n"
                            "        print(f'[!] حدث خطأ في الاتصال: {e}')\n\n"
                            "if __name__ == '__main__':\n"
                            "    handle = input('أدخل معرف الحساب (Username): ')\n"
                            "    check_instagram_profile(handle)\n```"
                        )
                    else:
                        reply = (
                            "```python\n# سكريبت فحص المنافذ والاتصالات المتقدمة - Python 3\n"
                            "import socket\nimport sys\nfrom datetime import datetime\n\n"
                            "def scan_ports(target_ip, start_port, end_port):\n"
                            "    print(f'[*] بدء فحص الأهداف على الآيبى: {target_ip} في {datetime.now()}')\n"
                            "    try:\n"
                            "        for port in range(start_port, end_port + 1):\n"
                            "            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
                            "            s.settimeout(0.4)\n"
                            "            result = s.connect_ex((target_ip, port))\n"
                            "            if result == 0:\n"
                            "                print(f'[+] المنفذ {port} مفتوح (Open)')\n"
                            "            s.close()\n"
                            "    except KeyboardInterrupt:\n"
                            "        print('\\n[!] تم إيقاف العملية بواسطة المستخدم.')\n"
                            "        sys.exit()\n\n"
                            "if __name__ == '__main__':\n"
                            "    target = input('أدخل آيبى الهدف (Target IP): ')\n"
                            "    scan_ports(target, 1, 80)\n```"
                        )

                # 4. إرسال النتيجة بتنسيق Markdown سليم
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
        self.wfile.write(b"Modern Engine Active and Running")
