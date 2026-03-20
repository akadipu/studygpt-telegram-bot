import os
import json
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745
TARGET_USER_ID = 8071314699
DATA_FILE = "data.json"

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

# ================= CONTACT SYSTEM =================

active_users = set()
user_timers = {}
chat_messages = {}

async def expire_chat(user_id, context):
    await asyncio.sleep(180)

    if user_id in active_users:
        active_users.discard(user_id)

        for u, a in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, u)
                await context.bot.delete_message(ADMIN_ID, a)
            except:
                pass

        chat_messages[user_id] = []

        await context.bot.send_message(user_id, "Session expired & chat cleared.")
        await start_by_context(context, user_id)

async def start_by_context(context, user_id):
    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"],
        ["📞 Contact Us"]
    ]

    await context.bot.send_message(
        user_id,
        "Choose your class 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await start_by_context(context, update.message.chat_id)

# ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        ["➕ Add Material", "❌ Delete Material"],
        ["📨 Send Message"]
    ]

    await update.message.reply_text(
        "Admin Panel 👨‍💻",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= SUBJECT =================

async def show_subjects(update, context):
    cls = context.user_data.get("class")

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

    await update.message.reply_text(
        f"{cls} Subjects",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= MATERIAL MENU =================

async def show_materials(update, context):
    cls = context.user_data.get("class")

    if cls == "Class 9th":
        keyboard = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "❗ Imp Questions"]]
    elif cls == "Class 10th":
        keyboard = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "📄 PYQs"]]
    elif cls == "Class 11th":
        keyboard = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "❗ Imp Questions"]]
    else:
        keyboard = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "📄 PYQs"]]

    keyboard.append(["⬅ Back", "🏠 Main Menu"])
    context.user_data["last"] = "material"

    await update.message.reply_text(
        context.user_data.get("subject"),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else ""
    data = load_data()

    # ===== SAFE EXIT =====
    if user_id == ADMIN_ID and text == "🛑 Safe Exit":
        context.user_data.pop("send_mode", None)
        await admin(update, context)
        return

    # ================= CONTACT SYSTEM =================

    if text == "📞 Contact Us":
        active_users.add(user_id)

        keyboard = [["🧹 Clear History", "❌ End Chat"]]

        await update.message.reply_text(
            "💬 Support Chat Started\nSend your message...",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))
        return

    if text == "🧹 Clear History" and user_id in active_users:
        for u, a in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, u)
                await context.bot.delete_message(ADMIN_ID, a)
            except:
                pass

        chat_messages[user_id] = []
        await update.message.reply_text("🧹 History cleared!")
        return

    if text == "❌ End Chat" and user_id in active_users:
        active_users.discard(user_id)
        chat_messages[user_id] = []
        await update.message.reply_text("Chat ended.")
        await start(update, context)
        return

    # USER → ADMIN
    if user_id in active_users and user_id != ADMIN_ID:

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))

        sender = update.message.from_user
        caption = f"{sender.first_name}\n🆔 {sender.id}"

        if update.message.text:
            admin_msg = await context.bot.send_message(ADMIN_ID, f"{caption}\n\n{text}")
        elif update.message.photo:
            admin_msg = await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption)
        elif update.message.video:
            admin_msg = await context.bot.send_video(ADMIN_ID, update.message.video.file_id, caption=caption)
        elif update.message.document:
            admin_msg = await context.bot.send_document(ADMIN_ID, update.message.document.file_id, caption=caption)
        else:
            return

        chat_messages.setdefault(user_id, []).append(
            (update.message.message_id, admin_msg.message_id)
        )

        context.bot_data[admin_msg.message_id] = user_id
        return

    # ADMIN REPLY
    if user_id == ADMIN_ID and update.message.reply_to_message:
        target = context.bot_data.get(update.message.reply_to_message.message_id)

        if target:
            msg = update.message

            if msg.text:
                sent = await context.bot.send_message(target, msg.text)
            elif msg.photo:
                sent = await context.bot.send_photo(target, msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video:
                sent = await context.bot.send_video(target, msg.video.file_id, caption=msg.caption)
            elif msg.document:
                sent = await context.bot.send_document(target, msg.document.file_id, caption=msg.caption)
            else:
                return

            chat_messages.setdefault(target, []).append(
                (sent.message_id, update.message.message_id)
            )
            return

    # ================= SEND MESSAGE (SEPARATE) =================

    if user_id == ADMIN_ID and text == "📨 Send Message":
        context.user_data["send_mode"] = True
        await update.message.reply_text("Send message:", reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True))
        return

    if user_id == ADMIN_ID and context.user_data.get("send_mode"):

        if update.message.reply_to_message:
            return

        if text in ["➕ Add Material", "❌ Delete Material", "📨 Send Message"]:
            return

        if update.message.text:
            await context.bot.send_message(TARGET_USER_ID, text)
        elif update.message.photo:
            await context.bot.send_photo(TARGET_USER_ID, update.message.photo[-1].file_id)
        elif update.message.video:
            await context.bot.send_video(TARGET_USER_ID, update.message.video.file_id)
        elif update.message.document:
            await context.bot.send_document(TARGET_USER_ID, update.message.document.file_id)

        return

    # ================= NORMAL FLOW =================

    if text == "🏠 Main Menu":
        await start(update, context)
        return

    if text == "⬅ Back":
        last = context.user_data.get("last")

        if last == "material":
            await show_subjects(update, context)
        elif last == "subject":
            await start(update, context)
        else:
            await start(update, context)
        return

    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        context.user_data["last"] = "class"
        await show_subjects(update, context)
        return

    subjects = [
        "SCIENCE 🧪","MATHEMATICS 📐","ECONOMICS 💳","HISTORY 🏆",
        "POL. SCIENCE 👮","GEOGRAPHY 🌍","ENGLISH 📄",
        "PHYSICS ⚛️","CHEMISTRY 🧪","BIOLOGY 🌱","MATHS 📐"
    ]

    if text in subjects:
        context.user_data["subject"] = text
        context.user_data["last"] = "subject"
        await show_materials(update, context)
        return

# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()
