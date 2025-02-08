from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from shivu import application, user_collection

# Prices
CC_PRICE = 500  # 50 Zeni per CC
TICKET_PRICE = 1000  # 1000 Zeni per Summon Ticket

# Dictionary to track purchase requests
pending_purchases = {}

async def shop(update: Update, context: CallbackContext) -> None:
    """Display the shop menu with inline buttons."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user:
        await update.message.reply_text("😔 You have no Zeni! Earn some by guessing characters.")
        return

    coins = user.get('coins', 0)
    chrono_crystals = user.get('chrono_crystals', 0)
    summon_tickets = user.get('summon_tickets', 0)

    # Shop message
    shop_message = (
        f"🛒 **Welcome to the Shop!**\n\n"
        f"💰 **Your Zeni:** `{coins}`\n"
        f"💎 **Chrono Crystals:** `{chrono_crystals}`\n"
        f"🎟 **Summon Tickets:** `{summon_tickets}`\n\n"
        f"🔽 **Available Items:** 🔽"
    )

    # Inline buttons
    keyboard = [
        [InlineKeyboardButton("💎 Buy Chrono Crystals", callback_data="buy_cc")],
        [InlineKeyboardButton("🎟 Buy Summon Tickets", callback_data="buy_ticket")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(shop_message, parse_mode="Markdown", reply_markup=reply_markup)

async def request_amount(update: Update, context: CallbackContext) -> None:
    """Prompt the user to enter an amount after clicking a button."""
    query = update.callback_query
    user_id = query.from_user.id

    pending_purchases[user_id] = query.data  # Store purchase type (buy_cc or buy_ticket)
    await query.message.reply_text("🛍 Enter the amount you want to buy:")

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
            await update.message.reply_text("❌ Invalid amount! Please enter a number greater than 0.")
            return
    except ValueError:
        await update.message.reply_text("❌ Invalid input! Please enter a valid number.")
        return

    if purchase_type == "buy_cc":
        total_cost = amount * CC_PRICE
        if coins < total_cost:
            await update.message.reply_text(f"❌ Not enough Zeni! You need {total_cost} Zeni for {amount} CC.")
            return
        await user_collection.update_one({'id': user_id}, {'$inc': {'coins': -total_cost, 'chrono_crystals': amount}})
        await update.message.reply_text(f"✅ Purchased {amount} Chrono Crystals for {total_cost} Zeni!")

    elif purchase_type == "buy_ticket":
        total_cost = amount * TICKET_PRICE
        if coins < total_cost:
            await update.message.reply_text(f"❌ Not enough Zeni! You need {total_cost} Zeni for {amount} Summon Tickets.")
            return
        await user_collection.update_one({'id': user_id}, {'$inc': {'coins': -total_cost, 'summon_tickets': amount}})
        await update.message.reply_text(f"✅ Purchased {amount} Summon Tickets for {total_cost} Zeni!")

# Handlers
application.add_handler(CommandHandler("shop", shop, block=False))
application.add_handler(CallbackQueryHandler(request_amount, pattern="^buy_", block=False))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_purchase))
