from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, OWNER_ID, db

async def reset_db(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Only allow bot owner or sudo users
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You are not authorized to reset the database!")
        return

    try:
        # Explicitly delete all collections
        await db["characters"].delete_many({})  # Delete all characters
        await db["user_collection"].delete_many({})  # Delete user collections
        await db["user_totals_collection"].delete_many({})  # Delete user stats
        await db["group_user_totals_collection"].delete_many({})  # Delete group stats
        await db["top_global_groups_collection"].delete_many({})  # Delete global leaderboard
        await db["sequences"].delete_many({})  # Reset sequence numbers
        await db["total_pm_users"].delete_many({})  # Remove PM user data

        await update.message.reply_text("✅ Database has been completely reset!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error resetting database: {str(e)}")

# Add command handler
application.add_handler(CommandHandler("resetdb", reset_db, block=False))
