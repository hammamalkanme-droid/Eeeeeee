# -*- coding: utf-8 -*-
import telebot
from telebot import types
import sqlite3
import os
import time
import io
import csv
from datetime import datetime
from flask import Flask, request, send_file

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
WEBHOOK_URL = f"https://eeeeeee-production.up.railway.app/{TOKEN}"
ADMIN_ID = 1250493517

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    # جدول إعدادات المستخدم مع خيار عرض القناة (show_in_channel: 1 لعرضها، 0 للخاص فقط)
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                        user_id INTEGER PRIMARY KEY, 
                        title TEXT, 
                        custom_message TEXT, 
                        duration INTEGER DEFAULT 0,
                        show_in_channel INTEGER DEFAULT 1
                    )''')
    
    # جدول البوستات النشطة مع إضافة حقول لتخزين تفاصيل الإعداد والتحديث المباشر
    cursor.execute('''CREATE TABLE IF NOT EXISTS polls (
                        poll_id TEXT PRIMARY KEY, 
                        owner_id INTEGER, 
                        count INTEGER, 
                        title TEXT, 
                        end_time REAL DEFAULT 0, 
                        is_closed INTEGER DEFAULT 0,
                        show_in_channel INTEGER DEFAULT 1,
                        inline_message_id TEXT
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS poll_votes (
                        poll_id TEXT, 
                        user_id INTEGER, 
                        user_name TEXT, 
                        username TEXT, 
                        PRIMARY KEY (poll_id, user_id)
                    )''')
    
    # جدول أسماء المستخدمين المرتبطة بالـ ID لضمان ثبات اسم العضو حتى لو غيره
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id INTEGER PRIMARY KEY,
                        full_name TEXT,
                        username TEXT
                    )''')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS referrals (owner_id INTEGER PRIMARY KEY, visits_count INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_referral_logs (owner_id INTEGER, visitor_id INTEGER, PRIMARY KEY (owner_id, visitor_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_points (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

init_db()
user_states = {}

def get_arabic_date_string():
    days = {
        'Saturday': 'السبت', 'Sunday': 'الأحد', 'Monday': 'الإثنين',
        'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة'
    }
    months = {
        '1': 'يناير', '2': 'فبراير', '3': 'مارس', '4': 'أبريل',
        '5': 'مايو', '6': 'يونيو', '7': 'يوليو', '8': 'أغسطس',
        '9': 'سبتمبر', '10': 'كتوبر', '11': 'نوفمبر', '12': 'ديسمبر'
    }
    now = datetime.now()
    d_name = days.get(now.strftime('%A'), '')
    m_name = months.get(str(now.month), '')
    return f"{d_name} {now.day} {m_name} {now.year}"

# دالة مساعدة لإنشاء أزرار ملونة احترافية
def create_colored_btn(text, callback_data=None, switch_query=None, style="primary"):
    if switch_query:
        btn = types.InlineKeyboardButton(text=text, switch_inline_query=switch_query)
    else:
        btn = types.InlineKeyboardButton(text=text, callback_data=callback_data)
    btn.style = style 
    return btn

def get_main_inline_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_settings = create_colored_btn("⚙️ إعدادات البوست", callback_data="menu_settings", style="primary")
    btn_share = create_colored_btn("🔗 مشاركة وتفعيل", callback_data="menu_share", style="primary")
    markup.add(btn_settings, btn_share)
    
    btn_stats = create_colored_btn("📊 إحصائيات الحضور", callback_data="menu_stats", style="success")
    btn_top = create_colored_btn("🏆 قائمة المتصدرين", callback_data="menu_leaderboard", style="success")
    markup.add(btn_stats, btn_top)
    
    btn_points = create_colored_btn("🌟 لوحة النقاط", callback_data="menu_points", style="success")
    btn_support = create_colored_btn("🛠️ الدعم والمساعدة", callback_data="menu_support", style="success")
    markup.add(btn_points, btn_support)
    
    if user_id == ADMIN_ID:
        btn_admin = create_colored_btn("👑 لوحة تحكم المشرف", callback_data="menu_admin", style="danger")
        markup.add(btn_admin)
        
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # تحديث وتخزين البروفایل الثابت للمستخدم برابط الـ ID
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    uname_str = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
    cursor.execute("INSERT INTO user_profiles (user_id, full_name, username) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET full_name = ?, username = ?", 
                   (user_id, message.from_user.first_name, uname_str, message.from_user.first_name, uname_str))
    conn.commit()

    args = message.text.split()
    if len(args) > 1:
        try:
            owner_id = int(args[1])
            if owner_id != user_id:
                cursor.execute("SELECT * FROM user_referral_logs WHERE owner_id = ? AND visitor_id = ?", (owner_id, user_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO user_referral_logs (owner_id, visitor_id) VALUES (?, ?)", (owner_id, user_id))
                    cursor.execute("INSERT INTO referrals (owner_id, visits_count) VALUES (?, 1) ON CONFLICT(owner_id) DO UPDATE SET visits_count = visits_count + 1", (owner_id,))
                    conn.commit()
        except ValueError:
            pass

    cursor.execute("SELECT visits_count FROM referrals WHERE owner_id = ?", (user_id,))
    res = cursor.fetchone()
    total_visits = res[0] if res else 0
    cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
    p_res = cursor.fetchone()
    user_points = p_res[0] if p_res else 0
    conn.close()

    markup = get_main_inline_keyboard(user_id)
    welcome_text = (
        f"✨ **مرحباً بك عزيزي {message.from_user.first_name}**\n\n"
        f"> 📌 *أنشئ بوستات الحضور بكل احترافية، تحكم بوقت الإغلاق، وتتبع تفاعلات ونشاط أعضائك.*\n\n"
        f"🔗 **رابط دعوتك الشخصي:**\n`https://t.me/{bot.get_me().username}?start={user_id}`\n\n"
        f"📊 **إجمالي زوار رابطك:** `{total_visits}` شخص\n"
        f"🌟 **رصيدك من النقاط:** `{user_points}` نقطة\n\n"
        f"👇 **اختر ما تحتاجه من الأزرار الملونة أدناه:**"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu_callbacks(call):
    user_id = call.from_user.id
    action = call.data.replace("menu_", "")
    
    if action == "settings":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(create_colored_btn("📝 اختيار عنوان / كليشة البوست", callback_data="wizard_title_type", style="primary"))
        markup.add(create_colored_btn("⏱️ ضبط مدة البوست الافتراضية", callback_data="set_duration", style="primary"))
        markup.add(create_colored_btn("👁️ ضبط خيار عرض القائمة (بالقناة / خاص)", callback_data="set_display_mode", style="primary"))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ **إعدادات بوستات الحضور:**\n\n> *اختر الخيار الذي تريد ضبطه بدقة:*", parse_mode="Markdown", reply_markup=markup)
    
    elif action == "share":
        bot.answer_callback_query(call.id)
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(create_colored_btn("🚀 انشر البوست الآن في قناة/مجموعة", switch_query="create", style="success"))
        bot.send_message(call.message.chat.id, "📌 *اضغط على الزر أدناه لبدء نشر بوست الحضور الجديد وفق خياراتك الإعدادية:*", parse_mode="Markdown", reply_markup=inline_markup)
    
    elif action == "stats":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT poll_id, title, count FROM polls WHERE owner_id = ?", (user_id,))
        user_polls = cursor.fetchall()
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
            f"> • **زوار رابط الدعوة الخاص بك:** `{total_visits}`\n\n"
            f"📥 **تحميل كشوفات الحضور (Excel / CSV):**"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        if user_polls:
            for pid, title, cnt in user_polls:
                short_title = title[:20] + "..." if len(title) > 20 else title
                markup.add(create_colored_btn(f"📄 تحميل كشف: {short_title} ({cnt})", callback_data=f"export_{pid}", style="success"))
        else:
            markup.add(create_colored_btn("⚠️ لا توجد بوستات نشطة حالياً", callback_data="none", style="danger"))
            
        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown", reply_markup=markup)
    
    elif action == "leaderboard":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id, visits_count FROM referrals ORDER BY visits_count DESC LIMIT 5")
        top_users = cursor.fetchall()
        cursor.execute("SELECT user_id, points FROM user_points ORDER BY points DESC LIMIT 5")
        top_points = cursor.fetchall()
        conn.close()
        
        leaderboard_text = "🏆 **قوائم المتصدرين في البوت:**\n\n"
        leaderboard_text += "🔗 **أكثر المستخدمين جلباً للزوار:**\n"
        if not top_users:
            leaderboard_text += "> *لا توجد بيانات حتى الآن..*\n\n"
        else:
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, (uid, count) in enumerate(top_users):
                medal = medals[i] if i < len(medals) else "🔹"
                leaderboard_text += f"> {medal} أيدي: `{uid}` — **{count}** زائر\n"
            leaderboard_text += "\n"
            
        leaderboard_text += "🌟 **أكثر الأعضاء تفاعلاً ونقاطاً:**\n"
        if not top_points:
            leaderboard_text += "> *لا توجد نقاط مسجلة حتى الآن..*"
        else:
            for i, (uid, pts) in enumerate(top_points):
                medal = medals[i] if i < len(medals) else "🔹"
                leaderboard_text += f"> {medal} أيدي: `{uid}` — **{pts}** نقطة\n"
                
        bot.send_message(call.message.chat.id, leaderboard_text, parse_mode="Markdown")
        
    elif action == "points":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        pts = res[0] if res else 0
        conn.close()
        points_msg = (
            f"🌟 **نظام النقاط والمكافآت:**\n\n"
            f"> • رصيدك الحالي هو: **{pts} نقطة**\n"
            f"> • تحصل على النقاط تلقائياً كلما قمت بتسجيل حضورك في بوستات الحضور داخل القنوات والمجموعات!\n"
        )
        bot.send_message(call.message.chat.id, points_msg, parse_mode="Markdown")
    
    elif action == "support":
        bot.answer_callback_query(call.id)
        user_states[user_id] = "waiting_support_msg"
        bot.send_message(call.message.chat.id, "💬 *أرسل رسالتك أو استفسارك الآن، وسيتم تحويله مباشرة إلى الإدارة:*", parse_mode="Markdown")
    
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
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(create_colored_btn("📢 إرسال رسالة جماعية (Broadcast)", callback_data="admin_broadcast", style="danger"))
        
        admin_panel = (
            f"👑 **لوحة تحكم المشرف العامة:**\n\n"
            f"> • **إجمالي المستخدمين المسجلين:** `{total_users}`\n"
            f"> • **إجمالي بوستات الحضور:** `{total_polls}`\n"
            f"> • **حالة السيرفر:** `يعمل بكفاءة عالية 🟢`"
        )
        bot.send_message(call.message.chat.id, admin_panel, parse_mode="Markdown", reply_markup=markup)

# خطوات إنشاء البوست وتسميته (يدوي أو باليوم والتاريخ)
@bot.callback_query_handler(func=lambda call: call.data == "wizard_title_type")
def wizard_title_type(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        create_colored_btn("✏️ اسم يدوي (اكتبه بنفسك)", callback_data="w_title_manual", style="primary"),
        create_colored_btn(f"📅 اسم تلقائي باليوم والتاريخ ({get_arabic_date_string()})", callback_data="w_title_auto", style="success")
    )
    bot.send_message(call.message.chat.id, "📌 *اختر كيف تريد تسمية بوست الحضور الجديد:*", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "w_title_manual")
def wizard_title_manual(call):
    user_states[call.from_user.id] = "waiting_manual_title"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📝 *أرسل الآن العنوان أو الكليشة اليدوية التي تريدها للبوست:*", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "w_title_auto")
def wizard_title_auto(call):
    user_id = call.from_user.id
    auto_title = f"سجل الحضور — {get_arabic_date_string()}"
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, title, duration, show_in_channel) VALUES (?, ?, 0, 1)", (user_id, auto_title))
    cursor.execute("UPDATE user_settings SET title = ? WHERE user_id = ?", (auto_title, user_id))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, "✅ تم اعتماد اسم التاريخ تلقائياً!")
    # الانتقال لخطوة اختيار الوقت
    ask_duration_wizard(call.message)

def ask_duration_wizard(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        create_colored_btn("5 دقائق", callback_data="w_dur_5", style="primary"),
        create_colored_btn("10 دقائق", callback_data="w_dur_10", style="primary"),
        create_colored_btn("30 دقيقة", callback_data="w_dur_30", style="primary")
    )
    markup.add(
        create_colored_btn("ساعة واحدة", callback_data="w_dur_60", style="primary"),
        create_colored_btn("ساعتين", callback_data="w_dur_120", style="primary"),
        create_colored_btn("بدون وقت إغلاق (مفتوح)", callback_data="w_dur_0", style="success")
    )
    bot.send_message(message.chat.id, "⏱️ *اختر المدة الزمنية لصلاحية البوست بعد نشره:*", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_duration")
def callback_set_duration(call):
    bot.answer_callback_query(call.id)
    ask_duration_wizard(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("w_dur_"))
def handle_wizard_duration(call):
    user_id = call.from_user.id
    duration = int(call.data.replace("w_dur_", ""))
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_settings SET duration = ? WHERE user_id = ?", (duration, user_id))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, "✅ تم حفظ الوقت بنجاح!")
    
    # الخطوة التالية: اختيار عرض القائمة بالعضو أو خاص
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        create_colored_btn("📺 عرض القائمة بالقناة (تتحدث تلقائياً مع طي الأسماء)", callback_data="w_show_1", style="success"),
        create_colored_btn("🔒 إرسال الكشف للخاص فقط وعدم عرضه بالقناة", callback_data="w_show_0", style="primary")
    )
    bot.send_message(call.message.chat.id, "👁️ *كيف تريد عرض قائمة أسماء الحضور المسجلين؟*\n\n> *ملاحظة: في الحالتين سيصلك الكشف الكامل على الخاص.*", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("w_show_"))
def handle_wizard_show_mode(call):
    user_id = call.from_user.id
    show_mode = int(call.data.replace("w_show_", ""))
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_settings SET show_in_channel = ? WHERE user_id = ?", (show_mode, user_id))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, "✨ تم حفظ الإعدادات بنجاح!")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(create_colored_btn("🚀 انشر البوست الآن في قناتك", switch_query="create", style="success"))
    bot.send_message(call.message.chat.id, "🎉 **أصبح بوست الحضور جاهزاً تماماً للنشر!**\n\n> *اضغط على الزر أدناه لاختيار القناة أو المجموعة ونشر البوست:*", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_manual_title")
def save_manual_title(message):
    user_id = message.from_user.id
    title = message.text
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, title, duration, show_in_channel) VALUES (?, ?, 0, 1)", (user_id, title))
    cursor.execute("UPDATE user_settings SET title = ? WHERE user_id = ?", (title, user_id))
    conn.commit()
    conn.close()
    user_states.pop(user_id, None)
    
    bot.reply_to(message, "✅ *تم حفظ عنوان البوست بنجاح!*", parse_mode="Markdown")
    ask_duration_wizard(message)

@bot.callback_query_handler(func=lambda call: call.data == "set_display_mode")
def callback_set_display_mode(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        create_colored_btn("📺 عرض القائمة بالقناة (مع طي الأسماء)", callback_data="w_show_1", style="success"),
        create_colored_btn("🔒 إرسال الكشف للخاص فقط", callback_data="w_show_0", style="primary")
    )
    bot.send_message(call.message.chat.id, "👁️ *اختر طريقة عرض الكشف:*", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("export_"))
def export_attendance_csv(call):
    poll_id = call.data.replace("export_", "")
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM polls WHERE poll_id = ? AND owner_id = ?", (poll_id, call.from_user.id))
    poll = cursor.fetchone()
    if not poll:
        bot.answer_callback_query(call.id, "❌ البوست غير موجود أو ليس لك صلاحية.", show_alert=True)
        conn.close()
        return
    title = poll[0]
    cursor.execute("SELECT user_id, user_name, username FROM poll_votes WHERE poll_id = ?", (poll_id,))
    votes = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'Full Name', 'Username'])
    for uid, name, uname in votes:
        writer.writerow([uid, name, uname])
    output.seek(0)
    
    bytes_io = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    bytes_io.name = f"attendance_{poll_id}.csv"
    
    bot.answer_callback_query(call.id)
    bot.send_document(call.message.chat.id, bytes_io, caption=f"📄 **كشف الحضور لبوست:**\n`{title}`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_prompt(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "للمشرف فقط ⛔", show_alert=True)
        return
    user_states[ADMIN_ID] = "waiting_broadcast_msg"
    bot.answer_callback_query(call.id)
    bot.send_message(ADMIN_ID, "📢 *أرسل الآن نص الرسالة الجماعية (Broadcast):*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_broadcast_msg")
def execute_broadcast(message):
    user_states.pop(ADMIN_ID, None)
    broadcast_text = message.text
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM user_settings")
    users = cursor.fetchall()
    conn.close()
    
    success_count = 0
    fail_count = 0
    status_msg = bot.reply_to(message, "🚀 *جاري بدء إرسال الرسالة الجماعية..*", parse_mode="Markdown")
    
    for (uid,) in users:
        try:
            bot.send_message(uid, f"📢 **تنبيه هام من الإدارة:**\n\n> {broadcast_text}", parse_mode="Markdown")
            success_count += 1
        except Exception:
            fail_count += 1
            
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=f"✅ **تم الانتهاء من الإرسال الجماعي بنجاح!**\n\n> • **تم بنجاح:** `{success_count}`\n> • **فشل:** `{fail_count}`",
        parse_mode="Markdown"
    )

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
        bot.reply_to(message, "✅ *تم إرسال رسالتك بنجاح إلى الإدارة!*", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "❌ حدث خطأ أثناء إرسال الرسالة.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def admin_start_reply(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "للمشرف فقط ⛔", show_alert=True)
        return
    target_user_id = call.data.replace("reply_", "")
    user_states[ADMIN_ID] = f"admin_reply_to_{target_user_id}"
    bot.answer_callback_query(call.id)
    bot.send_message(ADMIN_ID, f"✍️ *اكتب الرد للمستخدم (ID: `{target_user_id}`):*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.from_user.id in user_states and user_states[message.from_user.id].startswith("admin_reply_to_"))
def send_admin_reply_to_user(message):
    target_user_id = int(user_states[ADMIN_ID].replace("admin_reply_to_", ""))
    user_states.pop(ADMIN_ID, None)
    try:
        bot.send_message(target_user_id, f"📥 **رد جديد من الدعم الفني:**\n\n> {message.text}", parse_mode="Markdown")
        bot.reply_to(message, "✅ تم إرسال الرد بنجاح!")
    except Exception:
        bot.reply_to(message, "❌ فشل إرسال الرد.")

# معالجة استعلام النشر عبر الـ Inline Query
@bot.inline_handler(func=lambda query: True)
def inline_query(query):
    user_id = query.from_user.id
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT title, duration, show_in_channel FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    title = row[0] if row and row[0] else f"سجل الحضور — {get_arabic_date_string()}"
    duration = row[1] if row and row[1] is not None else 0
    show_in_channel = row[2] if row and row[2] is not None else 1
    
    poll_id = f"poll_{user_id}_{query.id}"
    current_time = time.time()
    end_time = (current_time + (duration * 60)) if duration > 0 else 0
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO polls (poll_id, owner_id, count, title, end_time, is_closed, show_in_channel) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                   (poll_id, user_id, 0, title, end_time, 0, show_in_channel))
    conn.commit()
    conn.close()
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(create_colored_btn("✅ تسجيل الحضور [0]", callback_data=f"attend_{poll_id}", style="success"))
    
    time_note = f"\n> ⏱️ *ينتهي هذا البوست تلقائياً بعد {duration} دقيقة.*" if duration > 0 else "\n> ⏱️ *البوست مفتوح طوال الوقت لتسجيل الحضور.*"
    
    msg_content = f"📢 **{title}**\n\n> *اضغط على الزر الملون أدناه لتسجيل حضورك الرسمي فوراً:*{time_note}"
    if show_in_channel == 1:
        msg_content += "\n\n> 👥 **قائمة الحضور المسجلين (0):**\n> *لا توجد تسجيلات حتى الآن.*"

    articles = [
        types.InlineQueryResultArticle(
            id=poll_id,
            title="إنشاء ونشر بوست تسجيل الحضور",
            description=title,
            input_message_content=types.InputTextMessageContent(
                message_text=msg_content,
                parse_mode="Markdown"
            ),
            reply_markup=keyboard
        )
    ]
    bot.answer_inline_query(query.id, articles, cache_time=1)

# تسجيل الحضور وضمان استخدام الاسم الثابت المرتبط بالـ ID
@bot.callback_query_handler(func=lambda call: call.data.startswith("attend_"))
def handle_channel_attendance(call):
    poll_id = call.data.replace("attend_", "")
    user = call.from_user
    current_time = time.time()
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # تحديث وتثبيت اسم العضو المرتبط بالـ ID بناءً على سجله في البوت
    uname_str = f"@{user.username}" if user.username else "لا يوجد"
    cursor.execute("SELECT full_name FROM user_profiles WHERE user_id = ?", (user.id,))
    prof = cursor.fetchone()
    if prof:
        fixed_name = prof[0]
    else:
        fixed_name = user.first_name
        cursor.execute("INSERT INTO user_profiles (user_id, full_name, username) VALUES (?, ?, ?)", (user.id, fixed_name, uname_str))
        conn.commit()

    cursor.execute("SELECT owner_id, count, title, end_time, is_closed, show_in_channel FROM polls WHERE poll_id = ?", (poll_id,))
    poll = cursor.fetchone()
    if not poll:
        bot.answer_callback_query(call.id, "❌ انتهت صلاحية هذا البوست.", show_alert=True)
        conn.close()
        return
        
    owner_id, count, title, end_time, is_closed, show_in_channel = poll
    
    if is_closed == 1 or (end_time > 0 and current_time > end_time):
        bot.answer_callback_query(call.id, "⌛ عذراً، انتهى وقت تسجيل الحضور لهذا البوست!", show_alert=True)
        conn.close()
        return
        
    cursor.execute("SELECT * FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user.id))
    if cursor.fetchone():
        bot.answer_callback_query(call.id, "⚠️ لقد قمت بتسجيل حضورك مسبقاً!", show_alert=True)
        conn.close()
        return
        
    new_count = count + 1
    cursor.execute("UPDATE polls SET count = ? WHERE poll_id = ?", (new_count, poll_id))
    cursor.execute("INSERT INTO poll_votes (poll_id, user_id, user_name, username) VALUES (?, ?, ?, ?)", (poll_id, user.id, fixed_name, uname_str))
    
    # منح نقاط تفاعلية للمستخدم
    cursor.execute("INSERT INTO user_points (user_id, points) VALUES (?, 5) ON CONFLICT(user_id) DO UPDATE SET points = points + 5", (user.id,))
    
    # جلب جميع الأعضاء المسجلين في هذا البوست لتحديث القائمة بتنسيق القائمة المنسدلة (الطي)
    cursor.execute("SELECT user_name FROM poll_votes WHERE poll_id = ?", (poll_id,))
    all_voters = cursor.fetchall()
    
    conn.commit()
    conn.close()
    
    # إشعار المنشئ دائماً على الخاص مع اسم العضو الثابت المرتبط بالـ ID
    owner_notification = (
        f"🔔 **تسجيل حضور جديد في بوستك!**\n\n"
        f"> • **البوست:** {title}\n"
        f"> • **المسجل:** {fixed_name}\n"
        f"> • **المعرف:** `{uname_str}`\n"
        f"> • **الأيدي:** `{user.id}`"
    )
    try:
        bot.send_message(owner_id, owner_notification, parse_mode="Markdown")
    except Exception:
        pass 
        
    # تحديث رسالة القناة تلقائياً لو كان الخيار مفعلاً بعرض القائمة داخل اقتباس (طي)
    try:
        duration_note = "" # ملاحظة الوقت يمكن إضافتها عند الحاجة
        new_keyboard = types.InlineKeyboardMarkup()
        new_keyboard.add(create_colored_btn(f"✅ تسجيل الحضور [{new_count}]", callback_data=f"attend_{poll_id}", style="success"))
        
        # بناء قائمة الاقتباس للأسماء
        voters_list_str = ""
        if show_in_channel == 1:
            voters_lines = [f"> {i+1}. {v[0]}" for i, v in enumerate(all_voters)]
            voters_list_str = "\n" + "\n".join(voters_lines)

        updated_text = f"📢 **{title}**\n\n> *اضغط على الزر الملون أدناه لتسجيل حضورك الرسمي فوراً:*"
        if show_in_channel == 1:
            updated_text += f"\n\n> 👥 **قائمة الحضور المسجلين ({new_count}):**{voters_list_str}"

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=updated_text,
            parse_mode="Markdown",
            reply_markup=new_keyboard
        )
    except Exception:
        pass
        
    bot.answer_callback_query(call.id, f"✨ تم تسجيل حضورك بنجاح يا {fixed_name} وحصلت على 5 نقاط!", show_alert=True)

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
