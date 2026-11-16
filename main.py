import os
import time
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG (မင်းရဲ့ Token နဲ့ Chat ID ဒီမှာ သေချာပြန်ထည့်ပါ) =================
BOT_TOKEN = "9232024866:AAGdO3i-s20H16KkLifls500wVmWb5AK_ZA"
ADMIN_CHAT_ID = "7102568821"

FIREBASE_URL = "https://dataseller-e4c0e-default-rtdb.firebaseio.com"
WEB_URL = "https://data-seller.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

# မူလ Package နှင့် ဈေးနှုန်းများ
DEFAULT_PACKAGES = {
    "m1": {"cat": "mytel_mb", "name": "1GB (3 Days)", "price": 930, "provider": "Mytel Agent App", "order": 1},
    "m2": {"cat": "mytel_min", "name": "100 Min (30 Days)", "price": 800, "provider": "Mytel App", "order": 2},
    "a1": {"cat": "atom_mb", "name": "870MB / 1GB (3D/30D)", "price": 1000, "provider": "Eagle App", "order": 3},
    "mp1": {"cat": "mytel_plan", "name": "15GB + 8000 Min", "price": 13800, "provider": "Mytel MBCCS App", "order": 4},
    "mp2": {"cat": "mytel_plan", "name": "40GB + 250 Min", "price": 18000, "provider": "Mytel MBCCS App", "order": 5},
    "mp3": {"cat": "mytel_plan", "name": "120GB Plan", "price": 27500, "provider": "Mytel Agent App", "order": 6},
    "ap1": {"cat": "atom_plan", "name": "24GB + 8000 Min", "price": 13800, "provider": "Eagle App", "order": 7},
    "ap2": {"cat": "atom_plan", "name": "135GB Plan", "price": 28000, "provider": "Eagle App", "order": 8}
}

VALID_CATEGORIES = ["mytel_mb", "mytel_min", "atom_mb", "mytel_plan", "atom_plan"]

APP_MAP = {
    "agent": "Mytel Agent App",
    "myid": "Mytel App",
    "mbccs": "Mytel MBCCS App",
    "eagle": "Eagle App"
}

def get_mm_time():
    return (datetime.utcnow() + timedelta(hours=6, minutes=30)).strftime("%d/%m/%Y %I:%M %p")

def get_user(phone):
    res = requests.get(f"{FIREBASE_URL}/users/{phone}.json")
    if res.status_code == 200 and res.json():
        return res.json()
    return None

def save_user(phone, data):
    requests.patch(f"{FIREBASE_URL}/users/{phone}.json", json=data)

def get_all_packages():
    res = requests.get(f"{FIREBASE_URL}/packages.json")
    if res.status_code == 200 and res.json():
        return res.json()
    requests.put(f"{FIREBASE_URL}/packages.json", json=DEFAULT_PACKAGES)
    return DEFAULT_PACKAGES

def add_history(phone, item_id, record):
    requests.patch(f"{FIREBASE_URL}/history/{phone}/{item_id}.json", json=record)

def get_history(phone):
    res = requests.get(f"{FIREBASE_URL}/history/{phone}.json")
    if res.status_code == 200 and res.json():
        data = res.json()
        items = list(data.values())
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return items[:15]
    return []

@app.route('/', methods=['GET'])
def index():
    return "Telecom Reseller Server V7 (Full Admin Control) is Running 24/7!", 200

@app.route('/packages', methods=['GET'])
def fetch_packages():
    pkgs = get_all_packages()
    grouped = {"mytel_mb": [], "mytel_min": [], "atom_mb": [], "mytel_plan": [], "atom_plan": []}
    sorted_items = sorted(pkgs.values(), key=lambda x: x.get('order', 99))
    for item in sorted_items:
        cat = item.get("cat")
        if cat in grouped:
            grouped[cat].append(item)
    return jsonify(grouped)

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

@app.route('/user_data/<phone>', methods=['GET'])
def user_data(phone):
    user = get_user(phone)
    bal = user.get("balance", 0) if user else 0
    hist = get_history(phone)
    return jsonify({"balance": bal, "history": hist})

@app.route('/upload_receipt', methods=['POST'])
def upload_receipt():
    user_phone = request.form.get('user_phone')
    amount = int(request.form.get('amount'))
    method = request.form.get('method')
    tid = request.form.get('tid', '').strip()
    receipt_img = request.files['receipt']

    if not tid or len(tid) < 4:
        return jsonify({"status": "error", "msg": "ပြေစာပေါ်မှ လုပ်ငန်းစဉ်အမှတ် (နောက်ဆုံး ၆ လုံး) မှန်ကန်စွာ ထည့်ပါ။"})

    tid_check = requests.get(f"{FIREBASE_URL}/used_tids/{tid}.json").json()
    if tid_check:
        return jsonify({"status": "error", "msg": "⚠️ ဤပြေစာ (လုပ်ငန်းစဉ်အမှတ်) ကို အသုံးပြုပြီးသား ဖြစ်နေပါသည်!"})

    requests.put(f"{FIREBASE_URL}/used_tids/{tid}.json", json={"user": user_phone, "amount": amount, "status": "pending"})

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
        f"🔔 ငွေဖြည့်သွင်းမှု အသစ်\n\n"
        f"👤 အကောင့်: {user_phone}\n"
        f"💳 Payment: {method}\n"
        f"🔢 နောက်ဆုံး ၆ လုံး: {tid}\n"
        f"💰 ပမာဏ: {amount:,} Ks"
    )

    bot.send_photo(ADMIN_CHAT_ID, receipt_img, caption=caption, reply_markup=markup)
    return jsonify({"status": "success", "msg": "ပြေစာပို့ပြီးပါပြီ။ Admin အတည်ပြုပြီးပါက အကောင့်ထဲ ငွေဝင်လာပါမည်။"})

@app.route('/buy_package', methods=['POST'])
def buy_package():
    data = request.json
    user_phone = data.get('user_phone')
    target_phone = data.get('target_phone', '').strip()
    pkg_name = data.get('pkg_name')
    price = int(data.get('price'))
    provider = data.get('provider')

    if "Mytel" in provider and not target_phone.startswith("096"):
        return jsonify({"status": "error", "msg": "⚠️ Mytel Package အတွက် 096 ဖြင့်စသော Mytel နံပါတ်သာ ထည့်သွင်းပါ။"})
    if "Eagle" in provider and not target_phone.startswith("097"):
        return jsonify({"status": "error", "msg": "⚠️ Atom Package အတွက် 097 ဖြင့်စသော Atom နံပါတ်သာ ထည့်သွင်းပါ။"})

    user = get_user(user_phone)
    current_bal = user.get("balance", 0) if user else 0

    if current_bal < price:
        return jsonify({"status": "error", "type": "low_balance", "msg": "သင့်အကောင့်ထဲတွင် လက်ကျန်ငွေ မလုံလောက်ပါ။"})

    new_bal = current_bal - price
    save_user(user_phone, {"balance": new_bal})

    ts = int(time.time())
    order_id = f"ord_{ts}"
    add_history(user_phone, order_id, {
        "type": "buy",
        "title": f"{pkg_name} -> {target_phone}",
        "amount": price,
        "status": "✅ ဝယ်ယူပြီး",
        "time": get_mm_time(),
        "timestamp": ts
    })

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔄 ငွေပြန်အမ်းမည် (Refund)", callback_data=f"refund_{user_phone}_{price}_{ts}")
    )

    order_msg = (
        f"📦 Package အော်ဒါအသစ် ဝင်ပါသည်\n\n"
        f"👤 ဝယ်သူအကောင့်: {user_phone}\n"
        f"📱 ထည့်သွင်းမည့်ဖုန်း: {target_phone}\n"
        f"🎁 Package: {pkg_name}\n"
        f"💵 ကျသင့်ငွေ: {price:,} Ks\n"
        f"⚙️ စနစ်: {provider}"
    )
    bot.send_message(ADMIN_CHAT_ID, order_msg, reply_markup=markup)

    return jsonify({"status": "success", "msg": "ဝယ်ယူမှု အောင်မြင်ပါသည်။"})

# ================= TELEGRAM ADMIN COMMANDS =================
@bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_all_commands(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return

    parts = message.text.strip().split()
    cmd = parts[0].lower()

    if cmd in ['/start', '/help']:
        help_text = (
            "🛠 Admin ထိန်းချုပ်ရေး လမ်းညွှန်\n\n"
            "1️⃣ အကောင့်နှင့် Password စစ်ရန်:\n"
            "/check 09xxxxxxxxx\n\n"
            "2️⃣ Password အသစ်ပြောင်းပေးရန်:\n"
            "/setpass 09xxxxxxxxx စကားဝှက်အသစ်\n\n"
            "3️⃣ Package စာရင်းနှင့် ကုဒ်များကြည့်ရန်:\n"
            "/prices\n\n"
            "4️⃣ Package ဈေးနှုန်း ပြောင်းရန်:\n"
            "/setprice ကုဒ် ဈေးနှုန်းအသစ်\n"
            "(ဥပမာ - /setprice m1 950)\n\n"
            "5️⃣ Package အသစ် ထပ်တိုးရန်:\n"
            "/addpkg ကုဒ် အမျိုးအစား Appအမည် ဈေးနှုန်း နာမည်\n"
            "(ဥပမာ - /addpkg m3 mytel_mb agent 1800 2GB 5Days)\n\n"
            "6️⃣ ဝယ်မည့် App ပြောင်းရန်:\n"
            "/setapp ကုဒ် Appအမည်\n"
            "(ဥပမာ - /setapp m1 myid)\n\n"
            "7️⃣ Package ပြန်ဖျက်ရန်:\n"
            "/delpkg ကုဒ်\n"
            "(ဥပမာ - /delpkg m3)\n\n"
            "📌 App အမည် အတိုကောက်များ:\n"
            "agent = Mytel Agent App\n"
            "myid = Mytel App (MyID)\n"
            "mbccs = Mytel MBCCS App\n"
            "eagle = Eagle App"
        )
        bot.reply_to(message, help_text)

    elif cmd == '/check':
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ ဖုန်းနံပါတ် ထည့်ရိုက်ပါ။ ဥပမာ - /check 09688022655")
            return
        phone = parts[1]
        user = get_user(phone)
        if not user:
            bot.reply_to(message, "❌ ဤဖုန်းနံပါတ်ဖြင့် အကောင့်မရှိပါ။")
        else:
            msg = (
                f"👤 အကောင့် အချက်အလက်\n\n"
                f"📱 ဖုန်းနံပါတ်: {phone}\n"
                f"🔑 Password: {user.get('password')}\n"
                f"💰 လက်ကျန်ငွေ: {user.get('balance', 0):,} Ks"
            )
            bot.reply_to(message, msg)

    elif cmd == '/setpass':
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ ဥပမာ - /setpass 09688022655 123456 ဟု ရိုက်ပါ။")
            return
        phone, new_pass = parts[1], parts[2]
        user = get_user(phone)
        if not user:
            bot.reply_to(message, "❌ ဤဖုန်းနံပါတ်ဖြင့် အကောင့်မရှိပါ။")
        else:
            save_user(phone, {"password": new_pass})
            bot.reply_to(message, f"✅ {phone} ၏ Password ကို {new_pass} သို့ ပြောင်းလဲပြီးပါပြီ။")

    elif cmd in ['/prices', '/price']:
        pkgs = get_all_packages()
        lines = ["📋 လက်ရှိ Package စာရင်းနှင့် ကုဒ်များ\n"]
        for code, info in sorted(pkgs.items(), key=lambda x: x[1].get('order', 99)):
            lines.append(f"🔹 {code} ({info['cat']})\n   {info['name']} = {info['price']:,} Ks\n   ⚙️ [{info.get('provider', 'App')}]")
        lines.append("\n💡 ဈေးပြောင်းရန် - /setprice m1 950")
        lines.append("⚙️ App ပြောင်းရန် - /setapp m1 myid")
        lines.append("➕ အသစ်တိုးရန် - /addpkg m3 mytel_mb agent 1800 2GB (5D)")
        lines.append("🗑 ပြန်ဖျက်ရန် - /delpkg m3")
        bot.reply_to(message, "\n".join(lines))

    elif cmd == '/setprice':
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ ဥပမာ - /setprice m1 950 ဟု ရိုက်ပါ။")
            return
        code = parts[1].lower()
        try:
            new_price = int(parts[2])
        except ValueError:
            bot.reply_to(message, "⚠️ ဈေးနှုန်းကို ဂဏန်းဖြင့်သာ ရိုက်ပါ။")
            return

        pkgs = get_all_packages()
        if code not in pkgs:
            bot.reply_to(message, "❌ ကုဒ်မှားနေပါသည်။ /prices ဟုရိုက်ပြီး ကုဒ်များကို စစ်ဆေးပါ။")
            return

        requests.patch(f"{FIREBASE_URL}/packages/{code}.json", json={"price": new_price})
        bot.reply_to(message, f"✅ {pkgs[code]['name']} ဈေးနှုန်းကို {new_price:,} Ks သို့ ပြောင်းလဲပြီးပါပြီ!")

    elif cmd == '/addpkg':
        raw_parts = message.text.strip().split(maxsplit=5)
        if len(raw_parts) < 6:
            msg = (
                "⚠️ ပုံစံမှားနေပါသည်။ အောက်ပါအတိုင်း ရိုက်ပါ -\n"
                "/addpkg ကုဒ် အမျိုးအစား Appအမည် ဈေးနှုန်း နာမည်\n\n"
                "🔹 အမျိုးအစား (၅) ခု:\n"
                "mytel_mb, mytel_min, atom_mb, mytel_plan, atom_plan\n\n"
                "🔹 App အမည် (၄) ခု:\n"
                "agent, myid, mbccs, eagle\n\n"
                "ဥပမာ -\n"
                "/addpkg m3 mytel_mb agent 1800 2GB (5 Days)"
            )
            bot.reply_to(message, msg)
            return

        code = raw_parts[1].lower()
        cat = raw_parts[2].lower()
        app_key = raw_parts[3].lower()
        try:
            price = int(raw_parts[4])
        except ValueError:
            bot.reply_to(message, "⚠️ ဈေးနှုန်းနေရာတွင် ဂဏန်းသီးသန့် ရိုက်ပါ။")
            return
        name = raw_parts[5]

        if cat not in VALID_CATEGORIES:
            bot.reply_to(message, "❌ အမျိုးအစား မှားနေပါသည်။ (mytel_mb, mytel_min, atom_mb, mytel_plan, atom_plan ထဲမှ တစ်ခုရွေးပါ)")
            return

        if app_key not in APP_MAP:
            bot.reply_to(message, "❌ App အမည် မှားနေပါသည်။ (agent, myid, mbccs, eagle ထဲမှ တစ်ခုရွေးပါ)")
            return

        provider = APP_MAP[app_key]
        new_item = {
            "cat": cat,
            "name": name,
            "price": price,
            "provider": provider,
            "order": int(time.time())
        }
        requests.put(f"{FIREBASE_URL}/packages/{code}.json", json=new_item)
        bot.reply_to(message, f"✅ Package အသစ် ထပ်တိုးပြီးပါပြီ!\n\n🔹 ကုဒ်: {code}\n📂 အမျိုးအစား: {cat}\n⚙️ ဝယ်မည့် App: {provider}\n🎁 နာမည်: {name}\n💰 ဈေးနှုန်း: {price:,} Ks")

    elif cmd == '/setapp':
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ ဥပမာ - /setapp m1 agent ဟု ရိုက်ပါ။\n(ရွေးနိုင်သော App များ - agent, myid, mbccs, eagle)")
            return
        code = parts[1].lower()
        app_key = parts[2].lower()

        pkgs = get_all_packages()
        if code not in pkgs:
            bot.reply_to(message, "❌ ကုဒ်မှားနေပါသည်။ /prices တွင် စစ်ဆေးပါ။")
            return
        if app_key not in APP_MAP:
            bot.reply_to(message, "❌ App အမည်ကို agent, myid, mbccs, eagle ထဲမှ တစ်ခုရွေးပါ။")
            return

        new_provider = APP_MAP[app_key]
        requests.patch(f"{FIREBASE_URL}/packages/{code}.json", json={"provider": new_provider})
        bot.reply_to(message, f"✅ {pkgs[code]['name']} ({code}) ကို {new_provider} မှ ဝယ်ယူရန် ပြောင်းလဲပြီးပါပြီ!")

    elif cmd == '/delpkg':
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ ဖျက်လိုသော ကုဒ်ကို ထည့်ရိုက်ပါ။ ဥပမာ - /delpkg m3")
            return
        code = parts[1].lower()
        pkgs = get_all_packages()
        if code not in pkgs:
            bot.reply_to(message, "❌ ၎င်းကုဒ်ဖြင့် Package မရှိပါ။ /prices တွင် စစ်ဆေးပါ။")
            return

        pkg_name = pkgs[code].get('name', code)
        requests.delete(f"{FIREBASE_URL}/packages/{code}.json")
        bot.reply_to(message, f"🗑 {pkg_name} ({code}) ကို စာရင်းမှ ဖျက်လိုက်ပါပြီ!")

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print("Webhook Error:", e)
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

        elif action == "refund":
            price = int(data[2])
            ts = data[3]

            user = get_user(user_phone)
            current_bal = user.get("balance", 0) if user else 0
            save_user(user_phone, {"balance": current_bal + price})
            add_history(user_phone, f"ord_{ts}", {"status": "🔄 ငွေပြန်အမ်းပြီး (Refunded)", "type": "topup"})

            bot.answer_callback_query(call.id, "🔄 ဝယ်သူ့အကောင့်ထဲ ငွေပြန်အမ်းပေးပြီးပါပြီ!")
            new_text = f"{call.message.text}\n\n🔄 ငွေပြန်အမ်းပြီး ({price:,} Ks ပြန်ထည့်ပေးပြီးပါပြီ)"
            bot.edit_message_text(text=new_text, chat_id=call.message.chat.id, message_id=call.message.message_id)

    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)

@app.route('/set_webhook')
def set_webhook():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEB_URL}/webhook", drop_pending_updates=True)
    return "Webhook ချိတ်ဆက်မှု အောင်မြင်ပါပြီ!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
