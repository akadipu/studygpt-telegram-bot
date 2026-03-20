import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745
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

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"]
    ]

    await update.message.reply_text(
        "🚀 StudyGPT: Notes & PYQs\n\nChoose your class 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [["➕ Add Material"]]

    await update.message.reply_text(
        "Admin Panel",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    data = load_data()

    # ================= ADMIN FLOW =================
    if user_id == ADMIN_ID:

        if text == "➕ Add Material":
            context.user_data["step"] = "class"
            keyboard = [
                ["Class 9th", "Class 10th"],
                ["Class 11th", "Class 12th"]
            ]
            await update.message.reply_text("Select Class", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return

        elif context.user_data.get("step") == "class":
            context.user_data["class"] = text
            context.user_data["step"] = "subject"

            keyboard = [
                ["SCIENCE 🧪", "MATHS 📐"],
                ["ENGLISH 📄"]
            ]

            await update.message.reply_text("Select Subject", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return

        elif context.user_data.get("step") == "subject":
            context.user_data["subject"] = text
            context.user_data["step"] = "type"

            keyboard = [["Notes", "PYQ"]]

            await update.message.reply_text("Select Type", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            return

        elif context.user_data.get("step") == "type":
            context.user_data["type"] = text
            context.user_data["step"] = "content"

            await update.message.reply_text("Send content (text/link)")
            return

        elif context.user_data.get("step") == "content":
            key = f"{context.user_data['class']}|{context.user_data['subject']}|{context.user_data['type']}"

            data["categories"].setdefault(key, []).append({
                "text": text
            })

            save_data(data)

            await update.message.reply_text("✅ Material Added")
            context.user_data.clear()
            return

    # ================= USER FLOW =================

    # Class
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text

        keyboard = [
            ["SCIENCE 🧪", "MATHS 📐"],
            ["ENGLISH 📄"]
        ]

        await update.message.reply_text("Select Subject", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    # Subject
    elif "class" in context.user_data and "subject" not in context.user_data:
        context.user_data["subject"] = text

        keyboard = [["Notes", "PYQ"]]

        await update.message.reply_text("Select Type", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    # Show Material
    elif "subject" in context.user_data:
        cls = context.user_data["class"]
        sub = context.user_data["subject"]
        typ = text

        key = f"{cls}|{sub}|{typ}"

        materials = data["categories"].get(key)

        if materials:
            for item in materials:
                await update.message.reply_text(item["text"])
        else:
            await update.message.reply_text("No material found ❌")

        return

# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()