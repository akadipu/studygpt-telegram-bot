import os
import json
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

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"],
        ["📞 Contact Us"]
    ]

    await update.message.reply_text(
        "Choose your class 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

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

    elif cls == "Class 12th":
        keyboard = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "📄 PYQs"]]

    keyboard.append(["⬅ Back", "🏠 Main Menu"])

    await update.message.reply_text(
        f"{context.user_data.get('subject')}",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else ""

    data = load_data()

    # ===== SAFE EXIT (TOP PRIORITY) =====
    if user_id == ADMIN_ID and text == "🛑 Safe Exit":
        context.user_data.pop("send_mode", None)

        keyboard = [
            ["➕ Add Material", "❌ Delete Material"],
            ["📨 Send Message"]
        ]

        await update.message.reply_text(
            "✅ Exited send mode safely.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # ===== MAIN MENU =====
    if text == "🏠 Main Menu":
        await start(update, context)
        return

    # ===== BACK BUTTON =====
    if text == "⬅ Back":
        last = context.user_data.get("last")

        if last == "subject":
            await show_subjects(update, context)

        elif last == "material":
            await show_materials(update, context)

        else:
            await start(update, context)

        return

    # ===== SEND MESSAGE START =====
    if user_id == ADMIN_ID and text == "📨 Send Message":
        context.user_data["send_mode"] = True

        keyboard = [["🛑 Safe Exit"]]

        await update.message.reply_text(
            "Send message to user:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # ===== SEND MODE ACTIVE =====
    if user_id == ADMIN_ID and context.user_data.get("send_mode"):

        # ignore menu clicks
        if text in ["➕ Add Material", "❌ Delete Material", "📨 Send Message"]:
            return

        if update.message.text:
            await context.bot.send_message(TARGET_USER_ID, update.message.text)

        elif update.message.photo:
            await context.bot.send_photo(
                TARGET_USER_ID,
                photo=update.message.photo[-1].file_id,
                caption=update.message.caption
            )

        elif update.message.video:
            await context.bot.send_video(
                TARGET_USER_ID,
                video=update.message.video.file_id,
                caption=update.message.caption
            )

        elif update.message.document:
            await context.bot.send_document(
                TARGET_USER_ID,
                document=update.message.document.file_id,
                caption=update.message.caption
            )

        else:
            await update.message.reply_text("Unsupported format")

        return

    # ===== CLASS =====
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        context.user_data["last"] = "main"
        await show_subjects(update, context)
        return

    # ===== SUBJECT =====
    subjects = [
        "SCIENCE 🧪", "MATHEMATICS 📐", "ECONOMICS 💳",
        "HISTORY 🏆", "POL. SCIENCE 👮", "GEOGRAPHY 🌍",
        "ENGLISH 📄", "PHYSICS ⚛️", "CHEMISTRY 🧪",
        "BIOLOGY 🌱", "MATHS 📐"
    ]

    if text in subjects:
        context.user_data["subject"] = text
        context.user_data["last"] = "subject"
        await show_materials(update, context)
        return

    # ================= ADMIN ADD =================

    if user_id == ADMIN_ID and text == "➕ Add Material":
        context.user_data["step"] = "class"
        await update.message.reply_text("Select Class:")
        return

    if user_id == ADMIN_ID and context.user_data.get("step"):

        step = context.user_data["step"]

        if step == "class":
            context.user_data["class"] = text
            context.user_data["step"] = "subject"
            await show_subjects(update, context)
            return

        elif step == "subject":
            context.user_data["subject"] = text
            context.user_data["step"] = "type"
            await show_materials(update, context)
            return

        elif step == "type":
            context.user_data["type"] = text
            context.user_data["step"] = "content"
            await update.message.reply_text("Send material:")
            return

        elif step == "content":

            cls = context.user_data["class"]
            sub = context.user_data["subject"]
            typ = context.user_data["type"]

            data.setdefault("categories", {})
            data["categories"].setdefault(cls, {})
            data["categories"][cls].setdefault(sub, {})
            data["categories"][cls][sub].setdefault(typ, [])

            item = {}

            if update.message.text:
                item = {"type": "text", "content": update.message.text}

            elif update.message.document:
                item = {"type": "document", "file_id": update.message.document.file_id}

            elif update.message.photo:
                item = {"type": "photo", "file_id": update.message.photo[-1].file_id}

            elif update.message.video:
                item = {"type": "video", "file_id": update.message.video.file_id}

            else:
                await update.message.reply_text("Unsupported!")
                return

            data["categories"][cls][sub][typ].append(item)
            save_data(data)

            context.user_data.clear()
            await update.message.reply_text("✅ Added!")
            return

    # ================= DELETE =================

    if user_id == ADMIN_ID and text == "❌ Delete Material":
        context.user_data["del"] = "class"
        await update.message.reply_text("Select Class:")
        return

    if user_id == ADMIN_ID and context.user_data.get("del"):

        step = context.user_data["del"]

        if step == "class":
            context.user_data["class"] = text
            context.user_data["del"] = "subject"
            await show_subjects(update, context)
            return

        elif step == "subject":
            context.user_data["subject"] = text
            context.user_data["del"] = "type"
            await show_materials(update, context)
            return

        elif step == "type":

            cls = context.user_data["class"]
            sub = context.user_data["subject"]
            typ = text

            items = data.get("categories", {}).get(cls, {}).get(sub, {}).get(typ, [])

            if not items:
                await update.message.reply_text("No material found")
                context.user_data.clear()
                return

            items.pop()
            save_data(data)

            context.user_data.clear()
            await update.message.reply_text("❌ Deleted last item")
            return

    # ================= USER VIEW =================

    cls = context.user_data.get("class")
    sub = context.user_data.get("subject")

    if cls and sub:
        context.user_data["last"] = "material"

        materials = data.get("categories", {}).get(cls, {}).get(sub, {}).get(text, [])

        if not materials:
            await update.message.reply_text("No material available")
            return

        for item in materials:
            if item["type"] == "text":
                await update.message.reply_text(item["content"])

            elif item["type"] == "document":
                await update.message.reply_document(item["file_id"])

            elif item["type"] == "photo":
                await update.message.reply_photo(item["file_id"])

            elif item["type"] == "video":
                await update.message.reply_video(item["file_id"])

        return

# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()
