from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import user_collection, application

async def inventory(update: Update, context: CallbackContext) -> None:
    """Shows the user's inventory (Coins & Chrono Crystals)."""
    user_id = update.effective_user.id

    user = await user_collection.find_one({'id': user_id})

    if not user:
        await update.message.reply_text("😔 You haven't collected any characters yet!")
        return

    coins = user.get('coins', 0)
    chrono_crystals = user.get('chrono_crystals', 0)

    inventory_message = (
        f"🛍 **{update.effective_user.first_name}'s Inventory**\n\n"
        f"💰 **Zeni:** `{coins}`\n"
        f"💎 **Chrono Crystals:** `{chrono_crystals}`\n\n"
        f"Keep guessing to earn more rewards!"
    )

    await update.message.reply_text(inventory_message, parse_mode="Markdown")

# ✅ Add Command Handler
application.add_handler(CommandHandler("inventory", inventory, block=False))
