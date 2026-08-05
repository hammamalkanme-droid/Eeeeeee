import telebot
from telebot import types
import sqlite3

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
bot = telebot.TeleBot(TOKEN)

# --- إعداد قاعدة البيانات الحقيقية (لا تفقد البيانات أبداً عند إعادة التشغيل) ---
def init_db():
    conn = sqlite3.connect('elite_team.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            task TEXT,
            assignee TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# قائمة المدراء والصلاحيات الأساسية لفريق النخبة
ADMINS = [123456789] # ضع معرف التيليجرام الخاص بك هنا للمدير الأعلى

# 1. لوحة التحكم والبداية الرئيسية
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_tasks = types.InlineKeyboardButton("📋 سجل المهام", callback_data="show_tasks")
    btn_add = types.InlineKeyboardButton("➕ إضافة مهمة جديدة", callback_data="add_task_prompt")
    btn_team = types.InlineKeyboardButton("👥 الإدارة العليا", callback_data="show_team")
    btn_projects = types.InlineKeyboardButton("🌐 مشاريع الفريق", callback_data="show_projects")
    markup.add(btn_tasks, btn_add, btn_team, btn_projects)
    
    welcome_text = (
        f"🌐 **المنظومة الإدارية الرسمية لفريق النخبة**\n"
        f"أهلاً بك يا {message.from_user.first_name} في النظام المركزي.\n\n"
        "اختر القسم المطلوب من الأزرار أدناه:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# 2. الاستجابة للأزرار التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    conn = sqlite3.connect('elite_team.db', check_same_thread=False)
    cursor = conn.cursor()
    
    if call.data == "show_tasks":
        cursor.execute("SELECT id, project, task, assignee, status FROM tasks")
        rows = cursor.fetchall()
        if not rows:
            bot.answer_callback_query(call.id, "لا توجد مهام مسجلة حالياً")
            bot.send_message(call.message.chat.id, "📋 **سجل المهام المركزي:**\nلا توجد أي مهام مسجلة في قاعدة البيانات حتى الآن.")
        else:
            resp = "📋 **سجل مهام فريق النخبة النشط:**\n\n"
            for r in rows:
                resp += f"🔹 **رقم #{r[0]}** | **المشروع:** {r[1]}\n   📌 **المهمة:** {r[2]}\n   👤 **المسؤول:** {r[3]}\n   📊 **الحالة:** {r[4]}\n\n"
            bot.send_message(call.message.chat.id, resp, parse_mode="Markdown")
            
    elif call.data == "add_task_prompt":
        bot.send_message(call.message.chat.id, 
                         "📌 **إضافة مهمة جديدة للمنظومة:**\n\n"
                         "أرسل الأمر بهذا التنسيق المباشر:\n"
                         "`/new المشروع | المهمة | المسؤول`\n\n"
                         "مثال:\n`/new بوتات زيد | رفع ملخصات الفيزيا | سفيان اليونسي`", 
                         parse_mode="Markdown")
                         
    elif call.data == "show_team":
        team_text = (
            "👥 **هيكل إدارة فريق النخبة:**\n\n"
            "▪️ **همَّام الكانمي** -> المؤسس / الإدارة العليا\n"
            "▪️ **سفيان اليونسي** -> رئيس العمليات / تطوير\n"
            "▪️ **عبد القادر مجيد** -> إدارة المشاريع\n"
            "▪️ **احميدة جمال** -> تنظيم الجداول والفعاليات\n"
            "▪️ **علي النايلي** -> الدعم التقني"
        )
        bot.send_message(call.message.chat.id, team_text, parse_mode="Markdown")
        
    elif call.data == "show_projects":
        proj_text = (
            "🌐 **مشاريع فريق النخبة المركزية:**\n\n"
            "1️⃣ **بوتات زيد:** توزيع الملخصات والاختبارات الإلكترونية.\n"
            "2️⃣ **مشروع فضاء:** تنظيم وتنسيق الجداول والفعاليات.\n"
            "3️⃣ **مناهل العلم:** الأرشيف التعليمي للطلاب.\n"
            "4️⃣ **الندوات واللقاءات:** مثل ويبينار سبيل الهمّة."
        )
        bot.send_message(call.message.chat.id, proj_text, parse_mode="Markdown")
        
    conn.close()

# 3. أمر إضافة مهمة جديدة وحفظها نهائياً في قاعدة البيانات
@bot.message_handler(commands=['new'])
def add_new_task(message):
    try:
        content = message.text.replace('/new', '').strip()
        parts = content.split('|')
        if len(parts) >= 3:
            project = parts[0].strip()
            task_desc = parts[1].strip()
            assignee = parts[2].strip()
            
            conn = sqlite3.connect('elite_team.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (project, task, assignee, status) VALUES (?, ?, ?, ?)",
                           (project, task_desc, assignee, "قيد العمل ⏳"))
            conn.commit()
            conn.close()
            
            bot.reply_to(message, f"✅ تم حفظ وتثبيت المهمة في قاعدة البيانات بنجاح لصالح ({assignee})!")
        else:
            bot.reply_to(message, "❌ الخطأ في التنسيق. استخدم الأمر هكذا:\n`/new المشروع | المهمة | المسؤول`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء حفظ المهمة في قاعدة البيانات.")

print("منظومة فريق النخبة المتكاملة تعمل الآن...")
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
    except Exception as e:
        bot.reply_to(message, "حدث خطأ، تأكد من كتابة الأمر بالشكل الصحيح.")

print("البوت المتكامل يعمل الآن...")
bot.infinity_polling()
