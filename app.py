import telebot
from telebot import types
import sqlite3
import os
from flask import Flask, request

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
WEBHOOK_URL = f"https://eeeeeee-production.up.railway.app/{TOKEN}"
ADMIN_ID = 1250493517  # أيدي حسابك الشخصي للإدارة

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# 🔧 تهيئة قاعدة البيانات الاحترافية
def init_db():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # إعدادات المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            title TEXT,
            custom_message TEXT
        )
    ''')
    # بوستات الحضور
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            owner_id INTEGER,
            count INTEGER,
            title TEXT
        )
    ''')
    # منع تكرار التصويت
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poll_votes (
            poll_id TEXT,
            user_id INTEGER,
            PRIMARY KEY (poll_id, user_id)
        )
    ''')
    # جدول النقاط والإحالات (لتتبع المتصدرين بالرابط)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            owner_id INTEGER PRIMARY KEY,
            visits_count INTEGER DEFAULT 0
        )
    ''')
    # جدول لتسجيل من زار رابط من لتجنب تكرار احتساب نفس الزائر لنفس الشخص
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_referral_logs (
            owner_id INTEGER,
            visitor_id INTEGER,
            PRIMARY KEY (owner_id, visitor_id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()
user_states = {}

# 🎨 لوحة التحكم المتطورة
def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("⚙️ إعدادات البوست"), types.KeyboardButton("🔗 مشاركة وتفعيل ⚡️"))
    markup.add(types.KeyboardButton("📊 إحصائيات الحضور 💎"), types.KeyboardButton("👑 قائمة المتصدرين"))
    markup.add(types.KeyboardButton("📞 الدعم والمساعدة"))
    
    # لو كان أنت المطور/الأدمن، نقدر نضيف لك زر لوحة تحكم خاصة
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("🛠 لوحة تحكم المشرف"))
        
    return markup

# 🚀 أمر البداية مع نظام تتبع الروابط والإحالات
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    # نظام تتبع الزائر عبر الرابط الخاص
    if len(args) > 1:
        try:
            owner_id = int(args[1])
            if owner_id != user_id:  # لا يحسب الشخص لنفسه
                conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
                cursor = conn.cursor()
                
                # التحقق هل الزائر زار هذا الرابط مسبقاً؟
                cursor.execute("SELECT * FROM user_referral_logs WHERE owner_id = ? AND visitor_id = ?", (owner_id, user_id))
                if not cursor.fetchone():
                    # تسجيل الزيارة
                    cursor.execute("INSERT INTO user_referral_logs (owner_id, visitor_id) VALUES (?, ?)", (owner_id, user_id))
                    cursor.execute("INSERT INTO referrals (owner_id, visits_count) VALUES (?, 1) ON CONFLICT(owner_id) DO UPDATE SET visits_count = visits_count + 1", (owner_id,))
                    conn.commit()
                conn.close()
        except ValueError:
            pass

    markup = get_main_keyboard(user_id)

    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT visits_count FROM referrals WHERE owner_id = ?", (user_id,))
    res = cursor.fetchone()
    total_visits = res[0] if res else 0
    conn.close()

    welcome_text = (
        f"<b>أهلاً بك - {message.from_user.first_name}.</b> 🤖\n\n"
        "<blockquote>هنا النظام الأقوى لإدارة بوستات الحضور، تجميع الزوار، ومتابعة المسابقات بكل احترافية وأمان..</blockquote>\n\n"
        "<b>🔗 رابط دعوتك الخاص للنشر (يكتسب نقاط كل ما دخل منه شخص):</b>\n"
        f"<code>https://t.me/{bot.get_me().username}?start={user_id}</code>\n\n"
        f"📊 <b>عدد زوار رابطك الشخصي:</b> {total_visits}\n\n"
        "<b>اختر ما تحتاجه من الأزرار بالأسفل 👇</b>"
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

# --- استجابة للأزرار السفلية المتطورة ---
@bot.message_handler(func=lambda message: message.text in ["⚙️ إعدادات البوست", "🔗 مشاركة وتفعيل ⚡️", "📊 إحصائيات الحضور 💎", "👑 قائمة المتصدرين", "📞 الدعم والمساعدة", "🛠 لوحة تحكم المشرف"])
def handle_menu_buttons(message):
    user_id = message.from_user.id
    
    if message.text == "⚙️ إعدادات البوست":
        user_states[user_id] = "waiting_title"
        bot.reply_to(message, "📝 **أرسل الآن عنوان أو كليشة البوست** التي ستظهر أعلى زر الحضور:", parse_mode="Markdown")
        
    elif message.text == "🔗 مشاركة وتفعيل ⚡️":
        inline_markup = types.InlineKeyboardMarkup()
        btn_share = types.InlineKeyboardButton("🚀 انشر البوست الآن", switch_inline_query="create")
        inline_markup.add(btn_share)
        bot.reply_to(message, "اضغط على الزر أدناه لاختيار القناة أو المجموعة التي تريد نشر بوست الحضور فيها:", reply_markup=inline_markup)
        
    elif message.text == "📊 إحصائيات الحضور 💎":
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(count) FROM polls WHERE owner_id = ?", (user_id,))
        polls_count, total_votes = cursor.fetchone()
        
        cursor.execute("SELECT visits_count FROM referrals WHERE owner_id = ?", (user_id,))
        ref_res = cursor.fetchone()
        total_visits = ref_res[0] if ref_res else 0
        conn.close()
        
        polls_count = polls_count if polls_count else 0
        total_votes = total_votes if total_votes else 0
        
        stats_text = (
            f"📊 **إحصائياتك الشاملة:**\n\n"
            f"📦 عدد البوستات التي أنشأتها: `{polls_count}`\n"
            f"👥 إجمالي الحضور المسجلين في بوستاتك: `{total_votes}`\n"
            f"🔗 عدد الزوار عبر رابطك الشخصي: `{total_visits}`"
        )
        bot.reply_to(message, stats_text, parse_mode="Markdown")
        
    elif message.text == "👑 قائمة المتصدرين":
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id, visits_count FROM referrals ORDER BY visits_count DESC LIMIT 5")
        top_users = cursor.fetchall()
        conn.close()
        
        leaderboard_text = "👑 **قائمة أكثر المستخدمين دخولاً وتفاعلاً عبر روابطهم:**\n\n"
        if not top_users:
            leaderboard_text += "<i>لا توجد بيانات متصدرين حتى الآن.. كن أول المنضمين!</i>"
        else:
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, (uid, count) in enumerate(top_users):
                medal = medals[i] if i < len(medals) else "🔹"
                leaderboard_text += f"{medal} المعرف (ID: <code>{uid}</code>) — <b>{count}</b> زائر\n"
                
        bot.reply_to(message, leaderboard_text, parse_mode="HTML")
        
    elif message.text == "📞 الدعم والمساعدة":
        user_states[user_id] = "waiting_support_msg"
        bot.reply_to(message, "💬 **أرسل رسالتك أو استفسارك الآن وسيتم تحويله مباشرة إلى فريق الإدارة والدعم الفني:**", parse_mode="Markdown")
        
    elif message.text == "🛠 لوحة تحكم المشرف" and user_id == ADMIN_ID:
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_settings")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM polls")
        total_polls = cursor.fetchone()[0]
        conn.close()
        
        admin_panel = (
            f"🛠 **لوحة تحكم المشرف الخاص بك:**\n\n"
            f"👥 إجمالي المستخدمين المسجلين: `{total_users}`\n"
            f"📦 إجمالي البوستات في النظام: `{total_polls}`\n"
            "Status: Server is running & Webhook is active ✅"
        )
        bot.reply_to(message, admin_panel, parse_mode="Markdown")

# نظام استقبال وتوجيه رسائل الدعم الفني للأدمن
@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_support_msg")
def forward_support_message(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    
    # إرسال الرسالة لك كأدمن مع معلومات المستخدم
    support_forward = (
        f"📩 **رسالة دعم جديدة من مستخدم:**\n\n"
        f"👤 الاسم: {message.from_user.first_name}\n"
        f"🆔 الأيدي: `{user_id}`\n"
        f"🔗 المعرف: @{message.from_user.username if message.from_user.username else 'لا يوجد'}\n\n"
        f"💬 **النص:**\n{message.text}"
    )
    try:
        bot.send_message(ADMIN_ID, support_forward, parse_mode="Markdown")
        bot.reply_to(message, "✅ **تم إرسال رسالتك بنجاح إلى الإدارة!** سيتم الرد عليك قريباً.")
    except Exception:
        bot.reply_to(message, "❌ حدث خطأ أثناء إرسال الرسالة، حاول مرة أخرى لاحقاً.")

# حفظ الكليشة
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
    
    cursor.execute("UPDATE polls SET count = ? WHERE poll_id = ?", (new_count, poll_id))
    cursor.execute("INSERT INTO poll_votes (poll_id, user_id) VALUES (?, ?)", (poll_id, user.id))
    conn.commit()
    conn.close()
    
    username_text = f"@{user.username}" if user.username else "لا يوجد معرف"
    owner_notification = (
        f"📥 **تسجيل حضور جديد في بوستك!**\n\n"
        f"📌 **البوست:** {title}\n"
        f"👤 **المسجل:** {user.first_name}\n"
        f"🔗 **المعرف:** {username_text}"
    )
    try:
        bot.send_message(owner_id, owner_notification)
    except Exception:
        pass 
        
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

# 🖥️ مسارات Flask
@app.route('/' + TOKEN, methods=['POST'])
def webhook_listener():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Forbidden", 403

@app.route("/")
def index():
    return "Bot is running smoothly with advanced features!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
        )
    ''')
    conn.commit()
    conn.close()

init_db()
user_states = {}

# 🎨 لوحة التحكم
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("⚙️ إعدادات البوست"), types.KeyboardButton("🔗 مشاركة وتفعيل ⚡️"))
    markup.add(types.KeyboardButton("📊 إحصائيات الحضور 💎"))
    markup.add(types.KeyboardButton("👑 قائمة المتصدرين"), types.KeyboardButton("📞 الدعم والمساعدة"))
    return markup

# 🚀 أمر البداية
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    markup = get_main_keyboard()

    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(count) FROM polls WHERE owner_id = ?", (user_id,))
    res = cursor.fetchone()
    total_visits = res[0] if res and res[0] else 0
    conn.close()

    welcome_text = (
        f"<b>أهلاً بك - {message.from_user.first_name}.</b> 🤖\n\n"
        "<blockquote>هنا تقدر تصنع بوستات حضور، تدير مسابقاتك، وتستقبل التفاعلات بكل احترافية وأمان..</blockquote>\n\n"
        "<b>رابطك الخاص للنشر:</b>\n"
        f"<code>https://t.me/{bot.get_me().username}?start={user_id}</code>\n\n"
        f"📊 <b>عدد زوار بوستاتك:</b> {total_visits}\n\n"
        "<b>شرح استخدام البوت &lt;&gt; صنع بوست | متابعة</b>\n"
        "<blockquote>✨ نتمنى لك تجربة ممتعة وقوية داخل النظام</blockquote>"
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

# --- استجابة للأزرار السفلية ---
@bot.message_handler(func=lambda message: message.text in ["⚙️ إعدادات البوست", "🔗 مشاركة وتفعيل ⚡️", "📊 إحصائيات الحضور 💎", "👑 قائمة المتصدرين", "📞 الدعم والمساعدة"])
def handle_menu_buttons(message):
    user_id = message.from_user.id
    
    if message.text == "⚙️ إعدادات البوست":
        user_states[user_id] = "waiting_title"
        bot.reply_to(message, "📝 **أرسل الآن عنوان أو كليشة البوست** التي ستظهر أعلى زر الحضور:", parse_mode="Markdown")
        
    elif message.text == "🔗 مشاركة وتفعيل ⚡️":
        inline_markup = types.InlineKeyboardMarkup()
        btn_share = types.InlineKeyboardButton("🚀 انشر البوست الآن", switch_inline_query="create")
        inline_markup.add(btn_share)
        bot.reply_to(message, "اضغط على الزر أدناه لاختيار القناة أو المجموعة التي تريد نشر بوست الحضور فيها:", reply_markup=inline_markup)
        
    elif message.text == "📊 إحصائيات الحضور 💎":
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(count) FROM polls WHERE owner_id = ?", (user_id,))
        polls_count, total_votes = cursor.fetchone()
        conn.close()
        
        polls_count = polls_count if polls_count else 0
        total_votes = total_votes if total_votes else 0
        
        stats_text = (
            f"📊 **إحصائيات بوستاتك الحالية:**\n\n"
            f"📦 عدد البوستات التي أنشأتها: `{polls_count}`\n"
            f"👥 إجمالي الحضور المسجلين: `{total_votes}`"
        )
        bot.reply_to(message, stats_text, parse_mode="Markdown")
        
    else:
        bot.reply_to(message, "🛠 **هذه الميزة قيد التطوير وسيتم إضافتها في التحديث القادم!**", parse_mode="Markdown")

# حفظ الكليشة
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
    
    cursor.execute("UPDATE polls SET count = ? WHERE poll_id = ?", (new_count, poll_id))
    cursor.execute("INSERT INTO poll_votes (poll_id, user_id) VALUES (?, ?)", (poll_id, user.id))
    conn.commit()
    conn.close()
    
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

# 🖥️ مسارات Flask لاستقبال رسائل تليجرام
@app.route('/' + TOKEN, methods=['POST'])
def webhook_listener():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Forbidden", 403

@app.route("/")
def index():
    return "Bot is running smoothly!", 200

# تشغيل السيرفر وربط الويب هوك تلقائياً
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
