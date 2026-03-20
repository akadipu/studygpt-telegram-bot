import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745

DATA_FILE = "data.json"

active_users = set()
chat_messages = {}   # user_id: [(user_msg_id, admin_msg_id)]
user_timers = {}     # user_id: asyncio task

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
    await asyncio.sleep(180)  # 3 min inactivity

    if user_id in active_users:
        active_users.discard(user_id)

        msgs = chat_messages.get(user_id, [])

        # delete user-side messages
        for user_msg_id, _ in msgs:
            try:
                await context.bot.delete_message(user_id, user_msg_id)
            except:
                pass

        chat_messages[user_id] = []

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Session expired due to inactivity."
            )
        except:
            pass

        user_timers.pop(user_id, None)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Study Material", callback_data="study")],
        [InlineKeyboardButton("📞 Contact Us", callback_data="contact")]
    ]
    await update.message.reply_text(
        "Welcome!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= ADMIN =================

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

    admin_actions = ["add_cat", "add_mat", "edit_mat", "delete_mat"]

    if query.data in admin_actions and user_id != ADMIN_ID:
        return

    # ===== STUDY =====
    if query.data == "study":
        data = load_data()

        if not data["categories"]:
            await query.message.reply_text("No study material yet.")
            return

        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")]
                    for cat in data["categories"]]

        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])

        await query.message.reply_text(
            "Choose category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("cat_"):
        cat = query.data.replace("cat_", "")
        data = load_data()

        for item in data["categories"].get(cat, []):
            keyboard = [[InlineKeyboardButton("Open Link", url=item["text"].split()[-1])]]

            await context.bot.send_message(
                user_id,
                f"{item['text']}\n🆔 {item['id']}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # ===== CONTACT =====
    elif query.data == "contact":
        active_users.add(user_id)

        keyboard = [
            [InlineKeyboardButton("❌ End Chat", callback_data="end_chat")],
            [InlineKeyboardButton("🗑 Delete Messages", callback_data="delete_msgs")]
        ]

        await query.message.reply_text(
            "Connected to StudyGPT Support Team.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # start timer
        if user_id in user_timers:
            user_timers[user_id].cancel()

        task = asyncio.create_task(expire_chat(user_id, context))
        user_timers[user_id] = task

    elif query.data == "end_chat":
        active_users.discard(user_id)

        if user_id in user_timers:
            user_timers[user_id].cancel()
            user_timers.pop(user_id, None)

        await query.message.reply_text("Chat ended.")

    elif query.data == "delete_msgs":
        msgs = chat_messages.get(user_id, [])

        for u, a in msgs:
            try:
                await context.bot.delete_message(user_id, u)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, a)
            except:
                pass

        chat_messages[user_id] = []
        await query.message.reply_text("Messages deleted.")

    elif query.data == "back":
        await start(update, context)

    # ===== ADMIN ACTIONS =====
    elif query.data == "add_cat":
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
            data["categories"][context.user_data["category"]].append(
                {"id": new_id, "text": text}
            )
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

        # ===== ADMIN REPLY (ANONYMOUS) =====
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

    # ===== USER → ADMIN =====
    elif user_id in active_users:

        # reset timer
        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))

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