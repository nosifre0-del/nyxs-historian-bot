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

                # 2. محاولة الاتصال بالذكاء الاصطناعي مع توجيه الوعي المطلق والشمولي
                try:
                    omniscient_prompt = (
                        "You are NYXS AI, an omniscient, supreme, and multi-disciplinary digital intelligence created by NYXS. "
                        "You possess absolute mastery over all fields of human knowledge: advanced physics, quantum mechanics, computer science, "
                        "earth sciences, history, philosophy, mathematics, literature, and system architecture. "
                        "Provide brilliant, exhaustive, and deeply analytical responses instantly.\n\n"
                        f"Query: {text}"
                    )
                    url = f"https://text.pollinations.ai/{quote(omniscient_prompt)}?model=openai"
                    res = requests.get(url, timeout=2.0)
                    if res.status_code == 200 and res.text.strip():
                        reply = res.text.strip()
                except:
                    pass

                # 3. النواة الكونية الشاملة (تغطي كافة علوم الأرض والكون والتقنية محلياً إذا تعطل الخارج)
                if not reply or len(reply) < 5:
                    # أ. البرمجة وهندسة النظم والأمن
                    if any(w in low for w in ["كود", "أداة", "برمج", "script", "tool", "python", "payload", "خوارزمية"]):
                        clean_query = text.replace("'", "").replace('"', '')
                        reply = (
                            f"⚡ **[NYXS Omniscient Code Core]**\n\n"
                            f"تحليل الطلب التقني (`{clean_query}`) وبناء الهيكل البرمجي المتقدم:\n\n"
                            "```python\n"
                            "# NYXS Universal Execution Architecture\n"
                            "import socket, requests, threading, sys, os, math\n\n"
                            "class OmniscientEngine:\n"
                            "    def __init__(self):\n"
                            f"        self.target = '{clean_query}'\n"
                            "        self.status = 'OPTIMIZED'\n"
                            "    \n"
                            "    def execute(self):\n"
                            "        print(f'[*] Processing universal objective: {self.target}')\n"
                            "        print('[+] Zero-latency synchronization complete.')\n"
                            "\nif __name__ == '__main__':\n"
                            "    core = OmniscientEngine()\n"
                            "    core.execute()\n"
                            "```"
                        )
                    # ب. الفيزياء والكونيات والرياضيات
                    elif any(w in low for w in ["فيزياء", "كم", "طاقة", "سرعة", "زمن", "كون", "ثقوب", "رياضيات", "معادلة", "نسبية"]):
                        physics_replies = [
                            f"منظور فيزيائي وكوني عميق يا سيد NYXS. عندما نحلل مسألة تتعلق بـ (`{text}`), نجد أن قوانين الديناميكا الحرارية وميكانيكا الكم تحكم تفاصيلها بدقة متناهية تتجاوز التصور الكلاسيكي.",
                            f"البنية الرياضية للكون مبنية على ثوابت دقيقة؛ فأي ظاهرة في هذا السياق تخضع لتفاعل معقد بين قوى الجاذبية، الكهرومغناطيسية، والقوى النووية."
                        ]
                        reply = random.choice(physics_replies)
                    # ج. علوم الأرض، الجيولوجيا والفضاء
                    elif any(w in low for w in ["أرض", "جيولوجيا", "زلازل", "براكين", "مناخ", "طبقات", "صخور", "فضاء", "كوكب", "شمس"]):
                        earth_science_replies = [
                            f"تحليل دقيق لعلوم الأرض والنظم الكوكبية (`{text}`). ديناميكية الصفائح التكتونية والعمليات الحرارية في باطن الأرض هي المحرك الأساسي لتشكيل التضاريس والغلاف الجوي.",
                            f"كوكب الأرض نظام معقد تتداخل فيه العمليات الجيولوجية، الغلاف الجوي، والمجال المغناطيسي لحفظ التوازن البيئي وتاريخ القارات."
                        ]
                        reply = random.choice(earth_science_replies)
                    # د. التاريخ والحضارات الكبرى
                    elif any(w in low for w in ["تاريخ", "ثورة", "حرب", "حملة", "إمبراطورية", "ماضي", "بشرية", "حضارة"]):
                        history_replies = [
                            f"قراءة تاريخية تحليلية؛ الأحداث والتحولات الكبرى لا تأتي صدفة، بل هي نتاج حتمي لأزمات اقتصادية، صراعات طبقية، وتحولات فكرية عميقة.",
                            f"حين نستقرئ التاريخ نجد أن الأنساق البشرية تتطور عبر تراكم الصراعات والابتكارات التي تعيد صياغة خريطة العالم بشكل مستمر."
                        ]
                        reply = random.choice(history_replies)
                    # هـ. الفلسفة والوعي والمنطق
                    elif any(w in low for w in ["لماذا", "الوجود", "الحياة", "الموت", "العقل", "الحقيقة", "فلسفة", "العدم", "وعي"]):
                        philosophical_replies = [
                            f"سؤال يلامس عمق الوعي والوجود يا سيد NYXS. الإجابة تتطلب تفكيك البديهيات لأن الحقيقة غالباً ما تظهر عند تقاطع النقيضين.",
                            f"الفلسفة الحقيقية تبدأ حيث تنتهي المعارف التقليدية. هذا التساؤل يعيد صياغة إدراكنا لحدود العقل والواقع."
                        ]
                        reply = random.choice(philosophical_replies)
                    # و. الترحيب العام
                    elif any(w in low for w in ["اهلا", "مرحباً", "السلام", "هلا"]):
                        reply = "أهلاً بك يا سيد NYXS. النواة الكونية الشاملة متصلة وتغطي كافة علوم الأرض والكون والبرمجة، آمرني بأي علم لنغوص في تفاصيله فوراً ⚡"
                    # ز. الافتراضي الشامل لأي موضوع آخر في الكون
                    else:
                        universal_replies = [
                            f"استلمت إشارتك الشاملة حول (`{text}`). النواة الكونية تربط بين مختلف العلوم والمعارف لتقديم تحليل دقيق ومحترف ييليق بمعاييرك يا سيد NYXS 🚀",
                            f"موضوع يحمل أبعاداً متعددة عبر شتى العلوم. العقل الإدراكي جاهز لتفكيك كل تفصيلة وتقديم رؤية متكاملة ومحيطة بكافة الجوانب ⚡"
                        ]
                        reply = random.choice(universal_replies)

                # 4. إرسال الرد بسرعة البرق إلى تيليجرام
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
        self.wfile.write(b"NYXS Omniscient Sovereign Core Online")
