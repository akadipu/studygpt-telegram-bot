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
        "🚀 StudyGPT: Ace your exams with Notes & PYQs!\n\nChoose your class 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        ["➕ Add Material"],
        ["✏️ Edit Material"],
        ["❌ Delete Material"]
    ]

    await update.message.reply_text(
        "Admin Panel",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    data = load_data()

    # ================= ADMIN =================
    if user_id == ADMIN_ID:

        if text == "➕ Add Material":
            context.user_data["step"] = "add_class"
            await update.message.reply_text("Enter Class:")
            return

        elif context.user_data.get("step") == "add_class":
            context.user_data["class"] = text
            context.user_data["step"] = "add_subject"
            await update.message.reply_text("Enter Subject:")
            return

        elif context.user_data.get("step") == "add_subject":
            context.user_data["subject"] = text
            context.user_data["step"] = "add_type"
            await update.message.reply_text("Enter Type:")
            return

        elif context.user_data.get("step") == "add_type":
            context.user_data["type"] = text
            context.user_data["step"] = "add_content"
            await update.message.reply_text("Send Content:")
            return

        elif context.user_data.get("step") == "add_content":
            key = f"{context.user_data['class']}|{context.user_data['subject']}|{context.user_data['type']}"
            data["categories"].setdefault(key, []).append({"text": text})
            save_data(data)

            await update.message.reply_text("✅ Added")
            context.user_data.clear()
            return

        # DELETE
        if text == "❌ Delete Material":
            keys = list(data["categories"].keys())
            msg = "\n".join([f"{i+1}. {k}" for i, k in enumerate(keys)])
            context.user_data["keys"] = keys
            context.user_data["step"] = "delete"
            await update.message.reply_text(f"Select:\n{msg}")
            return

        elif context.user_data.get("step") == "delete":
            try:
                key = context.user_data["keys"][int(text)-1]
                del data["categories"][key]
                save_data(data)
                await update.message.reply_text("Deleted")
            except:
                await update.message.reply_text("Invalid")
            context.user_data.clear()
            return

        # EDIT
        if text == "✏️ Edit Material":
            keys = list(data["categories"].keys())
            msg = "\n".join([f"{i+1}. {k}" for i, k in enumerate(keys)])
            context.user_data["keys"] = keys
            context.user_data["step"] = "edit"
            await update.message.reply_text(f"Select:\n{msg}")
            return

        elif context.user_data.get("step") == "edit":
            try:
                key = context.user_data["keys"][int(text)-1]
                context.user_data["edit_key"] = key
                context.user_data["step"] = "edit_content"
                await update.message.reply_text("Send new content:")
            except:
                await update.message.reply_text("Invalid")
            return

        elif context.user_data.get("step") == "edit_content":
            key = context.user_data["edit_key"]
            data["categories"][key] = [{"text": text}]
            save_data(data)
            await update.message.reply_text("Updated")
            context.user_data.clear()
            return

    # ================= USER FLOW =================

    # Class selected
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text

        keyboard = [
            ["SCIENCE 🧪", "MATHS 📐"],
            ["ENGLISH 📄"]
        ]

        await update.message.reply_text(
            "Select Subject",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # Subject selected
    elif "class" in context.user_data and "subject" not in context.user_data:
        context.user_data["subject"] = text

        keyboard = [
            ["Notes", "PYQ"],
            ["Back"]
        ]

        await update.message.reply_text(
            "Select Type",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    # Type selected → SHOW MATERIAL
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