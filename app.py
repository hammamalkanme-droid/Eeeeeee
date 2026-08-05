# -*- coding: utf-8 -*-
import telebot
from telebot import types
import sqlite3
import os
from flask import Flask, request

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
WEBHOOK_URL = f"https://eeeeeee-production.up.railway.app/{TOKEN}"
ADMIN_ID = 1250493517

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS user_settings (user_id INTEGER PRIMARY KEY, title TEXT, custom_message TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS polls (poll_id TEXT PRIMARY KEY, owner_id INTEGER, count INTEGER, title TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS poll_votes (poll_id TEXT, user_id INTEGER, PRIMARY KEY (poll_id, user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS referrals (owner_id INTEGER PRIMARY KEY, visits_count INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_referral_logs (owner_id INTEGER, visitor_id INTEGER, PRIMARY KEY (owner_id, visitor_id))')
    conn.commit()
    conn.close()

init_db()
user_states = {}

# دالة مساعدة لإنشاء أزرار ملونة احترافية تحت الرسائل
def create_colored_btn(text, callback_data=None, switch_query=None, style="primary"):
    if switch_query:
        btn = types.InlineKeyboardButton(text=text, switch_inline_query=switch_query)
    else:
        btn = types.InlineKeyboardButton(text=text, callback_data=callback_data)
    btn.style = style  # الألوان المتاحة: primary (بنفسجي), success (أخضر), danger (أحمر)
    return btn

# لوحة القائمة الرئيسية الملونة (Inline Keyboard)
def get_main_inline_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # صف الأزرار الأول (بنفسجي)
    btn_settings = create_colored_btn("⚙️ إعدادات البوست", callback_data="menu_settings", style="primary")
    btn_share = create_colored_btn("🔗 مشاركة وتفعيل", callback_data="menu_share", style="primary")
    markup.add(btn_settings, btn_share)
    
    # صف الأزرار الثاني (أخضر)
    btn_stats = create_colored_btn("📊 إحصائيات الحضور", callback_data="menu_stats", style="success")
    btn_top = create_colored_btn("🏆 قائمة المتصدرين", callback_data="menu_leaderboard", style="success")
    markup.add(btn_stats, btn_top)
    
    # صف الأزرار الثالث (أخضر أو بنفسجي)
    btn_support = create_colored_btn("🛠️ الدعم والمساعدة", callback_data="menu_support", style="success")
    markup.add(btn_support)
    
    # لوحة تحكم المشرف تظهر للمشرف فقط باللون الأحمر (danger)
    if user_id == ADMIN_ID:
        btn_admin = create_colored_btn("👑 لوحة تحكم المشرف", callback_data="menu_admin", style="danger")
        markup.add(btn_admin)
        
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1:
        try:
            owner_id = int(args[1])
            if owner_id != user_id:
                conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_referral_logs WHERE owner_id = ? AND visitor_id = ?", (owner_id, user_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO user_referral_logs (owner_id, visitor_id) VALUES (?, ?)", (owner_id, user_id))
                    cursor.execute("INSERT INTO referrals (owner_id, visits_count) VALUES (?, 1) ON CONFLICT(owner_id) DO UPDATE SET visits_count = visits_count + 1", (owner_id,))
                    conn.commit()
                conn.close()
        except ValueError:
            pass

    markup = get_main_inline_keyboard(user_id)
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT visits_count FROM referrals WHERE owner_id = ?", (user_id,))
    res = cursor.fetchone()
    total_visits = res[0] if res else 0
    conn.close()

    welcome_text = (
        f"✨ **مرحباً بك عزيزي {message.from_user.first_name}**\n\n"
        f"> 📌 *هنا يمكنك إنشاء بوستات الحضور بكل احترافية، متابعة التفاعلات، وجلب الزوار عبر رابطك الخاص.*\n\n"
        f"🔗 **رابط دعوتك الشخصي:**\n`https://t.me/{bot.get_me().username}?start={user_id}`\n\n"
        f"📊 **إجمالي زوار رابطك:** `{total_visits}` شخص\n\n"
        f"👇 **اختر ما تحتاجه من الأزرار الملونة أدناه:**"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# معالجة ضغط أزرار القائمة الرئيسية الملونة
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu_callbacks(call):
    user_id = call.from_user.id
    action = call.data.replace("menu_", "")
    
    if action == "settings":
        user_states[user_id] = "waiting_title"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📝 *أرسل الآن عنوان أو كليشة البوست التي ستظهر للمستخدمين عند تسجيل الحضور:*", parse_mode="Markdown")
    
    elif action == "share":
        bot.answer_callback_query(call.id)
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(create_colored_btn("🚀 انشر البوست الآن في قناة/مجموعة", switch_query="create", style="success"))
        bot.send_message(call.message.chat.id, "📌 *اضغط على الزر الملون أدناه لاختيار المكان الذي تريد نشر بوست الحضور فيه:*", parse_mode="Markdown", reply_markup=inline_markup)
    
    elif action == "stats":
        bot.answer_callback_query(call.id)
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
            f"📊 **إحصائيات حسابك الشاملة:**\n\n"
            f"> • **عدد البوستات المنشأة:** `{polls_count}`\n"
            f"> • **إجمالي الحضور المسجلين:** `{total_votes}`\n"
            f"> • **زوار رابط الدعوة الخاص بك:** `{total_visits}`"
        )
        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown")
    
    elif action == "leaderboard":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id, visits_count FROM referrals ORDER BY visits_count DESC LIMIT 5")
        top_users = cursor.fetchall()
        conn.close()
        leaderboard_text = "🏆 **قائمة أكثر المستخدمين جلباً للزوار:**\n\n"
        if not top_users:
            leaderboard_text += "> *لا توجد بيانات متصدرين حتى الآن.. كن الأول!*"
        else:
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, (uid, count) in enumerate(top_users):
                medal = medals[i] if i < len(medals) else "🔹"
                leaderboard_text += f"> {medal} أيدي: `{uid}` — **{count}** زائر\n"
        bot.send_message(call.message.chat.id, leaderboard_text, parse_mode="Markdown")
    
    elif action == "support":
        bot.answer_callback_query(call.id)
        user_states[user_id] = "waiting_support_msg"
        bot.send_message(call.message.chat.id, "💬 *أرسل رسالتك أو استفسارك الآن، وسيتم تحويله مباشرة إلى الإدارة للرد عليك:*", parse_mode="Markdown")
    
    elif action == "admin":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "هذا الزر للمشرف فقط ⛔", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_settings")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM polls")
        total_polls = cursor.fetchone()[0]
        conn.close()
        admin_panel = (
            f"👑 **لوحة تحكم المشرف العامة:**\n\n"
            f"> • **إجمالي المستخدمين المسجلين:** `{total_users}`\n"
            f"> • **إجمالي بوستات الحضور:** `{total_polls}`\n"
            f"> • **حالة السيرفر:** `يعمل بكفاءة عالية 🟢`"
        )
        bot.send_message(call.message.chat.id, admin_panel, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_support_msg")
def forward_support_message(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    support_forward = (
        f"📩 **رسالة دعم فني جديدة:**\n\n"
        f"> • **الاسم:** {message.from_user.first_name}\n"
        f"> • **الأيدي:** `{user_id}`\n"
        f"> • **المعرف:** @{message.from_user.username if message.from_user.username else 'لا يوجد'}\n\n"
        f"💬 **النص:**\n> {message.text}"
    )
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(create_colored_btn("💬 الرد على المستخدم", callback_data=f"reply_{user_id}", style="primary"))
    try:
        bot.send_message(ADMIN_ID, support_forward, parse_mode="Markdown", reply_markup=admin_markup)
        bot.reply_to(message, "✅ *تم إرسال رسالتك بنجاح إلى الإدارة! سيتم الرد عليك قريباً.*", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "❌ حدث خطأ أثناء إرسال الرسالة، حاول مرة أخرى.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def admin_start_reply(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "هذا الزر مخصص للمشرف فقط ⛔", show_alert=True)
        return
    target_user_id = call.data.replace("reply_", "")
    user_states[ADMIN_ID] = f"admin_reply_to_{target_user_id}"
    bot.answer_callback_query(call.id, "اكتب الرد الآن.")
    bot.send_message(ADMIN_ID, f"✍️ *اكتب الرد الذي تريد إرساله للمستخدم (ID: `{target_user_id}`):*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.from_user.id in user_states and user_states[message.from_user.id].startswith("admin_reply_to_"))
def send_admin_reply_to_user(message):
    target_user_id = int(user_states[ADMIN_ID].replace("admin_reply_to_", ""))
    user_states.pop(ADMIN_ID, None)
    try:
        bot.send_message(target_user_id, f"📥 **رد جديد من إدارة الدعم الفني:**\n\n> {message.text}", parse_mode="Markdown")
        bot.reply_to(message, "✅ تم إرسال الرد للمستخدم بنجاح!")
    except Exception:
        bot.reply_to(message, "❌ فشل إرسال الرد، ربما قام المستخدم بحظر البوت.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_title")
def save_title(message):
    user_id = message.from_user.id
    title = message.text
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, title, custom_message) VALUES (?, ?, ?)", (user_id, title, "تم تسجيل حضورك بنجاح"))
    conn.commit()
    conn.close()
    user_states.pop(user_id, None)
    markup = types.InlineKeyboardMarkup()
    markup.add(create_colored_btn("🚀 انشر البوست الآن", switch_query="create", style="success"))
    bot.reply_to(message, "✅ *تم حفظ الكليشة بنجاح! يمكنك النشر الآن عبر الزر الملون أدناه:*", parse_mode="Markdown", reply_markup=markup)

@bot.inline_handler(func=lambda query: True)
def inline_query(query):
    user_id = query.from_user.id
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    title = row[0] if row else "📌 سجل الحضور اليومي"
    poll_id = f"poll_{user_id}_{query.id}"
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO polls (poll_id, owner_id, count, title) VALUES (?, ?, ?, ?)", (poll_id, user_id, 0, title))
    conn.commit()
    conn.close()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(create_colored_btn("✅ تسجيل الحضور [0]", callback_data=f"attend_{poll_id}", style="success"))
    
    articles = [
        types.InlineQueryResultArticle(
            id=poll_id,
            title="إنشاء بوست تسجيل الحضور",
            description=title,
            input_message_content=types.InputTextMessageContent(
                message_text=f"📢 **{title}**\n\n> *اضغط على الزر الملون أدناه لتسجيل حضورك الرسمي فوراً:*",
                parse_mode="Markdown"
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
        f"🔔 **تسجيل حضور جديد في بوستك!**\n\n"
        f"> • **البوست:** {title}\n"
        f"> • **المسجل:** {user.first_name}\n"
        f"> • **المعرف:** `{username_text}`"
    )
    try:
        bot.send_message(owner_id, owner_notification, parse_mode="Markdown")
    except Exception:
        pass 
    try:
        new_keyboard = types.InlineKeyboardMarkup()
        new_keyboard.add(create_colored_btn(f"✅ تسجيل الحضور [{new_count}]", callback_data=f"attend_{poll_id}", style="success"))
        bot.edit_message_reply_markup(inline_message_id=call.inline_message_id, reply_markup=new_keyboard)
    except Exception:
        pass
    bot.answer_callback_query(call.id, "✨ تم تسجيل حضورك بنجاح!", show_alert=True)

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
    return "Bot is running perfectly!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
