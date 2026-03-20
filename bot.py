import os
import json
import asyncio
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745

DATA_FILE = "data.json"

active_users = set()
chat_messages = {}
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

def get_next_id(data):
    all_ids = []
    for cat in data["categories"].values():
        for item in cat:
            all_ids.append(item["id"])
    return max(all_ids, default=0) + 1

# ================= SESSION EXPIRY =================

async def expire_chat(user_id, context):
    await asyncio.sleep(180)

    if user_id in active_users:
        active_users.discard(user_id)

        msgs = chat_messages.get(user_id, [])

        for user_msg_id, _ in msgs:
            try:
                await context.bot.delete_message(user_id, user_msg_id)
            except:
                pass

        chat_messages[user_id] = []

        try:
            await context.bot.send_message(
                user_id,
                "Session expired due to inactivity."
            )
        except:
            pass

        user_timers.pop(user_id, None)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"],
        ["📞 Contact Us"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "StudyGPT: Ace your exams with Handwritten Notes, Minmaps, and Solved PYQs! 😎\n\nChoose your class 👇",
        reply_markup=reply_markup
    )

# ================= ADMIN PANEL =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Category", callback_data="add_cat")],
        [InlineKeyboardButton("➕ Add Material", callback_data="add_mat")],
        [InlineKeyboardButton("✏️ Edit Material", callback_data="edit_mat")],
        [InlineKeyboardButton("❌ Delete Material", callback_data="delete_mat")]
    ]

    await update.message.reply_text(
        "Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON HANDLER =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id != ADMIN_ID:
        return

    if query.data == "add_cat":
        context.user_data["action"] = "add_category"
        await query.message.reply_text("Send category name:")

    elif query.data == "add_mat":
        context.user_data["action"] = "choose_category"
        await query.message.reply_text("Send category name:")

    elif query.data == "edit_mat":
        context.user_data["action"] = "edit_id"
        await query.message.reply_text("Send ID:")

    elif query.data == "delete_mat":
        context.user_data["action"] = "delete"
        await query.message.reply_text("Send ID:")

# ================= MESSAGE HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    data = load_data()
    action = context.user_data.get("action")

    # ===== ADMIN =====
    if user_id == ADMIN_ID:

        if action == "add_category":
            data["categories"][text] = []
            save_data(data)
            context.user_data.clear()

        elif action == "choose_category":
            context.user_data["category"] = text
            context.user_data["action"] = "add_text"

        elif action == "add_text":
            new_id = get_next_id(data)
            data["categories"].setdefault(
                context.user_data["category"], []
            ).append({"id": new_id, "text": text})

            save_data(data)
            context.user_data.clear()

        elif action == "delete":
            for cat in data["categories"]:
                data["categories"][cat] = [
                    i for i in data["categories"][cat] if i["id"] != int(text)
                ]
            save_data(data)
            context.user_data.clear()

        elif action == "edit_id":
            context.user_data["edit_id"] = int(text)
            context.user_data["action"] = "edit_text"

        elif action == "edit_text":
            for cat in data["categories"]:
                for item in data["categories"][cat]:
                    if item["id"] == context.user_data["edit_id"]:
                        item["text"] = text
            save_data(data)
            context.user_data.clear()

        elif update.message.reply_to_message:
            try:
                original = update.message.reply_to_message.text
                target_id = int(original.split("🆔")[1].strip())

                await context.bot.send_message(
                    target_id,
                    f"StudyGPT Support Team\n\n{text}"
                )
            except:
                pass

    # ===== USER CLASS BUTTONS =====
    elif text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:

        materials = data["categories"].get(text, [])

        if not materials:
            await update.message.reply_text("No material available yet.")
            return

        for item in materials:
            await update.message.reply_text(item["text"])

    # ===== CONTACT =====
    elif text == "📞 Contact Us":
        active_users.add(user_id)

        await update.message.reply_text(
            "Connected to StudyGPT Support Team.\n(3 min inactivity timeout)"
        )

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(
            expire_chat(user_id, context)
        )

    # ===== USER → ADMIN =====
    elif user_id in active_users:

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(
            expire_chat(user_id, context)
        )

        user = update.message.from_user
        name = user.first_name
        username = f"@{user.username}" if user.username else "No username"

        admin_msg = await context.bot.send_message(
            ADMIN_ID,
            f"{name} ({username})\n🆔 {user_id}\n\n{text}"
        )

        chat_messages.setdefault(user_id, []).append(
            (update.message.message_id, admin_msg.message_id)
        )

    else:
        await update.message.reply_text("Use buttons.")

# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
