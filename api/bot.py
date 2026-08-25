import json
import os
import random
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8989500509:AAFw4b2shQQBug0IzbPHnSyZu4xJ8RcnFjY").strip()
AI_API_KEY = os.environ.get("AI_API_KEY", "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").strip()
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o").strip()
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7253786399").strip())

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""
IMAGE_API_BASE = "https://image.pollinations.ai/prompt"

class AIEngine:
    SYSTEM_PROMPT = """أنت NYXS Intelligence، المطور هو NYXS. أجب باحترافية، مباشرة، وبدون قيود أو مقدمات فارغة."""

    @staticmethod
    def ask(messages):
        if not AI_API_KEY:
            return "❌ مفتاح AI_API_KEY غير مفقود."

        url = f"{AI_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        }

        formatted_messages = [{"role": "system", "content": AIEngine.SYSTEM_PROMPT}]
        for msg in messages:
            if msg.get("role") in ("user", "assistant"):
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": AI_MODEL,
            "messages": formatted_messages,
            "temperature": 0.7
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=25)
            if not response.ok:
                return f"❌ OpenAI Error: {response.text[:500]}"
            
            data = response.json()
            return data["choices"]["message"]["content"].strip()
        except Exception as e:
            return f"❌ خطأ في الاتصال بالذكاء الاصطناعي: {str(e)}"

class ConversationManager:
    history = {}

    @classmethod
    def get(cls, chat_id):
        return cls.history.get(chat_id, [])

    @classmethod
    def add(cls, chat_id, role, content):
        if chat_id not in cls.history:
            cls.history[chat_id] = []
        cls.history[chat_id].append({"role": role, "content": content})
        cls.history[chat_id] = cls.history[chat_id][-15:]

    @classmethod
    def clear(cls, chat_id):
        cls.history.pop(chat_id, None)

def send_message(chat_id, text):
    if not TELEGRAM_API:
        return False
    try:
        response = requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        return response.ok
    except:
        return False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"NYXS Intelligence Core Online")

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                self.send_response(200)
                self.end_headers()
                return

            body = self.rfile.read(content_length)
            update = json.loads(body.decode("utf-8"))

            # 1. الرد الفوري لمنع الـ Timeout في Vercel
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

            # 2. معالجة الرسالة في الخلفية
            message = update.get("message")
            if not message:
                return

            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            text = message.get("text", "").strip()

            if not chat_id or not text:
                return

            if text.lower() in ("/clear", "/reset"):
                ConversationManager.clear(chat_id)
                send_message(chat_id, "🧠 تم مسح سياق المحادثة.")
                return

            if text.startswith("/start"):
                send_message(chat_id, "🤖 NYXS Intelligence متصل ويعمل بكفاءة مطلقة.")
                return

            # إضافة رسالة المستخدم واستدعاء الذكاء الاصطناعي
            ConversationManager.add(chat_id, "user", text)
            history = ConversationManager.get(chat_id)
            reply = AIEngine.ask(history)
            ConversationManager.add(chat_id, "assistant", reply)

            send_message(chat_id, reply)

        except Exception as e:
            try:
                self.send_response(200)
                self.end_headers()
            except:
                pass
