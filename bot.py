import os
import json
import asyncio
from collections import deque
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8558716745
MAX_RECENT = 10

INACTIVITY_SECONDS = 120   # 2 minutes → auto-close

# ── runtime state ──────────────────────────────────────────────────────────────
active_users      = set()
user_timers       = {}          # inactivity auto-close tasks  {user_id: Task}
chat_messages     = {}          # {user_id: [(user_msg_id, admin_msg_id), ...]}
admin_active_user = None

# ── delivered/read status message IDs ─────────────────────────────────────────
# When user sends a message we send a small "✅ Delivered" status line to the user.
# When admin opens the DM (admin_open_chat) we upgrade it to "👀 Seen by Admin".
# {user_id: status_message_id}  — the current status bubble in user's chat
user_status_msg   = {}

# ── recent contacts ────────────────────────────────────────────────────────────
recent_contacts       = {}
recent_contacts_order = deque(maxlen=MAX_RECENT)


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# LINKS  ← Edit this to add/change links
# Format: LINKS["Class"]["Subject"]["Material Type"] = "your link here"
# Leave as "" if no link yet — bot will say "coming soon"
# ══════════════════════════════════════════════════════════════════════════════

LINKS = {
    "Class 9th": {
        "SCIENCE 🧪": {
            "📚 Lectures":       "https://your-link-here.com",
            "📝 Notes":          "https://your-link-here.com",
            "🧠 Mindmaps":       "https://your-link-here.com",
            "❗ Imp Questions":  "https://your-link-here.com",
        },
        "MATHEMATICS 📐": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "ECONOMICS 💳": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "HISTORY 🏆": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "POL. SCIENCE 👮": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "GEOGRAPHY 🌍": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "ENGLISH 📄": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
    },
    "Class 10th": {
        "SCIENCE 🧪": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "MATHEMATICS 📐": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "ECONOMICS 💳": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "HISTORY 🏆": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "POL. SCIENCE 👮": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "GEOGRAPHY 🌍": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "ENGLISH 📄": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
    },
    "Class 11th": {
        "PHYSICS ⚛️": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "CHEMISTRY 🧪": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "BIOLOGY 🌱": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "MATHS 📐": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
        "ENGLISH 📄": {
            "📚 Lectures":       "",
            "📝 Notes":          "",
            "🧠 Mindmaps":       "",
            "❗ Imp Questions":  "",
        },
    },
    "Class 12th": {
        "PHYSICS ⚛️": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "CHEMISTRY 🧪": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "BIOLOGY 🌱": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "MATHS 📐": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
        "ENGLISH 📄": {
            "📚 Lectures":  "",
            "📝 Notes":     "",
            "🧠 Mindmaps":  "",
            "📄 PYQs":      "",
        },
    },
}

async def delete_all_messages(bot, user_id: int):
    """Delete all bridged messages for user_id from both sides instantly using gather."""
    pairs = chat_messages.get(user_id, [])
    if not pairs:
        return

    tasks = []
    for user_msg_id, admin_msg_id in pairs:
        tasks.append(bot.delete_message(user_id, user_msg_id))
        tasks.append(bot.delete_message(ADMIN_ID, admin_msg_id))

    # also delete status bubble if present
    status_mid = user_status_msg.pop(user_id, None)
    if status_mid:
        tasks.append(bot.delete_message(user_id, status_mid))

    await asyncio.gather(*tasks, return_exceptions=True)
    chat_messages[user_id] = []


def track_contact(user_id: int, sender):
    name     = (sender.full_name or sender.first_name or "").strip()
    username = f"@{sender.username}" if sender.username else ""
    recent_contacts[user_id] = {"name": name, "username": username}
    if user_id in recent_contacts_order:
        recent_contacts_order.remove(user_id)
    recent_contacts_order.append(user_id)


# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARDS
# ══════════════════════════════════════════════════════════════════════════════

def admin_chat_keyboard():
    return ReplyKeyboardMarkup(
        [["🧹 Clear History", "❌ End Chat"],
         ["👥 Recent Contacts", "🛑 Exit to Panel"]],
        resize_keyboard=True
    )

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [["Class 9th",  "Class 10th"],
         ["Class 11th", "Class 12th"],
         ["📞 Contact Us"]],
        resize_keyboard=True
    )

def admin_panel_keyboard():
    return ReplyKeyboardMarkup(
        [["🚪 Exit Admin Mode"],
         ["👥 Recent Contacts"]],
        resize_keyboard=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# DELIVERED / READ STATUS
# ══════════════════════════════════════════════════════════════════════════════

async def set_delivered(bot, user_id: int):
    """Post (or replace) the status bubble in the user's chat with ✅ Delivered."""
    old = user_status_msg.pop(user_id, None)
    if old:
        try:
            await bot.delete_message(user_id, old)
        except Exception:
            pass
    try:
        m = await bot.send_message(user_id, "✅ Delivered")
        user_status_msg[user_id] = m.message_id
    except Exception:
        pass


async def set_seen(bot, user_id: int):
    """Upgrade the status bubble to 👀 Seen by Admin."""
    old = user_status_msg.pop(user_id, None)
    if old:
        try:
            await bot.delete_message(user_id, old)
        except Exception:
            pass
    try:
        m = await bot.send_message(user_id, "👀 Seen by Admin")
        user_status_msg[user_id] = m.message_id
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# INACTIVITY AUTO-CLOSE  (2 minutes)
# ══════════════════════════════════════════════════════════════════════════════

async def inactivity_close(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(INACTIVITY_SECONDS)

    if user_id not in active_users:
        return

    global admin_active_user

    await delete_all_messages(context.bot, user_id)
    active_users.discard(user_id)

    try:
        await context.bot.send_message(
            user_id,
            "⏳ Chat auto-closed due to 2 minutes of inactivity.\n"
            "History has been cleared."
        )
        await asyncio.sleep(1)
        await context.bot.send_message(
            user_id,
            "🚀 StudyGPT — Choose your class 👇",
            reply_markup=main_menu_keyboard()
        )
    except Exception:
        pass

    if admin_active_user == user_id:
        admin_active_user = None
        info = recent_contacts.get(user_id, {})
        name = info.get("name", str(user_id))
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"⏳ Chat with {name} auto-closed (2 min inactivity). History cleared.",
                reply_markup=admin_panel_keyboard()
            )
        except Exception:
            pass


def reset_inactivity_timer(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    if user_id in user_timers:
        user_timers[user_id].cancel()
    user_timers[user_id] = asyncio.create_task(
        inactivity_close(user_id, context)
    )


# ══════════════════════════════════════════════════════════════════════════════
# START
# ══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🚀 StudyGPT: Ace your exams with Handwritten Notes, Mindmaps, and Solved PYQs!\n\n"
        "Choose your class 👇",
        reply_markup=main_menu_keyboard()
    )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN COMMAND
# ══════════════════════════════════════════════════════════════════════════════

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    context.user_data.clear()
    await update.message.reply_text(
        "Admin Panel 👨‍💻\n\nWhat would you like to do?",
        reply_markup=admin_panel_keyboard()
    )


# ══════════════════════════════════════════════════════════════════════════════
# SUBJECT / MATERIAL MENUS
# ══════════════════════════════════════════════════════════════════════════════

ALL_CLASSES          = ["Class 9th", "Class 10th", "Class 11th", "Class 12th"]
SUBJECTS_9_10        = ["SCIENCE 🧪", "MATHEMATICS 📐", "ECONOMICS 💳", "HISTORY 🏆",
                        "POL. SCIENCE 👮", "GEOGRAPHY 🌍", "ENGLISH 📄"]
SUBJECTS_11_12       = ["PHYSICS ⚛️", "CHEMISTRY 🧪", "BIOLOGY 🌱", "MATHS 📐", "ENGLISH 📄"]
MATERIAL_TYPES_9_11  = ["📚 Lectures", "📝 Notes", "🧠 Mindmaps", "❗ Imp Questions"]
MATERIAL_TYPES_10_12 = ["📚 Lectures", "📝 Notes", "🧠 Mindmaps", "📄 PYQs"]

def get_subjects_for_class(cls):
    return SUBJECTS_9_10 if cls in ["Class 9th", "Class 10th"] else SUBJECTS_11_12

def get_material_types_for_class(cls):
    return MATERIAL_TYPES_9_11 if cls in ["Class 9th", "Class 11th"] else MATERIAL_TYPES_10_12


async def show_subjects(update, context):
    cls = context.user_data.get("class")
    if cls in ["Class 9th", "Class 10th"]:
        kb = [["SCIENCE 🧪", "MATHEMATICS 📐"], ["ECONOMICS 💳", "HISTORY 🏆"],
              ["POL. SCIENCE 👮", "GEOGRAPHY 🌍"], ["ENGLISH 📄"]]
    else:
        kb = [["PHYSICS ⚛️", "CHEMISTRY 🧪"], ["BIOLOGY 🌱", "MATHS 📐"], ["ENGLISH 📄"]]
    kb.append(["⬅ Back", "🏠 Main Menu"])
    context.user_data["last"] = "main"
    await update.message.reply_text(
        f"📚 {cls} — Choose a Subject:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )


async def show_materials(update, context):
    cls     = context.user_data.get("class")
    subject = context.user_data.get("subject")
    if cls in ["Class 9th", "Class 11th"]:
        kb = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "❗ Imp Questions"]]
    else:
        kb = [["📚 Lectures", "📝 Notes"], ["🧠 Mindmaps", "📄 PYQs"]]
    kb.append(["⬅ Back", "🏠 Main Menu"])
    context.user_data["last"] = "class"
    await update.message.reply_text(
        f"📂 {subject} — Choose material type:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )


async def show_content(update, context):
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    cls      = context.user_data.get("class")
    subject  = context.user_data.get("subject")
    mat_type = context.user_data.get("material_type")
    context.user_data["last"] = "material"

    back_kb = ReplyKeyboardMarkup([["⬅ Back", "🏠 Main Menu"]], resize_keyboard=True)

    link = LINKS.get(cls, {}).get(subject, {}).get(mat_type, "")

    if not link:
        await update.message.reply_text(
            f"⏳ {mat_type} for {subject} ({cls}) is coming soon!\n\nCheck back later.",
            reply_markup=back_kb
        )
        return

    await update.message.reply_text(
        f"📂 {subject} ({cls})\n{mat_type}",
        reply_markup=back_kb
    )
    await update.message.reply_text(
        f"Tap below to open 👇",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"Open {mat_type} 🔗", url=link)]]
        )
    )



# ══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL FORWARDER
# ══════════════════════════════════════════════════════════════════════════════

async def forward_any(bot, to_chat: int, msg,
                      caption_prefix: str = "",
                      reply_to_message_id: int = None):
    kw = {}
    if reply_to_message_id:
        kw["reply_to_message_id"] = reply_to_message_id

    cp = (caption_prefix + "\n\n" + (msg.caption or "")).strip() if caption_prefix else (msg.caption or "")

    if msg.text:
        body = (caption_prefix + "\n\n" + msg.text).strip() if caption_prefix else msg.text
        return await bot.send_message(to_chat, body, **kw)
    if msg.sticker:
        if caption_prefix:
            await bot.send_message(to_chat, caption_prefix, **kw)
        return await bot.send_sticker(to_chat, sticker=msg.sticker.file_id)
    if msg.animation:
        return await bot.send_animation(to_chat, animation=msg.animation.file_id,
                                        caption=cp or None, **kw)
    if msg.photo:
        return await bot.send_photo(to_chat, photo=msg.photo[-1].file_id,
                                    caption=cp or None, **kw)
    if msg.video:
        return await bot.send_video(to_chat, video=msg.video.file_id,
                                    caption=cp or None, **kw)
    if msg.video_note:
        if caption_prefix:
            await bot.send_message(to_chat, caption_prefix, **kw)
        return await bot.send_video_note(to_chat, video_note=msg.video_note.file_id)
    if msg.voice:
        return await bot.send_voice(to_chat, voice=msg.voice.file_id,
                                    caption=cp or None, **kw)
    if msg.audio:
        return await bot.send_audio(to_chat, audio=msg.audio.file_id,
                                    caption=cp or None, **kw)
    if msg.document:
        return await bot.send_document(to_chat, document=msg.document.file_id,
                                       caption=cp or None, **kw)
    if msg.location:
        if caption_prefix:
            await bot.send_message(to_chat, caption_prefix, **kw)
        return await bot.send_location(to_chat,
                                       latitude=msg.location.latitude,
                                       longitude=msg.location.longitude)
    if msg.contact:
        if caption_prefix:
            await bot.send_message(to_chat, caption_prefix, **kw)
        return await bot.send_contact(to_chat,
                                      phone_number=msg.contact.phone_number,
                                      first_name=msg.contact.first_name)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN LIVE-CHAT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

async def admin_show_recent(update, context):
    if not recent_contacts_order:
        await update.message.reply_text("📭 No recent contacts yet.",
                                        reply_markup=admin_panel_keyboard())
        return

    context.user_data["admin_mode"] = "pick_recent"
    ids_list = list(reversed(recent_contacts_order))
    context.user_data["recent_ids"] = ids_list

    lines = ["👥 Recent Contacts — send a number to open DM:\n"]
    for i, uid in enumerate(ids_list, 1):
        info   = recent_contacts.get(uid, {})
        name   = info.get("name", "Unknown")
        uname  = info.get("username", "")
        online = "🟢" if uid in active_users else "🔴"
        lines.append(f"{i}. {online} {name} {uname}  [ID: {uid}]")

    kb = [[str(i)] for i in range(1, len(ids_list) + 1)] + [["🛑 Exit to Panel"]]
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )


async def admin_open_chat(update, context, target_user_id: int):
    global admin_active_user
    admin_active_user = target_user_id
    context.user_data["admin_mode"] = "live_chat"

    info   = recent_contacts.get(target_user_id, {})
    name   = info.get("name", str(target_user_id))
    uname  = info.get("username", "")
    status = "🟢 Online" if target_user_id in active_users else "🔴 Offline"

    await update.message.reply_text(
        f"💬 Now chatting with: {name} {uname}\n"
        f"🆔 {target_user_id}  |  {status}\n\n"
        f"Just type or send anything — it goes straight to them.\n"
        f"Swipe-reply any forwarded message for a quoted reply.",
        reply_markup=admin_chat_keyboard()
    )

    await set_seen(context.bot, target_user_id)

    if target_user_id in active_users:
        reset_inactivity_timer(target_user_id, context)


async def admin_clear_history(update, context):
    uid = admin_active_user
    if not uid:
        return
    await delete_all_messages(context.bot, uid)
    await update.message.reply_text("🧹 Chat history cleared!", reply_markup=admin_chat_keyboard())


async def admin_end_chat(update, context):
    global admin_active_user
    uid = admin_active_user
    if uid:
        await delete_all_messages(context.bot, uid)
        active_users.discard(uid)
        if uid in user_timers:
            user_timers[uid].cancel()
        try:
            await context.bot.send_message(uid, "❌ Admin ended the chat session.")
            await asyncio.sleep(0.5)
            await context.bot.send_message(uid, "🚀 StudyGPT — Choose your class 👇",
                                           reply_markup=main_menu_keyboard())
        except Exception:
            pass

    admin_active_user = None
    context.user_data.clear()
    await update.message.reply_text("✅ Chat ended.", reply_markup=admin_panel_keyboard())


# ══════════════════════════════════════════════════════════════════════════════
# MAIN MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_active_user

    msg     = update.message
    user_id = msg.from_user.id
    text    = msg.text or ""

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN SIDE
    # ══════════════════════════════════════════════════════════════════════════
    if user_id == ADMIN_ID:
        admin_mode = context.user_data.get("admin_mode", "")

        # ── EXIT ──────────────────────────────────────────────────────────────
        if text in ("🛑 Exit to Panel", "🛑 Safe Exit", "🚪 Exit Admin Mode"):
            admin_active_user = None
            context.user_data.clear()
            if text == "🚪 Exit Admin Mode":
                await msg.reply_text("👋 Exited admin mode. You're now in user mode.",
                                     reply_markup=main_menu_keyboard())
            else:
                await msg.reply_text("Admin Panel 👨‍💻", reply_markup=admin_panel_keyboard())
            return

        if text == "🏠 Main Menu" and admin_mode:
            admin_active_user = None
            context.user_data.clear()
            await msg.reply_text("Admin Panel 👨‍💻", reply_markup=admin_panel_keyboard())
            return

        # ── LIVE CHAT CONTROLS ─────────────────────────────────────────────────
        if text == "🧹 Clear History" and admin_active_user:
            await admin_clear_history(update, context)
            return

        if text == "❌ End Chat" and admin_active_user:
            await admin_end_chat(update, context)
            return

        # ── RECENT CONTACTS ────────────────────────────────────────────────────
        if text == "👥 Recent Contacts":
            await admin_show_recent(update, context)
            return

        # ── PICK FROM RECENT LIST ──────────────────────────────────────────────
        if admin_mode == "pick_recent":
            ids_list = context.user_data.get("recent_ids", [])
            if text.isdigit():
                idx = int(text) - 1
                if 0 <= idx < len(ids_list):
                    await admin_open_chat(update, context, ids_list[idx])
                    return
            return

        # ── ADMIN IN LIVE DM MODE ──────────────────────────────────────────────
        if admin_mode == "live_chat" and admin_active_user:
            target = admin_active_user

            # Reset inactivity timer (admin just spoke)
            if target in active_users:
                reset_inactivity_timer(target, context)

            # Detect quoted reply
            reply_to_in_user_chat = None
            if msg.reply_to_message:
                replied_admin_id = msg.reply_to_message.message_id
                for user_msg_id, admin_msg_id in chat_messages.get(target, []):
                    if admin_msg_id == replied_admin_id:
                        reply_to_in_user_chat = user_msg_id
                        break

            try:
                sent = await forward_any(
                    context.bot, target, msg,
                    caption_prefix="",
                    reply_to_message_id=reply_to_in_user_chat
                )
                if sent:
                    chat_messages.setdefault(target, []).append(
                        (sent.message_id, msg.message_id)
                    )
                    context.bot_data[f"admin_msg_{msg.message_id}"] = target
            except Exception as e:
                await msg.reply_text(f"⚠️ Could not send: {e}")
            return

    # ══════════════════════════════════════════════════════════════════════════
    # USER SIDE  (also reached by admin in user/study mode)
    # ══════════════════════════════════════════════════════════════════════════

    # ── GLOBAL NAVIGATION ─────────────────────────────────────────────────────
    if text == "🏠 Main Menu":
        await start(update, context)
        return

    if text == "⬅ Back":
        last = context.user_data.get("last")
        if   last == "main":     await start(update, context)
        elif last == "class":    await show_subjects(update, context)
        elif last == "material": await show_materials(update, context)
        else:                    await start(update, context)
        return

    # ── CONTACT US ─────────────────────────────────────────────────────────────
    if text == "📞 Contact Us":
        active_users.add(user_id)
        track_contact(user_id, msg.from_user)

        await msg.reply_text(
            "StudyGPT Support Team:\n\n"
            "💬 Send your message here and our team will reply directly! 🚀\n\n"
            "⏳ Note: Chat auto-closes after 2 minutes of inactivity.",
            reply_markup=ReplyKeyboardMarkup(
                [["🧹 Clear History", "❌ End Chat"]], resize_keyboard=True
            )
        )

        info  = recent_contacts.get(user_id, {})
        name  = info.get("name", str(user_id))
        uname = info.get("username", "")
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🔔 New contact from {name} {uname} [ID: {user_id}]\n\n"
                f"Use 👥 Recent Contacts → select number to open DM.",
                reply_markup=admin_panel_keyboard()
            )
        except Exception:
            pass

        reset_inactivity_timer(user_id, context)
        return

    # ── USER: CLEAR HISTORY ────────────────────────────────────────────────────
    if text == "🧹 Clear History" and user_id in active_users:
        await delete_all_messages(context.bot, user_id)
        await msg.reply_text("🧹 History cleared!")
        reset_inactivity_timer(user_id, context)
        return

    # ── USER: END CHAT ─────────────────────────────────────────────────────────
    if text == "❌ End Chat" and user_id in active_users:
        await delete_all_messages(context.bot, user_id)
        active_users.discard(user_id)
        if user_id in user_timers:
            user_timers[user_id].cancel()

        if admin_active_user == user_id:
            try:
                info = recent_contacts.get(user_id, {})
                await context.bot.send_message(
                    ADMIN_ID,
                    f"❌ {info.get('name', user_id)} ended the chat.",
                    reply_markup=admin_panel_keyboard()
                )
            except Exception:
                pass

        await msg.reply_text("Chat ended & history cleared.")
        await asyncio.sleep(1)
        await start(update, context)
        return

    # ── ACTIVE CONTACT-US CHAT: forward user → admin ───────────────────────────
    if user_id in active_users:
        reset_inactivity_timer(user_id, context)

        track_contact(user_id, msg.from_user)
        info   = recent_contacts.get(user_id, {})
        prefix = f"👤 {info.get('name', msg.from_user.first_name)} {info.get('username', '')}\n🆔 {user_id}"

        # Detect quoted reply
        reply_to_admin_id = None
        if msg.reply_to_message:
            replied_user_side_id = msg.reply_to_message.message_id
            for user_msg_id, admin_msg_id in chat_messages.get(user_id, []):
                if user_msg_id == replied_user_side_id:
                    reply_to_admin_id = admin_msg_id
                    break

        try:
            admin_msg = await forward_any(
                context.bot, ADMIN_ID, msg,
                caption_prefix=prefix,
                reply_to_message_id=reply_to_admin_id
            )
            if admin_msg:
                chat_messages.setdefault(user_id, []).append(
                    (msg.message_id, admin_msg.message_id)
                )
                context.bot_data[f"admin_msg_{admin_msg.message_id}"] = user_id

                await set_delivered(context.bot, user_id)

                if admin_active_user == user_id:
                    await asyncio.sleep(0.5)
                    await set_seen(context.bot, user_id)
                else:
                    ids_newest_first = list(reversed(recent_contacts_order))
                    try:
                        pos = ids_newest_first.index(user_id) + 1
                    except ValueError:
                        pos = "?"
                    name  = info.get("name", str(user_id))
                    uname = info.get("username", "")
                    try:
                        await context.bot.send_message(
                            ADMIN_ID,
                            f"💬 New message from {name} {uname}\n"
                            f"Open 👥 Recent Contacts and tap {pos} to reply in DM."
                        )
                    except Exception:
                        pass

        except Exception as e:
            await msg.reply_text(f"⚠️ Could not forward message: {e}")
        return

    # ── CLASS / SUBJECT / MATERIAL NAVIGATION ─────────────────────────────────
    if text in ALL_CLASSES:
        context.user_data.update({"class": text, "last": "main"})
        await show_subjects(update, context)
        return

    if text in SUBJECTS_9_10 + SUBJECTS_11_12:
        context.user_data.update({"subject": text, "last": "class"})
        await show_materials(update, context)
        return

    if text in MATERIAL_TYPES_9_11 + MATERIAL_TYPES_10_12:
        context.user_data.update({"material_type": text, "last": "material"})
        await show_content(update, context)
        return


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_cmd))
app.add_handler(MessageHandler(~filters.COMMAND, handle_message))

app.run_polling()
