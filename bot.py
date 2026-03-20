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
TARGET_USER_ID = 8558716745
DATA_FILE = "data.json"

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

        for user_msg_id, admin_msg_id in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, user_msg_id)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, admin_msg_id)
            except:
                pass

        chat_messages[user_id] = []

        try:
            await context.bot.send_message(user_id, "Session expired & chat cleared.")
            await asyncio.sleep(1)
            await context.bot.send_message(
                user_id,
                "🚀 StudyGPT: Ace your exams with Handwritten Notes, Mindmaps, and Solved PYQs!\n\nChoose your class 👇",
                reply_markup=ReplyKeyboardMarkup(
                    [["Class 9th", "Class 10th"],
                     ["Class 11th", "Class 12th"],
                     ["📞 Contact Us"]],
                    resize_keyboard=True
                )
            )
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
        "🚀 StudyGPT: Ace your exams with Handwritten Notes, Mindmaps, and Solved PYQs!\n\nChoose your class 👇",
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

# ================= SUBJECT MENU =================

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
        context.user_data.get("Subjects"),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else ""

    data = load_data()

    # ===== ADMIN REPLY SYSTEM =====
    if user_id == ADMIN_ID and update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        target_user = context.bot_data.get(replied_msg_id)

        if target_user:
            msg = update.message

            if msg.text:
                sent = await context.bot.send_message(target_user, msg.text)

            elif msg.photo:
                sent = await context.bot.send_photo(
                    target_user,
                    photo=msg.photo[-1].file_id,
                    caption=msg.caption
                )

            elif msg.video:
                sent = await context.bot.send_video(
                    target_user,
                    video=msg.video.file_id,
                    caption=msg.caption
                )

            elif msg.document:
                sent = await context.bot.send_document(
                    target_user,
                    document=msg.document.file_id,
                    caption=msg.caption
                )

            elif msg.audio:
                sent = await context.bot.send_audio(
                    target_user,
                    audio=msg.audio.file_id,
                    caption=msg.caption
                )

            else:
                return

            # 🔥 TRACK ADMIN REPLY
            chat_messages.setdefault(target_user, []).append(
                (sent.message_id, update.message.message_id)
            )

            return

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

        keyboard = [["🧹 Clear History", "❌ End Chat"]]

        await update.message.reply_text(
            "StudyGPT Support Team:\n\n💬 Need help? Send your message here and our team will get back to you directly! 🚀",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))
        return

    # ===== CLEAR HISTORY =====
    if text == "🧹 Clear History" and user_id in active_users:
        for user_msg_id, admin_msg_id in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, user_msg_id)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, admin_msg_id)
            except:
                pass

        chat_messages[user_id] = []
        await update.message.reply_text("🧹 History cleared!")
        return

    # ===== END CHAT =====
    if text == "❌ End Chat" and user_id in active_users:

        for user_msg_id, admin_msg_id in chat_messages.get(user_id, []):
            try:
                await context.bot.delete_message(user_id, user_msg_id)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, admin_msg_id)
            except:
                pass

        chat_messages[user_id] = []
        active_users.discard(user_id)

        await update.message.reply_text("Chat ended & history cleared.")
        await asyncio.sleep(1)
        await start(update, context)
        return

    # ===== CHAT (MEDIA + TEXT) =====
    if user_id in active_users:

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))

        user = update.message
        sender = update.message.from_user
        caption = f"{sender.first_name}\n🆔 {sender.id}"

        if user.text:
            admin_msg = await context.bot.send_message(
                ADMIN_ID,
                f"{caption}\n\n{user.text}"
            )
        elif user.photo:
            admin_msg = await context.bot.send_photo(
                ADMIN_ID,
                photo=user.photo[-1].file_id,
                caption=caption
            )
        elif user.video:
            admin_msg = await context.bot.send_video(
                ADMIN_ID,
                video=user.video.file_id,
                caption=caption
            )
        elif user.document:
            admin_msg = await context.bot.send_document(
                ADMIN_ID,
                document=user.document.file_id,
                caption=caption
            )
        elif user.audio:
            admin_msg = await context.bot.send_audio(
                ADMIN_ID,
                audio=user.audio.file_id,
                caption=caption
            )
        else:
            return

        chat_messages.setdefault(user_id, []).append(
            (update.message.message_id, admin_msg.message_id)
        )

        # 🔥 MAP ADMIN MESSAGE → USER
        context.bot_data[admin_msg.message_id] = user_id

        return
        
    # ===== SAFE EXIT =====
    if user_id == ADMIN_ID and text == "🛑 Safe Exit":
        context.user_data.pop("send_mode", None)
        await admin(update, context)
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


    # ===== CLASS SELECT =====
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        context.user_data["last"] = "main"
        await show_subjects(update, context)

# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()
