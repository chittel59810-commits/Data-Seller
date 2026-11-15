import os
import time
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG (ဒီနေရာ ၂ ခုမှာ မင်းရဲ့ Token နဲ့ ID ပြန်ထည့်ပါ) =================
BOT_TOKEN = "9232024866:AAGdO3i-s20H16KkLifls500wVmWb5AK_ZA"
ADMIN_CHAT_ID = "7102568821"

FIREBASE_URL = "https://dataseller-e4c0e-default-rtdb.firebaseio.com"
WEB_URL = "https://data-seller.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

def get_mm_time():
    return (datetime.utcnow() + timedelta(hours=6, minutes=30)).strftime("%d/%m/%Y %I:%M %p")

def get_user(phone):
    res = requests.get(f"{FIREBASE_URL}/users/{phone}.json")
    if res.status_code == 200 and res.json():
        return res.json()
    return None

def save_user(phone, data):
    requests.patch(f"{FIREBASE_URL}/users/{phone}.json", json=data)

def add_history(phone, item_id, record):
    requests.patch(f"{FIREBASE_URL}/history/{phone}/{item_id}.json", json=record)

def get_history(phone):
    res = requests.get(f"{FIREBASE_URL}/history/{phone}.json")
    if res.status_code == 200 and res.json():
        data = res.json()
        items = list(data.values())
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return items[:15] # နောက်ဆုံး ၁၅ ခု ပြသမည်
    return []

@app.route('/', methods=['GET'])
def index():
    return "Telecom Reseller Server V2 is Running 24/7!", 200

# ၁။ Login နှင့် Register API
@app.route('/auth', methods=['POST'])
def auth():
    data = request.json
    mode = data.get('mode')
    phone = data.get('phone')
    password = data.get('password')

    user = get_user(phone)

    if mode == 'register':
        if user:
            return jsonify({"status": "error", "msg": "ဤဖုန်းနံပါတ်ဖြင့် အကောင့်ရှိပြီးသားဖြစ်ပါသည်။"})
        save_user(phone, {"password": password, "balance": 0})
        return jsonify({"status": "success", "msg": "အကောင့်သစ်ဖွင့်ခြင်း အောင်မြင်ပါသည်။"})

    elif mode == 'login':
        if user and str(user.get("password")) == str(password):
            return jsonify({"status": "success", "balance": user.get("balance", 0)})
        return jsonify({"status": "error", "msg": "ဖုန်းနံပါတ် သို့မဟုတ် Password မှားယွင်းနေပါသည်။"})

# ၂။ လက်ကျန်ငွေ နှင့် History စစ်ဆေးရန် API
@app.route('/user_data/<phone>', methods=['GET'])
def user_data(phone):
    user = get_user(phone)
    bal = user.get("balance", 0) if user else 0
    hist = get_history(phone)
    return jsonify({"balance": bal, "history": hist})

# ၃။ ငွေဖြည့်ပြေစာ Upload တင်သည့် API (ပြေစာအတု/အဟောင်း စစ်ဆေးသည့်စနစ် ပါဝင်သည်)
@app.route('/upload_receipt', methods=['POST'])
def upload_receipt():
    user_phone = request.form.get('user_phone')
    amount = int(request.form.get('amount'))
    method = request.form.get('method')
    tid = request.form.get('tid', '').strip()
    receipt_img = request.files['receipt']

    if not tid or len(tid) < 4:
        return jsonify({"status": "error", "msg": "ပြေစာပေါ်မှ လုပ်ငန်းစဉ်အမှတ် (နောက်ဆုံး ၆ လုံး) မှန်ကန်စွာ ထည့်ပါ။"})

    # ဤ Transaction ID သုံးပြီးသားလား စစ်ဆေးခြင်း
    tid_check = requests.get(f"{FIREBASE_URL}/used_tids/{tid}.json").json()
    if tid_check:
        return jsonify({"status": "error", "msg": "⚠️ ဤပြေစာ (လုပ်ငန်းစဉ်အမှတ်) ကို အသုံးပြုပြီးသား ဖြစ်နေပါသည်! ပြေစာအဟောင်း ပြန်တင်၍မရပါ။"})

    # Transaction ID ကို မှတ်သားထားခြင်း
    requests.put(f"{FIREBASE_URL}/used_tids/{tid}.json", json={"user": user_phone, "amount": amount, "status": "pending"})

    # User History ထဲတွင် စောင့်ဆိုင်းဆဲ (Pending) အဖြစ် ထည့်သွင်းခြင်း
    add_history(user_phone, f"topup_{tid}", {
        "type": "topup",
        "title": f"ငွေသွင်း ({method} - #{tid})",
        "amount": amount,
        "status": "⏳ စစ်ဆေးဆဲ",
        "time": get_mm_time(),
        "timestamp": int(time.time())
    })

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ အတည်ပြုပါ (Confirm)", callback_data=f"confirm_{user_phone}_{amount}_{tid}"),
        InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data=f"reject_{user_phone}_{tid}")
    )

    caption = (
        f"🔔 **ငွေဖြည့်သွင်းမှု အသစ်**\n\n"
        f"👤 **အကောင့်:** `{user_phone}`\n"
        f"💳 **Payment:** {method}\n"
        f"🔢 **နောက်ဆုံး ၆ လုံး:** `{tid}`\n"
        f"💰 **ပမာဏ:** {amount:,} Ks"
    )

    bot.send_photo(ADMIN_CHAT_ID, receipt_img, caption=caption, parse_mode="Markdown", reply_markup=markup)
    return jsonify({"status": "success", "msg": "ပြေစာပို့ပြီးပါပြီ။ Admin အတည်ပြုပြီးပါက အကောင့်ထဲ အလိုလို ငွေဝင်လာပါမည်။"})

# ၄။ Data / Plan ဝယ်ယူသည့် API
@app.route('/buy_package', methods=['POST'])
def buy_package():
    data = request.json
    user_phone = data.get('user_phone')
    target_phone = data.get('target_phone')
    pkg_name = data.get('pkg_name')
    price = int(data.get('price'))
    provider = data.get('provider')

    user = get_user(user_phone)
    current_bal = user.get("balance", 0) if user else 0

    if current_bal < price:
        return jsonify({"status": "error", "type": "low_balance", "msg": "သင့်အကောင့်ထဲတွင် လက်ကျန်ငွေ မလုံလောက်ပါ။"})

    agent_balance_ok = True
    if not agent_balance_ok:
        return jsonify({"status": "error", "type": "system_error"})

    new_bal = current_bal - price
    save_user(user_phone, {"balance": new_bal})

    order_id = f"ord_{int(time.time())}"
    add_history(user_phone, order_id, {
        "type": "buy",
        "title": f"{pkg_name} -> {target_phone}",
        "amount": price,
        "status": "✅ ဝယ်ယူပြီး",
        "time": get_mm_time(),
        "timestamp": int(time.time())
    })

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

# ၅။ Telegram Webhook
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        data = call.data.split('_')
        action = data[0]
        user_phone = data[1]

        if action == "confirm":
            amount = int(data[2])
            tid = data[3] if len(data) > 3 else "000"

            user = get_user(user_phone)
            current_bal = user.get("balance", 0) if user else 0
            save_user(user_phone, {"balance": current_bal + amount})

            add_history(user_phone, f"topup_{tid}", {"status": "✅ ငွေဝင်ပြီး"})

            bot.answer_callback_query(call.id, "✅ ငွေထည့်ပေးပြီးပါပြီ!")
            new_caption = f"{call.message.caption}\n\n✅ အတည်ပြုပြီး ({amount:,} Ks ထည့်ပေးပြီးပါပြီ)"
            bot.edit_message_caption(caption=new_caption, chat_id=call.message.chat.id, message_id=call.message.message_id)

        elif action == "reject":
            tid = data[2] if len(data) > 2 else "000"
            add_history(user_phone, f"topup_{tid}", {"status": "❌ ပယ်ဖျက်ခံရသည်"})

            bot.answer_callback_query(call.id, "❌ ငြင်းပယ်လိုက်ပါပြီ!")
            new_caption = f"{call.message.caption}\n\n❌ ငြင်းပယ်လိုက်ပါသည်"
            bot.edit_message_caption(caption=new_caption, chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)

@app.route('/set_webhook')
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEB_URL}/webhook")
    return "Webhook ချိတ်ဆက်မှု အောင်မြင်ပါပြီ!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
