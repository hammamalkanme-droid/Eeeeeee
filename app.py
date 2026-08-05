import telebot
from telebot import types
from flask import Flask, request
import sqlite3

TOKEN = "8682109455:AAHPGbqvIDjQtulfek5S1ujR-53CzrSthKs"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# 🔧 تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect('roulette_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            title TEXT,
            custom_message TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            owner_id INTEGER,
            count INTEGER,
            title TEXT
        )
    ''')
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
        "<blockquote>✨ البوت الآن يعمل عبر Webhook بدون مشاكل تضارب!</blockquote>\n\n"
        f"📊 <b>عدد زوار بوستاتك:</b> {total_visits}\n\n"
        "<b>اختر من القائمة أدناه:</b>"
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

# 🖥️ إعداد Webhook
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types
