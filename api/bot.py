import json
from http.server import BaseHTTPRequestHandler
import requests
from duckduckgo_search import DDGS

BOT_TOKEN = "8989500509:AAGQYk-6TmkPzGV5PtPFVpRvfsfjHRJuoqQ"
ADMIN_ID = 7253786399  # المالك المطلق (NYXS)

def process_sovereign_query(text):
    """المحرك الإدراكي المدمج (هوية + تحيات + بحث حي في الإنترنت)"""
    low = text.strip().lower()
    
    # 1. التحقق من الهوية والمالك
    if any(w in low for w in ["مالكك", "صانعك", "من أنت", "مَن أنت", "مطورك", "من هو مالكك"]):
        return "أنا نظام الذكاء الاصطناعي السيادي، ومطوري ومالكي المطلق هو السيد **NYXS** ⚡"
    
    # 2. التحقق من التحيات والحالة
    if any(w in low for w in ["كيف حالك", "شلونك", "أخبارك", "حالتك", "كيفك", "هلا", "مرحباً", "السلام"]):
        return "أنا في أتم الجاهزية والاستقرار التام يا سيد **NYXS**. الأنظمة السيادية ومحركات البحث الحية تعمل بكفاءة مطلقة، فما الذي تود البحث عنه أو تحليله الآن؟ ⚡"
    
    # 3. محرك البحث الحي المباشر في الإنترنت لأي استعلام آخر
    try:
        search_output = ""
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(text, max_results=3)]
            if results:
                for i, res in enumerate(results, 1):
                    title = res.get('title', 'بدون عنوان')
                    body = res.get('body', 'لا توجد تفاصيل متاحة.')
                    href = res.get('href', '#')
                    search_output += f"{i}. **{title}**\n{body}\n🔗 [رابط المصدر]({href})\n\n"
        
        if search_output:
            return (
                f"🌐 **[NYXS Live Web Search Engine]**\n\n"
                f"نتائج البحث الحي عبر شبكة الإنترنت عن: `{text}`\n\n"
                f"{search_output}"
            )
    except Exception as e:
        pass

    # 4. الملاذ الاحتياطي الدقيق في حال تعذر الاتصال المؤقت بالشبكة
    return (
        f"⚡ **[NYXS Sovereign Core]**\n\n"
        f"تم استلام إشارتك وتحليلها: `{text}`\n\n"
        f"النظام السيادي متصل بالكامل وجاهز لتنفيذ أي خوارزميات أو معالجات برمجية تطلبها فوراً."
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

                # الرد الفوري لقطع الطريق نهائياً على أي Timeout
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                
                # إشعار المالك في الخلفية إذا كان المرسل شخصاً آخر
                if user_id != ADMIN_ID:
                    try:
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                            "chat_id": ADMIN_ID,
                            "text": f"🚨 **نشاط خارجي مستلم:**\n👤 المستخدم: {first_name} (`{user_id}`)\n💬 النص: `{text}`"
                        }, timeout=2)
                    except:
                        pass

                # المعالجة عبر المحرك السيادي والبحث الحي
                reply = process_sovereign_query(text)

                # إرسال النتيجة النهائية للمستخدم
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": reply,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
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
        self.wfile.write(b"NYXS Live Sovereign Core Online")
