import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745
TARGET_USER_ID = 8071314699

active_users = set()
user_timers = {}
chat_messages = {}

# ================= TRACK FUNCTION =================

def track(user_id, msg_id):
    chat_messages.setdefault(user_id, []).append((None, msg_id))

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
                await context.bot.delete_message(user_id, a_msg)
            except:
                pass
            try:
                await context.bot.delete_message(ADMIN_ID, a_msg)
            except:
                pass

    chat_messages[user_id] = []

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "Select your class:",
        reply_markup=ReplyKeyboardMarkup(
            [["Class 9th", "Class 10th"],
             ["Class 11th", "Class 12th"],
             ["📞 Contact Us"]],
            resize_keyboard=True
        )
    )

    track(update.message.from_user.id, msg.message_id)

# ================= TIMEOUT =================

async def expire_chat(user_id, context):
    await asyncio.sleep(180)

    if user_id in active_users:
        await clear_all_chat(user_id, context)
        active_users.discard(user_id)

        try:
            msg = await context.bot.send_message(user_id, "Session expired.")
            track(user_id, msg.message_id)

            msg2 = await context.bot.send_message(
                user_id,
                "Select your class:",
                reply_markup=ReplyKeyboardMarkup(
                    [["Class 9th", "Class 10th"],
                     ["Class 11th", "Class 12th"],
                     ["📞 Contact Us"]],
                    resize_keyboard=True
                )
            )
            track(user_id, msg2.message_id)

        except:
            pass

# ================= MAIN =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text or ""

    # ===== CONTACT =====
    if text == "📞 Contact Us":
        active_users.add(user_id)

        msg = await update.message.reply_text(
            "Support chat started.",
            reply_markup=ReplyKeyboardMarkup(
                [["🧹 Clear History", "❌ End Chat"]],
                resize_keyboard=True
            )
        )
        track(user_id, msg.message_id)

        if user_id in user_timers:
            user_timers[user_id].cancel()

        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))
        return

    # ===== CLEAR HISTORY =====
    if text == "🧹 Clear History" and user_id in active_users:

        try:
            await context.bot.delete_message(user_id, update.message.message_id)
        except:
            pass

        await clear_all_chat(user_id, context)

        if user_id in user_timers:
            user_timers[user_id].cancel()

        active_users.discard(user_id)

        await start(update, context)
        return

    # ===== END CHAT =====
    if text == "❌ End Chat" and user_id in active_users:

        try:
            await context.bot.delete_message(user_id, update.message.message_id)
        except:
            pass

        await clear_all_chat(user_id, context)

        if user_id in user_timers:
            user_timers[user_id].cancel()

        active_users.discard(user_id)

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

    # ===== ADMIN REPLY MODE =====
    if user_id == ADMIN_ID and context.user_data.get("mode") == "reply_mode":

        msg = update.message

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

        except:
            await update.message.reply_text("Failed")

        return

    # ===== ADMIN MODE CONTROL =====
    if user_id == ADMIN_ID:

        if text == "💬 Reply Mode":
            context.user_data["mode"] = "reply_mode"

            await update.message.reply_text(
                "Reply Mode ON",
                reply_markup=ReplyKeyboardMarkup([["❌ Exit Reply Mode"]], resize_keyboard=True)
            )
            return

        if text == "❌ Exit Reply Mode":
            context.user_data.clear()

            await update.message.reply_text(
                "Reply Mode OFF",
                reply_markup=ReplyKeyboardMarkup(
                    [["💬 Reply Mode"]],
                    resize_keyboard=True
                )
            )
            return

    # ===== START MENU =====
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th", "🏠 Main Menu"]:
        await start(update, context)
        return

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()