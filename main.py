import telebot
from duckduckgo_search import DDGS
import ollama

# توكين البوت الخاص بك
BOT_TOKEN = "8989500509:AAGQYk-6TmkPzGV5PtPFVpRvfsfjHRJuoqQ"
bot = telebot.TeleBot(BOT_TOKEN)

# اسم النموذج المحدد على خادمك (مثل: qwen2.5 أو llama3:instruct-uncensored)
MODEL_NAME = "qwen2.5"

def search_web(query: str, max_results: int = 3) -> str:
    """إجراء بحث سريع في الإنترنت"""
    try:
        with DDGS() as ddgs:
            results = [f"• {r['title']}: {r['body']}" for r in ddgs.text(query, max_results=max_results)]
            return "\n\n".join(results) if results else ""
    except Exception:
        return ""

def get_ai_response(user_prompt: str) -> str:
    """استخراج الكلمات المفتاحية للبحث ثم صياغة الإجابة كاملة"""
    # 1. استخراج كلمة البحث
    search_query_res = ollama.chat(
        model=MODEL_NAME,
        messages=[{'role': 'user', 'content': f"اكتب كلمة أو الجملة المفتاحية للبحث عن هذا الموضوع فقط بدون أي مقدمات: {user_prompt}"}]
    )
    search_query = search_query_res['message']['content'].strip()

    # 2. تنفيذ البحث
    web_context = search_web(search_query)

    # 3. صياغة الإجابة بدون قيود مسبقة
    system_instruction = f"""أنت نموذج ذكاء اصطناعي خاص ومستقل يجيب على المستخدم مباشرة وبكامل التفاصيل.

بيانات حية من البحث:
{web_context if web_context else 'لا تتوفر نتائج بحث حية.'}"""

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {'role': 'system', 'content': system_instruction},
            {'role': 'user', 'content': user_prompt}
        ]
    )
    return response['message']['content']

# الاستجابة لأمر /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "⚡ البوت جاهز ومربوط بالذكاء الاصطناعي والبحث الحي. اكتب سؤالك وسأجيبك فوراً.")

# معالجة كل الرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    status_msg = bot.reply_to(message, "🌐 جاري البحث والتفكير...")
    try:
        answer = get_ai_response(message.text)
        # تعديل الرسالة لإظهار الإجابة النهائية
        bot.edit_message_text(answer, chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء المعالجة: {e}", chat_id=message.chat.id, message_id=status_msg.message_id)

if __name__ == "__main__":
    print("🚀 البوت يعمل الآن ويستقبل الرسائل...")
    bot.infinity_polling()
