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
TARGET_USER_ID = 8071314699
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
            await context.bot.send_message(user_id, "⏳ Session expired & chat cleared.")
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

    context.user_data.clear()

    keyboard = [
        ["➕ Add Material", "❌ Delete Material"],
        ["📋 List Materials", "📨 Send Message"]
    ]

    await update.message.reply_text(
        "Admin Panel 👨‍💻\n\nWhat would you like to do?",
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

    # Track navigation: coming from main menu → back should go to main
    context.user_data["last"] = "main"

    await update.message.reply_text(
        f"📚 {cls} — Choose a Subject:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= MATERIAL TYPE MENU =================

async def show_materials(update, context):
    cls = context.user_data.get("class")
    subject = context.user_data.get("subject")

    if cls in ["Class 9th", "Class 11th"]:
        keyboard = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "❗ Imp Questions"]]
    else:  # 10th and 12th
        keyboard = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "📄 PYQs"]]

    keyboard.append(["⬅ Back", "🏠 Main Menu"])

    # Track navigation: coming from subject → back should go to subjects
    context.user_data["last"] = "class"

    await update.message.reply_text(
        f"📂 {subject} — Choose material type:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= SHOW CONTENT =================

async def show_content(update, context):
    """Send the actual stored files/links for the selected class > subject > type."""
    cls = context.user_data.get("class")
    subject = context.user_data.get("subject")
    mat_type = context.user_data.get("material_type")

    # Track navigation: coming from material type → back should go to material types
    context.user_data["last"] = "material"

    data = load_data()
    key = f"{cls}|{subject}|{mat_type}"
    items = data.get("categories", {}).get(key, [])

    back_keyboard = ReplyKeyboardMarkup([["⬅ Back", "🏠 Main Menu"]], resize_keyboard=True)

    if not items:
        await update.message.reply_text(
            f"📭 No {mat_type} found for {subject} ({cls}) yet.\n\nCheck back later!",
            reply_markup=back_keyboard
        )
        return

    await update.message.reply_text(
        f"📦 {mat_type} — {subject} ({cls}):\n\nSending {len(items)} item(s)...",
        reply_markup=back_keyboard
    )

    for item in items:
        item_type = item.get("type")
        file_id = item.get("file_id")
        caption = item.get("caption", "")

        try:
            if item_type == "text":
                await update.message.reply_text(file_id)
            elif item_type == "photo":
                await update.message.reply_photo(photo=file_id, caption=caption)
            elif item_type == "document":
                await update.message.reply_document(document=file_id, caption=caption)
            elif item_type == "video":
                await update.message.reply_video(video=file_id, caption=caption)
            elif item_type == "audio":
                await update.message.reply_audio(audio=file_id, caption=caption)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Could not send item: {e}")

# ================= ADMIN: ADD MATERIAL FLOW =================

ALL_CLASSES = ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]
SUBJECTS_9_10 = ["SCIENCE 🧪", "MATHEMATICS 📐", "ECONOMICS 💳", "HISTORY 🏆",
                  "POL. SCIENCE 👮", "GEOGRAPHY 🌍", "ENGLISH 📄"]
SUBJECTS_11_12 = ["PHYSICS ⚛️", "CHEMISTRY 🧪", "BIOLOGY 🌱", "MATHS 📐", "ENGLISH 📄"]
MATERIAL_TYPES_9_11 = ["📚 Lectures", "📝 Notes", "🧠 Mindmaps", "❗ Imp Questions"]
MATERIAL_TYPES_10_12 = ["📚 Lectures", "📝 Notes", "🧠 Mindmaps", "📄 PYQs"]

def get_subjects_for_class(cls):
    if cls in ["Class 9th", "Class 10th"]:
        return SUBJECTS_9_10
    return SUBJECTS_11_12

def get_material_types_for_class(cls):
    if cls in ["Class 9th", "Class 11th"]:
        return MATERIAL_TYPES_9_11
    return MATERIAL_TYPES_10_12

async def admin_start_add(update, context):
    context.user_data["admin_mode"] = "add"
    context.user_data["add_step"] = "choose_class"

    keyboard = [[c] for c in ALL_CLASSES] + [["🛑 Safe Exit"]]
    await update.message.reply_text(
        "➕ Add Material\n\nStep 1️⃣ — Choose the class:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def admin_start_delete(update, context):
    context.user_data["admin_mode"] = "delete"
    context.user_data["del_step"] = "choose_class"

    keyboard = [[c] for c in ALL_CLASSES] + [["🛑 Safe Exit"]]
    await update.message.reply_text(
        "❌ Delete Material\n\nStep 1️⃣ — Choose the class:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def admin_start_list(update, context):
    context.user_data["admin_mode"] = "list"
    context.user_data["list_step"] = "choose_class"

    keyboard = [[c] for c in ALL_CLASSES] + [["🛑 Safe Exit"]]
    await update.message.reply_text(
        "📋 List Materials\n\nChoose the class:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text if update.message.text else ""

    # ===== ADMIN REPLY SYSTEM (reply to forwarded user msg) =====
    if user_id == ADMIN_ID and update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        target_user = context.bot_data.get(replied_msg_id)

        if target_user:
            msg = update.message

            if msg.text:
                sent = await context.bot.send_message(target_user, msg.text)
            elif msg.photo:
                sent = await context.bot.send_photo(target_user, photo=msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video:
                sent = await context.bot.send_video(target_user, video=msg.video.file_id, caption=msg.caption)
            elif msg.document:
                sent = await context.bot.send_document(target_user, document=msg.document.file_id, caption=msg.caption)
            elif msg.audio:
                sent = await context.bot.send_audio(target_user, audio=msg.audio.file_id, caption=msg.caption)
            else:
                return

            chat_messages.setdefault(target_user, []).append(
                (sent.message_id, update.message.message_id)
            )
            return

    # ===== SAFE EXIT (Admin) =====
    if user_id == ADMIN_ID and text == "🛑 Safe Exit":
        context.user_data.clear()
        await admin(update, context)
        return

    # ===== MAIN MENU =====
    if text == "🏠 Main Menu":
        if user_id == ADMIN_ID:
            await admin(update, context)
        else:
            await start(update, context)
        return

    # ===== BACK BUTTON =====
    if text == "⬅ Back":
        last = context.user_data.get("last")

        if last == "main":
            # Was on subjects page → go back to class selection (main menu)
            await start(update, context)
        elif last == "class":
            # Was on material type page → go back to subjects
            await show_subjects(update, context)
        elif last == "material":
            # Was on content page → go back to material types
            await show_materials(update, context)
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

    # ===== ACTIVE CHAT (forward user msgs to admin) =====
    if user_id in active_users:
        if user_id in user_timers:
            user_timers[user_id].cancel()
        user_timers[user_id] = asyncio.create_task(expire_chat(user_id, context))

        user = update.message
        sender = update.message.from_user
        caption = f"👤 {sender.first_name}\n🆔 {sender.id}"

        if user.text:
            admin_msg = await context.bot.send_message(ADMIN_ID, f"{caption}\n\n{user.text}")
        elif user.photo:
            admin_msg = await context.bot.send_photo(ADMIN_ID, photo=user.photo[-1].file_id, caption=caption)
        elif user.video:
            admin_msg = await context.bot.send_video(ADMIN_ID, video=user.video.file_id, caption=caption)
        elif user.document:
            admin_msg = await context.bot.send_document(ADMIN_ID, document=user.document.file_id, caption=caption)
        elif user.audio:
            admin_msg = await context.bot.send_audio(ADMIN_ID, audio=user.audio.file_id, caption=caption)
        else:
            return

        chat_messages.setdefault(user_id, []).append(
            (update.message.message_id, admin_msg.message_id)
        )
        context.bot_data[admin_msg.message_id] = user_id
        return

    # ===================================================================
    # ========================= ADMIN FLOWS =============================
    # ===================================================================

    if user_id == ADMIN_ID:

        admin_mode = context.user_data.get("admin_mode")

        # ---------- ADD MATERIAL FLOW ----------
        if text == "➕ Add Material":
            await admin_start_add(update, context)
            return

        if admin_mode == "add":
            step = context.user_data.get("add_step")

            if step == "choose_class":
                if text in ALL_CLASSES:
                    context.user_data["add_class"] = text
                    context.user_data["add_step"] = "choose_subject"
                    subjects = get_subjects_for_class(text)
                    keyboard = [[s] for s in subjects] + [["🛑 Safe Exit"]]
                    await update.message.reply_text(
                        f"Step 2️⃣ — Choose the subject for {text}:",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                return

            if step == "choose_subject":
                all_subjects = SUBJECTS_9_10 + SUBJECTS_11_12
                if text in all_subjects:
                    context.user_data["add_subject"] = text
                    context.user_data["add_step"] = "choose_type"
                    cls = context.user_data.get("add_class")
                    types = get_material_types_for_class(cls)
                    keyboard = [[t] for t in types] + [["🛑 Safe Exit"]]
                    await update.message.reply_text(
                        f"Step 3️⃣ — Choose the material type:",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                return

            if step == "choose_type":
                all_types = MATERIAL_TYPES_9_11 + MATERIAL_TYPES_10_12
                if text in all_types:
                    context.user_data["add_type"] = text
                    context.user_data["add_step"] = "send_content"
                    await update.message.reply_text(
                        f"Step 4️⃣ — Now send the file, photo, video, audio, or text you want to add.\n\n"
                        f"📌 Class: {context.user_data['add_class']}\n"
                        f"📌 Subject: {context.user_data['add_subject']}\n"
                        f"📌 Type: {text}\n\n"
                        f"Send the content now 👇",
                        reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True)
                    )
                return

            if step == "send_content":
                msg = update.message
                cls = context.user_data["add_class"]
                subject = context.user_data["add_subject"]
                mat_type = context.user_data["add_type"]
                key = f"{cls}|{subject}|{mat_type}"

                data = load_data()
                data["categories"].setdefault(key, [])

                if msg.text:
                    data["categories"][key].append({"type": "text", "file_id": msg.text, "caption": ""})
                elif msg.photo:
                    data["categories"][key].append({"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""})
                elif msg.video:
                    data["categories"][key].append({"type": "video", "file_id": msg.video.file_id, "caption": msg.caption or ""})
                elif msg.document:
                    data["categories"][key].append({"type": "document", "file_id": msg.document.file_id, "caption": msg.caption or ""})
                elif msg.audio:
                    data["categories"][key].append({"type": "audio", "file_id": msg.audio.file_id, "caption": msg.caption or ""})
                else:
                    await update.message.reply_text("⚠️ Unsupported content type. Send text, photo, video, document, or audio.")
                    return

                save_data(data)
                total = len(data["categories"][key])
                await update.message.reply_text(
                    f"✅ Material added successfully!\n\n"
                    f"📌 {cls} › {subject} › {mat_type}\n"
                    f"📦 Total items in this slot: {total}\n\n"
                    f"Send another file to add more, or press 🛑 Safe Exit.",
                )
                return

        # ---------- DELETE MATERIAL FLOW ----------
        if text == "❌ Delete Material":
            await admin_start_delete(update, context)
            return

        if admin_mode == "delete":
            step = context.user_data.get("del_step")

            if step == "choose_class":
                if text in ALL_CLASSES:
                    context.user_data["del_class"] = text
                    context.user_data["del_step"] = "choose_subject"
                    subjects = get_subjects_for_class(text)
                    keyboard = [[s] for s in subjects] + [["🛑 Safe Exit"]]
                    await update.message.reply_text(
                        f"Choose the subject for {text}:",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                return

            if step == "choose_subject":
                all_subjects = SUBJECTS_9_10 + SUBJECTS_11_12
                if text in all_subjects:
                    context.user_data["del_subject"] = text
                    context.user_data["del_step"] = "choose_type"
                    cls = context.user_data.get("del_class")
                    types = get_material_types_for_class(cls)
                    keyboard = [[t] for t in types] + [["🛑 Safe Exit"]]
                    await update.message.reply_text(
                        f"Choose the material type to delete from:",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                return

            if step == "choose_type":
                all_types = MATERIAL_TYPES_9_11 + MATERIAL_TYPES_10_12
                if text in all_types:
                    context.user_data["del_type"] = text
                    cls = context.user_data["del_class"]
                    subject = context.user_data["del_subject"]
                    key = f"{cls}|{subject}|{text}"

                    data = load_data()
                    items = data.get("categories", {}).get(key, [])

                    if not items:
                        await update.message.reply_text(
                            f"📭 No items found in {cls} › {subject} › {text}.",
                            reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True)
                        )
                        return

                    # List items with index numbers
                    context.user_data["del_step"] = "choose_index"
                    lines = [f"📦 {cls} › {subject} › {text}\n\nItems ({len(items)}):\n"]
                    for i, item in enumerate(items):
                        item_type = item.get("type", "?")
                        caption = item.get("caption", "") or item.get("file_id", "")[:40]
                        lines.append(f"{i + 1}. [{item_type}] {caption}")
                    lines.append("\nReply with the item number to delete (e.g. 1):")
                    await update.message.reply_text(
                        "\n".join(lines),
                        reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True)
                    )
                return

            if step == "choose_index":
                cls = context.user_data["del_class"]
                subject = context.user_data["del_subject"]
                mat_type = context.user_data["del_type"]
                key = f"{cls}|{subject}|{mat_type}"

                data = load_data()
                items = data.get("categories", {}).get(key, [])

                if text.isdigit():
                    idx = int(text) - 1
                    if 0 <= idx < len(items):
                        removed = items.pop(idx)
                        data["categories"][key] = items
                        save_data(data)
                        await update.message.reply_text(
                            f"🗑️ Item #{idx + 1} deleted from {cls} › {subject} › {mat_type}.\n"
                            f"📦 Remaining items: {len(items)}",
                            reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True)
                        )
                    else:
                        await update.message.reply_text(f"⚠️ Invalid number. Enter 1–{len(items)}.")
                else:
                    await update.message.reply_text("⚠️ Please send a number.")
                return

        # ---------- LIST MATERIALS FLOW ----------
        if text == "📋 List Materials":
            await admin_start_list(update, context)
            return

        if admin_mode == "list":
            step = context.user_data.get("list_step")

            if step == "choose_class":
                if text in ALL_CLASSES:
                    context.user_data["list_class"] = text
                    context.user_data["list_step"] = "choose_subject"
                    subjects = get_subjects_for_class(text)
                    keyboard = [[s] for s in subjects] + [["🛑 Safe Exit"]]
                    await update.message.reply_text(
                        f"Choose the subject for {text}:",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                return

            if step == "choose_subject":
                all_subjects = SUBJECTS_9_10 + SUBJECTS_11_12
                if text in all_subjects:
                    cls = context.user_data["list_class"]
                    data = load_data()
                    types = get_material_types_for_class(cls)
                    lines = [f"📋 {cls} › {text}\n"]
                    for t in types:
                        key = f"{cls}|{text}|{t}"
                        count = len(data.get("categories", {}).get(key, []))
                        lines.append(f"  {t}: {count} item(s)")
                    await update.message.reply_text(
                        "\n".join(lines),
                        reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True)
                    )
                return

        # ---------- SEND MESSAGE FLOW ----------
        if text == "📨 Send Message":
            context.user_data["admin_mode"] = "send"
            await update.message.reply_text(
                "📨 Send Message\n\nType your message to send to the target user:",
                reply_markup=ReplyKeyboardMarkup([["🛑 Safe Exit"]], resize_keyboard=True)
            )
            return

        if admin_mode == "send":
            if update.message.reply_to_message:
                return
            if update.message.text:
                await context.bot.send_message(TARGET_USER_ID, text)
                await update.message.reply_text("✅ Message sent!")
            return

    # ===================================================================
    # ========================= USER FLOWS ==============================
    # ===================================================================

    # ===== CLASS SELECT =====
    if text in ALL_CLASSES:
        context.user_data["class"] = text
        context.user_data["last"] = "main"
        await show_subjects(update, context)
        return

    # ===== SUBJECT SELECT =====
    all_subjects = SUBJECTS_9_10 + SUBJECTS_11_12
    if text in all_subjects:
        context.user_data["subject"] = text
        context.user_data["last"] = "class"
        await show_materials(update, context)
        return

    # ===== MATERIAL TYPE SELECT =====
    all_types = MATERIAL_TYPES_9_11 + MATERIAL_TYPES_10_12
    if text in all_types:
        context.user_data["material_type"] = text
        context.user_data["last"] = "material"
        await show_content(update, context)
        return

# ================= MAIN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()
