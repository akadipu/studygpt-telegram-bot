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
chat_messages = {}
user_timers = {}

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

    # ===== SAFE EXIT =====
    if user_id == ADMIN_ID and text == "🛑 Safe Exit":
        context.user_data.pop("send_mode", None)
        await admin(update, context)
        return

    # ================= CONTACT SYSTEM =================

    if text == "📞 Contact Us":
        active_users.add(user_id)

        await update.message.reply_text(
            "💬 Support Chat Started\nSend your message...",
            reply_markup=ReplyKeyboardMarkup(
                [["🧹 Clear History", "❌ End Chat"]],
                resize_keyboard=True
            )
        )
        return

    if user_id in active_users and user_id != ADMIN_ID:

        sender = update.message.from_user
        caption = f"{sender.first_name}\n🆔 {sender.id}"

        if update.message.text:
            admin_msg = await context.bot.send_message(
                ADMIN_ID, f"{caption}\n\n{text}"
            )
        else:
            return

        context.bot_data[admin_msg.message_id] = user_id
        return

    if user_id == ADMIN_ID and update.message.reply_to_message:
        target = context.bot_data.get(update.message.reply_to_message.message_id)
        if target:
            await context.bot.send_message(target, text)
            return

    if text == "❌ End Chat" and user_id in active_users:
        active_users.discard(user_id)
        await start(update, context)
        return

    # ================= SEND MESSAGE =================

    if user_id == ADMIN_ID and text == "📨 Send Message":
        context.user_data["send_mode"] = True
        await update.message.reply_text(
            "Send message:",
            reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True)
        )
        return

    if user_id == ADMIN_ID and context.user_data.get("send_mode"):
        if update.message.reply_to_message:
            return
        if update.message.text:
            await context.bot.send_message(TARGET_USER_ID, text)
        return

    # ================= NORMAL FLOW =================

    if text == "🏠 Main Menu":
        await start(update, context)
        return

    # ===== BACK BUTTON FIX =====
    if text == "⬅ Back":

        last = context.user_data.get("last")

        if last == "material":
            context.user_data["last"] = "subject"
            await show_subjects(update, context)

        elif last == "subject":
            context.user_data["last"] = "class"

            keyboard = [
                ["Class 9th", "Class 10th"],
                ["Class 11th", "Class 12th"],
                ["📞 Contact Us"]
            ]

            await update.message.reply_text(
                "Choose your class 👇",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )

        elif last == "class":
            await start(update, context)

        else:
            await start(update, context)

        return

    # ===== CLASS =====
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        context.user_data["last"] = "class"
        await show_subjects(update, context)
        return

    # ===== SUBJECT =====
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
