from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import user_collection, application, OWNER_ID, sudo_users

async def inventory(update: Update, context: CallbackContext) -> None:
    """Shows the user's inventory (Coins & Chrono Crystals)."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user:
        await user_collection.insert_one({'id': user_id, 'coins': 0, 'chrono_crystals': 0})  # Ensure inventory exists
        await update.message.reply_text("😔 You haven't collected any characters yet!")
        return

    coins = user.get('coins', 0)
    chrono_crystals = user.get('chrono_crystals', 0)

    inventory_message = (
        f"🎒 **{update.effective_user.first_name}'s Inventory**\n\n"
        f"💰 **Zeni:** `{coins}`\n"
        f"💎 **Chrono Crystals:** `{chrono_crystals}`\n\n"
        f"Keep guessing to earn more rewards!"
    )

    await update.message.reply_text(inventory_message, parse_mode="Markdown")

async def modify_inventory(update: Update, context: CallbackContext, add=True) -> None:
    """Allows the owner or sudo users to add/remove items in a user's inventory."""
    user_id = update.effective_user.id

    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to modify inventories!")
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text("❌ Usage: `/additem <user_id> <zeni/cc> <amount>`\n"
                                            "or `/removeitem <user_id> <zeni/cc> <amount>`")
            return

        target_id = int(args[0])  # Target user's ID
        item = args[1].lower()
        amount = int(args[2])

        if item not in ["zeni", "cc"]:
            await update.message.reply_text("❌ Invalid item! Use `zeni` or `cc`.")
            return

        field = "coins" if item == "zeni" else "chrono_crystals"
        
        # ✅ Ensure user has an inventory (prevents disappearing on restart)
        user = await user_collection.find_one({'id': target_id})
        if not user:
            await user_collection.insert_one({'id': target_id, 'coins': 0, 'chrono_crystals': 0})
            user = {'coins': 0, 'chrono_crystals': 0}  # Default values

        # ✅ Prevent negative values when removing
        new_value = max(0, user.get(field, 0) + (amount if add else -amount))

        await user_collection.update_one({'id': target_id}, {'$set': {field: new_value}})

        action = "added to" if add else "removed from"
        await update.message.reply_text(f"✅ `{amount}` {item.capitalize()} {action} user `{target_id}`'s inventory!")

    except ValueError:
        await update.message.reply_text("❌ Invalid number format! Make sure the amount is a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ✅ Add Command Handlers
application.add_handler(CommandHandler("inventory", inventory, block=False))
application.add_handler(CommandHandler("additem", lambda u, c: modify_inventory(u, c, add=True), block=False))
application.add_handler(CommandHandler("removeitem", lambda u, c: modify_inventory(u, c, add=False), block=False))
