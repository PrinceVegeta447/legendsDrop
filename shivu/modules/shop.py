from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection

# ✅ Prices
SHOP_ITEMS = {
    "cc_100": {"name": "💎 100 Chrono Crystals", "cost": 50000, "currency": "coins", "gives": {"chrono_crystals": 100}},
    "cc_500": {"name": "💎 500 Chrono Crystals", "cost": 220000, "currency": "coins", "gives": {"chrono_crystals": 500}},
    "ticket_1": {"name": "🎟 1 Summon Ticket", "cost": 220, "currency": "chrono_crystals", "gives": {"summon_tickets": 1}},
    "ticket_5": {"name": "🎟 5 Summon Tickets", "cost": 1100, "currency": "chrono_crystals", "gives": {"summon_tickets": 5}},
}

# ✅ Shop Command
async def shop(update: Update, context: CallbackContext) -> None:
    """Displays the shop with available items."""
    shop_text = "🛒 **Welcome to the Shop!**\n\nUse /buy `<item> <amount>` to purchase.\n\n"
    
    for key, item in SHOP_ITEMS.items():
        shop_text += f"{item['name']} - {item['cost']} {item['currency'].capitalize()}\n"
    
    # Inline Buttons
    buttons = [
        [InlineKeyboardButton("💎 Buy CC", callback_data="shop:cc"), InlineKeyboardButton("🎟 Buy Tickets", callback_data="shop:tickets")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(shop_text, parse_mode="Markdown", reply_markup=reply_markup)

# ✅ Buy Command
async def buy(update: Update, context: CallbackContext) -> None:
    """Processes item purchases."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user:
        await update.message.reply_text("😔 You don't have an inventory yet. Start collecting characters first!")
        return

    # ✅ Parse user input
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Incorrect format!\nUse: `/buy <item> <amount>`\nExample: `/buy cc_100 2`")
        return

    item_key, amount = args[0], args[1]

    if item_key not in SHOP_ITEMS:
        await update.message.reply_text("❌ Invalid item! Use `/shop` to view available items.")
        return

    try:
        amount = int(amount)
        if amount < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Amount must be a **valid number** greater than 0.")
        return

    item = SHOP_ITEMS[item_key]
    total_cost = item["cost"] * amount
    currency = item["currency"]

    # ✅ Check if user has enough currency
    if user.get(currency, 0) < total_cost:
        await update.message.reply_text(f"❌ Not enough {currency}! You need **{total_cost} {currency}**.")
        return

    # ✅ Deduct cost & Add items to inventory
    update_data = {
        "$inc": {currency: -total_cost}  # Deduct cost
    }
    for key, value in item["gives"].items():
        update_data["$inc"][key] = value * amount  # Add items

    await user_collection.update_one({'id': user_id}, update_data)

    # ✅ Confirmation message
    await update.message.reply_text(f"✅ Purchased {amount}x {item['name']}!\n\n💰 **Remaining {currency.capitalize()}:** {user.get(currency, 0) - total_cost}")

# ✅ Handlers
application.add_handler(CommandHandler("shop", shop, block=False))
application.add_handler(CommandHandler("buy", buy, block=False))
