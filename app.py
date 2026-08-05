# -*- coding: utf-8 -*-
import telebot
from telebot import types
import sqlite3
import os
import time
import io
import csv
import html
import threading
from datetime import datetime
from flask import Flask, request

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
WEBHOOK_URL = f"https://eeeeeee-production.up.railway.app/{TOKEN}"
ADMIN_ID = 1250493517

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تسجيل الويب هوك هنا مباشرة ليعمل مع سيرفر الإنتاج (Gunicorn) فور الإقلاع
try:
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook set successfully!")
except Exception as e:
    print(f"Error setting webhook: {e}")

def init_db():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                        user_id INTEGER PRIMARY KEY, 
                        title TEXT, 
                        custom_message TEXT, 
                        duration INTEGER DEFAULT 0,
                        show_in_channel INTEGER DEFAULT 1
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS polls (
                        poll_id TEXT PRIMARY KEY, 
                        owner_id INTEGER, 
                        count INTEGER, 
                        title TEXT, 
                        end_time REAL DEFAULT 0, 
                        is_closed INTEGER DEFAULT 0,
                        show_in_channel INTEGER DEFAULT 1,
                        channel_id TEXT,
                        message_id INTEGER
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS poll_votes (
                        poll_id TEXT, 
                        user_id INTEGER, 
                        user_name TEXT, 
                        username TEXT, 
                        PRIMARY KEY (poll_id, user_id)
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS channel_daily_attendance (
                        user_id INTEGER,
                        channel_id TEXT,
                        date_str TEXT,
                        count INTEGER DEFAULT 0,
                        PRIMARY KEY (user_id, channel_id, date_str)
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS channel_daily_posts (
                        channel_id TEXT,
                        date_str TEXT,
                        posts_count INTEGER DEFAULT 0,
                        PRIMARY KEY (channel_id, date_str)
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS saved_channels (
                        user_id INTEGER,
                        channel_id TEXT,
                        channel_title TEXT,
                        PRIMARY KEY (user_id, channel_id)
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS authorized_question_creators (
                        user_id INTEGER PRIMARY KEY
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id INTEGER PRIMARY KEY,
                        full_name TEXT,
                        username TEXT
                    )''')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS referrals (owner_id INTEGER PRIMARY KEY, visits_count INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_referral_logs (owner_id INTEGER, visitor_id INTEGER, PRIMARY KEY (owner_id, visitor_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS user_points (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS coupons (
                        code TEXT PRIMARY KEY,
                        points INTEGER,
                        max_uses INTEGER,
                        uses_count INTEGER DEFAULT 0,
                        expires_at REAL,
                        is_closed INTEGER DEFAULT 0
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS coupon_uses (
                        code TEXT,
                        user_id INTEGER,
                        PRIMARY KEY (code, user_id)
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
                        question_id TEXT PRIMARY KEY,
                        owner_id INTEGER,
                        question_text TEXT,
                        opt_a TEXT,
                        opt_b TEXT,
                        opt_c TEXT,
                        opt_d TEXT,
                        correct_opt TEXT,
                        channel_id TEXT,
                        message_id INTEGER,
                        is_closed INTEGER DEFAULT 0
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS question_answers (
                        question_id TEXT,
                        user_id INTEGER,
                        selected_option TEXT,
                        is_correct INTEGER,
                        earned_points INTEGER,
                        PRIMARY KEY (question_id, user_id)
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_badges (
                        user_id INTEGER PRIMARY KEY,
                        badge_name TEXT,
                        badge_icon TEXT
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts (
                        sched_id TEXT PRIMARY KEY,
                        user_id INTEGER,
                        channel_id TEXT,
                        post_type TEXT,
                        title TEXT,
                        content_data TEXT,
                        run_time REAL
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS question_speed_race (
                        question_id TEXT,
                        user_id INTEGER,
                        user_name TEXT,
                        rank_pos INTEGER,
                        PRIMARY KEY (question_id, user_id)
                    )''')
    
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
        '9': 'سبتمبر', '10': 'أكتوبر', '11': 'نوفمبر', '12': 'ديسمبر'
    }
    now = datetime.now()
    d_name = days.get(now.strftime('%A'), '')
    m_name = months.get(str(now.month), '')
    return f"{d_name} {now.day} {m_name} {now.year}"

def get_user_badge(points):
    if points >= 500:
        return "💎 ماسي متقدم", "💎"
    elif points >= 250:
        return "🥇 ذهبي مميز", "🥇"
    elif points >= 100:
        return "🥈 فضي نشط", "🥈"
    elif points >= 30:
        return "🥉 برونزي تفاعلي", "🥉"
    else:
        return "🏅 عضو جديد", "🏅"

def create_colored_btn(text, callback_data=None, url=None, style="primary"):
    if url:
        btn = types.InlineKeyboardButton(text=text, url=url)
    else:
        btn = types.InlineKeyboardButton(text=text, callback_data=callback_data)
    btn.style = style 
    return btn

def get_main_inline_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_settings = create_colored_btn("⚙️ إعدادات البوست", callback_data="menu_settings", style="primary")
    btn_share = create_colored_btn("🚀 نشر بوست جديد بالقناة", callback_data="menu_share", style="primary")
    markup.add(btn_settings, btn_share)
    
    btn_q_create = create_colored_btn("❓ طرح سؤال تفاعلي", callback_data="menu_create_question", style="success")
    btn_coupon_redeem = create_colored_btn("🎁 شحن كوبون هدية", callback_data="menu_redeem_prompt", style="success")
    markup.add(btn_q_create, btn_coupon_redeem)

    btn_sched = create_colored_btn("⏰ جدولة بوست/سؤال", callback_data="menu_schedule_prompt", style="primary")
    btn_stats = create_colored_btn("📊 إحصائيات التحليل المتقدم", callback_data="menu_stats", style="success")
    markup.add(btn_sched, btn_stats)

    btn_top = create_colored_btn("🏆 قائمة المتصدرين", callback_data="menu_leaderboard", style="success")
    btn_points = create_colored_btn("🌟 لوحة النقاط", callback_data="menu_points", style="success")
    markup.add(btn_top, btn_points)
    
    btn_profile = create_colored_btn("👤 الملف الشخصي (/profile)", callback_data="menu_profile", style="primary")
    btn_support = create_colored_btn("🛠️ الدعم والمساعدة", callback_data="menu_support", style="success")
    markup.add(btn_profile, btn_support)
    
    if user_id == ADMIN_ID:
        btn_admin = create_colored_btn("👑 لوحة تحكم المشرف", callback_data="menu_admin", style="danger")
        markup.add(btn_admin)
        
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    uname_str = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
    cursor.execute("INSERT INTO user_profiles (user_id, full_name, username) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET full_name = ?, username = ?", 
                   (user_id, message.from_user.first_name, uname_str, message.from_user.first_name, uname_str))
    conn.commit()

    args = message.text.split()
    if len(args) > 1 and message.text.startswith('/start'):
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
    
    badge_name, badge_icon = get_user_badge(user_points)
    cursor.execute("INSERT OR REPLACE INTO user_badges (user_id, badge_name, badge_icon) VALUES (?, ?, ?)", (user_id, badge_name, badge_icon))
    conn.commit()
    conn.close()

    markup = get_main_inline_keyboard(user_id)
    welcome_text = (
        f"✨ <b>مرحباً بك عزيزي {message.from_user.first_name}</b>\n\n"
        f"<blockquote>📌 <i>أنشئ بوستات الحضور والأسئلة التفاعلية بكل احترافية، مع تحليلات ذكية ونظام الأوسمة وتحديات السرعة المتقدمة.</i></blockquote>\n\n"
        f"🏅 <b>وسامك الحالي:</b> {badge_icon} <b>{badge_name}</b>\n\n"
        f"⚠️ <b>تنبيه هام جداً:</b> ارفع البوت <b>مشرفاً (Admin)</b> في قناتك مع صلاحية (تعديل رسائل الآخرين وحذفها) لكي يعمل التحديث الفوري.\n\n"
        f"🔗 <b>رابط دعوتك الشخصي:</b>\n<code>https://t.me/{bot.get_me().username}?start={user_id}</code>\n\n"
        f"📊 <b>إجمالي زوار رابطك:</b> <code>{total_visits}</code> شخص\n"
        f"🌟 <b>رصيدك من النقاط:</b> <code>{user_points}</code> نقطة\n\n"
        f"👇 <b>اختر ما تحتاجه من الأزرار الملونة أدناه:</b>"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=['backup'])
def cmd_backup(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ هذا الأمر مخصص للمشرف فقط.")
        return
    if os.path.exists('roulette_bot.db'):
        with open('roulette_bot.db', 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📦 <b>نسخة احتياطية لقاعدة البيانات (Backup)</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, "❌ ملف قاعدة البيانات غير موجود.")

@bot.message_handler(commands=['restore'])
def cmd_restore(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ هذا الأمر مخصص للمشرف فقط.")
        return
    user_states[ADMIN_ID] = "waiting_restore_file"
    bot.reply_to(message, "📥 <b>أرسل الآن ملف قاعدة البيانات (.db) لاستعادة النسخة الاحتياطية (Restore):</b>", parse_mode="HTML")

@bot.message_handler(content_types=['document'], func=lambda message: message.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID) == "waiting_restore_file")
def process_restore_file(message):
    user_states.pop(ADMIN_ID, None)
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open('roulette_bot.db', 'wb') as f:
            f.write(downloaded_file)
        bot.reply_to(message, "✅ <b>تم استعادة قاعدة البيانات (Restore) بنجاح وبدء العمل بالنسخة الجديدة!</b>", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ <b>فشل استعادة قاعدة البيانات:</b> <code>{e}</code>", parse_mode="HTML")

@bot.message_handler(commands=['points', 'رصيدي'])
def cmd_points(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    pts = res[0] if res else 0
    b_name, b_icon = get_user_badge(pts)
    conn.close()
    bot.reply_to(message, f"🌟 <b>رصيدك الحالي:</b> <code>{pts}</code> نقطة\n🏅 <b>الوسام:</b> {b_icon} {b_name}", parse_mode="HTML")

@bot.message_handler(commands=['profile'])
def cmd_profile(message):
    show_profile_data(message.chat.id, message.from_user.id)

def show_profile_data(chat_id, user_id):
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
    p_res = cursor.fetchone()
    pts = p_res[0] if p_res else 0
    
    badge_name, badge_icon = get_user_badge(pts)
    cursor.execute("SELECT COUNT(*) FROM user_points WHERE points > ?", (pts,))
    higher_users = cursor.fetchone()[0]
    rank = higher_users + 1
    
    cursor.execute("SELECT COUNT(*), SUM(is_correct) FROM question_answers WHERE user_id = ?", (user_id,))
    q_res = cursor.fetchone()
    total_q = q_res[0] if q_res and q_res[0] else 0
    correct_q = q_res[1] if q_res and q_res[1] else 0
    accuracy = round((correct_q / total_q) * 100, 1) if total_q > 0 else 0.0
    
    cursor.execute("SELECT DISTINCT channel_title, channel_id FROM saved_channels WHERE user_id = ?", (user_id,))
    saved_channels = cursor.fetchall()
    
    cursor.execute("SELECT code FROM coupon_uses WHERE user_id = ?", (user_id,))
    used_coupons = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    coupons_str = ", ".join(used_coupons) if used_coupons else "لا توجد"
    channels_str = ", ".join([f"{c[0]} ({c[1]})" for c in saved_channels]) if saved_channels else "لا توجد قنوات مسجلة"
    
    profile_text = (
        f"👤 <b>لوحة الملف الشخصي والإحصائيات الفردية:</b>\n\n"
        f"🏅 <b>الوسام والرتبة:</b>\n"
        f"<blockquote>• الوسام الحالي: {badge_icon} <b>{badge_name}</b>\n"
        f"• رصيد النقاط: <code>{pts}</code> نقطة\n"
        f"• الرتبة العالمية: المركز <code>{rank}</code></blockquote>\n\n"
        f"📊 <b>سجل إجابات الأسئلة وتحديات السرعة:</b>\n"
        f"<blockquote>• إجمالي الأسئلة المشارك بها: <code>{total_q}</code>\n"
        f"• الإجابات الصحيحة: <code>{correct_q}</code>\n"
        f"• نسبة الدقة: <code>{accuracy}%</code></blockquote>\n\n"
        f"🌐 <b>القنوات والمجموعات المسجلة:</b>\n"
        f"<blockquote>{channels_str}</blockquote>\n\n"
        f"🎁 <b>سجل الكوبونات المستخدمة:</b>\n"
        f"<blockquote>{coupons_str}</blockquote>"
    )
    bot.send_message(chat_id, profile_text, parse_mode="HTML")

@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ هذا الأمر مخصص للمشرف فقط.")
        return
    show_admin_panel(message.chat.id)

def show_admin_panel(chat_id):
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_settings")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM polls")
    total_polls = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM coupons")
    total_coupons = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM scheduled_posts")
    total_scheduled = cursor.fetchone()[0]
    conn.close()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(create_colored_btn("📢 إرسال رسالة جماعية (Broadcast)", callback_data="admin_broadcast", style="danger"))
    markup.add(create_colored_btn("📊 إرسال التقرير الأسبوعي الفوري", callback_data="admin_send_weekly_report", style="success"))
    markup.add(create_colored_btn("👥 إدارة مصممي الأسئلة", callback_data="admin_manage_q_creators", style="primary"))
    
    admin_panel = (
        f"👑 <b>لوحة تحكم المشرف العامة:</b>\n\n"
        f"<blockquote>• <b>إجمالي المستخدمين المسجلين:</b> <code>{total_users}</code>\n"
        f"• <b>إجمالي بوستات الحضور:</b> <code>{total_polls}</code>\n"
        f"• <b>الposts المجدولة نشطة:</b> <code>{total_scheduled}</code>\n"
        f"• <b>إجمالي الكوبونات النشطة:</b> <code>{total_coupons}</code>\n"
        f"• <b>أوامر النظام المساعدة:</b> استخدم <code>/backup</code> لتحميل نسخة احتياطية أو <code>/restore</code> لاستعادة البيانات.</blockquote>"
    )
    bot.send_message(chat_id, admin_panel, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu_callbacks(call):
    user_id = call.from_user.id
    action = call.data.replace("menu_", "")
    
    if action == "settings":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(create_colored_btn("📝 اختيار عنوان / كليشة البوست", callback_data="wizard_title_type", style="primary"))
        markup.add(create_colored_btn("⏱️ ضبط مدة البوست الافتراضية", callback_data="set_duration", style="primary"))
        markup.add(create_colored_btn("👁️ ضبط خيار عرض القائمة بالرسالة", callback_data="set_display_mode", style="primary"))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ <b>إعدادات بوستات الحضور:</b>\n\n<blockquote>اختر الخيار الذي تريد ضبطه بدقة:</blockquote>", parse_mode="HTML", reply_markup=markup)
    
    elif action == "share":
        bot.answer_callback_query(call.id)
        show_channel_selection_menu(call.message.chat.id, user_id)

    elif action == "schedule_prompt":
        bot.answer_callback_query(call.id)
        user_states[user_id] = "waiting_sched_input"
        bot.send_message(
            call.message.chat.id,
            "⏰ <b>نظام جدولـة البوستات والأسئلة:</b>\n\n"
            "<blockquote>أرسل الآن نص البوست أو عنوان الحضور الذي تريد جدولته للنشر لاحقاً:</blockquote>",
            parse_mode="HTML"
        )
        
    elif action == "create_question":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM authorized_question_creators WHERE user_id = ?", (user_id,))
        is_authorized = cursor.fetchone() or (user_id == ADMIN_ID)
        conn.close()
        
        if not is_authorized:
            bot.send_message(call.message.chat.id, "⛔ عذراً، ميزة طرح الأسئلة التفاعلية مخصصة للمطور والمصرح لهم فقط.", parse_mode="HTML")
            return
            
        user_states[user_id] = "waiting_q_text"
        bot.send_message(
            call.message.chat.id,
            "❓ <b>نظام الأسئلة التفاعلية مع تحدي السرعة:</b>\n\n"
            "<blockquote>أرسل الآن نص السؤال التفاعلي الذي تريد طرحه:</blockquote>",
            parse_mode="HTML"
        )
    
    elif action == "redeem_prompt":
        bot.answer_callback_query(call.id)
        user_states[user_id] = "waiting_coupon_input"
        bot.send_message(call.message.chat.id, "🎁 <i>أرسل الآن كود الكوبون أو الهدية لشحنه ورصيدك فوراً:</i>", parse_mode="HTML")
        
    elif action == "profile":
        bot.answer_callback_query(call.id)
        show_profile_data(call.message.chat.id, user_id)

    elif action == "stats":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT poll_id, title, count FROM polls WHERE owner_id = ? ORDER BY rowid DESC", (user_id,))
        user_polls = cursor.fetchall()
        conn.close()
        
        if not user_polls:
            bot.send_message(call.message.chat.id, "📊 <b>الإحصائيات والتحليلات المتقدمة:</b>\n\n<blockquote>⚠️ لا توجد بوستات منشأة حتى الآن.</blockquote>", parse_mode="HTML")
            return
            
        stats_text = (
            "📊 <b>إحصائيات وتحليلي المتقدم للبوستات والقنوات:</b>\n\n"
            "<blockquote>💡 <i>توضيح البيانات (Unique vs Total): الأرقام أدناه توضح إجمالي التفاعلات، مع إمكانية استعراض المستخدمين الفريدين (Unique Reach) عند فتح تفاصيل كل بوست لتجنب تضخيم الأرقام الناتجة عن تداخل المشتركين.</i></blockquote>\n\n"
            "👇 <i>اختر البوست المطلوب لمعاينة التحليلات المعمقة:</i>"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        for pid, title, cnt in user_polls:
            short_title = title[:25] + "..." if len(title) > 25 else title
            markup.add(create_colored_btn(f"📌 {short_title} (إجمالي: {cnt})", callback_data=f"view_stats_{pid}", style="success"))
            
        bot.send_message(call.message.chat.id, stats_text, parse_mode="HTML", reply_markup=markup)
    
    elif action == "leaderboard":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.owner_id, r.visits_count, p.full_name, p.username 
            FROM referrals r 
            LEFT JOIN user_profiles p ON r.owner_id = p.user_id 
            ORDER BY r.visits_count DESC LIMIT 5
        """)
        top_users = cursor.fetchall()
        cursor.execute("""
            SELECT tp.user_id, tp.points, p.full_name, p.username, b.badge_icon 
            FROM user_points tp 
            LEFT JOIN user_profiles p ON tp.user_id = p.user_id 
            LEFT JOIN user_badges b ON tp.user_id = b.user_id
            ORDER BY tp.points DESC LIMIT 5
        """)
        top_points = cursor.fetchall()
        conn.close()
        
        leaderboard_text = "🏆 <b>قوائم المتصدرين في البوت:</b>\n\n🔗 <b>أكثر المستخدمين جلباً للزوار:</b>\n"
        if not top_users:
            leaderboard_text += "<blockquote>• لا توجد بيانات حتى الآن..</blockquote>\n\n"
        else:
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, (uid, count, fname, uname) in enumerate(top_users):
                medal = medals[i] if i < len(medals) else "🔹"
                name_display = fname if fname else f"مستخدم {uid}"
                uname_display = f" ({uname})" if uname and uname != "لا يوجد" else ""
                leaderboard_text += f"<blockquote>{medal} <b>{name_display}</b>{uname_display} — <b>{count}</b> زائر</blockquote>\n"
            leaderboard_text += "\n"
            
        leaderboard_text += "🌟 <b>أكثر الأعضاء تفاعلاً ونقاطاً والأوسمة:</b>\n"
        if not top_points:
            leaderboard_text += "<blockquote>• لا توجد نقاط مسجلة حتى الآن..</blockquote>"
        else:
            for i, (uid, pts, fname, uname, b_icon) in enumerate(top_points):
                medal = medals[i] if i < len(medals) else "🔹"
                icon = b_icon if b_icon else "🏅"
                name_display = fname if fname else f"مستخدم {uid}"
                uname_display = f" ({uname})" if uname and uname != "لا يوجد" else ""
                leaderboard_text += f"<blockquote>{medal} {icon} <b>{name_display}</b>{uname_display} — <b>{pts}</b> نقطة</blockquote>\n"
                
        bot.send_message(call.message.chat.id, leaderboard_text, parse_mode="HTML")
        
    elif action == "points":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        pts = res[0] if res else 0
        b_name, b_icon = get_user_badge(pts)
        conn.close()
        points_msg = (
            f"🌟 <b>نظام النقاط والأوسمة والمكافآت:</b>\n\n"
            f"<blockquote>• رصيدك الحالي هو: <b>{pts} نقطة</b>\n"
            f"• وسامك الحالي: {b_icon} <b>{b_name}</b>\n"
            f"• تحصل على النقاط وترقية الأوسمة تلقائياً كلما قمت بتسجيل حضورك أو المشاركة في تحديات السرعة والأسئلة!</blockquote>"
        )
        bot.send_message(call.message.chat.id, points_msg, parse_mode="HTML")
    
    elif action == "support":
        bot.answer_callback_query(call.id)
        user_states[user_id] = "waiting_support_msg"
        bot.send_message(call.message.chat.id, "💬 <i>أرسل رسالتك أو استفسارك الآن، وسيتم تحويله مباشرة إلى الإدارة:</i>", parse_mode="HTML")
    
    elif action == "admin":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "هذا الزر للمشرف فقط ⛔", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        show_admin_panel(call.message.chat.id)

def show_channel_selection_menu(chat_id, user_id):
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_title, channel_id FROM saved_channels WHERE user_id = ?", (user_id,))
    saved = cursor.fetchall()
    conn.close()
    
    if saved:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for c_title, c_id in saved:
            markup.add(create_colored_btn(f"📢 {c_title}", callback_data=f"select_chan_{c_id}", style="success"))
        markup.add(create_colored_btn("➕ إضافة قناة جديدة", callback_data="add_new_channel_prompt", style="primary"))
        bot.send_message(chat_id, "🚀 <b>اختر إحدى قنواتك المحفوظة أو أضف قناة جديدة للنشر:</b>\n\n<i>(ملاحظة: الحد الأقصى لبوستات الحضور هو بوستان فقط لكل قناة يومياً)</i>", parse_mode="HTML", reply_markup=markup)
    else:
        user_states[user_id] = "waiting_channel_username"
        bot.send_message(
            chat_id, 
            "🚀 <b>نشر بوست الحضور مباشرة بواسطة البوت:</b>\n\n"
            "<blockquote>أرسل الآن معرف قناتك أو مجموعة (مثال: <code>@MyChannel</code> أو رابط الدعوة أو الأيدي الخاص بالقناة)، وتأكد أن البوت مشرف فيها.\n(الحد الأقصى بوستان يومياً لكل قناة).</blockquote>", 
            parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: call.data == "add_new_channel_prompt")
def add_new_channel_prompt(call):
    user_id = call.from_user.id
    user_states[user_id] = "waiting_channel_username"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🚀 <b>أرسل الآن معرف القناة الجديدة أو الرابط أو الأيدي:</b>\n<i>(الحد الأقصى بوستان يومياً لكل قناة)</i>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_chan_"))
def select_saved_channel(call):
    user_id = call.from_user.id
    channel_id = call.data.replace("select_chan_", "")
    bot.answer_callback_query(call.id)
    publish_poll_to_channel(call.message, user_id, channel_id)

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_channel_username")
def process_channel_posting(message):
    user_id = message.from_user.id
    channel_input = message.text.strip()
    user_states.pop(user_id, None)
    publish_poll_to_channel(message, user_id, channel_input)

def publish_poll_to_channel(message_or_call_msg, user_id, channel_input):
    chat_id_to_send = message_or_call_msg.chat.id if hasattr(message_or_call_msg, 'chat') else message_or_call_msg.message.chat.id
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        chat_info = bot.get_chat(channel_input)
        real_channel_id = str(chat_info.id)
        c_title = chat_info.title or real_channel_id
    except Exception as e:
        conn.close()
        bot.send_message(chat_id_to_send, f"❌ <b>فشل الوصول للقناة أو المعرف غير صحيح:</b>\n<code>{e}</code>", parse_mode="HTML")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT posts_count FROM channel_daily_posts WHERE channel_id = ? AND date_str = ?", (real_channel_id, today_str))
    p_row = cursor.fetchone()
    posts_today = p_row[0] if p_row else 0
    
    if posts_today >= 2:
        conn.close()
        bot.send_message(chat_id_to_send, "⚠️ <b>عذراً، لقد وصلت للحد الأقصى لنشر بوستات الحضور في هذه القناة اليوم (مرتان فقط كحد أقصى يومياً).</b>", parse_mode="HTML")
        return

    cursor.execute("SELECT title, duration, show_in_channel FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    title = row[0] if row and row[0] else f"سجل الحضور — {get_arabic_date_string()}"
    duration = row[1] if row and row[1] is not None else 0
    show_in_channel = row[2] if row and row[2] is not None else 1
    
    poll_id = f"poll_{user_id}_{int(time.time())}"
    current_time = time.time()
    end_time = (current_time + (duration * 60)) if duration > 0 else 0
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(create_colored_btn("✅ تسجيل الحضور [0]", callback_data=f"attend_{poll_id}", style="success"))
    
    time_note = f"\n<i>⏱️ ينتهي هذا البوست تلقائياً بعد {duration} دقيقة.</i>" if duration > 0 else "\n<i>⏱️ البوست مفتوح طوال الوقت لتسجيل الحضور.</i>"
    
    msg_content = f"<b>📢 {html.escape(title)}</b>\n\n<i>اضغط على الزر الملون أدناه لتسجيل حضورك الرسمي فوراً:</i>{time_note}"
    if show_in_channel == 1:
        msg_content += "\n\n<blockquote expandable><b>👥 قائمة الحضور المسجلين (0):</b>\nلا توجد تسجيلات حتى الآن.</blockquote>"

    try:
        sent_msg = bot.send_message(real_channel_id, msg_content, parse_mode="HTML", reply_markup=keyboard)
        
        cursor.execute("INSERT OR REPLACE INTO saved_channels (user_id, channel_id, channel_title) VALUES (?, ?, ?)", 
                       (user_id, real_channel_id, c_title))
        cursor.execute("INSERT INTO channel_daily_posts (channel_id, date_str, posts_count) VALUES (?, ?, 1) ON CONFLICT(channel_id, date_str) DO UPDATE SET posts_count = posts_count + 1", 
                       (real_channel_id, today_str))
        cursor.execute("INSERT OR REPLACE INTO polls (poll_id, owner_id, count, title, end_time, is_closed, show_in_channel, channel_id, message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (poll_id, user_id, 0, title, end_time, 0, show_in_channel, real_channel_id, sent_msg.message_id))
        conn.commit()
        conn.close()
        
        bot.send_message(chat_id_to_send, "✅ <b>تم نشر بوست الحضور بنجاح في القناة وحفظها بقنواتك!</b>", parse_mode="HTML")
    except Exception as e:
        conn.close()
        bot.send_message(chat_id_to_send, f"❌ <b>فشل النشر في القناة:</b>\n\n<blockquote>تأكد أن البوت <b>مشرف</b> في القناة ولديه صلاحية إرسال الرسائل.\nالتفاصيل التقنية: <code>{e}</code></blockquote>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_sched_input")
def process_sched_title(message):
    user_id = message.from_user.id
    title = message.text.strip()
    user_states[user_id] = {"sched_title": title, "step": "waiting_sched_channel"}
    bot.reply_to(message, "📌 <i>أرسل الآن معرف القناة المراد النشر فيها تلقائياً (مثال: @MyChannel):</i>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and isinstance(user_states[message.from_user.id], dict) and user_states[message.from_user.id].get("step") == "waiting_sched_channel")
def process_sched_channel(message):
    user_id = message.from_user.id
    channel_input = message.text.strip()
    user_states[user_id]["sched_channel"] = channel_input
    user_states[user_id]["step"] = "waiting_sched_minutes"
    bot.reply_to(message, "⏱️ <i>بعد كم دقيقة تريد أن يتم نشر هذا البوست تلقائياً في القناة؟ (أرسل رقم بالدقائق، مثال: 30):</i>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and isinstance(user_states[message.from_user.id], dict) and user_states[message.from_user.id].get("step") == "waiting_sched_minutes")
def process_sched_minutes(message):
    user_id = message.from_user.id
    try:
        minutes = int(message.text.strip())
    except ValueError:
        bot.reply_to(message, "❌ يجِب إرسال رقم صحيح بالدقائق.")
        return
        
    sched_data = user_states.pop(user_id, None)
    sched_id = f"sched_{user_id}_{int(time.time())}"
    run_time = time.time() + (minutes * 60)
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scheduled_posts (sched_id, user_id, channel_id, post_type, title, content_data, run_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (sched_id, user_id, sched_data["sched_channel"], "poll", sched_data["sched_title"], "", run_time))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"⏰ <b>تمت جدولة البوست بنجاح!</b>\nسيتم نشره تلقائياً في القناة بعد <code>{minutes}</code> دقيقة.", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_coupon_input")
def process_coupon_text_input(message):
    user_id = message.from_user.id
    code = message.text.strip()
    user_states.pop(user_id, None)
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT points, max_uses, uses_count, is_closed FROM coupons WHERE code = ?", (code,))
    c_row = cursor.fetchone()
    if not c_row:
        bot.reply_to(message, "❌ <b>عذراً، كود الكوبون غير صحيح.</b>", parse_mode="HTML")
        conn.close()
        return
    pts, max_uses, uses_count, is_closed = c_row
    if is_closed == 1 or uses_count >= max_uses:
        bot.reply_to(message, "⌛ <b>عذراً، هذا الكوبون انتهى أو استنفد استخداماته!</b>", parse_mode="HTML")
        conn.close()
        return
    cursor.execute("SELECT * FROM coupon_uses WHERE code = ? AND user_id = ?", (code, user_id))
    if cursor.fetchone():
        bot.reply_to(message, "⚠️ <b>لقد استخدمت هذا الكوبون مسبقاً!</b>", parse_mode="HTML")
        conn.close()
        return
    cursor.execute("INSERT INTO coupon_uses (code, user_id) VALUES (?, ?)", (code, user_id))
    cursor.execute("UPDATE coupons SET uses_count = uses_count + 1 WHERE code = ?", (code,))
    cursor.execute("INSERT INTO user_points (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + ?", (user_id, pts, pts))
    
    cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
    new_pts = cursor.fetchone()[0]
    b_name, b_icon = get_user_badge(new_pts)
    cursor.execute("INSERT OR REPLACE INTO user_badges (user_id, badge_name, badge_icon) VALUES (?, ?, ?)", (user_id, b_name, b_icon))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"🎉 <b>تم شحن الكوبون بنجاح!</b>\nأُضيف إلى رصيدك <code>{pts}</code> نقطة.\n🏅 الوسام الحالي: {b_icon} {b_name}", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_q_text")
def q_step_text(message):
    user_id = message.from_user.id
    q_text = message.text.strip()
    user_states[user_id] = {"q_text": q_text, "step": "waiting_opt_a"}
    bot.reply_to(message, "📌 <i>أرسل الآن الخيار الأول (أ):</i>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and isinstance(user_states[message.from_user.id], dict) and user_states[message.from_user.id].get("step") == "waiting_opt_a")
def q_step_opt_a(message):
    user_id = message.from_user.id
    user_states[user_id]["opt_a"] = message.text.strip()
    user_states[user_id]["step"] = "waiting_opt_b"
    bot.reply_to(message, "📌 <i>أرسل الآن الخيار الثاني (ب):</i>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and isinstance(user_states[message.from_user.id], dict) and user_states[message.from_user.id].get("step") == "waiting_opt_b")
def q_step_opt_b(message):
    user_id = message.from_user.id
    user_states[user_id]["opt_b"] = message.text.strip()
    user_states[user_id]["step"] = "waiting_opt_c"
    bot.reply_to(message, "📌 <i>أرسل الآن الخيار الثالث (ج):</i>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and isinstance(user_states[message.from_user.id], dict) and user_states[message.from_user.id].get("step") == "waiting_opt_c")
def q_step_opt_c(message):
    user_id = message.from_user.id
    user_states[user_id]["opt_c"] = message.text.strip()
    user_states[user_id]["step"] = "waiting_opt_d"
    bot.reply_to(message, "📌 <i>أرسل الآن الخيار الرابع (د):</i>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and isinstance(user_states[message.from_user.id], dict) and user_states[message.from_user.id].get("step") == "waiting_opt_d")
def q_step_opt_d(message):
    user_id = message.from_user.id
    user_states[user_id]["opt_d"] = message.text.strip()
    user_states[user_id]["step"] = "waiting_correct_opt"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        create_colored_btn("الخيار (أ)", callback_data="q_correct_A", style="success"),
        create_colored_btn("الخيار (ب)", callback_data="q_correct_B", style="success"),
        create_colored_btn("الخيار (ج)", callback_data="q_correct_C", style="success"),
        create_colored_btn("الخيار (د)", callback_data="q_correct_D", style="success")
    )
    bot.reply_to(message, "🎯 <i>اختر الإجابة الصحيحة من الأزرار أدناه:</i>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("q_correct_"))
def q_step_correct_chosen(call):
    user_id = call.from_user.id
    if user_id not in user_states or not isinstance(user_states[user_id], dict):
        bot.answer_callback_query(call.id, "❌ انتهت الجلسة، ابدأ من جديد.", show_alert=True)
        return
    correct_opt = call.data.replace("q_correct_", "")
    user_states[user_id]["correct_opt"] = correct_opt
    user_states[user_id]["step"] = "waiting_q_channel"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🚀 <i>أرسل الآن معرف قناتك لنشر السؤال التفاعلي مع (تحدي السرعة) فيها (مثال: <code>@MyChannel</code>):</i>", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and isinstance(user_states[message.from_user.id], dict) and user_states[message.from_user.id].get("step") == "waiting_q_channel")
def q_step_publish(message):
    user_id = message.from_user.id
    channel_input = message.text.strip()
    q_data = user_states.pop(user_id, None)
    
    question_id = f"q_{user_id}_{int(time.time())}"
    q_text = q_data["q_text"]
    oa = q_data["opt_a"]
    ob = q_data["opt_b"]
    oc = q_data["opt_c"]
    od = q_data["opt_d"]
    correct_opt = q_data["correct_opt"]
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        create_colored_btn(f"أ) {oa}", callback_data=f"ans_{question_id}_A", style="primary"),
        create_colored_btn(f"ب) {ob}", callback_data=f"ans_{question_id}_B", style="primary"),
        create_colored_btn(f"ج) {oc}", callback_data=f"ans_{question_id}_C", style="primary"),
        create_colored_btn(f"د) {od}", callback_data=f"ans_{question_id}_D", style="primary")
    )
    
    q_msg_content = (
        f"💡 <b>سؤال تفاعلي مع (تحدي السرعة):</b>\n\n"
        f"📌 <b>{html.escape(q_text)}</b>\n\n"
        f"🔹 أ) {html.escape(oa)}\n"
        f"🔹 ب) {html.escape(ob)}\n"
        f"🔹 ج) {html.escape(oc)}\n"
        f"🔹 د) {html.escape(od)}\n\n"
        f"🏁 <b>لوحة شرف تحدي السرعة (أسرع 3 أجابوا صح):</b>\n"
        f"<blockquote>1. في انتظار الأسرع...\n2. في انتظار الأسرع...\n3. في انتظار الأسرع...</blockquote>\n\n"
        f"<i>⏱️ اختر الإجابة الصحيحة الآن لتكون في لوحة الشرف!</i>"
    )
    
    try:
        sent_msg = bot.send_message(channel_input, q_msg_content, parse_mode="HTML", reply_markup=keyboard)
        conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO questions (question_id, owner_id, question_text, opt_a, opt_b, opt_c, opt_d, correct_opt, channel_id, message_id, is_closed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                       (question_id, user_id, q_text, oa, ob, oc, od, correct_opt, str(sent_msg.chat.id), sent_msg.message_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, "✅ <b>تم نشر السؤال التفاعلي مع نظام تحدي السرعة بنجاح في القناة!</b>", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ <b>فشل نشر السؤال في القناة:</b>\n\n<blockquote>تأكد أن البوت مشرف ولديه صلاحيات الإرسال.\nالتفاصيل: <code>{e}</code></blockquote>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def handle_question_answer(call):
    raw_data = call.data[4:]
    last_underscore_idx = raw_data.rfind('_')
    if last_underscore_idx == -1:
        return
    question_id = raw_data[:last_underscore_idx]
    chosen_opt = raw_data[last_underscore_idx+1:]
    user = call.from_user
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT owner_id, correct_opt, is_closed, question_text, opt_a, opt_b, opt_c, opt_d, channel_id, message_id FROM questions WHERE question_id = ?", (question_id,))
    q_row = cursor.fetchone()
    if not q_row:
        bot.answer_callback_query(call.id, "❌ عذراً، هذا السؤال غير موجود أو انتهى.", show_alert=True)
        conn.close()
        return
    owner_id, correct_opt, is_closed, q_text, oa, ob, oc, od, channel_id, message_id = q_row
    if is_closed == 1:
        bot.answer_callback_query(call.id, "⌛ عذراً، تم إغلاق هذا السؤال!", show_alert=True)
        conn.close()
        return
    cursor.execute("SELECT * FROM question_answers WHERE question_id = ? AND user_id = ?", (question_id, user.id))
    if cursor.fetchone():
        bot.answer_callback_query(call.id, "⚠️ لقد قمت بالإجابة على هذا السؤال مسبقاً!", show_alert=True)
        conn.close()
        return
        
    is_correct = 1 if chosen_opt == correct_opt else 0
    earned_points = 0
    speed_bonus_note = ""
    
    cursor.execute("SELECT full_name FROM user_profiles WHERE user_id = ?", (user.id,))
    prof = cursor.fetchone()
    fixed_name = prof[0] if prof else user.first_name

    if is_correct == 1:
        cursor.execute("SELECT COUNT(*) FROM question_speed_race WHERE question_id = ?", (question_id,))
        current_rank = cursor.fetchone()[0] + 1
        
        if current_rank <= 3:
            cursor.execute("INSERT INTO question_speed_race (question_id, user_id, user_name, rank_pos) VALUES (?, ?, ?, ?)", (question_id, user.id, fixed_name, current_rank))
            if current_rank == 1:
                earned_points = 25
                speed_bonus_note = " 🚀 (المركز الأول في تحدي السرعة! +25 نقطة)"
            elif current_rank == 2:
                earned_points = 18
                speed_bonus_note = " 🥈 (المركز الثاني في تحدي السرعة! +18 نقطة)"
            elif current_rank == 3:
                earned_points = 12
                speed_bonus_note = " 🥉 (المركز الثالث في تحدي السرعة! +12 نقطة)"
        else:
            earned_points = 5
            speed_bonus_note = " ✅ (إجابة صحيحة! +5 نقاط)"
            
        cursor.execute("INSERT INTO user_points (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + ?", (user.id, earned_points, earned_points))
        
        cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user.id,))
        new_pts = cursor.fetchone()[0]
        b_name, b_icon = get_user_badge(new_pts)
        cursor.execute("INSERT OR REPLACE INTO user_badges (user_id, badge_name, badge_icon) VALUES (?, ?, ?)", (user.id, b_name, b_icon))
    else:
        earned_points = 0
        speed_bonus_note = " ❌ (إجابة خاطئة!)"
        
    cursor.execute("INSERT INTO question_answers (question_id, user_id, selected_option, is_correct, earned_points) VALUES (?, ?, ?, ?, ?)",
                   (question_id, user.id, chosen_opt, is_correct, earned_points))
                   
    cursor.execute("SELECT rank_pos, user_name FROM question_speed_race WHERE question_id = ? ORDER BY rank_pos ASC", (question_id,))
    speed_racers = cursor.fetchall()
    conn.commit()
    conn.close()
    
    try:
        racers_dict = {r[0]: r[1] for r in speed_racers}
        r1 = racers_dict.get(1, "في انتظار الأسرع...")
        r2 = racers_dict.get(2, "في انتظار الأسرع...")
        r3 = racers_dict.get(3, "في انتظار الأسرع...")
        
        updated_q_content = (
            f"💡 <b>سؤال تفاعلي مع (تحدي السرعة):</b>\n\n"
            f"📌 <b>{html.escape(q_text)}</b>\n\n"
            f"🔹 أ) {html.escape(oa)}\n"
            f"🔹 ب) {html.escape(ob)}\n"
            f"🔹 ج) {html.escape(oc)}\n"
            f"🔹 د) {html.escape(od)}\n\n"
            f"🏁 <b>لوحة شرف تحدي السرعة (أسرع 3 أجابوا صح):</b>\n"
            f"<blockquote>1. {html.escape(str(r1))}\n2. {html.escape(str(r2))}\n3. {html.escape(str(r3))}</blockquote>\n\n"
            f"<i>⏱️ اختر الإجابة الصحيحة الآن لتكون في لوحة الشرف!</i>"
        )
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            create_colored_btn(f"أ) {oa}", callback_data=f"ans_{question_id}_A", style="primary"),
            create_colored_btn(f"ب) {ob}", callback_data=f"ans_{question_id}_B", style="primary"),
            create_colored_btn(f"ج) {oc}", callback_data=f"ans_{question_id}_C", style="primary"),
            create_colored_btn(f"د) {od}", callback_data=f"ans_{question_id}_D", style="primary")
        )
        bot.edit_message_text(chat_id=channel_id, message_id=message_id, text=updated_q_content, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        print(f"Error updating speed race message: {e}")

    bot.answer_callback_query(call.id, f"{speed_bonus_note}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_stats_"))
def view_poll_detailed_stats(call):
    poll_id = call.data.replace("view_stats_", "")
    user_id = call.from_user.id
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT title, count, end_time FROM polls WHERE poll_id = ? AND owner_id = ?", (poll_id, user_id))
    poll = cursor.fetchone()
    if not poll:
        bot.answer_callback_query(call.id, "❌ البوست غير موجود أو ليس لك صلاحية.", show_alert=True)
        conn.close()
        return
    title, count, end_time = poll
    cursor.execute("SELECT user_name, username FROM poll_votes WHERE poll_id = ?", (poll_id,))
    votes = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM poll_votes WHERE poll_id = ?", (poll_id,))
    unique_users_count = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM user_profiles")
    total_bot_users = cursor.fetchone()[0] or 1
    conn.close()
    
    attendance_rate = round((unique_users_count / total_bot_users) * 100, 1)
    if attendance_rate > 100: attendance_rate = 100
    
    voters_str = ""
    if votes:
        voters_lines = [f"<blockquote>{i+1}. <b>{v[0]}</b> ({v[1]})</blockquote>" for i, v in enumerate(votes)]
        voters_str = "\n".join(voters_lines)
    else:
        voters_str = "<blockquote>• لم يسجل أحد حضوره حتى الآن.</blockquote>"
        
    stats_detail_msg = (
        f"📊 <b>التحليلات المتقدمة وإحصائيات البوست:</b>\n\n"
        f"<blockquote>• <b>عنوان البوست:</b> <code>{title}</code>\n"
        f"• <b>إجمالي التفاعلات (Total):</b> <code>{count}</code> تفاعل\n"
        f"• <b>الأشخاص الفريدون (Unique Reach):</b> <code>{unique_users_count}</code> مستخدم حقيقي\n"
        f"• <b>معدل التفاعل الفعلي (Engagement Rate):</b> <code>{attendance_rate}%</code></blockquote>\n\n"
        f"💡 <i>ملاحظة تحليلية: تم فصل الأرقام لتوضيح تداخل المشتركين بدقة وعكس الواقع الفعلي للتفاعل.</i>\n\n"
        f"👥 <b>قائمة الحاضرين المسجلين:</b>\n"
        f"{voters_str}"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(create_colored_btn("📥 تحميل كشف الحضور (CSV)", callback_data=f"export_{poll_id}", style="primary"))
    markup.add(create_colored_btn("🗑️ حذف البوست نهائياً", callback_data=f"delete_poll_{poll_id}", style="danger"))
    markup.add(create_colored_btn("🔙 العودة للإحصائيات", callback_data="menu_stats", style="success"))
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=stats_detail_msg,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_poll_"))
def delete_poll_callback(call):
    poll_id = call.data.replace("delete_poll_", "")
    user_id = call.from_user.id
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, message_id FROM polls WHERE poll_id = ? AND owner_id = ?", (poll_id, user_id))
    poll = cursor.fetchone()
    if not poll:
        bot.answer_callback_query(call.id, "❌ البوست غير موجود.", show_alert=True)
        conn.close()
        return
    channel_id, message_id = poll
    try:
        bot.delete_message(chat_id=channel_id, message_id=message_id)
    except Exception:
        pass
    cursor.execute("DELETE FROM polls WHERE poll_id = ?", (poll_id,))
    cursor.execute("DELETE FROM poll_votes WHERE poll_id = ?", (poll_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "✅ تم حذف البوست بنجاح!", show_alert=True)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🗑️ <b>تم حذف البوست وسجله بنجاح.</b>",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "wizard_title_type")
def wizard_title_type(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        create_colored_btn("✏️ اسم يدوي (اكتبه بنفسك)", callback_data="w_title_manual", style="primary"),
        create_colored_btn(f"📅 اسم تلقائي باليوم والتاريخ ({get_arabic_date_string()})", callback_data="w_title_auto", style="success")
    )
    bot.send_message(call.message.chat.id, "📌 <i>اختر كيف تريد تسمية بوست الحضور الجديد:</i>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "w_title_manual")
def wizard_title_manual(call):
    user_states[call.from_user.id] = "waiting_manual_title"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📝 <i>أرسل الآن العنوان أو الكليشة اليدوية التي تريدها للبوست:</i>", parse_mode="HTML")

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
    bot.send_message(message.chat.id, "⏱️ <i>اختر المدة الزمنية لصلاحية البوست بعد نشره:</i>", parse_mode="HTML", reply_markup=markup)

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
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        create_colored_btn("📺 عرض الأسماء في رسالة البوست بالقناة", callback_data="w_show_1", style="success"),
        create_colored_btn("🔒 إخفاء الأسماء من القناة وإرسالها للخاص فقط", callback_data="w_show_0", style="primary")
    )
    bot.send_message(call.message.chat.id, "👁️ <b>كيف تريد عرض قائمة أسماء الحضور المسجلين؟</b>\n\n<blockquote>ملاحظة: في الحالتين سيصلك الكشف الكامل على الخاص.</blockquote>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("w_show_"))
def handle_wizard_show_mode(call):
    user_id = call.from_user.id
    show_mode = int(call.data.replace("w_show_", ""))
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE user_settings SET show_in_channel = ? WHERE user_id = ?", (show_mode, user_id))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "✨ تم حفظ الإعدادات بنجاح وانتقال للنشر!")
    show_channel_selection_menu(call.message.chat.id, user_id)

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
    bot.reply_to(message, "✅ <i>تم حفظ عنوان البوست بنجاح!</i>", parse_mode="HTML")
    ask_duration_wizard(message)

@bot.callback_query_handler(func=lambda call: call.data == "set_display_mode")
def callback_set_display_mode(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        create_colored_btn("📺 عرض القائمة بالقناة", callback_data="w_show_1", style="success"),
        create_colored_btn("🔒 إرسال الكشف للخاص فقط", callback_data="w_show_0", style="primary")
    )
    bot.send_message(call.message.chat.id, "👁️ <i>اختر طريقة عرض الكشف:</i>", parse_mode="HTML", reply_markup=markup)

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
    bot.send_document(call.message.chat.id, bytes_io, caption=f"📄 <b>كشف الحضور لبوست:</b>\n<code>{title}</code>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_prompt(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "للمشرف فقط ⛔", show_alert=True)
        return
    user_states[ADMIN_ID] = "waiting_broadcast_msg"
    bot.answer_callback_query(call.id)
    bot.send_message(ADMIN_ID, "📢 <i>أرسل الآن نص الرسالة الجماعية (Broadcast):</i>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_send_weekly_report")
def send_weekly_report_manual(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "للمشرف فقط ⛔", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    send_weekly_report_to_admin()
    bot.send_message(ADMIN_ID, "📊 <b>تم إرسال التقرير الأسبوعي التحليلي الشامل بنجاح!</b>", parse_mode="HTML")

def send_weekly_report_to_admin():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_profiles")
    total_users = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM polls")
    total_polls = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM questions")
    total_q = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(count) FROM polls")
    total_attendance = cursor.fetchone()[0] or 0
    conn.close()
    
    report_text = (
        f"📊 <b>التقرير الأسبوعي الآلي لأداء البوت والقنوات:</b>\n\n"
        f"<blockquote>• <b>إجمالي المستخدمين المسجلين:</b> <code>{total_users}</code>\n"
        f"• <b>إجمالي بوستات الحضور المنشورة:</b> <code>{total_polls}</code>\n"
        f"• <b>إجمالي الأسئلة التفاعلية المطروحة:</b> <code>{total_q}</code>\n"
        f"• <b>إجمالي عمليات الحضور المسجلة:</b> <code>{total_attendance}</code> تفاعل\n\n"
        f"💡 <i>الوضع التشغيلي مستقر تماماً، وتعمل أنظمة الجدولة والأوسمة بكفاءة عالية.</i></blockquote>"
    )
    try:
        bot.send_message(ADMIN_ID, report_text, parse_mode="HTML")
    except Exception as e:
        print(f"Error sending weekly report: {e}")

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
    status_msg = bot.reply_to(message, "🚀 <i>جاري بدء إرسال الرسالة الجماعية..</i>", parse_mode="HTML")
    for (uid,) in users:
        try:
            bot.send_message(uid, f"📢 <b>تنبيه هام من الإدارة:</b>\n\n<blockquote>{broadcast_text}</blockquote>", parse_mode="HTML")
            success_count += 1
        except Exception:
            fail_count += 1
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=f"✅ <b>تم الانتهاء من الإرسال الجماعي بنجاح!</b>\n\n<blockquote>• تم بنجاح: <code>{success_count}</code>\n• فشل: <code>{fail_count}</code></blockquote>",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == "waiting_support_msg")
def forward_support_message(message):
    user_id = message.from_user.id
    user_states.pop(user_id, None)
    support_forward = (
        f"📩 <b>رسالة دعم فني جديدة:</b>\n\n"
        f"<blockquote>• الاسم: {message.from_user.first_name}\n"
        f"• الأيدي: <code>{user_id}</code>\n"
        f"• المعرف: @{message.from_user.username if message.from_user.username else 'لا يوجد'}</blockquote>\n\n"
        f"💬 <b>النص:</b>\n<blockquote>{message.text}</blockquote>"
    )
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(create_colored_btn("💬 الرد على المستخدم", callback_data=f"reply_{user_id}", style="primary"))
    try:
        bot.send_message(ADMIN_ID, support_forward, parse_mode="HTML", reply_markup=admin_markup)
        bot.reply_to(message, "✅ <i>تم إرسال رسالتك بنجاح إلى الإدارة!</i>", parse_mode="HTML")
    except Exception:
        bot.reply_to(message, "❌ حدث خطأ أثناء إرسال الرسالة.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("attend_"))
def handle_channel_attendance(call):
    poll_id = call.data.replace("attend_", "")
    user = call.from_user
    current_time = time.time()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    uname_str = f"@{user.username}" if user.username else "لا يوجد"
    cursor.execute("SELECT full_name FROM user_profiles WHERE user_id = ?", (user.id,))
    prof = cursor.fetchone()
    if prof:
        fixed_name = prof[0]
    else:
        fixed_name = user.first_name
        cursor.execute("INSERT INTO user_profiles (user_id, full_name, username) VALUES (?, ?, ?)", (user.id, fixed_name, uname_str))
        conn.commit()

    cursor.execute("SELECT owner_id, count, title, end_time, is_closed, show_in_channel, channel_id, message_id FROM polls WHERE poll_id = ?", (poll_id,))
    poll = cursor.fetchone()
    if not poll:
        bot.answer_callback_query(call.id, "❌ انتهت صلاحية هذا البوست.", show_alert=True)
        conn.close()
        return
        
    owner_id, count, title, end_time, is_closed, show_in_channel, channel_id, message_id = poll
    if is_closed == 1 or (end_time > 0 and current_time > end_time):
        bot.answer_callback_query(call.id, "⌛ عذراً، انتهى وقت تسجيل الحضور لهذا البوست!", show_alert=True)
        conn.close()
        return

    cursor.execute("SELECT count FROM channel_daily_attendance WHERE user_id = ? AND channel_id = ? AND date_str = ?", (user.id, channel_id, today_str))
    att_row = cursor.fetchone()
    att_count = att_row[0] if att_row else 0
    if att_count >= 2:
        bot.answer_callback_query(call.id, "⚠️ لقد وصلت للحد الأقصى لتسجيل الحضور في هذه القناة اليوم (مرتان فقط يومياً).", show_alert=True)
        conn.close()
        return
        
    cursor.execute("SELECT * FROM poll_votes WHERE poll_id = ? AND user_id = ?", (poll_id, user.id))
    if cursor.fetchone():
        bot.answer_callback_query(call.id, "⚠️ لقد قمت بتسجيل حضورك مسبقاً في هذا البوست!", show_alert=True)
        conn.close()
        return
        
    cursor.execute("INSERT INTO channel_daily_attendance (user_id, channel_id, date_str, count) VALUES (?, ?, ?, 1) ON CONFLICT(user_id, channel_id, date_str) DO UPDATE SET count = count + 1", 
                   (user.id, channel_id, today_str))

    new_count = count + 1
    cursor.execute("UPDATE polls SET count = ? WHERE poll_id = ?", (new_count, poll_id))
    cursor.execute("INSERT INTO poll_votes (poll_id, user_id, user_name, username) VALUES (?, ?, ?, ?)", (poll_id, user.id, fixed_name, uname_str))
    cursor.execute("INSERT INTO user_points (user_id, points) VALUES (?, 5) ON CONFLICT(user_id) DO UPDATE SET points = points + 5", (user.id,))
    
    cursor.execute("SELECT points FROM user_points WHERE user_id = ?", (user.id,))
    new_pts = cursor.fetchone()[0]
    b_name, b_icon = get_user_badge(new_pts)
    cursor.execute("INSERT OR REPLACE INTO user_badges (user_id, badge_name, badge_icon) VALUES (?, ?, ?)", (user.id, b_name, b_icon))

    cursor.execute("SELECT user_name FROM poll_votes WHERE poll_id = ?", (poll_id,))
    all_voters = cursor.fetchall()
    conn.commit()
    conn.close()
    
    owner_notification = (
        f"🔔 <b>تسجيل حضور جديد في بوستك!</b>\n\n"
        f"<blockquote>• البوست: {title}\n"
        f"• المسجل: {fixed_name}\n"
        f"• المعرف: <code>{uname_str}</code>\n"
        f"• الأيدي: <code>{user.id}</code></blockquote>"
    )
    try:
        bot.send_message(owner_id, owner_notification, parse_mode="HTML")
    except Exception:
        pass 
        
    try:
        new_keyboard = types.InlineKeyboardMarkup()
        new_keyboard.add(create_colored_btn(f"✅ تسجيل الحضور [{new_count}]", callback_data=f"attend_{poll_id}", style="success"))
        voters_list_str = ""
        if show_in_channel == 1:
            if all_voters:
                voters_lines = [f"{i+1}. {html.escape(v[0])}" for i, v in enumerate(all_voters)]
                voters_list_str = "\n".join(voters_lines)
            else:
                voters_list_str = "لا توجد تسجيلات حتى الآن."

        updated_text = f"<b>📢 {html.escape(title)}</b>\n\n<i>اضغط على الزر الملون أدناه لتسجيل حضورك الرسمي فوراً:</i>"
        if show_in_channel == 1:
            updated_text += f"\n\n<blockquote expandable><b>👥 قائمة الحضور المسجلين ({new_count}):</b>\n{voters_list_str}</blockquote>"

        bot.edit_message_text(
            chat_id=channel_id,
            message_id=message_id,
            text=updated_text,
            parse_mode="HTML",
            reply_markup=new_keyboard
        )
    except Exception as e:
        print(f"Error editing message directly: {e}")
        
    bot.answer_callback_query(call.id, f"✨ تم تسجيل حضورك بنجاح يا {fixed_name} وحصلت على 5 نقاط!\n🏅 الوسام: {b_icon} {b_name}", show_alert=True)

def background_scheduler_loop():
    while True:
        try:
            current_t = time.time()
            conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT sched_id, user_id, channel_id, title FROM scheduled_posts WHERE run_time <= ?", (current_t,))
            due_posts = cursor.fetchall()
            
            for sched_id, user_id, channel_id, title in due_posts:
                try:
                    poll_id = f"poll_sched_{user_id}_{int(time.time())}"
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(create_colored_btn("✅ تسجيل الحضور [0]", callback_data=f"attend_{poll_id}", style="success"))
                    msg_content = f"<b>📢 {html.escape(title)}</b>\n\n<i>(بوست مجدول تلقائياً) - اضغط على الزر أدناه لتسجيل حضورك:</i>"
                    
                    sent_msg = bot.send_message(channel_id, msg_content, parse_mode="HTML", reply_markup=keyboard)
                    cursor.execute("INSERT OR REPLACE INTO polls (poll_id, owner_id, count, title, end_time, is_closed, show_in_channel, channel_id, message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                   (poll_id, user_id, 0, title, 0, 0, 1, channel_id, sent_msg.message_id))
                except Exception as ex:
                    print(f"Error publishing scheduled post: {ex}")
                
                cursor.execute("DELETE FROM scheduled_posts WHERE sched_id = ?", (sched_id,))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Background worker error: {e}")
        time.sleep(60)

threading.Thread(target=background_scheduler_loop, daemon=True).start()

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
    return "Bot is running perfectly with advanced analytics, badges, scheduling and speed races!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
