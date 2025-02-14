from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, CallbackContext, filters
from shivu import user_collection, application, OWNER_ID

# ✅ Check if a User is Banned
async def is_banned(user_id: int) -> bool:
    """Returns True if the user is banned, otherwise False."""
    user = await user_collection.find_one({"id": user_id})
    return user.get("banned", False) if user else False

# ✅ Ban a User
async def ban_user(update: Update, context: CallbackContext) -> None:
    """Ban a user from using bot commands permanently."""
    user_id = update.effective_user.id

    # ✅ Restrict to Owners & Sudo Users
    if user_id not in [OWNER_ID] + SUDO_USERS:
        return

    # ✅ Check if User ID is Given
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/banuser <user_id>`", parse_mode="Markdown")
        return

    target_id = int(context.args[0])
    user = await user_collection.find_one({"id": target_id})

    if not user:
        await update.message.reply_text(f"❌ No data found for User ID `{target_id}`!", parse_mode="Markdown")
        return

    # ✅ Ban User in Database
    await user_collection.update_one({"id": target_id}, {"$set": {"banned": True}}, upsert=True)
    await update.message.reply_text(f"✅ User `{target_id}` is now **banned permanently** from the bot!", parse_mode="Markdown")

# ✅ Unban a User
async def unban_user(update: Update, context: CallbackContext) -> None:
    """Unban a user and restore bot access."""
    user_id = update.effective_user.id

    # ✅ Restrict to Owners & Sudo Users
    if user_id not in [OWNER_ID] + SUDO_USERS:
        return

    # ✅ Check if User ID is Given
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/unbanuser <user_id>`", parse_mode="Markdown")
        return

    target_id = int(context.args[0])
    user = await user_collection.find_one({"id": target_id})

    if not user:
        await update.message.reply_text(f"❌ No data found for User ID `{target_id}`!", parse_mode="Markdown")
        return

    # ✅ Remove Ban
    await user_collection.update_one({"id": target_id}, {"$set": {"banned": False}})
    await update.message.reply_text(f"✅ User `{target_id}` is now **unbanned** and can use the bot again!", parse_mode="Markdown")

# ✅ Block Banned Users from Using Commands Silently
async def block_banned_users(update: Update, context: CallbackContext) -> None:
    """Blocks banned users silently (no warning message)."""
    user_id = update.effective_user.id
    if await is_banned(user_id):
        return  # Do nothing (ignore the command)

# ✅ Register Commands
application.add_handler(CommandHandler("banuser", ban_user, block=False))
application.add_handler(CommandHandler("unbanuser", unban_user, block=False))

# ✅ Add a Global Command Filter to Prevent Banned Users (Silently)
application.add_handler(MessageHandler(filters.COMMAND, block_banned_users))
