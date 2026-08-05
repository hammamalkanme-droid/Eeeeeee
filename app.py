import telebot
from telebot import types
from datetime import datetime
import pytz

TOKEN = "8843031279:AAHZKUZDKGwczgjLDgufG9TNCqdD1yL1nRY"
# حط الـ ID الخاص بيك هنا (أرقام فقط)، لو ما تعرفاش ابحث في التليجرام عن @userinfobot وانسخ الـ Id
ADMIN_ID = 1250493517 

bot = telebot.TeleBot(TOKEN)

# ذاكرة مؤقتة بسيطة لمنع العضو من تسجيل حضوره مرتين في نفس اليوم لنفس الفترة
attendance_log = set()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # إنشاء أزرار تسجيل الحضور (فترتين كمثال)
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_morning = types.InlineKeyboardButton("☀️ تسجيل حضور (الفترة الصباحية)", callback_data="attend_morning")
    btn_evening = types.InlineKeyboardButton("🌙 تسجيل حضور (الفترة المسائية)", callback_data="attend_evening")
    markup.add(btn_morning, btn_evening)
    
    welcome_text = (
        "أهلاً بك في نظام المتابعة وتسجيل الحضور الخاص بفريق النخبة.\n\n"
        "الرجاء الضغط على الزر المناسب لتسجيل حضورك اليوم:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("attend_"))
def handle_attendance(call):
    # تحديد الفترة بناءً على الزر اللي ضغطه العضو
    period = "الصباحية ☀️" if "morning" in call.data else "المسائية 🌙"
    
    user_name = call.from_user.first_name
    username = f"(@{call.from_user.username})" if call.from_user.username else ""
    user_id = call.from_user.id
    
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
