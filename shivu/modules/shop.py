from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from shivu import application, user_collection

# Prices
CC_PRICE = 500  # 500 Zeni per CC
TICKET_PRICE = 1000  # 1000 Zeni per Summon Ticket

# Dictionary to track purchase requests
pending_purchases = {}

async def shop(update: Update, context: CallbackContext) -> None:
    """Display the enhanced shop menu with inline buttons."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user:
        await update.message.reply_text("😔 You have no Zeni! Earn some by guessing characters.")
        return

    coins = user.get('coins', 0)
    chrono_crystals = user.get('chrono_crystals', 0)
    summon_tickets = user.get('summon_tickets', 0)

    # 🛒 **Shop Menu**
    shop_message = (
        f"🛍️ <b>Welcome to the Shop!</b>\n\n"
        f"💰 <b>Your Zeni:</b> <code>{coins}</code>\n"
        f"💎 <b>Chrono Crystals:</b> <code>{chrono_crystals}</code>\n"
        f"🎟 <b>Summon Tickets:</b> <code>{summon_tickets}</code>\n\n"
        f"🛒 <b>Available Items:</b>\n"
        f" ├ 💎 <b>Chrono Crystals</b> - {CC_PRICE} Zeni per CC\n"
        f" └ 🎟 <b>Summon Tickets</b> - {TICKET_PRICE} Zeni per Ticket\n\n"
        f"🔽 <b>Select an item to purchase:</b>"
    )

    # Inline buttons
    keyboard = [
        [InlineKeyboardButton("💎 Buy Chrono Crystals", callback_data="buy_cc")],
        [InlineKeyboardButton("🎟 Buy Summon Tickets", callback_data="buy_ticket")],
        [InlineKeyboardButton("❌ Close", callback_data="close_shop")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(shop_message, parse_mode="HTML", reply_markup=reply_markup)

async def request_amount(update: Update, context: CallbackContext) -> None:
    """Prompt the user to enter an amount after clicking a button."""
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "close_shop":
        await query.message.delete()
        return

    pending_purchases[user_id] = query.data  # Store purchase type (buy_cc or buy_ticket)
    await query.message.reply_text(
        "🛍 <b>Enter the amount you want to buy:</b>\n\n"
        "✏️ Type a number in chat (e.g., 10 for 10 units).",
        parse_mode="HTML"
    )

async def process_purchase(update: Update, context: CallbackContext) -> None:
    """Process the purchase after user enters an amount."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if user_id not in pending_purchases:
        return  # Ignore messages not related to purchase

    purchase_type = pending_purchases.pop(user_id)  # Retrieve purchase type
    coins = user.get('coins', 0)

    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ <b>Invalid amount!</b> Please enter a number greater than 0.", parse_mode="HTML")
            return
    except ValueError:
        await update.message.reply_text("❌ <b>Invalid input!</b> Please enter a valid number.", parse_mode="HTML")
        return

    if purchase_type == "buy_cc":
        total_cost = amount * CC_PRICE
        if coins < total_cost:
            await update.message.reply_text(f"❌ <b>Not enough Zeni!</b>\nYou need <code>{total_cost}</code> Zeni for <code>{amount}</code> CC.", parse_mode="HTML")
            return
        await user_collection.update_one({'id': user_id}, {'$inc': {'coins': -total_cost, 'chrono_crystals': amount}})
        await update.message.reply_text(f"✅ <b>Successfully purchased:</b>\n💎 <code>{amount}</code> Chrono Crystals\n💰 Cost: <code>{total_cost}</code> Zeni", parse_mode="HTML")

    elif purchase_type == "buy_ticket":
        total_cost = amount * TICKET_PRICE
        if coins < total_cost:
            await update.message.reply_text(f"❌ <b>Not enough Zeni!</b>\nYou need <code>{total_cost}</code> Zeni for <code>{amount}</code> Summon Tickets.", parse_mode="HTML")
            return
        await user_collection.update_one({'id': user_id}, {'$inc': {'coins': -total_cost, 'summon_tickets': amount}})
        await update.message.reply_text(f"✅ <b>Successfully purchased:</b>\n🎟 <code>{amount}</code> Summon Tickets\n💰 Cost: <code>{total_cost}</code> Zeni", parse_mode="HTML")

# Handlers
application.add_handler(CommandHandler("shop", shop, block=False))
application.add_handler(CallbackQueryHandler(request_amount, pattern="^buy_|close_shop$", block=False))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_purchase))
