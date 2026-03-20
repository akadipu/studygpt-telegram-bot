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
DATA_FILE = "data.json"

active_users = set()
user_timers = {}

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
        try:
            await context.bot.send_message(user_id, "Session expired.")
        except:
            pass

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"],
        ["📞 Contact Us"]
    ]

    await update.message.reply_text(
        "🚀 StudyGPT: Ace your exams with Handwritten Notes, Mindmaps, and Solved PYQs! 🎓/n /nChoose your class 👇",
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

# ================= SUBJECT MENU =================

async def show_subjects(update, context):
    cls = context.user_data.get("class")

    if cls == "Class 9th":
        keyboard = [
            ["SCIENCE 🧪", "MATHEMATICS 📐"],
            ["ECONOMICS 💳", "HISTORY 🏆"],
            ["POL. SCIENCE 👮", "GEOGRAPHY 🌍"],
            ["ENGLISH 📄"]
        ]

    elif cls == "Class 10th":
        keyboard = [
            ["SCIENCE 🧪", "MATHEMATICS 📐"],
            ["ECONOMICS 💳", "HISTORY 🏆"],
            ["POL. SCIENCE 👮", "GEOGRAPHY 🌍"],
            ["ENGLISH 📄"]
        ]

    elif cls == "Class 11th":
        keyboard = [
            ["PHYSICS ⚛️", "CHEMISTRY 🧪"],
            ["BIOLOGY 🌱", "MATHS 📐"],
            ["ENGLISH 📄"]
        ]

    else:  # Class 12th
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

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    data = load_data()

    # ===== MAIN MENU =====
    if text == "🏠 Main Menu":
        await start(update, context)
        return

    # ===== BACK =====
    if text == "⬅ Back":
        last = context.user_data.get("last")

        if last == "main":
            await start(update, context)
        elif last == "class":
            await show_subjects(update, context)
        else:
            await start(update, context)
        return

    # ===== CONTACT =====
    if text == "📞 Contact Us":
        active_users.add(user_id)

        await update.message.reply_text(
            "StudyGPT Support Team\n(3 min inactivity timeout)"
        )

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))
        return

    # ===== CHAT =====
    if user_id in active_users:
        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))

        user = update.message.from_user

        await context.bot.send_message(
            ADMIN_ID,
            f"{user.first_name}\n🆔 {user_id}\n\n{text}"
        )
        return

    # ================= ADMIN FLOW =================

    if user_id == ADMIN_ID:

        if text == "➕ Add Material":
            context.user_data["admin_step"] = "class"

            keyboard = [
                ["Class 9th", "Class 10th"],
                ["Class 11th", "Class 12th"]
            ]

            await update.message.reply_text(
                "Select Class",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

        elif context.user_data.get("admin_step") == "class":
            context.user_data["class"] = text
            context.user_data["admin_step"] = "subject"
            await show_subjects(update, context)
            return

        elif context.user_data.get("admin_step") == "subject":
            context.user_data["subject"] = text
            context.user_data["admin_step"] = "type"

            cls = context.user_data["class"]

            if cls in ["Class 9th", "Class 11th"]:
                keyboard = [
                    ["Lectures 📚", "Handwritten Notes 📝"],
                    ["NCERT Exercises ✍️", "Mindmaps 🤩"]
                ]
            elif cls == "Class 12th":
                keyboard = [
                    ["Lectures 🎥", "Handwritten Notes 📝"],
                    ["NCERT Exercises ✍️", "Mindmaps 🔥"],
                    ["PYQs 📄"]
                ]
            else:
                keyboard = [
                    ["Lectures 📚", "Handwritten Notes 📝"],
                    ["NCERT Exercises ✍️", "Mindmaps 🤩"],
                    ["PYQs 📄"],
                    ["Top 100 Most Expected Questions 😎"]
                ]

            await update.message.reply_text(
                "Select Content Type",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

        elif context.user_data.get("admin_step") == "type":
            context.user_data["type"] = text
            context.user_data["admin_step"] = "final"

            await update.message.reply_text("Send material")
            return

        elif context.user_data.get("admin_step") == "final":
            key = f"{context.user_data['class']}|{context.user_data['subject']}|{context.user_data['type']}"

            data["categories"].setdefault(key, []).append({"text": text})
            save_data(data)

            await update.message.reply_text("✅ Material Added")
            context.user_data.clear()
            return

    # ================= USER FLOW =================

    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        context.user_data["last"] = "main"
        await show_subjects(update, context)

    elif text in [
        "SCIENCE 🧪", "MATHEMATICS 📐", "ECONOMICS 💳",
        "HISTORY 🏆", "POL. SCIENCE 👮", "GEOGRAPHY 🌍",
        "ENGLISH 📄", "PHYSICS ⚛️", "CHEMISTRY 🧪",
        "BIOLOGY 🌱", "MATHS 📐"
    ]:
        context.user_data["subject"] = text
        context.user_data["last"] = "class"

        cls = context.user_data.get("class")

        if cls == "Class 9th":
            keyboard = [
                ["Lectures 📚", "Handwritten Notes 📝"],
                ["NCERT Exercises ✍️", "Mindmaps 🤩"]
            ]
        elif cls == "Class 11th":
            keyboard = [
                ["Lectures 🎥", "Handwritten Notes 📝"],
                ["NCERT Exercises ✍️", "Mindmaps 🔥"]
            ]
        elif cls == "Class 12th":
            keyboard = [
                ["Lectures 🎥", "Handwritten Notes 📝"],
                ["NCERT Exercises ✍️", "Mindmaps 🔥"],
                ["PYQs 📄"]
            ]
        else:
            keyboard = [
                ["Lectures 📚", "Handwritten Notes 📝"],
                ["NCERT Exercises ✍️", "Mindmaps 🤩"],
                ["PYQs 📄"],
                ["Top 100 Most Expected Questions 😎"]
            ]

        keyboard.append(["⬅ Back", "🏠 Main Menu"])

        await update.message.reply_text(
            "Choose content 👇",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    # ===== FETCH =====
    elif text in [
        "Lectures 📚", "Lectures 🎥",
        "Handwritten Notes 📝",
        "NCERT Exercises ✍️",
        "Mindmaps 🤩", "Mindmaps 🔥",
        "PYQs 📄",
        "Top 100 Most Expected Questions 😎"
    ]:

        key = f"{context.user_data.get('class')}|{context.user_data.get('subject')}|{text}"

        materials = data["categories"].get(key, [])

        if not materials:
            await update.message.reply_text("No material yet.")
            return

        for item in materials:
            await update.message.reply_text(item["text"])

# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
