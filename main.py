import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG (ဒီနေရာ ၃ ခုကို မင်းရဲ့ အချက်အလက်နဲ့ ပြင်ပါ) =================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_CHAT_ID = "YOUR_CHAT_ID" # @htet7701 ရဲ့ Chat ID နံပါတ် (ဂဏန်းသီးသန့်)
WEB_URL = "https://your-app-name.onrender.com" # Render တင်ပြီးမှ ရလာတဲ့ Link ကို လာထည့်ရန်

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

# Database တည်ဆောက်ခြင်း
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (phone TEXT PRIMARY KEY, password TEXT, balance INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# Server အလုပ်လုပ်မလုပ် စမ်းသပ်ရန် Home Route
@app.route('/', methods=['GET'])
def index():
    return "Telecom Reseller Server is Running 24/7!", 200

# ၁။ Login နှင့် Register API
@app.route('/auth', methods=['POST'])
def auth():
    data = request.json
    mode = data.get('mode')
    phone = data.get('phone')
    password = data.get('password')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if mode == 'register':
        c.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "msg": "ဤဖုန်းနံပါတ်ဖြင့် အကောင့်ရှိပြီးသားဖြစ်ပါသည်။"})
        c.execute("INSERT INTO users VALUES (?, ?, 0)", (phone, password))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "msg": "အကောင့်သစ်ဖွင့်ခြင်း အောင်မြင်ပါသည်။"})

    elif mode == 'login':
        c.execute("SELECT balance FROM users WHERE phone = ? AND password = ?", (phone, password))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify({"status": "success", "balance": row[0]})
        return jsonify({"status": "error", "msg": "ဖုန်းနံပါတ် သို့မဟုတ် Password မှားယွင်းနေပါသည်။"})

# ၂။ လက်ကျန်ငွေ စစ်ဆေးရန် API
@app.route('/balance/<phone>', methods=['GET'])
def get_balance(phone):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE phone = ?", (phone,))
    row = c.fetchone()
    conn.close()
    return jsonify({"balance": row[0] if row else 0})

# ၃။ ငွေဖြည့်ပြေစာ Upload တင်သည့် API
@app.route('/upload_receipt', methods=['POST'])
def upload_receipt():
    user_phone = request.form.get('user_phone')
    amount = int(request.form.get('amount'))
    method = request.form.get('method')
    receipt_img = request.files['receipt']

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ အတည်ပြုပါ (Confirm)", callback_data=f"confirm_{user_phone}_{amount}"),
        InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data=f"reject_{user_phone}")
    )

    caption = (
        f"🔔 **ငွေဖြည့်သွင်းမှု အသစ်**\n\n"
        f"👤 **အကောင့် (ဖုန်း):** `{user_phone}`\n"
        f"💳 **Payment:** {method}\n"
        f"💰 **ပမာဏ:** {amount:,} Ks"
    )

    bot.send_photo(ADMIN_CHAT_ID, receipt_img, caption=caption, parse_mode="Markdown", reply_markup=markup)
    return jsonify({"status": "success", "msg": "ပြေစာပို့ပြီးပါပြီ။ Admin အတည်ပြုချက် စောင့်ဆိုင်းပါ။"})

# ၄။ Data / Plan ဝယ်ယူသည့် API
@app.route('/buy_package', methods=['POST'])
def buy_package():
    data = request.json
    user_phone = data.get('user_phone')
    target_phone = data.get('target_phone')
    pkg_name = data.get('pkg_name')
    price = int(data.get('price'))
    provider = data.get('provider')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE phone = ?", (user_phone,))
    row = c.fetchone()

    if not row or row[0] < price:
        conn.close()
        return jsonify({"status": "error", "type": "low_balance", "msg": "သင့်အကောင့်ထဲတွင် လက်ကျန်ငွေ မလုံလောက်ပါ။"})

    # Auto ဝယ်မည့် Agent အကောင့်ထဲ ပိုက်ဆံလောက်မလောက် စစ်ဆေးခြင်း
    agent_balance_ok = True # False ပြောင်းပါက ဝယ်သူဘက်တွင် System Error ပြမည်

    if not agent_balance_ok:
        conn.close()
        return jsonify({"status": "error", "type": "system_error"})

    # ဝယ်သူအကောင့်မှ ငွေဖြတ်ခြင်း
    c.execute("UPDATE users SET balance = balance - ? WHERE phone = ?", (price, user_phone))
    conn.commit()
    conn.close()

    # Admin ဆီသို့ အော်ဒါဝင်ကြောင်း အသိပေးစာပို့ခြင်း
    order_msg = (
        f"📦 **Package အော်ဒါအသစ် ဝင်ပါသည်**\n\n"
        f"👤 ဝယ်သူအကောင့်: `{user_phone}`\n"
        f"📱 ထည့်သွင်းမည့်ဖုန်း: `{target_phone}`\n"
        f"🎁 Package: {pkg_name}\n"
        f"💵 ကျသင့်ငွေ: {price:,} Ks\n"
        f"⚙️ စနစ်: {provider}"
    )
    bot.send_message(ADMIN_CHAT_ID, order_msg, parse_mode="Markdown")

    return jsonify({"status": "success", "msg": "ဝယ်ယူမှု အောင်မြင်ပါသည်။"})

# ၅။ Telegram Webhook (Confirm ခလုတ်နှိပ်လျှင် အလုပ်လုပ်မည့်အပိုင်း)
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    data = call.data.split('_')
    action = data[0]
    user_phone = data[1]

    if action == "confirm":
        amount = int(data[2])
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE phone = ?", (amount, user_phone))
        conn.commit()
        conn.close()

        bot.edit_message_caption(
            caption=call.message.caption + f"\n\n✅ **အတည်ပြုပြီး ({amount:,} Ks ထည့်ပေးပြီးပါပြီ)**",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    elif action == "reject":
        bot.edit_message_caption(
            caption=call.message.caption + "\n\n❌ **ငြင်းပယ်လိုက်ပါသည်**",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

@app.route('/set_webhook')
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEB_URL}/{BOT_TOKEN}")
    return "Webhook ချိတ်ဆက်မှု အောင်မြင်ပါပြီ!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
