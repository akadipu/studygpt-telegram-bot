import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745
DATA_FILE = "data.json"

# ================= DATA =================

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"],
        ["📞 Contact Us"]
    ]
    await update.message.reply_text(
        "Select your class:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= ADMIN PANEL =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        ["➕ Add Material", "✏️ Edit/Delete"],
        ["📩 Send Message"],
        ["⬅ Back"]
    ]

    await update.message.reply_text("Admin Panel", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# ================= SUBJECTS =================

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
    subject = context.user_data.get("subject")
    cls = context.user_data.get("class")

    if cls == "Class 10th":
        keyboard = [
            ["Lectures 📖", "Handwritten Notes 🗒️"],
            ["NCERT Exercises ✍️", "Mindmaps 🤩"],
            ["PYQs 📚", "Top 100 Expected Questions 😎"],
            ["⬅ Back", "🏠 Main Menu"]
        ]
    elif cls == "Class 12th":
        keyboard = [
            ["Lectures 📖", "Handwritten Notes 🗒️"],
            ["NCERT Exercises ✍️", "Mindmaps 🤩"],
            ["PYQs 📚"],
            ["⬅ Back", "🏠 Main Menu"]
        ]
    else:
        keyboard = [
            ["Lectures 📖", "Handwritten Notes 🗒️"],
            ["NCERT Exercises ✍️", "Mindmaps 🤩"],
            ["⬅ Back", "🏠 Main Menu"]
        ]

    await update.message.reply_text(
        f"{subject} - Select a resource:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= MAIN HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text or ""

    data = load_data()

    # ===== MAIN MENU =====
    if text == "🏠 Main Menu":
        await start(update, context)
        return

    # ===== CLASS SELECT =====
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        await show_subjects(update, context)
        return

    # ===== SUBJECT SELECT =====
    subjects = [
        "SCIENCE 🧪","MATHEMATICS 📐","ECONOMICS 💳","HISTORY 🏆",
        "POL. SCIENCE 👮","GEOGRAPHY 🌍","ENGLISH 📄",
        "PHYSICS ⚛️","CHEMISTRY 🧪","BIOLOGY 🌱","MATHS 📐"
    ]

    if text in subjects:
        context.user_data["subject"] = text
        await show_materials(update, context)
        return

    # ===== USER VIEW CONTENT =====
    materials = [
        "Lectures 📖","Handwritten Notes 🗒️","NCERT Exercises ✍️",
        "Mindmaps 🤩","PYQs 📚","Top 100 Expected Questions 😎"
    ]

    if text in materials:
        cls = context.user_data.get("class")
        sub = context.user_data.get("subject")

        content = data.get(cls, {}).get(sub, {}).get(text, [])

        if not content:
            await update.message.reply_text("No content available.")
            return

        for item in content:
            try:
                if item["type"] == "text":
                    await update.message.reply_text(item["content"])

                elif item["type"] == "photo":
                    await update.message.reply_photo(item["file_id"], caption=item.get("caption"))

                elif item["type"] == "document":
                    await update.message.reply_document(item["file_id"], caption=item.get("caption"))

                elif item["type"] == "video":
                    await update.message.reply_video(item["file_id"], caption=item.get("caption"))

                elif item["type"] == "audio":
                    await update.message.reply_audio(item["file_id"], caption=item.get("caption"))
            except:
                pass
        return

    # ================= ADMIN =================

    if user_id == ADMIN_ID:

        step = context.user_data.get("admin_step")

        # ADD MATERIAL
        if text == "➕ Add Material":
            context.user_data["admin_step"] = "class"
            await update.message.reply_text("Select Class:")
            return

        if step == "class":
            context.user_data["admin_class"] = text
            context.user_data["admin_step"] = "subject"
            context.user_data["class"] = text
            await show_subjects(update, context)
            return

        if step == "subject":
            context.user_data["admin_subject"] = text
            context.user_data["admin_step"] = "category"
            await show_materials(update, context)
            return

        if step == "category":
            context.user_data["admin_category"] = text
            context.user_data["admin_step"] = "content"
            await update.message.reply_text("Send content now:")
            return

        if step == "content":
            cls = context.user_data["admin_class"]
            sub = context.user_data["admin_subject"]
            cat = context.user_data["admin_category"]

            data.setdefault(cls, {}).setdefault(sub, {}).setdefault(cat, [])

            msg = update.message

            if msg.text:
                item = {"type": "text", "content": msg.text}
            elif msg.photo:
                item = {"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption}
            elif msg.document:
                item = {"type": "document", "file_id": msg.document.file_id, "caption": msg.caption}
            elif msg.video:
                item = {"type": "video", "file_id": msg.video.file_id, "caption": msg.caption}
            elif msg.audio:
                item = {"type": "audio", "file_id": msg.audio.file_id, "caption": msg.caption}
            else:
                await update.message.reply_text("Unsupported format")
                return

            data[cls][sub][cat].append(item)
            save_data(data)

            await update.message.reply_text("Saved successfully")
            context.user_data.clear()
            return

        # DIRECT MESSAGE
        if text == "📩 Send Message":
            context.user_data["admin_step"] = "send_id"
            await update.message.reply_text("Enter User ID:")
            return

        if step == "send_id":
            context.user_data["target"] = int(text)
            context.user_data["admin_step"] = "send_msg"
            await update.message.reply_text("Send message:")
            return

        if step == "send_msg":
            target = context.user_data["target"]
            msg = update.message

            try:
                if msg.text:
                    await context.bot.send_message(target, msg.text)
                elif msg.photo:
                    await context.bot.send_photo(target, msg.photo[-1].file_id, caption=msg.caption)
                elif msg.document:
                    await context.bot.send_document(target, msg.document.file_id, caption=msg.caption)
                elif msg.video:
                    await context.bot.send_video(target, msg.video.file_id, caption=msg.caption)
                elif msg.audio:
                    await context.bot.send_audio(target, msg.audio.file_id, caption=msg.caption)

                await update.message.reply_text("Message sent")
            except:
                await update.message.reply_text("Failed (user must start bot)")

            context.user_data.clear()
            return

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()