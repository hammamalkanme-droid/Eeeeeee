import telebot
from telebot import types

# ضع التوكن الذي أعطاه لك BotFather هنا بين القوسين
TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
bot = telebot.TeleBot(TOKEN)

# قائمة مؤقتة لتخزين المهام
tasks_db = []

# أمر البداية /start
@bot.message_handler(commands=['start'])
def send_welcome(markup_msg):
    user_name = markup_msg.from_user.first_name
    welcome_text = (
        f"أهلاً بك يا {user_name} في بوت إدارة فريق النخبة 🌐\n\n"
        "الأوامر المتاحة:\n"
        "📌 /newtask - إضافة مهمة جديدة\n"
        "📋 /tasks - عرض كافة المهام الحالية"
    )
    bot.reply_to(markup_msg, welcome_text)

# أمر عرض المهام /tasks
@bot.message_handler(commands=['tasks'])
def show_tasks(message):
    if not tasks_db:
        bot.reply_to(message, "لا توجد أي مهام مسجلة حالياً.")
        return
    
    response = "📋 **قائمة مهام فريق النخبة:**\n\n"
    for i, t in enumerate(tasks_db, 1):
        response += f"{i}. **المشروع:** {t['project']}\n   **المهمة:** {t['task']}\n   **المسؤول:** {t['assignee']}\n   **الحالة:** {t['status']}\n\n"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

# أمر إضافة مهمة جديدة /newtask
@bot.message_handler(commands=['newtask'])
def start_add_task(message):
    msg = bot.reply_to(message, "أرسل تفاصيل المهمة بهذا الشكل:\n`اسم المشروع | المهمة | اسم المسؤول`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_task)

def save_task(message):
    try:
        parts = message.text.split('|')
        if len(parts) == 3:
            project = parts[0].strip()
            task_desc = parts[1].strip()
            assignee = parts[2].strip()
            
            tasks_db.append({
                "project": project,
                "task": task_desc,
                "assignee": assignee,
                "status": "قيد العمل ⏳"
            })
            bot.reply_to(message, "✅ تم تسجيل المهمة وإضافتها بنجاح!")
        else:
            bot.reply_to(message, "❌ الخطأ في التنسيق. تأكد من استخدام الفاصلة العمودية (|).")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء حفظ المهمة، حاول مجدداً.")

# تشغيل البوت
print("البوت يعمل الآن...")
bot.infinity_polling()
