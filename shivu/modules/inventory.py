from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from shivu import user_collection, application, OWNER_ID, sudo_users

async def inventory(update: Update, context: CallbackContext) -> None:
    """Shows the user's inventory (Zeni, Chrono Crystals, Tickets, and Exclusive Tokens)."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    # ✅ Ensure user exists in the database (Prevents missing inventory)
    if not user:
        user = {'id': user_id, 'coins': 0, 'chrono_crystals': 0, 'summon_tickets': 0, 'exclusive_tokens': 0}
        await user_collection.insert_one(user)

    coins = user.get('coins', 0)
    chrono_crystals = user.get('chrono_crystals', 0)
    summon_tickets = user.get('summon_tickets', 0)
    exclusive_tokens = user.get('exclusive_tokens', 0)

    # 🏆 **Enhanced Inventory Message**
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

    # ✅ Inline Button for Shop Access
    keyboard = [[InlineKeyboardButton("🛍️ Open Shop", callback_data="open_shop")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(inventory_message, parse_mode="HTML", reply_markup=reply_markup)

async def modify_inventory(update: Update, context: CallbackContext, add=True) -> None:
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
        user = await user_collection.find_one({'id': target_id})
        if not user:
            user = {'id': target_id, 'coins': 0, 'chrono_crystals': 0, 'summon_tickets': 0, 'exclusive_tokens': 0}
            await user_collection.insert_one(user)

        # ✅ Prevent negative values when removing items
        new_value = max(0, user.get(field, 0) + (amount if add else -amount))

        await user_collection.update_one({'id': target_id}, {'$set': {field: new_value}})

        action = "added to" if add else "removed from"
        await update.message.reply_text(f"✅ <b>{amount} {item.capitalize()} {action} user {target_id}'s inventory!</b>", parse_mode="HTML")

    except ValueError:
        await update.message.reply_text("❌ Invalid number format! Please enter a valid amount.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode="HTML")

# ✅ Add Command Handlers
application.add_handler(CommandHandler("inventory", inventory, block=False))
application.add_handler(CommandHandler("additem", lambda u, c: modify_inventory(u, c, add=True), block=False))
application.add_handler(CommandHandler("removeitem", lambda u, c: modify_inventory(u, c, add=False), block=False))
