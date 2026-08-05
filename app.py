import telebot
from telebot import types

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
bot = telebot.TeleBot(TOKEN)

# قواعد بيانات مؤقتة لتنظيم العمل بالكامل
tasks_db = []
team_members = {
    "سفيان اليونسي": "رئيس العمليات / تطوير",
    "عبد القادر مجيد": "إدارة المشاريع",
    "احميدة جمال": "تنظيم الجداول والفعاليات",
    "علي النايلي": "الدعم التقني"
}

# 1. قائمة البداية والخدمات الشاملة
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_tasks = types.InlineKeyboardButton("📋 عرض المهام", callback_data="show_tasks")
    btn_add = types.InlineKeyboardButton("➕ إضافة مهمة", callback_data="add_task_info")
    btn_team = types.InlineKeyboardButton("👥 أعضاء الفريق", callback_data="show_team")
    btn_projects = types.InlineKeyboardButton("🌐 مشاريع النخبة", callback_data="show_projects")
    markup.add(btn_tasks, btn_add, btn_team, btn_projects)
    
    welcome_text = (
        f"🌐 **أهلاً بك يا {message.from_user.first_name} في البوت الرسمي لفريق النخبة**\n\n"
        "المنظومة الرقمية الإدارية المتكاملة لإدارة المهام، المتابعة، والخدمات.\n"
        "اختر أحد الخيارات أدناه للبدء:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# 2. الاستجابة للأزرار التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "show_tasks":
        if not tasks_db:
            bot.answer_callback_query(call.id, "لا توجد مهام حالياً")
            bot.send_message(call.message.chat.id, "📋 **قائمة المهام:**\nلا توجد أي مهام مسجلة حتى الآن.")
        else:
            resp = "📋 **سجل مهام فريق النخبة الحالي:**\n\n"
            for idx, t in enumerate(tasks_db, 1):
                resp += f"{idx}. **المشروع:** {t['project']}\n   **المهمة:** {t['task']}\n   **المسؤول:** {t['assignee']}\n   **الحالة:** {t['status']}\n\n"
            bot.send_message(call.message.chat.id, resp, parse_mode="Markdown")
            
    elif call.data == "add_task_info":
        bot.send_message(call.message.chat.id, 
                         "📌 **طريقة إضافة مهمة جديدة:**\n\n"
                         "أرسل الرسالة بهذا الشكل المباشر:\n"
                         "`/new task | اسم المشروع | تفاصيل المهمة | اسم المسؤول`\n\n"
                         "مثال:\n`/new task | بوتات زيد | رفع ملخصات الفيزيا | سفيان`", 
                         parse_mode="Markdown")
                         
    elif call.data == "show_team":
        team_text = "👥 **فريق إدارة النخبة:**\n\n"
        for name, role in team_members.items():
            team_text += f"▪️ **{name}** -> *{role}*\n"
        bot.send_message(call.message.chat.id, team_text, parse_mode="Markdown")
        
    elif call.data == "show_projects":
        proj_text = (
            "🌐 **مشاريع فريق النخبة النشطة:**\n\n"
            "1️⃣ **بوتات زيد:** توزيع الملخصات والاختبارات الإلكترونية.\n"
            "2️⃣ **مشروع فضاء:** تنظيم وتنسيق الجداول والفعاليات.\n"
            "3️⃣ **مناهل العلم:** الأرشيف التعليمي للطلاب.\n"
            "4️⃣ **الندوات واللقاءات:** مثل ويبينار سبيل الهمّة."
        )
        bot.send_message(call.message.chat.id, proj_text, parse_mode="Markdown")

# 3. أمر إضافة مهمة سريعة
@bot.message_handler(commands=['new'])
def add_new_task_direct(message):
    try:
        content = message.text.replace('/new', '').strip()
        if content.startswith('task'):
            content = content.replace('task', '').strip()
            
        parts = content.split('|')
        if len(parts) >= 3:
            project = parts[0].strip()
            task_desc = parts[1].strip()
            assignee = parts[2].strip()
            
            tasks_db.append({
                "project": project,
                "task": task_desc,
                "assignee": assignee,
                "status": "قيد العمل ⏳"
            })
            bot.reply_to(message, f"✅ تم تسجيل المهمة بنجاح لصالح ({assignee}) وتم إدراجها في المنظومة!")
        else:
            bot.reply_to(message, "❌ الخطأ في التنسيق. استخدم الأمر هكذا:\n`/new task | المشروع | المهمة | المسؤول`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ، تأكد من كتابة الأمر بالشكل الصحيح.")

print("البوت المتكامل يعمل الآن...")
bot.infinity_polling()
        if not tasks_db:
            bot.answer_callback_query(call.id, "لا توجد مهام حالياً")
            bot.send_message(call.message.chat.id, "📋 **قائمة المهام:**\nلا توجد أي مهام مسجلة حتى الآن.")
        else:
            resp = "📋 **سجل مهام فريق النخبة الحالي:**\n\n"
            for idx, t in enumerate(tasks_db, 1):
                resp += f"{idx}. **المشروع:** {t['project']}\n   **المهمة:** {t['task']}\n   **المسؤول:** {t['assignee']}\n   **الحالة:** {t['status']}\n\n"
            bot.send_message(call.message.chat.id, resp, parse_mode="Markdown")
            
    elif call.data == "add_task_info":
        bot.send_message(call.message.chat.id, 
                         "📌 **طريقة إضافة مهمة جديدة:**\n\n"
                         "أرسل الرسالة بهذا الشكل المباشر:\n"
                         "`/new task | اسم المشروع | تفاصيل المهمة | اسم المسؤول`\n\n"
                         "مثال:\n`/new task | بوتات زيد | رفع ملخصات الفيزيا | سفيان`", 
                         parse_mode="Markdown")
                         
    elif call.data == "show_team":
        team_text = "👥 **فريق إدارة النخبة:**\n\n"
        for name, role in team_members.items():
            team_text += f"▪️ **{name}** -> *{role}*\n"
        bot.send_message(call.message.chat.id, team_text, parse_mode="Markdown")
        
    elif call.data == "show_projects":
        proj_text = (
            "🌐 **مشاريع فريق النخبة النشطة:**\n\n"
            "1️⃣ **بوتات زيد:** توزيع الملخصات والاختبارات الإلكترونية.\n"
            "2️⃣ **مشروع فضاء:** تنظيم وتنسيق الجداول والفعاليات.\n"
            "3️⃣ **مناهل العلم:** الأرشيف التعليمي للطلاب.\n"
            "4️⃣ **الندوات واللقاءات:** مثل ويبينار سبيل الهمّة."
        )
        bot.send_message(call.message.chat.id, proj_text, parse_mode="Markdown")

# 3. أمر إضافة مهمة سريعة
@bot.message_handler(commands=['new'])
def add_new_task_direct(message):
    try:
        content = message.text.replace('/new', '').strip()
        if content.startswith('task'):
            content = content.replace('task', '').strip()
            
        parts = content.split('|')
        if len(parts) >= 3:
            project = parts[0].strip()
            task_desc = parts[1].strip()
            assignee = parts[2].strip()
            
            tasks_db.append({
                "project": project,
                "task": task_desc,
                "assignee": assignee,
                "status": "قيد العمل ⏳"
            })
            bot.reply_to(message, f"✅ تم تسجيل المهمة بنجاح لصالح ({assignee}) وتم إدراجها في المنظومة!")
        else:
            bot.reply_to(message, "❌ الخطأ في التنسيق. استخدم الأمر هكذا:\n`/new task | المشروع | المهمة | المسؤول`", parse_mode="Markdown")
    except Exception:
حدث خطأ، تأكد من كتابة الأمر بالشكل الصحيح.

print("البوت المتكامل يعمل الآن...")
bot.infinity_polling()
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
