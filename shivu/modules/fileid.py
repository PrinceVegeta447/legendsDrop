from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, OWNER_ID, sudo_users

async def get_file_id_cmd(update: Update, context: CallbackContext) -> None:
    """Extracts both temporary and permanent file_id from a replied image, video, or document."""
    user_id = update.effective_user.id

    # ✅ Check permissions
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to extract file IDs!")
        return

    # ✅ Ensure user replied to a message
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to an image, video, or document with `/fileid` to extract the file_id!")
        return

    # ✅ Extract file_id & unique_file_id based on media type
    replied_msg = update.message.reply_to_message
    file_type = None
    file_id = None
    unique_file_id = None

    if replied_msg.photo:
        file_id = replied_msg.photo[-1].file_id
        unique_file_id = replied_msg.photo[-1].file_unique_id
        file_type = "🖼 Photo"
    elif replied_msg.video:
        file_id = replied_msg.video.file_id
        unique_file_id = replied_msg.video.file_unique_id
        file_type = "🎥 Video"
    elif replied_msg.document:
        file_id = replied_msg.document.file_id
        unique_file_id = replied_msg.document.file_unique_id
        file_type = "📄 Document"
    elif replied_msg.animation:
        file_id = replied_msg.animation.file_id
        unique_file_id = replied_msg.animation.file_unique_id
        file_type = "🎞 GIF"
    else:
        await update.message.reply_text("❌ No supported media found! Reply to an image, video, or document.")
        return

    # ✅ Send formatted response
    await update.message.reply_text(
        f"✅ **Extracted File ID**\n\n"
        f"📌 **Type:** {file_type}\n"
        f"📂 **Temporary File ID:** `{file_id}`\n"
        f"📂 **Permanent File ID:** `{unique_file_id}`\n\n"
        f"🔹 **Use Unique File ID to prevent issues!**",
        parse_mode="Markdown"
    )

# ✅ Add Handler
application.add_handler(CommandHandler("fileid", get_file_id_cmd, block=False))
