import requests
from io import BytesIO
from bs4 import BeautifulSoup
from PIL import Image
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8700889812:AAEgha36C0FPkZ5AFSqGVjrx9MoLZH94my0"
BASE_URL = "https://esheba.sylhetboard.gov.bd/publicResult/"

# এখানে ইউজার সেশন সেভ রাখার জন্য ডিকশনারি
user_sessions = {}

# ক্যাপচা রিসাইজ ফাংশন (আগের মতোই আছে)
def resize_captcha(image_bytes):
    img = Image.open(BytesIO(image_bytes))
    img = img.resize((250, 80))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ইউজার স্টার্ট দিলে তার পুরনো ডাটা মুছে নতুন সেশন শুরু হবে
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        
    keyboard = [["🚀 Start"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("সিলেট বোর্ড রেজাল্ট বক্সে স্বাগতম!\n\n📥 শুরু করতে নিচের বাটনে চাপ দিন:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text == "🚀 Start":
        # সেশন শুরু করা
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        # প্রথমে ইনডেক্স পেজ ভিজিট করে কুকি সেট করা
        session.get(BASE_URL + "index.php")
        
        user_sessions[user_id] = {
            "step": "ROLL",
            "session": session
        }
        await update.message.reply_text("📥 তোমার রোল নম্বরটি দাও:")
        return

    if user_id not in user_sessions:
        await update.message.reply_text("দয়া করে 🚀 Start বাটনে ক্লিক করে শুরু করুন।")
        return

    user_data = user_sessions[user_id]

    # স্টেপ ১: রোল নম্বর নেওয়া এবং ক্যাপচা পাঠানো
    if user_data["step"] == "ROLL":
        user_data["roll"] = text
        user_data["step"] = "CAPTCHA"
        
        # ওই একই সেশন ব্যবহার করে ক্যাপচা আনা
        captcha_res = user_data["session"].get(BASE_URL + "captcha.php")
        img = resize_captcha(captcha_res.content)
        
        await update.message.reply_photo(photo=img, caption="🔐 উপরে ছবিতে থাকা সংখ্যাগুলো (CAPTCHA) লিখো:")
    
    # স্টেপ ২: ক্যাপচা ভেরিফাই এবং রেজাল্ট আনা
    elif user_data["step"] == "CAPTCHA":
        captcha_code = text
        session = user_data["session"]
        
        payload = {
            "hroll": user_data["roll"],
            "autocaptcha": captcha_code,
            "btnSubmit": "Submit",
            "btnaction": "c2hvd1B1YmxpY1Jlc3VsdA==", # Base64 encoded action
            "param": "MjAyMg==" # 2022 এর জন্য প্যারামিটার (পরিবর্তন করতে পারেন)
        }
        
        headers = {
            "Referer": BASE_URL + "index.php",
            "Origin": "https://esheba.sylhetboard.gov.bd"
        }

        try:
            res = session.post(BASE_URL + "include/function.php", data=payload, headers=headers)
            html = res.text

            if "STUDENT INFORMATION" in html:
                # এখানে আপনার এক্সট্রাক্ট করা লজিকগুলো আগের মতো থাকবে
                await update.message.reply_text("✅ রেজাল্ট পাওয়া গেছে! (এখানে রেজাল্ট দেখানোর কোড বসবে)")
                # সেশন ক্লিয়ার করে দেওয়া
                del user_sessions[user_id]
            else:
                await update.message.reply_text("❌ ভুল ক্যাপচা বা রোল নম্বর! আবার চেষ্টা করতে 🚀 Start দিন।")
                del user_sessions[user_id]
        except Exception as e:
            await update.message.reply_text("⚠️ সার্ভারে সমস্যা হচ্ছে। পরে চেষ্টা করুন।")
            del user_sessions[user_id]

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
