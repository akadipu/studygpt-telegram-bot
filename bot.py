import os
import json
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 8558716745 
DATA_FILE = "data.json"

# State tracking
active_users = set()
user_timers = {}
chat_messages = {}

# ================= DATA PERSISTENCE =================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"categories": {}}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"categories": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= SESSION MANAGEMENT =================

async def expire_chat(user_id, context):
    await asyncio.sleep(180)
    if user_id in active_users:
        active_users.discard(user_id)
        chat_messages[user_id] = []
        try:
            await context.bot.send_message(user_id, "⏱ Session expired.")
            await start(None, context, user_id)
        except: pass

# ================= MENUS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, alt_user_id=None):
    uid = alt_user_id or update.effective_user.id
    context.user_data.clear()
    
    keyboard = [["Class 9th", "Class 10th"], ["Class 11th", "Class 12th"], ["📞 Contact Us"]]
    text = "🚀 StudyGPT: Ace your exams with Handwritten Notes, Mindmaps, and Solved PYQs!\n\nChoose your class 👇"
    
    if update:
        await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    else:
        await context.bot.send_message(uid, text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def show_subjects(update, context):
    cls = context.user_data.get("class")
    if "9" in cls or "10" in cls:
        kb = [["SCIENCE 🧪", "MATHEMATICS 📐"], ["ECONOMICS 💳", "HISTORY 🏆"], ["POL. SCIENCE 👮", "GEOGRAPHY 🌍"], ["ENGLISH 📄"]]
    else:
        kb = [["PHYSICS ⚛️", "CHEMISTRY 🧪"], ["BIOLOGY 🌱", "MATHS 📐"], ["ENGLISH 📄"]]
    kb.append(["⬅ Back", "🏠 Main Menu"])
    await update.message.reply_text(f"{cls} Subjects", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def show_materials(update, context):
    kb = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "📄 PYQs"], ["⬅ Back", "🏠 Main Menu"]]
    await update.message.reply_text(f"Select Material for {context.user_data.get('subject')}", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# ================= MAIN HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or ""

    # 1. ADMIN - REPLY SYSTEM (When replying to a forwarded user message)
    if user_id == ADMIN_ID and update.message.reply_to_message:
        target_user = context.bot_data.get(update.message.reply_to_message.message_id)
        if target_user:
            sent = await update.message.copy(target_user)
            chat_messages.setdefault(target_user, []).append((sent.message_id, update.message.message_id))
            return

    # 2. ADMIN - ADD/DELETE SYSTEM
    if user_id == ADMIN_ID:
        if text in ["➕ Add Material", "❌ Delete Material"]:
            context.user_data["admin_mode"] = "ADD" if "Add" in text else "DELETE"
            context.user_data["admin_state"] = "selecting_class"
            kb = [["Class 9th", "Class 10th"], ["Class 11th", "Class 12th"], ["🏠 Main Menu"]]
            await update.message.reply_text(f"🛠 {context.user_data['admin_mode']} MODE\nSelect Class:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return

        state = context.user_data.get("admin_state")
        if state == "selecting_class" and "Class" in text:
            context.user_data["temp_class"] = text
            context.user_data["admin_state"] = "selecting_subject"
            await update.message.reply_text("Type the Subject name (Exactly as it appears in menus):")
            return

        if state == "selecting_subject":
            context.user_data["temp_subject"] = text
            context.user_data["admin_state"] = "selecting_type"
            kb = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "📄 PYQs"], ["🏠 Main Menu"]]
            await update.message.reply_text("Select Category:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return

        if state == "selecting_type":
            mode, c, s, t = context.user_data.get("admin_mode"), context.user_data["temp_class"], context.user_data["temp_subject"], text
            if mode == "DELETE":
                data = load_data()
                if c in data["categories"] and s in data["categories"][c] and t in data["categories"][c][s]:
                    del data["categories"][c][s][t]
                    save_data(data)
                    await update.message.reply_text(f"🗑 Deleted {t} for {s}.")
                else: await update.message.reply_text("❌ No data found.")
                context.user_data.clear()
                return
            else:
                context.user_data["temp_type"] = t
                context.user_data["admin_state"] = "uploading"
                await update.message.reply_text(f"📤 Send the File, Photo, or Link for {s}:")
                return

        if state == "uploading":
            f_id = update.message.document.file_id if update.message.document else (update.message.photo[-1].file_id if update.message.photo else update.message.text)
            if f_id:
                data = load_data()
                c, s, t = context.user_data["temp_class"], context.user_data["temp_subject"], context.user_data["temp_type"]
                data.setdefault("categories", {}).setdefault(c, {}).setdefault(s, {}).setdefault(t, []).append(f_id)
                save_data(data)
                await update.message.reply_text("✅ Added successfully!")
                context.user_data.clear()
                return

    # 3. NAVIGATION
    if text == "🏠 Main Menu":
        await start(update, context)
        return

    if text == "⬅ Back":
        last = context.user_data.get("last")
        if last == "class": await show_subjects(update, context)
        else: await start(update, context)
        return

    # 4. USER - CLASS/SUBJECT SELECTION
    if text in ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]:
        context.user_data["class"] = text
        context.user_data["last"] = "main"
        await show_subjects(update, context)
        return

    subjects = ["SCIENCE 🧪", "MATHEMATICS 📐", "ECONOMICS 💳", "HISTORY 🏆", "POL. SCIENCE 👮", "GEOGRAPHY 🌍", "ENGLISH 📄", "PHYSICS ⚛️", "CHEMISTRY 🧪", "BIOLOGY 🌱", "MATHS 📐"]
    if any(s in text for s in subjects):
        context.user_data["subject"] = text
        context.user_data["last"] = "class"
        await show_materials(update, context)
        return

    # 5. USER - MATERIAL RETRIEVAL
    if text in ["📚 Lectures", "📝 Notes", "🧠 Mindmaps", "📄 PYQs"]:
        data = load_data()
        c, s = context.user_data.get("class"), context.user_data.get("subject")
        try:
            files = data["categories"][c][s][text]
            for f_id in files:
                if "http" in str(f_id): await update.message.reply_text(f"🔗 Link: {f_id}")
                else: await context.bot.send_document(user_id, f_id)
        except:
            await update.message.reply_text("⌛ Nothing uploaded here yet.")
        return

    # 6. USER - CONTACT SYSTEM
    if text == "📞 Contact Us":
        active_users.add(user_id)
        if user_id in user_timers: user_timers[user_id].cancel()
        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))
        await update.message.reply_text("💬 Support Mode Active. Send your message and we will reply!", reply_markup=ReplyKeyboardMarkup([["❌ End Chat"]], resize_keyboard=True))
        return

    if user_id in active_users:
        if text == "❌ End Chat":
            active_users.discard(user_id)
            await start(update, context)
            return
        # Forward to Admin
        admin_msg = await update.message.forward(ADMIN_ID)
        context.bot_data[admin_msg.message_id] = user_id
        return

# ================= ADMIN COMMAND =================

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kb = [["➕ Add Material", "❌ Delete Material"], ["🏠 Main Menu"]]
    await update.message.reply_text("👨‍💻 Admin Panel", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# ================= INIT =================

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()
