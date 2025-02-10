from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import user_collection, application, OWNER_ID, sudo_users

async def inventory(update: Update, context: CallbackContext) -> None:
    """Shows the user's inventory (Zeni, Chrono Crystals, Tickets, and Exclusive Tokens)."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id}) or {}

    # ✅ Initialize inventory if user does not exist
    user.setdefault('coins', 0)
    user.setdefault('chrono_crystals', 0)
    user.setdefault('summon_tickets', 0)
    user.setdefault('exclusive_tokens', 0)

    coins = user['coins']
    chrono_crystals = user['chrono_crystals']
    summon_tickets = user['summon_tickets']
    exclusive_tokens = user['exclusive_tokens']

    # 🎒 **Enhanced Inventory Message**
    inventory_message = (
        f"🎒 <b>{update.effective_user.first_name}'s Inventory</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Zeni:</b> <code>{coins}</code>\n"
        f"💎 <b>Chrono Crystals:</b> <code>{chrono_crystals}</code>\n"
        f"🎟 <b>Summon Tickets:</b> <code>{summon_tickets}</code>\n"
        f"🛡️ <b>Exclusive Tokens:</b> <code>{exclusive_tokens}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 Keep guessing characters to earn more rewards!\n"
    )

    await update.message.reply_text(inventory_message, parse_mode="HTML")

async def modify_inventory(update: Update, context: CallbackContext, add: bool) -> None:
    """Allows the owner or sudo users to add/remove items from a user's inventory."""
    user_id = update.effective_user.id

    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to modify inventories!")
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(
                "❌ Usage:\n"
                "🔹 `/additem <user_id> <zeni/cc/ticket/token> <amount>`\n"
                "🔹 `/removeitem <user_id> <zeni/cc/ticket/token> <amount>`",
                parse_mode="HTML"
            )
            return

        target_id = int(args[0])  # Target user's ID
        item = args[1].lower()
        amount = int(args[2])

        item_map = {
            "zeni": "coins",
            "cc": "chrono_crystals",
            "ticket": "summon_tickets",
            "token": "exclusive_tokens"
        }

        if item not in item_map:
            await update.message.reply_text("❌ Invalid item! Use `zeni`, `cc`, `ticket`, or `token`.", parse_mode="HTML")
            return

        field = item_map[item]

        # ✅ Ensure user exists in the database (Prevents missing inventory)
        user = await user_collection.find_one({'id': target_id}) or {}
        user.setdefault(field, 0)  # Default to 0 if missing

        # ✅ Prevent negative values when removing items
        new_value = max(0, user[field] + (amount if add else -amount))

        await user_collection.update_one({'id': target_id}, {'$set': {field: new_value}})

        action = "added to" if add else "removed from"
        await update.message.reply_text(f"✅ <b>{amount} {item.capitalize()} {action} user {target_id}'s inventory!</b>", parse_mode="HTML")

    except ValueError:
        await update.message.reply_text("❌ Invalid number format! Please enter a valid amount.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode="HTML")

# ✅ **Separate handlers for Add & Remove Inventory**
async def add_inventory(update: Update, context: CallbackContext) -> None:
    """Command for adding inventory items."""
    await modify_inventory(update, context, add=True)

async def remove_inventory(update: Update, context: CallbackContext) -> None:
    """Command for removing inventory items."""
    await modify_inventory(update, context, add=False)

# ✅ **Fixed Handlers**
application.add_handler(CommandHandler("inventory", inventory, block=False))
application.add_handler(CommandHandler("additem", add_inventory, block=False))
application.add_handler(CommandHandler("removeitem", remove_inventory, block=False))
