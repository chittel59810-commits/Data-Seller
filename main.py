import os
import time
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG (Bot ၂ ခုအတွက် Token နှင့် Admin ID များ) =================
DATA_BOT_TOKEN = "9232024866:AAGdO3i-s20H16KkLifls500wVmWb5AK_ZA"
DATA_ADMIN_ID = "7102568821"

MLBB_BOT_TOKEN = "9165666227:AAHh5qF4vDppjxcFmQ4k9vcKABiMXBEAzYw"
MLBB_ADMIN_ID = "7102568821"

FIREBASE_URL = "https://dataseller-e4c0e-default-rtdb.firebaseio.com"
WEB_URL = "https://data-seller-7pfm.onrender.com"

data_bot = telebot.TeleBot(DATA_BOT_TOKEN, threaded=False)
mlbb_bot = telebot.TeleBot(MLBB_BOT_TOKEN, threaded=False)

app = Flask(__name__)
CORS(app)

DEFAULT_PACKAGES = {
    # Mytel Packages
    "mb1": {"cat": "mytel_bill", "name": "1,000 Ks ဖုန်းဘေလ်", "price": 980, "provider": "Mytel Agent App", "order": 1},
    "mn1": {"cat": "mytel_normal", "name": "1GB (3 Days)", "price": 930, "provider": "Mytel Agent App", "order": 2},
    "mn2": {"cat": "mytel_normal", "name": "1GB (1 Month)", "price": 1030, "provider": "Mytel Agent App", "order": 3},
    "mm1": {"cat": "mytel_min", "name": "100 Min Onnet (1 Month)", "price": 850, "provider": "Mytel App", "order": 4},
    "mm2": {"cat": "mytel_min", "name": "41 Min Anynet (10 Days)", "price": 850, "provider": "Mytel App", "order": 5},
    "mm3": {"cat": "mytel_min", "name": "114 Min Anynet (1 Month)", "price": 2400, "provider": "Mytel App", "order": 6},
    "mm4": {"cat": "mytel_min", "name": "69 Min + 69 SMS (7 Days)", "price": 950, "provider": "Mytel App", "order": 7},
    "mm5": {"cat": "mytel_min", "name": "138 Min + 138 SMS (1 Month)", "price": 1900, "provider": "Mytel App", "order": 8},
    "mp1": {"cat": "mytel_plan", "name": "15GB Only (1 Month)", "price": 12000, "provider": "Mytel MBCCS App", "order": 9},
    "mp2": {"cat": "mytel_plan", "name": "15GB + 8000 Min + 5000 SMS (1 Month)", "price": 13900, "provider": "Mytel MBCCS App", "order": 10},
    "mp3": {"cat": "mytel_plan", "name": "40GB + 250 Min + Offnet 25 Min", "price": 18000, "provider": "Mytel MBCCS App", "order": 11},
    "mp4": {"cat": "mytel_plan", "name": "120GB Only", "price": 27500, "provider": "Mytel Agent App", "order": 12},

    # Atom Packages
    "ab1": {"cat": "atom_bill", "name": "1,000 Ks ဖုန်းဘေလ်", "price": 980, "provider": "Eagle App", "order": 13},
    "an1": {"cat": "atom_normal", "name": "870MB (3 Days)", "price": 1000, "provider": "Eagle App", "order": 14},
    "ap1": {"cat": "atom_plan", "name": "24GB + 8000 Min + 5000 SMS", "price": 13900, "provider": "Eagle App", "order": 15},
    "ap2": {"cat": "atom_plan", "name": "135GB Only", "price": 28000, "provider": "Eagle App", "order": 16},
    "apt1": {"cat": "atom_point", "name": "500 Points (7 Days)", "price": 600, "provider": "Eagle App", "order": 17},
    "aotp1": {"cat": "atom_otp", "name": "1.5GB အထက် OTP Data (မကုန်မချင်း သက်တမ်းတိုး)", "price": 1200, "provider": "Eagle App", "order": 18}
}

VALID_CATEGORIES = [
    "mytel_bill", "mytel_normal", "mytel_min", "mytel_plan",
    "atom_bill", "atom_normal", "atom_plan", "atom_point", "atom_otp"
]

APP_MAP = {
    "agent": "Mytel Agent App",
    "myid": "Mytel App",
    "mbccs": "Mytel MBCCS App",
    "eagle": "Eagle App"
}

def get_mm_now():
    return datetime.utcnow() + timedelta(hours=6, minutes=30)

def get_mm_time():
    return get_mm_now().strftime("%d/%m/%Y %I:%M %p")

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
        existing = res.json()
        if "mb1" not in existing:
            requests.put(f"{FIREBASE_URL}/packages.json", json=DEFAULT_PACKAGES)
            return DEFAULT_PACKAGES
        return existing
    requests.put(f"{FIREBASE_URL}/packages.json", json=DEFAULT_PACKAGES)
    return DEFAULT_PACKAGES

def add_history(phone, item_id, record):
    requests.patch(f"{FIREBASE_URL}/history/{phone}/{item_id}.json", json=record)

def get_history(phone, limit=25):
    res = requests.get(f"{FIREBASE_URL}/history/{phone}.json")
    if res.status_code == 200 and res.json():
        data = res.json()
        items = [v for v in data.values() if isinstance(v, dict)]
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return items[:limit]
    return []

# Admin ဘက်မှ User History စစ်ဆေးရန် Helper Function
def format_user_history_for_admin(phone, filter_mode="all"):
    user = get_user(phone)
    if not user:
        return "❌ ဤဖုန်းနံပါတ်ဖြင့် အကောင့်မရှိပါ။"

    bal = user.get("balance", 0)
    items = get_history(phone, limit=50)

    if filter_mode == "topup":
        items = [i for i in items if i.get("type") == "topup" or "ငွေသွင်း" in i.get("title", "")]
        header_title = f"💳 <b>{phone} ၏ ငွေသွင်းမှတ်တမ်း (Top-ups)</b>"
    elif filter_mode == "withdraw":
        items = [i for i in items if "ငွေထုတ်" in i.get("title", "")]
        header_title = f"💸 <b>{phone} ၏ ငွေထုတ်မှတ်တမ်း (Withdrawals)</b>"
    else:
        header_title = f"📜 <b>{phone} ၏ မှတ်တမ်းအားလုံး (History)</b>"

    if not items:
        return f"{header_title}\n💰 လက်ရှိလက်ကျန်ငွေ: <b>{bal:,} Ks</b>\n\n⚠️ မှတ်တမ်း မရှိသေးပါ။"

    lines = [
        header_title,
        f"💰 လက်ရှိလက်ကျန်ငွေ: <b>{bal:,} Ks</b>",
        "--------------------------------"
    ]

    for idx, item in enumerate(items[:25], start=1):
        is_topup = item.get("type") == "topup"
        sign = "+" if is_topup else "-"
        amt = item.get("amount", 0)
        title = item.get("title", "N/A")
        status = item.get("status", "")
        t_str = item.get("time", "အချိန်မသိ")

        lines.append(
            f"{idx}. <b>{title}</b>\n"
            f"   💵 ပမာဏ: <b>{sign}{amt:,} Ks</b> | {status}\n"
            f"   🕒 အချိန်: <code>{t_str}</code>"
        )

    result = "\n".join(lines)
    if len(result) > 4000:
        result = result[:3950] + "\n... (နောက်ဆုံးမှတ်တမ်းများသာ ပြသထားပါသည်)"
    return result

# ================= WEB & OTA UI ROUTES =================
@app.route('/', methods=['GET'])
def index():
    return "Easy Data, Exchange, Withdraw & MLBB Arena Server V13 is Running!", 200

@app.route('/app', methods=['GET'])
def serve_app_ui():
    return send_from_directory('.', 'index.html')

@app.route('/packages', methods=['GET'])
def fetch_packages():
    pkgs = get_all_packages()
    grouped = {cat: [] for cat in VALID_CATEGORIES}
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
    hist = get_history(phone, limit=25)
    return jsonify({"balance": bal, "history": hist})

# ================= 1. WALLET TOPUP (DATA BOT) =================
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
        "title": f"Wallet ငွေသွင်း ({method} - #{tid})",
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
        f"🔔 <b>Wallet ငွေဖြည့်သွင်းမှု အသစ်</b>\n\n"
        f"👤 အကောင့်: <code>{user_phone}</code>\n"
        f"💳 Payment: {method}\n"
        f"🔢 နောက်ဆုံး ၆ လုံး: <code>{tid}</code>\n"
        f"💰 ပမာဏ: <b>{amount:,} Ks</b>\n"
        f"🕒 အချိန်: {get_mm_time()}"
    )

    data_bot.send_photo(DATA_ADMIN_ID, receipt_img, caption=caption, parse_mode="HTML", reply_markup=markup)
    return jsonify({"status": "success", "msg": "ပြေစာပို့ပြီးပါပြီ။ Admin အတည်ပြုပြီးပါက အကောင့်ထဲ ငွေဝင်လာပါမည်။"})

# ================= 2. ငွေချိန်း & MYTELPAY ငွေဖြည့် (DATA BOT) =================
@app.route('/exchange_request', methods=['POST'])
def exchange_request():
    user_phone = request.form.get('user_phone')
    ex_type = request.form.get('ex_type')
    amount = int(request.form.get('amount'))
    recv_phone = request.form.get('recv_phone', '').strip()
    recv_name = request.form.get('recv_name', '').strip()
    tid = request.form.get('tid', '').strip()
    receipt_img = request.files['receipt']

    if not tid or len(tid) < 4:
        return jsonify({"status": "error", "msg": "ပြေစာပေါ်မှ လုပ်ငန်းစဉ်အမှတ် (နောက်ဆုံး ၆ လုံး) မှန်ကန်စွာ ထည့်ပါ။"})

    tid_check = requests.get(f"{FIREBASE_URL}/used_tids/ex_{tid}.json").json()
    if tid_check:
        return jsonify({"status": "error", "msg": "⚠️ ဤပြေစာကို အသုံးပြုပြီးသား ဖြစ်နေပါသည်!"})

    requests.put(f"{FIREBASE_URL}/used_tids/ex_{tid}.json", json={"user": user_phone, "amount": amount})

    ts = int(time.time())
    add_history(user_phone, f"ex_{ts}", {
        "type": "buy",
        "title": f"💱 {ex_type} -> {recv_phone} ({recv_name})",
        "amount": amount,
        "status": "⏳ ငွေချိန်း/လွှဲပေးနေဆဲ",
        "time": get_mm_time(),
        "timestamp": ts
    })

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ လွှဲပြီးပြီ (Done)", callback_data=f"exdone_{user_phone}_{ts}"),
        InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data=f"exrej_{user_phone}_{ts}")
    )

    caption = (
        f"💱 <b>ငွေချိန်း / MytelPay အော်ဒါအသစ်</b>\n\n"
        f"🔄 အမျိုးအစား: <b>{ex_type}</b>\n"
        f"💰 ပမာဏ: <b>{amount:,} Ks</b> (300 Ks အပိုပါ/မပါ စစ်ပါ)\n"
        f"📱 ပြန်လွှဲပေးရမည့် ဖုန်း (နှိပ်၍ Copy ယူပါ):\n"
        f"👉 <code>{recv_phone}</code>\n"
        f"👤 အကောင့်နာမည်: <b>{recv_name}</b>\n"
        f"🔢 ပြေစာ No: <code>{tid}</code>\n"
        f"👤 တင်သူအကောင့်: <code>{user_phone}</code>\n"
        f"🕒 အချိန်: {get_mm_time()}"
    )

    data_bot.send_photo(DATA_ADMIN_ID, receipt_img, caption=caption, parse_mode="HTML", reply_markup=markup)
    return jsonify({"status": "success", "msg": "ပြေစာပို့ပြီးပါပြီ! Admin စစ်ဆေးပြီးပါက လွှဲပေးပါမည်။"})

# ================= 3. WALLET ငွေထုတ်ခြင်း (MLBB BOT) =================
@app.route('/withdraw', methods=['POST'])
def withdraw_money():
    data = request.json
    user_phone = data.get('user_phone')
    amount = int(data.get('amount', 0))
    method = data.get('method')
    recv_phone = data.get('recv_phone', '').strip()
    recv_name = data.get('recv_name', '').strip()

    if amount < 5000:
        return jsonify({"status": "error", "msg": "⚠️ အနည်းဆုံး ၅,၀၀၀ ကျပ် (5,000 Ks) မှသာ ငွေထုတ်ယူနိုင်ပါသည်။"})

    user = get_user(user_phone)
    current_bal = user.get("balance", 0) if user else 0

    if current_bal < amount:
        return jsonify({"status": "error", "msg": f"လက်ကျန်ငွေ မလုံလောက်ပါ။ (လက်ကျန်: {current_bal:,} Ks)"})

    save_user(user_phone, {"balance": current_bal - amount})

    ts = int(time.time())
    add_history(user_phone, f"wd_{ts}", {
        "type": "buy",
        "title": f"💸 ငွေထုတ် ({method} - {recv_phone} / {recv_name})",
        "amount": amount,
        "status": "⏳ ငွေထုတ်ပေးနေဆဲ",
        "time": get_mm_time(),
        "timestamp": ts
    })

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ ငွေလွှဲပြီးပြီ (Paid)", callback_data=f"wddone_{user_phone}_{ts}"),
        InlineKeyboardButton("🔄 ပယ်ဖျက်/ငွေပြန်အမ်း", callback_data=f"wdrej_{user_phone}_{amount}_{ts}")
    )

    msg = (
        f"💸 <b>ငွေထုတ်ယူမှု အသစ် (Withdraw)</b>\n\n"
        f"👤 အကောင့်: <code>{user_phone}</code>\n"
        f"💳 နည်းလမ်း: <b>{method}</b>\n"
        f"📱 လက်ခံမည့်ဖုန်း (နှိပ်၍ Copy ယူပါ):\n"
        f"👉 <code>{recv_phone}</code>\n"
        f"👤 အကောင့်နာမည်: <b>{recv_name}</b>\n"
        f"💰 ထုတ်ယူငွေ: <b>{amount:,} Ks</b> (Wallet မှ ဖြတ်ပြီး)\n"
        f"🕒 အချိန်: {get_mm_time()}"
    )
    mlbb_bot.send_message(MLBB_ADMIN_ID, msg, parse_mode="HTML", reply_markup=markup)

    return jsonify({"status": "success", "msg": "✅ ငွေထုတ်ယူရန် တင်ပြီးပါပြီ! Admin မှ မကြာမီ လွှဲပေးပါမည်။"})

# ================= 4. DATA / PLAN / BILL / POINT ဝယ်ယူခြင်း =================
@app.route('/buy_package', methods=['POST'])
def buy_package():
    mm_now = get_mm_now()
    if mm_now.hour < 7 or mm_now.hour >= 19:
        return jsonify({
            "status": "error",
            "msg": "⏰ ဆိုင်ပိတ်ချိန် ဖြစ်ပါသည်။ Order လက်ခံချိန် (မနက် 7:00 မှ ည 7:00 အတွင်း) မှ ပြန်လည်ဝယ်ယူပေးပါ။"
        })

    data = request.json
    user_phone = data.get('user_phone')
    target_phone = data.get('target_phone', '').strip()
    pkg_name = data.get('pkg_name')
    price = int(data.get('price'))
    provider = data.get('provider')

    if "Mytel" in provider and not target_phone.startswith("096"):
        return jsonify({"status": "error", "msg": "⚠️ Mytel အတွက် 096 ဖြင့်စသော ဖုန်းနံပါတ်သာ ထည့်သွင်းပါ။"})
    if "Eagle" in provider and not target_phone.startswith("097"):
        return jsonify({"status": "error", "msg": "⚠️ Atom အတွက် 097 ဖြင့်စသော ဖုန်းနံပါတ်သာ ထည့်သွင်းပါ။"})

    user = get_user(user_phone)
    current_bal = user.get("balance", 0) if user else 0

    if current_bal < price:
        return jsonify({"status": "error", "type": "low_balance", "msg": "သင့်အကောင့်ထဲတွင် လက်ကျန်ငွေ မလုံလောက်ပါ။"})

    save_user(user_phone, {"balance": current_bal - price})

    ts = int(time.time())
    order_id = f"ord_{ts}"
    add_history(user_phone, order_id, {
        "type": "buy",
        "title": f"{pkg_name} -> {target_phone}",
        "amount": price,
        "status": "⏳ ပို့ဆောင်နေဆဲ",
        "time": get_mm_time(),
        "timestamp": ts
    })

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ ပို့ပြီး (Done)", callback_data=f"done_{user_phone}_{ts}"),
        InlineKeyboardButton("🔄 ငွေပြန်အမ်း (Refund)", callback_data=f"refund_{user_phone}_{price}_{ts}")
    )

    order_msg = (
        f"📦 <b>Data / Bill အော်ဒါအသစ် ဝင်ပါသည်</b>\n\n"
        f"📱 ထည့်ပေးရမည့်ဖုန်း (နှိပ်၍ Copy ယူပါ):\n"
        f"👉 <code>{target_phone}</code>\n\n"
        f"🎁 Package: <b>{pkg_name}</b>\n"
        f"⚙️ ဝယ်ရမည့် App: <b>{provider}</b>\n"
        f"💵 ဖြတ်ထားသောငွေ: {price:,} Ks\n"
        f"👤 ဝယ်သူအကောင့်: <code>{user_phone}</code>\n"
        f"🕒 အချိန်: {get_mm_time()}"
    )
    data_bot.send_message(DATA_ADMIN_ID, order_msg, parse_mode="HTML", reply_markup=markup)

    return jsonify({"status": "success", "msg": "အော်ဒါတင်ပြီးပါပြီ။ မကြာမီ သင့်ဖုန်းသို့ ရောက်ရှိလာပါမည်။"})

# ================= 5. MLBB CUSTOM MATCH =================
@app.route('/mlbb/matches', methods=['GET'])
def get_mlbb_matches():
    res = requests.get(f"{FIREBASE_URL}/mlbb_matches.json")
    if res.status_code == 200 and res.json():
        data = res.json()
        open_matches = [v for v in data.values() if isinstance(v, dict) and v.get("status") == "open"]
        open_matches.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return jsonify(open_matches)
    return jsonify([])

@app.route('/mlbb/create', methods=['POST'])
def create_mlbb_match():
    data = request.json
    user_phone = data.get('user_phone')
    game_id = data.get('game_id')
    contact = data.get('contact')
    mode = data.get('mode')
    heroes = data.get('heroes')
    bet = int(data.get('bet', 0))
    rules = data.get('rules', 'စည်းကမ်း မသတ်မှတ်ထားပါ')

    if bet <= 0:
        return jsonify({"status": "error", "msg": "ကြေးပမာဏ မှန်ကန်စွာ ထည့်ပါ။"})

    user = get_user(user_phone)
    current_bal = user.get("balance", 0) if user else 0

    if current_bal < bet:
        return jsonify({"status": "error", "msg": f"လက်ကျန်ငွေ မလုံလောက်ပါ။ (လိုအပ်ငွေ: {bet:,} Ks)"})

    save_user(user_phone, {"balance": current_bal - bet})

    ts = int(time.time())
    match_id = f"match_{ts}"

    match_data = {
        "match_id": match_id,
        "creator_phone": user_phone,
        "game_id": game_id,
        "contact": contact,
        "mode": mode,
        "heroes": heroes,
        "bet": bet,
        "rules": rules,
        "status": "open",
        "time": get_mm_time(),
        "timestamp": ts
    }
    requests.put(f"{FIREBASE_URL}/mlbb_matches/{match_id}.json", json=match_data)

    add_history(user_phone, f"mlbb_c_{ts}", {
        "type": "buy",
        "title": f"🎮 MLBB ပွဲရှာ ({mode} - {heroes})",
        "amount": bet,
        "status": "⚔️ ပွဲရှာနေဆဲ",
        "time": get_mm_time(),
        "timestamp": ts
    })

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔄 ပွဲဖျက်ပြီး ငွေပြန်အမ်းမည် (Cancel)", callback_data=f"mlbbcancel_{user_phone}_{bet}_{match_id}_{ts}")
    )

    msg = (
        f"🚨 <b>New MLBB Match Request</b> 🚨\n\n"
        f"👤 အကောင့်: <code>{user_phone}</code>\n"
        f"🆔 Game ID: <code>{game_id}</code>\n"
        f"📞 ဆက်သွယ်ရန်: {contact}\n"
        f"🎮 Mode: <b>{mode}</b>\n"
        f"⚔️ Hero: <b>{heroes}</b>\n"
        f"💰 ကြေးပမာဏ: <b>{bet:,} Ks</b> (ငွေဖြတ်ပြီး)\n"
        f"📜 Rules:\n- {rules}\n"
        f"🕒 အချိန်: {get_mm_time()}"
    )
    mlbb_bot.send_message(MLBB_ADMIN_ID, msg, parse_mode="HTML", reply_markup=markup)

    return jsonify({"status": "success", "msg": "ပွဲအသစ် တင်ပြီးပါပြီ! ငွေဖြတ်တောက်ပြီးပါပြီ။"})

@app.route('/mlbb/accept', methods=['POST'])
def accept_mlbb_match():
    data = request.json
    match_id = data.get('match_id')
    acceptor_phone = data.get('user_phone')
    acc_game_id = data.get('game_id')
    acc_contact = data.get('contact')

    m_res = requests.get(f"{FIREBASE_URL}/mlbb_matches/{match_id}.json")
    if m_res.status_code != 200 or not m_res.json():
        return jsonify({"status": "error", "msg": "ဤပွဲကို ရှာမတွေ့တော့ပါ။"})

    match = m_res.json()
    if match.get("status") != "open":
        return jsonify({"status": "error", "msg": "⚠️ ဤပွဲကို တခြားသူတစ်ဦး လက်ခံသွားပြီး ဖြစ်ပါသည်။"})

    if match.get("creator_phone") == acceptor_phone:
        return jsonify({"status": "error", "msg": "မိမိကိုယ်တိုင် တင်ထားသော ပွဲကို ပြန်လက်ခံ၍ မရပါ။"})

    bet = int(match.get("bet", 0))
    user = get_user(acceptor_phone)
    current_bal = user.get("balance", 0) if user else 0

    if current_bal < bet:
        return jsonify({"status": "error", "msg": f"လက်ကျန်ငွေ မလုံလောက်ပါ။ (လိုအပ်ငွေ: {bet:,} Ks)"})

    save_user(acceptor_phone, {"balance": current_bal - bet})

    requests.patch(f"{FIREBASE_URL}/mlbb_matches/{match_id}.json", json={
        "status": "matched",
        "acceptor_phone": acceptor_phone,
        "acceptor_game_id": acc_game_id,
        "acceptor_contact": acc_contact
    })

    ts = int(time.time())
    add_history(acceptor_phone, f"mlbb_a_{ts}", {
        "type": "buy",
        "title": f"🎮 MLBB ပွဲလက်ခံ ({match['mode']} - {match['heroes']})",
        "amount": bet,
        "status": "✅ ပွဲဖြစ်မြောက်ပြီး",
        "time": get_mm_time(),
        "timestamp": ts
    })

    orig_ts = match.get("timestamp")
    if orig_ts:
        add_history(match['creator_phone'], f"mlbb_c_{orig_ts}", {"status": "✅ ပြိုင်ဘက်တွေ့ပြီး"})

    total_pot = bet * 2
    net_prize = int(total_pot * 0.95)

    win_markup = InlineKeyboardMarkup()
    win_markup.row(
        InlineKeyboardButton(f"🏆 Player 1 နိုင် ({net_prize:,} Ks)", callback_data=f"mlbbwin_{match['creator_phone']}_{net_prize}_{match_id}"),
        InlineKeyboardButton(f"🏆 Player 2 နိုင် ({net_prize:,} Ks)", callback_data=f"mlbbwin_{acceptor_phone}_{net_prize}_{match_id}")
    )

    accept_msg = (
        f"✅ <b>MLBB Match Accepted!</b> ✅\n\n"
        f"🎯 Mode: <b>{match['mode']}</b> | Hero: <b>{match['heroes']}</b>\n"
        f"💰 တစ်ဖက်ကြေး: <b>{bet:,} Ks</b> (စုစုပေါင်း: {total_pot:,} Ks)\n"
        f"🎁 5% နုတ်ပြီး နိုင်သူရမည့်ငွေ: <b>{net_prize:,} Ks</b>\n"
        f"------------------------\n"
        f"🔴 <b>Player 1 (စိန်ခေါ်သူ):</b>\n"
        f"   Acc: <code>{match['creator_phone']}</code>\n"
        f"   ID: <code>{match['game_id']}</code> | Ph: {match['contact']}\n"
        f"------------------------\n"
        f"🔵 <b>Player 2 (လက်ခံသူ):</b>\n"
        f"   Acc: <code>{acceptor_phone}</code>\n"
        f"   ID: <code>{acc_game_id}</code> | Ph: {acc_contact}\n\n"
        f"👇 <b>ပွဲပြီးပါက အနိုင်ရသူကို ရွေးချယ်ပေးပါ:</b>"
    )
    mlbb_bot.send_message(MLBB_ADMIN_ID, accept_msg, parse_mode="HTML", reply_markup=win_markup)

    return jsonify({"status": "success", "msg": "✅ ပွဲကို အောင်မြင်စွာ လက်ခံလိုက်ပါပြီ! Admin မှ ဆက်သွယ်ပေးပါမည်။"})

# ================= DATA BOT COMMANDS & CALLBACKS =================
@data_bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_data_commands(message):
    if str(message.chat.id) != str(DATA_ADMIN_ID):
        return

    parts = message.text.strip().split()
    cmd = parts[0].lower()

    if cmd in ['/start', '/help']:
        help_text = (
            "🛠 Data & Exchange Admin Bot\n\n"
            "📜 User မှတ်တမ်းအားလုံး စစ်ရန်:\n"
            "/history 09xxxxxxxxx\n"
            "💳 User ငွေသွင်းမှတ်တမ်း သီးသန့်စစ်ရန်:\n"
            "/topups 09xxxxxxxxx\n"
            "💸 User ငွေထုတ်မှတ်တမ်း သီးသန့်စစ်ရန်:\n"
            "/withdraws 09xxxxxxxxx\n\n"
            "👥 သုံးစွဲသူ စာရင်း: /users\n"
            "💰 စိတ်ကြိုက်ငွေထည့်ရန်: /addbal 09xxxxxxxxx 5000\n"
            "🔍 အကောင့်စစ်ရန်: /check 09xxxxxxxxx\n"
            "🔑 Password ပြောင်းရန်: /setpass 09xxxxxxxxx စကားဝှက်\n"
            "📋 Package စာရင်း: /prices\n"
            "💵 ဈေးပြောင်းရန်: /setprice ကုဒ် ဈေးနှုန်း\n"
            "➕ အသစ်တိုးရန်: /addpkg ကုဒ် အမျိုးအစား App ဈေး နာမည်\n"
            "🗑 ဖျက်ရန်: /delpkg ကုဒ်"
        )
        data_bot.reply_to(message, help_text)

    elif cmd in ['/history', '/topups', '/withdraws']:
        if len(parts) < 2:
            data_bot.reply_to(message, f"⚠️ စစ်လိုသော ဖုန်းနံပါတ် ထည့်ရိုက်ပါ။ ဥပမာ - {cmd} 09688022655")
            return
        phone = parts[1].strip()
        mode = "topup" if cmd == '/topups' else ("withdraw" if cmd == '/withdraws' else "all")
        report = format_user_history_for_admin(phone, filter_mode=mode)
        data_bot.reply_to(message, report, parse_mode="HTML")

    elif cmd == '/addbal':
        if len(parts) < 3:
            data_bot.reply_to(message, "⚠️ ဥပမာ - /addbal 09688022655 5000 (ငွေနုတ်လိုပါက -5000 ဟု ရိုက်ပါ)")
            return
        phone = parts[1]
        try:
            amt = int(parts[2])
        except ValueError:
            data_bot.reply_to(message, "⚠️ ငွေပမာဏကို ဂဏန်းသီးသန့် ရိုက်ပါ။")
            return
        user = get_user(phone)
        if not user:
            data_bot.reply_to(message, "❌ ဤဖုန်းနံပါတ်ဖြင့် အကောင့်မရှိပါ။")
            return
        new_bal = max(0, user.get("balance", 0) + amt)
        save_user(phone, {"balance": new_bal})
        ts = int(time.time())
        add_history(phone, f"adm_{ts}", {
            "type": "topup" if amt >= 0 else "buy",
            "title": "🎁 Admin မှ ငွေထည့်ပေးခြင်း" if amt >= 0 else "⚙️ Admin မှ ငွေပြင်ဆင်ခြင်း",
            "amount": abs(amt),
            "status": "✅ အတည်ပြုပြီး",
            "time": get_mm_time(),
            "timestamp": ts
        })
        data_bot.reply_to(message, f"✅ {phone} အကောင့်သို့ {amt:,} Ks ပြင်ဆင်ပြီးပါပြီ!\n💰 လက်ရှိလက်ကျန်ငွေ: {new_bal:,} Ks")

    elif cmd == '/users':
        res = requests.get(f"{FIREBASE_URL}/users.json")
        if res.status_code == 200 and res.json():
            users_data = res.json()
            total_users = len(users_data)
            lines = [f"👥 <b>စုစုပေါင်း သုံးစွဲသူ: {total_users} ဦး</b>\n"]
            for idx, (u_phone, u_info) in enumerate(users_data.items(), start=1):
                bal = u_info.get('balance', 0) if isinstance(u_info, dict) else 0
                lines.append(f"{idx}. <code>{u_phone}</code> (လက်ကျန်: {bal:,} Ks)")
            lines.append("\n💡 မှတ်တမ်းစစ်ရန်: /history ဖုန်းနံပါတ်")
            msg_text = "\n".join(lines)
            if len(msg_text) > 4000:
                data_bot.reply_to(message, f"👥 <b>စုစုပေါင်း သုံးစွဲသူ: {total_users} ဦး</b> ရှိပါသည်။", parse_mode="HTML")
            else:
                data_bot.reply_to(message, msg_text, parse_mode="HTML")
        else:
            data_bot.reply_to(message, "👥 လက်ရှိ အကောင့်ဖွင့်ထားသူ မရှိသေးပါ။")

    elif cmd == '/check':
        if len(parts) < 2:
            data_bot.reply_to(message, "⚠️ ဥပမာ - /check 09688022655")
            return
        phone = parts[1]
        user = get_user(phone)
        if not user:
            data_bot.reply_to(message, "❌ အကောင့်မရှိပါ။")
        else:
            msg = (
                f"👤 <code>{phone}</code>\n"
                f"🔑 Pass: <code>{user.get('password')}</code>\n"
                f"💰 Bal: <b>{user.get('balance', 0):,} Ks</b>\n\n"
                f"📜 မှတ်တမ်းစစ်ရန်: <code>/history {phone}</code>"
            )
            data_bot.reply_to(message, msg, parse_mode="HTML")

    elif cmd == '/setpass':
        if len(parts) < 3:
            data_bot.reply_to(message, "⚠️ ဥပမာ - /setpass 09688022655 123456")
            return
        phone, new_pass = parts[1], parts[2]
        if not get_user(phone):
            data_bot.reply_to(message, "❌ အကောင့်မရှိပါ။")
        else:
            save_user(phone, {"password": new_pass})
            data_bot.reply_to(message, f"✅ {phone} Password ကို {new_pass} သို့ ပြောင်းပြီးပါပြီ။")

    elif cmd in ['/prices', '/price']:
        pkgs = get_all_packages()
        lines = ["📋 Package စာရင်း\n"]
        for code, info in sorted(pkgs.items(), key=lambda x: x[1].get('order', 99)):
            lines.append(f"🔹 {code} ({info['cat']}): {info['name']} = {info['price']:,} Ks")
        data_bot.reply_to(message, "\n".join(lines))

    elif cmd == '/setprice':
        if len(parts) < 3:
            data_bot.reply_to(message, "⚠️ ဥပမာ - /setprice mn1 950")
            return
        code = parts[1].lower()
        new_price = int(parts[2])
        pkgs = get_all_packages()
        if code not in pkgs:
            data_bot.reply_to(message, "❌ ကုဒ်မှားနေပါသည်။")
            return
        requests.patch(f"{FIREBASE_URL}/packages/{code}.json", json={"price": new_price})
        data_bot.reply_to(message, f"✅ {pkgs[code]['name']} ကို {new_price:,} Ks သို့ ပြောင်းပြီးပါပြီ!")

    elif cmd == '/addpkg':
        raw_parts = message.text.strip().split(maxsplit=5)
        if len(raw_parts) < 6:
            data_bot.reply_to(message, "⚠️ ဥပမာ - /addpkg mn3 mytel_normal agent 1800 2GB (5 Days)")
            return
        code, cat, app_key, price, name = raw_parts[1].lower(), raw_parts[2].lower(), raw_parts[3].lower(), int(raw_parts[4]), raw_parts[5]
        if cat not in VALID_CATEGORIES or app_key not in APP_MAP:
            data_bot.reply_to(message, "❌ အမျိုးအစား သို့မဟုတ် App အမည် မှားနေပါသည်။")
            return
        requests.put(f"{FIREBASE_URL}/packages/{code}.json", json={"cat": cat, "name": name, "price": price, "provider": APP_MAP[app_key], "order": int(time.time())})
        data_bot.reply_to(message, f"✅ {name} ({code}) ထပ်တိုးပြီးပါပြီ!")

    elif cmd == '/delpkg':
        if len(parts) < 2:
            data_bot.reply_to(message, "⚠️ ဥပမာ - /delpkg mn3")
            return
        code = parts[1].lower()
        pkgs = get_all_packages()
        if code not in pkgs:
            data_bot.reply_to(message, "❌ ကုဒ်မရှိပါ။")
            return
        requests.delete(f"{FIREBASE_URL}/packages/{code}.json")
        data_bot.reply_to(message, f"🗑 {code} ကို ဖျက်လိုက်ပါပြီ!")

@data_bot.callback_query_handler(func=lambda call: True)
def handle_data_callbacks(call):
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

            data_bot.answer_callback_query(call.id, "✅ ငွေထည့်ပေးပြီးပါပြီ!")
            data_bot.edit_message_caption(caption=f"{call.message.caption}\n\n✅ အတည်ပြုပြီး ({amount:,} Ks) - {get_mm_time()}", chat_id=call.message.chat.id, message_id=call.message.message_id)

        elif action == "reject":
            tid = data[2] if len(data) > 2 else "000"
            add_history(user_phone, f"topup_{tid}", {"status": "❌ ပယ်ဖျက်ခံရသည်"})
            data_bot.answer_callback_query(call.id, "❌ ငြင်းပယ်လိုက်ပါပြီ!")
            data_bot.edit_message_caption(caption=f"{call.message.caption}\n\n❌ ငြင်းပယ်လိုက်ပါသည်", chat_id=call.message.chat.id, message_id=call.message.message_id)

        elif action == "done":
            ts = data[2]
            add_history(user_phone, f"ord_{ts}", {"status": "✅ ဝယ်ယူပြီး"})
            data_bot.answer_callback_query(call.id, "✅ ပို့ပြီးကြောင်း မှတ်သားပြီးပါပြီ!")
            data_bot.edit_message_text(text=f"{call.message.text}\n\n✅ <b>ပို့ဆောင်ပြီး (Done)</b> - {get_mm_time()}", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

        elif action == "refund":
            price = int(data[2])
            ts = data[3]
            user = get_user(user_phone)
            current_bal = user.get("balance", 0) if user else 0
            save_user(user_phone, {"balance": current_bal + price})
            add_history(user_phone, f"ord_{ts}", {"status": "🔄 ငွေပြန်အမ်းပြီး (Refunded)", "type": "topup"})

            data_bot.answer_callback_query(call.id, "🔄 ငွေပြန်အမ်းပေးပြီးပါပြီ!")
            data_bot.edit_message_text(text=f"{call.message.text}\n\n🔄 <b>ငွေပြန်အမ်းပြီး ({price:,} Ks)</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

        elif action == "exdone":
            ts = data[2]
            add_history(user_phone, f"ex_{ts}", {"status": "✅ ငွေချိန်း/လွှဲပေးပြီးပါပြီ"})
            data_bot.answer_callback_query(call.id, "✅ ငွေချိန်းပြီးကြောင်း အတည်ပြုပြီးပါပြီ!")
            data_bot.edit_message_caption(caption=f"{call.message.caption}\n\n✅ <b>ငွေချိန်းပြီးပါပြီ</b> - {get_mm_time()}", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

        elif action == "exrej":
            ts = data[2]
            add_history(user_phone, f"ex_{ts}", {"status": "❌ ပယ်ဖျက်ခံရသည်"})
            data_bot.answer_callback_query(call.id, "❌ ပယ်ဖျက်လိုက်ပါပြီ!")
            data_bot.edit_message_caption(caption=f"{call.message.caption}\n\n❌ <b>ပယ်ဖျက်လိုက်ပါသည်</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

    except Exception as e:
        data_bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)

# ================= MLBB BOT COMMANDS & CALLBACKS =================
@mlbb_bot.message_handler(func=lambda m: m.text and m.text.startswith('/'))
def handle_mlbb_commands(message):
    if str(message.chat.id) != str(MLBB_ADMIN_ID):
        return

    parts = message.text.strip().split()
    cmd = parts[0].lower()

    if cmd in ['/start', '/help']:
        help_text = (
            "🎮 MLBB Custom Match & Withdraw Admin Bot\n\n"
            "📜 User မှတ်တမ်းအားလုံး စစ်ရန်:\n"
            "/history 09xxxxxxxxx\n"
            "💳 User ငွေသွင်းမှတ်တမ်း သီးသန့်စစ်ရန်:\n"
            "/topups 09xxxxxxxxx\n"
            "💸 User ငွေထုတ်မှတ်တမ်း သီးသန့်စစ်ရန်:\n"
            "/withdraws 09xxxxxxxxx\n\n"
            "💰 စိတ်ကြိုက်ငွေထည့်ရန်:\n"
            "/addbal 09xxxxxxxxx 5000\n"
            "🏆 ဆုကြေး သီးသန့်ထည့်ရန်:\n"
            "/win 09xxxxxxxxx 9500\n"
            "🔍 အကောင့် လက်ကျန်ငွေ စစ်ရန်:\n"
            "/check 09xxxxxxxxx"
        )
        mlbb_bot.reply_to(message, help_text)

    elif cmd in ['/history', '/topups', '/withdraws']:
        if len(parts) < 2:
            mlbb_bot.reply_to(message, f"⚠️ စစ်လိုသော ဖုန်းနံပါတ် ထည့်ရိုက်ပါ။ ဥပမာ - {cmd} 09688022655")
            return
        phone = parts[1].strip()
        mode = "topup" if cmd == '/topups' else ("withdraw" if cmd == '/withdraws' else "all")
        report = format_user_history_for_admin(phone, filter_mode=mode)
        mlbb_bot.reply_to(message, report, parse_mode="HTML")

    elif cmd == '/addbal':
        if len(parts) < 3:
            mlbb_bot.reply_to(message, "⚠️ ဥပမာ - /addbal 09688022655 5000")
            return
        phone = parts[1]
        try:
            amt = int(parts[2])
        except ValueError:
            mlbb_bot.reply_to(message, "⚠️ ငွေပမာဏကို ဂဏန်းသီးသန့် ရိုက်ပါ။")
            return
        user = get_user(phone)
        if not user:
            mlbb_bot.reply_to(message, "❌ ဤဖုန်းနံပါတ်ဖြင့် အကောင့်မရှိပါ။")
            return
        new_bal = max(0, user.get("balance", 0) + amt)
        save_user(phone, {"balance": new_bal})
        ts = int(time.time())
        add_history(phone, f"adm_{ts}", {
            "type": "topup" if amt >= 0 else "buy",
            "title": "🎁 Admin မှ ငွေထည့်ပေးခြင်း",
            "amount": abs(amt),
            "status": "✅ အတည်ပြုပြီး",
            "time": get_mm_time(),
            "timestamp": ts
        })
        mlbb_bot.reply_to(message, f"✅ {phone} အကောင့်သို့ {amt:,} Ks ထည့်ပေးပြီးပါပြီ!\n💰 လက်ရှိလက်ကျန်ငွေ: {new_bal:,} Ks")

    elif cmd == '/win':
        if len(parts) < 3:
            mlbb_bot.reply_to(message, "⚠️ ဥပမာ - /win 09688022655 9500")
            return
        phone = parts[1]
        prize = int(parts[2])
        user = get_user(phone)
        if not user:
            mlbb_bot.reply_to(message, "❌ အကောင့်မရှိပါ။")
            return
        save_user(phone, {"balance": user.get("balance", 0) + prize})
        ts = int(time.time())
        add_history(phone, f"mlbb_win_{ts}", {
            "type": "topup",
            "title": "🏆 MLBB ပွဲနိုင်ဆုကြေးငွေ",
            "amount": prize,
            "status": "✅ ဆုကြေးဝင်ပြီး",
            "time": get_mm_time(),
            "timestamp": ts
        })
        mlbb_bot.reply_to(message, f"🏆 {phone} အကောင့်ထဲသို့ ဆုကြေးငွေ {prize:,} Ks ထည့်ပေးပြီးပါပြီ!")

    elif cmd == '/check':
        if len(parts) < 2:
            mlbb_bot.reply_to(message, "⚠️ ဥပမာ - /check 09688022655")
            return
        phone = parts[1]
        user = get_user(phone)
        if not user:
            mlbb_bot.reply_to(message, "❌ အကောင့်မရှိပါ။")
        else:
            mlbb_bot.reply_to(message, f"👤 {phone}\n💰 လက်ကျန်ငွေ: {user.get('balance', 0):,} Ks\n📜 မှတ်တမ်းစစ်ရန်: /history {phone}")

@mlbb_bot.callback_query_handler(func=lambda call: True)
def handle_mlbb_callbacks(call):
    try:
        data = call.data.split('_')
        action = data[0]

        if action == "mlbbcancel":
            user_phone = data[1]
            bet = int(data[2])
            match_id = f"{data[3]}_{data[4]}"
            ts = data[5]

            m_res = requests.get(f"{FIREBASE_URL}/mlbb_matches/{match_id}.json")
            if m_res.status_code == 200 and m_res.json():
                if m_res.json().get("status") != "open":
                    mlbb_bot.answer_callback_query(call.id, "⚠️ ဤပွဲကို တခြားသူ လက်ခံပြီးဖြစ်၍ ပယ်ဖျက်မရပါ!", show_alert=True)
                    return

            requests.patch(f"{FIREBASE_URL}/mlbb_matches/{match_id}.json", json={"status": "cancelled"})
            user = get_user(user_phone)
            current_bal = user.get("balance", 0) if user else 0
            save_user(user_phone, {"balance": current_bal + bet})
            add_history(user_phone, f"mlbb_c_{ts}", {"status": "🔄 ပွဲဖျက်သိမ်း/ငွေပြန်အမ်းပြီး", "type": "topup"})

            mlbb_bot.answer_callback_query(call.id, "🔄 MLBB ပွဲဖျက်သိမ်းပြီး ငွေပြန်အမ်းပေးလိုက်ပါပြီ!")
            mlbb_bot.edit_message_text(text=f"{call.message.text}\n\n🔄 <b>ပွဲဖျက်သိမ်းပြီး ({bet:,} Ks ပြန်အမ်းပြီးပါပြီ)</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

        elif action == "mlbbwin":
            winner_phone = data[1]
            net_prize = int(data[2])
            match_id = f"{data[3]}_{data[4]}"

            m_res = requests.get(f"{FIREBASE_URL}/mlbb_matches/{match_id}.json")
            if m_res.status_code == 200 and m_res.json():
                if m_res.json().get("status") == "completed":
                    mlbb_bot.answer_callback_query(call.id, "⚠️ ဤပွဲအတွက် ဆုကြေးပေးပြီးသား ဖြစ်ပါသည်!", show_alert=True)
                    return

            requests.patch(f"{FIREBASE_URL}/mlbb_matches/{match_id}.json", json={"status": "completed", "winner": winner_phone})
            user = get_user(winner_phone)
            current_bal = user.get("balance", 0) if user else 0
            save_user(winner_phone, {"balance": current_bal + net_prize})

            ts = int(time.time())
            add_history(winner_phone, f"mlbb_win_{ts}", {
                "type": "topup",
                "title": "🏆 MLBB ပွဲနိုင်ဆုကြေး (5% နုတ်ပြီး)",
                "amount": net_prize,
                "status": "✅ ဆုကြေးဝင်ပြီး",
                "time": get_mm_time(),
                "timestamp": ts
            })

            mlbb_bot.answer_callback_query(call.id, f"🏆 {winner_phone} ထံ {net_prize:,} Ks ထည့်ပေးပြီးပါပြီ!")
            mlbb_bot.edit_message_text(text=f"{call.message.text}\n\n🏆 <b>အနိုင်ရသူ: {winner_phone} ထံ {net_prize:,} Ks (5% နုတ်ပြီး) Auto ထည့်ပေးပြီးပါပြီ!</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

        elif action == "wddone":
            user_phone = data[1]
            ts = data[2]
            add_history(user_phone, f"wd_{ts}", {"status": "✅ ငွေထုတ်ပြီးပါပြီ"})
            mlbb_bot.answer_callback_query(call.id, "✅ ငွေထုတ်ပြီးကြောင်း အတည်ပြုပြီးပါပြီ!")
            mlbb_bot.edit_message_text(text=f"{call.message.text}\n\n✅ <b>ငွေထုတ်ပြီးပါပြီ</b> - {get_mm_time()}", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

        elif action == "wdrej":
            user_phone = data[1]
            amount = int(data[2])
            ts = data[3]
            user = get_user(user_phone)
            current_bal = user.get("balance", 0) if user else 0
            save_user(user_phone, {"balance": current_bal + amount})
            add_history(user_phone, f"wd_{ts}", {"status": "🔄 ငွေထုတ်ပယ်ဖျက်/ပြန်အမ်းပြီး", "type": "topup"})

            mlbb_bot.answer_callback_query(call.id, "🔄 ငွေထုတ်ပယ်ဖျက်ပြီး Wallet ထဲ ပြန်ထည့်ပေးပါပြီ!")
            mlbb_bot.edit_message_text(text=f"{call.message.text}\n\n🔄 <b>ပယ်ဖျက်ပြီး ({amount:,} Ks ပြန်ထည့်ပေးပြီးပါပြီ)</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")

    except Exception as e:
        mlbb_bot.answer_callback_query(call.id, f"Error: {str(e)}", show_alert=True)

# ================= DUAL WEBHOOK ENDPOINTS =================
@app.route('/webhook_data', methods=['POST'])
def webhook_data():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        data_bot.process_new_updates([update])
    except Exception as e:
        print("Data Webhook Error:", e)
    return "OK", 200

@app.route('/webhook_mlbb', methods=['POST'])
def webhook_mlbb():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        mlbb_bot.process_new_updates([update])
    except Exception as e:
        print("MLBB Webhook Error:", e)
    return "OK", 200

@app.route('/set_webhook')
def set_webhook():
    data_bot.remove_webhook()
    mlbb_bot.remove_webhook()
    time.sleep(1)
    data_bot.set_webhook(url=f"{WEB_URL}/webhook_data", drop_pending_updates=True)
    mlbb_bot.set_webhook(url=f"{WEB_URL}/webhook_mlbb", drop_pending_updates=True)
    return "✅ Data Bot နှင့် MLBB Bot (၂) ခုလုံး Webhook ချိတ်ဆက်မှု အောင်မြင်ပါပြီ!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
