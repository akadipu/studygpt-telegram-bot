import os
import json
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745
TARGET_USER_ID = 8071314699

active_users = set()
user_timers = {}
chat_messages = {}

# ================= DELETE SYSTEM =================

async def clear_all_chat(user_id, context):
    for u_msg, a_msg in chat_messages.get(user_id, []):

        if u_msg:
            try:
                await context.bot.delete_message(user_id, u_msg)
            except:
                pass

        if a_msg:
            try:
                await context.bot.delete_message(ADMIN_ID, a_msg)
            except:
                pass
            try:
                await context.bot.delete_message(user_id, a_msg)
            except:
                pass

    chat_messages[user_id] = []

# ================= TIMEOUT =================

async def expire_chat(user_id, context):
    await asyncio.sleep(180)

    if user_id in active_users:
        await clear_all_chat(user_id, context)
        active_users.discard(user_id)

        try:
            await context.bot.send_message(user_id, "Session expired.")
            await context.bot.send_message(
                user_id,
                "Select your class:",
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
    keyboard = [
        ["Class 9th", "Class 10th"],
        ["Class 11th", "Class 12th"],
        ["📞 Contact Us"]
    ]

    await update.message.reply_text(
        "Select your class:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        ["📩 Send Message"],
        ["⬅ Back"]
    ]

    await update.message.reply_text(
        "Admin Panel",
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

# ================= MATERIAL =================

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

# ================= MAIN =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text or ""

    # ===== BACK =====
    if text == "⬅ Back":
        context.user_data.clear()
        await start(update, context)
        return

    # ===== MAIN MENU =====
    if text == "🏠 Main Menu":
        await start(update, context)
        return

    # ===== CONTACT =====
    if text == "📞 Contact Us":
        active_users.add(user_id)

        keyboard = [["🧹 Clear History", "❌ End Chat"]]

        await update.message.reply_text(
            "Support chat started.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))
        return

    # ===== CLEAR HISTORY =====
    if text == "🧹 Clear History" and user_id in active_users:
        await clear_all_chat(user_id, context)

        if user_id in user_timers:
            user_timers[user_id].cancel()

        active_users.discard(user_id)

        await update.message.reply_text("Chat cleared.")
        await start(update, context)
        return

    # ===== END CHAT =====
    if text == "❌ End Chat" and user_id in active_users:
        await clear_all_chat(user_id, context)

        if user_id in user_timers:
            user_timers[user_id].cancel()

        active_users.discard(user_id)

        await update.message.reply_text("Chat ended.")
        await start(update, context)
        return

    # ===== USER CHAT =====
    if user_id in active_users:

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))

        sender = update.message.from_user
        caption = f"{sender.first_name} ({sender.id})"

        if update.message.text:
            admin_msg = await context.bot.send_message(ADMIN_ID, f"{caption}\n\n{text}")
        elif update.message.photo:
            admin_msg = await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption)
        elif update.message.document:
            admin_msg = await context.bot.send_document(ADMIN_ID, update.message.document.file_id, caption=caption)
        elif update.message.video:
            admin_msg = await context.bot.send_video(ADMIN_ID, update.message.video.file_id, caption=caption)
        elif update.message.audio:
            admin_msg = await context.bot.send_audio(ADMIN_ID, update.message.audio.file_id, caption=caption)
        else:
            return

        chat_messages.setdefault(user_id, []).append(
            (update.message.message_id, admin_msg.message_id)
        )
        return

    # ===== ADMIN PANEL WITH CONFIRM =====
    if user_id == ADMIN_ID:

        # Start send mode
        if text == "📩 Send Message":
            context.user_data["mode"] = "preview"
            await update.message.reply_text("Send message to preview.")
            return

        # Preview step
        if context.user_data.get("mode") == "preview":

            context.user_data["preview_msg"] = update.message

            keyboard = [["✅ Confirm", "❌ Cancel"]]

            await update.message.reply_text(
                "Preview ready. Confirm?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )

            context.user_data["mode"] = "confirm"
            return

        # Confirm step
        if context.user_data.get("mode") == "confirm":

            if text == "❌ Cancel":
                context.user_data.clear()
                await update.message.reply_text("Cancelled.")
                return

            if text == "✅ Confirm":

                msg = context.user_data.get("preview_msg")

                try:
                    if msg.text:
                        sent = await context.bot.send_message(TARGET_USER_ID, msg.text)
                    elif msg.photo:
                        sent = await context.bot.send_photo(TARGET_USER_ID, msg.photo[-1].file_id, caption=msg.caption)
                    elif msg.document:
                        sent = await context.bot.send_document(TARGET_USER_ID, msg.document.file_id, caption=msg.caption)
                    elif msg.video:
                        sent = await context.bot.send_video(TARGET_USER_ID, msg.video.file_id, caption=msg.caption)
                    elif msg.audio:
                        sent = await context.bot.send_audio(TARGET_USER_ID, msg.audio.file_id, caption=msg.caption)
                    else:
                        return

                    chat_messages.setdefault(TARGET_USER_ID, []).append((None, sent.message_id))

                    await update.message.reply_text("Message sent")

                except:
                    await update.message.reply_text("Failed")

                context.user_data.clear()
                return

    # ===== CLASS =====
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        await show_subjects(update, context)
        return

    # ===== SUBJECT =====
    subjects = ["SCIENCE 🧪","MATHEMATICS 📐","ECONOMICS 💳","HISTORY 🏆",
                "POL. SCIENCE 👮","GEOGRAPHY 🌍","ENGLISH 📄",
                "PHYSICS ⚛️","CHEMISTRY 🧪","BIOLOGY 🌱","MATHS 📐"]

    if text in subjects:
        context.user_data["subject"] = text
        await show_materials(update, context)
        return

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()