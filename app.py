import telebot
from telebot import types
import sqlite3

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
bot = telebot.TeleBot(TOKEN)

# قاعدة بيانات خفيفة لتخزين إعدادات كل صاحب قناة وحالة العدادات
def init_db():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    # جدول إعدادات المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            title TEXT,
            custom_message TEXT,
            period_option TEXT
        )
    ''')
    # جدول العدادات لكل بوست يتم نشره
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            owner_id INTEGER,
            count INTEGER,
            title TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# تخزين مؤقت لحالة إعداد الرسالة أثناء محادثة البوت
user_states = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_create = types.InlineKeyboardButton("⚙️ إعداد وتخصيص رسالة الحضور", callback_data="config_menu")
    btn_share = types.InlineKeyboardButton("🔗 انشر بوست الحضور في قناتك", switch_inline_query="create_poll")
    markup.add(btn_create, btn_share)
    
    welcome_text = (
        f" أهلاً بك يا {message.from_user.first_name} في نظام إدارة الحضور الاحترافي.\n\n"
        "هذا البوت يتيح لك إنشاء زر حضور خاص بك لنشره في قناتك:\n"
        "• يضغط العضو على الزر فيتم تسجيل حضوره.\n"
        "• تصلك بياناته مباشرة في الخاص.\n"
        "• يتحدث عداد الحضور تلقائياً في قناتك.\n\n"
        "اختر ما تحب للبدء:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "config_menu")
def config_menu(call):
    user_id = call.from_user.id
    user_states[user_id] = "waiting_title"
    
    bot.send_message(
        call.message.chat.id, 
        "📝 **الخطوة 1 من 2:**\n"
        "أرسل الآن **عنوان أو كليشة البوست** التي ستظهر أعلى زر الحضور في قناتك (مثلاً: تسجيل حضور الفترة الصباحية لشهر أغسطس):"
    )

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_title")
def save_title(message):
    user_id = message.from_user.id
    title = message.text
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, title, custom_message, period_option) VALUES (?, ?, ?, ?)",
                   (user_id, title, "تم تسجيل حضورك بنجاح ✅", "مفعلة"))
    conn.commit()
    conn.close()
    
    user_states.pop(user_id, None)
    
    markup = types.InlineKeyboardMarkup()
    btn_share = types.InlineKeyboardButton("🚀 انشر البوست في قناتك الآن", switch_inline_query="my_attendance")
    markup.add(btn_share)
    
    bot.reply_to(message, "✅ **تم حفظ الإعدادات بنجاح!**\n\nاضغط على الزر أدناه لمشاركة بوست الحضور في قناتك:", reply_markup=markup)

# نظام المشاركة عبر الـ Inline (عشان ينشر البوست في القناة مع زر المشاركة)
@bot.inline_handler(func=lambda query: True)
def inline_query(query):
    user_id = query.from_user.id
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT title, custom_message FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    title = row[0] if row else "📋 سجل الحضور اليومي"
    
    # معرف فريد لهذا البوست
    poll_id = f"poll_{user_id}_{int(query.id[-5:])}"
    
    # حفظ البوست الجديد في قاعدة البيانات بصفر مسجلين
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO polls (poll_id, owner_id, count, title) VALUES (?, ?, ?, ?)",
                   (poll_id, user_id, 0, title))
    conn.commit()
    conn.close()
    
    # الزر الذي سيظهر في القناة
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"تسجيل الحضور [0]", callback_data=f"attend_{poll_id}"))
    
    articles = [
        types.InlineQueryResultArticle(
            id=poll_id,
            title="انشر بوست تسجيل الحضور",
            description=title,
            input_message_content=types.InputTextMessageContent(
                message_text=f"📌 **{title}**\n\nاضغط على الزر بالأسفل لتسجيل حضورك فوراً 👇"
            ),
            reply_markup=keyboard
        )
    ]
    bot.answer_inline_query(query.id, articles)

# عندما يضغط أي مستخدم على الزر في القناة
@bot.callback_query_handler(func=lambda call: call.data.startswith("attend_"))
def handle_channel_attendance(call):
    poll_id = call.data.replace("attend_", "")
    user = call.from_user
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # جلب معلومات البوست وصاحبه
    cursor.execute("SELECT owner_id, count, title FROM polls WHERE poll_id = ?", (poll_id,))
    poll = cursor.fetchone()
    
    if not poll:
        bot.answer_callback_query(call.id, "❌ انتهت صلاحية هذا البوست أو حدث خطأ.", show_alert=True)
        conn.close()
        return
        
    owner_id, count, title = poll
    
    # زيادة عداد الحضور بواحدة
    new_count = count + 1
    cursor.execute("UPDATE polls SET count = ? WHERE poll_id = ?", (new_count, poll_id))
    conn.commit()
    conn.close()
    
    # 1. إرسال تفاصيل العضو لصاحب الرابط (في الخاص)
    owner_notification = (
        f"📥 **تسجيل حضور جديد في بوستك!**\n\n"
        f"📌 **البوست:** {title}\n"
        f"👤 **المسجل:** {user.first_name}\n"
        f"🔗 **المعرف:** @{user.username if user.username else 'لا يوجد'}\n"
        f"🆔 **الـ ID:** `{user.id}`"
    )
    try:
        bot.send_message(owner_id, owner_notification, parse_mode="Markdown")
    except Exception:
        pass # لو صاحب البوست مش مفعل البوت في الخاص
        
    # 2. تحديث شكل الزر في القناة ليعرض العدد الجديد فوراً
    try:
        new_keyboard = types.InlineKeyboardMarkup()
        new_keyboard.add(types.InlineKeyboardButton(f"تسجيل الحضور [{new_count}]", callback_data=f"attend_{poll_id}"))
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=new_keyboard
        )
    except Exception:
        pass
        
    # 3. إعلام المستخدم الذي سجل حضوره بنجاح (تنبيه منبثق)
    bot.answer_callback_query(call.id, "✅ تم تسجيل حضورك وإرسال بياناتك بنجاح!", show_alert=True)

print("بوت الحضور الإحترافي للعامة يعمل الآن...")
bot.infinity_polling()
    # تحديد توقيت ليبيا (أو توقيت السيرفر)
    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M")
    
    # مفتاح فريد للتأكد إن العضو ما يسجلش مرتين في نفس الفترة اليوم
    record_key = f"{user_id}_{today}_{period}"
    
    if record_key in attendance_log:
        bot.answer_callback_query(call.id, "⚠️ لقد قمت بتسجيل حضورك مسبقاً لهذه الفترة!", show_alert=True)
        return
        
    # إضافة العضو لسجل الحضور
    attendance_log.add(record_key)
    
    # 1. إرسال إشعار للمدير (لك أنت في الخاص)
    admin_msg = (
        f"📌 **تسجيل حضور جديد:**\n\n"
        f"👤 **الاسم:** {user_name} {username}\n"
        f"🕒 **الفترة:** {period}\n"
        f"📅 **التاريخ:** {today}\n"
        f"⏱ **الوقت:** {current_time}"
    )
    try:
        bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except Exception as e:
        print("تأكد من إدخال الـ ID الخاص بك بشكل صحيح، وتأكد أنك قمت بمراسلة البوت بحسابك أولاً.")
        
    # 2. إرسال تأكيد للعضو نفسه
    bot.answer_callback_query(call.id, "✅ تم تسجيل حضورك بنجاح!")
    bot.send_message(call.message.chat.id, f"✅ **{user_name}**، تم إثبات حضورك اليوم للفترة {period}. بارك الله في جهودك!", parse_mode="Markdown")

print("بوت الحضور يعمل الآن...")
bot.infinity_polling()
