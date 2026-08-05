import telebot
from telebot import types
import sqlite3

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    # جدول إعدادات كل مستخدم (صاحب قناة)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            title TEXT,
            custom_message TEXT
        )
    ''')
    # جدول البوستات (الروليت)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            owner_id INTEGER,
            count INTEGER,
            title TEXT
        )
    ''')
    # جدول لتسجيل من ضغط عشان العضو ما يضغطش مرتين في نفس البوست
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poll_votes (
            poll_id TEXT,
            user_id INTEGER,
            PRIMARY KEY (poll_id, user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()
user_states = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_create = types.InlineKeyboardButton("⚙️ إعداد كليشة الحضور", callback_data="config_menu")
    btn_share = types.InlineKeyboardButton("🔗 انشر البوست في قناتك", switch_inline_query="create")
    markup.add(btn_create, btn_share)
    
    welcome_text = (
        f"أهلاً بك يا {message.from_user.first_name} في بوت الحضور الاحترافي.\n\n"
        "• قم بإعداد رسالتك.\n"
        "• انشرها في قناتك أو مجموعتك.\n"
        "• أي شخص يضغط تسجيل، بيوصلك إشعار خاص باسمه ومعرفه!\n"
        "• يتحدث عداد الحضور تلقائياً أمام الجميع."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "config_menu")
def config_menu(call):
    user_id = call.from_user.id
    user_states[user_id] = "waiting_title"
    bot.send_message(call.message.chat.id, "📝 **أرسل الآن عنوان أو كليشة البوست** التي ستظهر أعلى زر الحضور:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_title")
def save_title(message):
    user_id = message.from_user.id
    title = message.text
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, title, custom_message) VALUES (?, ?, ?)",
                   (user_id, title, "تم تسجيل حضورك بنجاح ✅"))
    conn.commit()
    conn.close()
    
    user_states.pop(user_id, None)
    
    markup = types.InlineKeyboardMarkup()
    btn_share = types.InlineKeyboardButton("🚀 انشر البوست الآن", switch_inline_query="create")
    markup.add(btn_share)
    
    bot.reply_to(message, "✅ **تم حفظ الكليشة بنجاح!**\n\nاضغط على الزر أدناه لنشرها في أي مكان:", reply_markup=markup)

@bot.inline_handler(func=lambda query: True)
def inline_query(query):
    user_id = query.from_user.id
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    title = row[0] if row else "📋 سجل الحضور اليومي"
    poll_id = f"poll_{user_id}_{query.id}"
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO polls (poll_id, owner_id, count, title) VALUES (?, ?, ?, ?)",
                   (poll_id, user_id, 0, title))
    conn.commit()
    conn.close()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("تسجيل الحضور [0]", callback_data=f"attend_{poll_id}"))
    
    articles = [
        types.InlineQueryResultArticle(
            id=poll_id,
            title="انشر بوست تسجيل الحضور",
            description=title,
            input_message_content=types.InputTextMessageContent(
                message_text=f"📌 **{title}**\n\nاضغط على الزر بالأسفل لتسجيل حضورك 👇"
            ),
            reply_markup=keyboard
        )
    ]
    bot.answer_inline_query(query.id, articles, cache_time=1)

@bot.callback_query_handler(func=lambda call: call.data.startswith("attend_"))
def handle_channel_attendance(call):
    poll_id = call.data.replace("attend_", "")
    user = call.from_user
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # منع العضو من الضغط مرتين والتلاعب بالعداد
    cursor.execute("SELECT * FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user.id))
    if cursor.fetchone():
        bot.answer_callback_query(call.id, "⚠️ لقد قمت بتسجيل حضورك مسبقاً!", show_alert=True)
        conn.close()
        return
        
    cursor.execute("SELECT owner_id, count, title FROM polls WHERE poll_id = ?", (poll_id,))
    poll = cursor.fetchone()
    
    if not poll:
        bot.answer_callback_query(call.id, "❌ انتهت صلاحية هذا البوست.", show_alert=True)
        conn.close()
        return
        
    owner_id, count, title = poll
    new_count = count + 1
    
    # تحديث العداد وتسجيل هوية المصوت
    cursor.execute("UPDATE polls SET count = ? WHERE poll_id = ?", (new_count, poll_id))
    cursor.execute("INSERT INTO poll_votes (poll_id, user_id) VALUES (?, ?)", (poll_id, user.id))
    conn.commit()
    conn.close()
    
    # إرسال التفاصيل لصاحب الرابط
    username_text = f"@{user.username}" if user.username else "لا يوجد معرف"
    owner_notification = (
        f"📥 **تسجيل حضور جديد!**\n\n"
        f"📌 **البوست:** {title}\n"
        f"👤 **المسجل:** {user.first_name}\n"
        f"🔗 **المعرف:** {username_text}"
    )
    try:
        bot.send_message(owner_id, owner_notification)
    except Exception:
        pass 
        
    # تحديث العداد في القناة أمام الجميع
    try:
        new_keyboard = types.InlineKeyboardMarkup()
        new_keyboard.add(types.InlineKeyboardButton(f"تسجيل الحضور [{new_count}]", callback_data=f"attend_{poll_id}"))
        bot.edit_message_reply_markup(
            inline_message_id=call.inline_message_id,
            reply_markup=new_keyboard
        )
    except Exception:
        pass
        
    bot.answer_callback_query(call.id, "✅ تم تسجيل حضورك وإرسال بياناتك بنجاح!", show_alert=True)

print("البوت يعمل الآن بصيغة الـ Inline...")
bot.infinity_polling()
