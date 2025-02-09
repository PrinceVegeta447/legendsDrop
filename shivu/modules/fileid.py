from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackContext
from shivu import application, banners_collection, OWNER_ID, sudo_users


async def get_file_id_cmd(update: Update, context: CallbackContext) -> None:
    """Extracts file_id from a replied image message."""
    user_id = update.effective_user.id

    # ✅ Check permissions
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to extract file IDs!")
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("❌ Reply to an image with `/getfileid` to extract the file_id!")
        return

    # ✅ Get the highest quality file_id
    file_id = update.message.reply_to_message.photo[-1].file_id

    await update.message.reply_text(f"📂 **File ID Extracted:**\n`{file_id}`", parse_mode="Markdown")

# ✅ Add Handlers
application.add_handler(CommandHandler("fileid", get_file_id_cmd, block=False))
