import os
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745
DATA_FILE = "data.json"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

flask_app = Flask(__name__)
app = ApplicationBuilder().token(TOKEN).build()

active_users = set()
user_timers = {}
chat_messages = {}

# ================= DATA =================

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"categories": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= SESSION =================

async def expire_chat(user_id, context):
    await asyncio.sleep(180)

    if user_id in active_users:
        active_users.discard(user_id)

        for u, a in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, u)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, a)
            except:
                pass

        chat_messages[user_id] = []

        try:
            await context.bot.send_message(user_id, "Session expired & chat cleared.")
            await asyncio.sleep(1)
            await send_main_menu(user_id, context)
        except:
            pass

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await send_main_menu(update.message.chat_id, context)

async def send_main_menu(chat_id, context):
    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"],
        ["📞 Contact Us"]
    ]

    await context.bot.send_message(
        chat_id,
        "🚀 StudyGPT: Ace your exams with Handwritten Notes, Mindmaps, and Solved PYQs!\n\nChoose your class 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [["➕ Add Material"]]

    await update.message.reply_text(
        "Admin Panel 👨‍💻",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= SUBJECT =================

async def show_subjects(chat_id, cls, context):
    if cls in ["Class 9th", "Class 10th"]:
        keyboard = [
            ["SCIENCE 🧪", "MATHEMATICS 📐"],
            ["ECONOMICS 💳", "HISTORY 🏆"],
            ["POL. SCIENCE 👮", "GEOGRAPHY 🌍"],
            ["ENGLISH 📄"]
        ]
    else:
        keyboard = [
            ["PHYSICS ⚛️", "CHEMISTRY 🧪"],
            ["BIOLOGY 🌱", "MATHS 📐"],
            ["ENGLISH 📄"]
        ]

    keyboard.append(["⬅ Back", "🏠 Main Menu"])

    await context.bot.send_message(
        chat_id,
        f"{cls} Subjects",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    msg = update.message
    text = msg.text if msg.text else ""

    # ===== ADMIN REPLY =====
    if user_id == ADMIN_ID and msg.reply_to_message:
        target = context.bot_data.get(msg.reply_to_message.message_id)
        if target:
            sent = await context.bot.copy_message(
                chat_id=target,
                from_chat_id=ADMIN_ID,
                message_id=msg.message_id
            )
            chat_messages.setdefault(target, []).append(
                (sent.message_id, msg.message_id)
            )
            return

    # ===== MAIN MENU =====
    if text == "🏠 Main Menu":
        await start(update, context)
        return

    # ===== BACK =====
    if text == "⬅ Back":
        cls = context.user_data.get("class")
        if cls:
            await show_subjects(user_id, cls, context)
        else:
            await start(update, context)
        return

    # ===== CONTACT =====
    if text == "📞 Contact Us":
        active_users.add(user_id)

        keyboard = [["🧹 Clear History", "❌ End Chat"]]

        await context.bot.send_message(
            user_id,
            "StudyGPT Support Team:\n\n💬 Send your message here and we’ll reply directly!",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))
        return

    # ===== CLEAR HISTORY =====
    if text == "🧹 Clear History" and user_id in active_users:
        for u, a in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, u)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, a)
            except:
                pass

        chat_messages[user_id] = []
        await context.bot.send_message(user_id, "🧹 History cleared!")
        return

    # ===== END CHAT =====
    if text == "❌ End Chat" and user_id in active_users:
        for u, a in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, u)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, a)
            except:
                pass

        chat_messages[user_id] = []
        active_users.discard(user_id)

        await context.bot.send_message(user_id, "Chat ended & history cleared.")
        await asyncio.sleep(1)
        await send_main_menu(user_id, context)
        return

    # ===== CHAT RELAY =====
    if user_id in active_users:
        admin_msg = await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=user_id,
            message_id=msg.message_id
        )

        chat_messages.setdefault(user_id, []).append(
            (msg.message_id, admin_msg.message_id)
        )

        context.bot_data[admin_msg.message_id] = user_id
        return

    # ===== CLASS =====
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        await show_subjects(user_id, text, context)

# ================= ROUTES =================

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    asyncio.run(app.process_update(update))
    return "ok"

@flask_app.route("/")
def home():
    return "Bot running"

# ================= MAIN =================

if __name__ == "__main__":
    import requests

    # set webhook
    requests.get(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/{TOKEN}"
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

    flask_app.run(host="0.0.0.0", port=8000)
