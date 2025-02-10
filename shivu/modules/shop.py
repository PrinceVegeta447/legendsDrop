from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from shivu import application, user_collection

# 🏪 **Item Prices**
CC_PRICE = 500       # 500 Zeni per Chrono Crystal
TICKET_PRICE = 1000  # 1000 Zeni per Summon Ticket

# 📌 **Track Pending Purchases**
pending_purchases = {}

async def shop(update: Update, context: CallbackContext) -> None:
    """Displays the enhanced shop menu with better UI & inline buttons."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user:
        await update.message.reply_text("😔 You have no Zeni! Earn some by guessing characters.")
        return

    coins = user.get('coins', 0)
    chrono_crystals = user.get('chrono_crystals', 0)
    summon_tickets = user.get('summon_tickets', 0)

    # 🎨 **Shop UI Message**
    shop_message = (
        f"🛒 <b>Welcome to the Shop, Warrior!</b>\n\n"
        f"💰 <b>Your Zeni:</b> <code>{coins}</code>\n"
        f"💎 <b>Chrono Crystals:</b> <code>{chrono_crystals}</code>\n"
        f"🎟 <b>Summon Tickets:</b> <code>{summon_tickets}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 <b>Available Items:</b>\n"
        f"   ├ 💎 <b>Chrono Crystals</b> - {CC_PRICE} Zeni each\n"
        f"   └ 🎟 <b>Summon Tickets</b> - {TICKET_PRICE} Zeni each\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 Select an item below to purchase:"
    )

    # 🛍 **Shop Buttons**
    keyboard = [
        [InlineKeyboardButton("💎 Buy Chrono Crystals", callback_data="buy_cc")],
        [InlineKeyboardButton("🎟 Buy Summon Tickets", callback_data="buy_ticket")],
        [InlineKeyboardButton("❌ Close Shop", callback_data="close_shop")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(shop_message, parse_mode="HTML", reply_markup=reply_markup)

async def request_amount(update: Update, context: CallbackContext) -> None:
    """Prompts user to enter the quantity before confirming purchase."""
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "close_shop":
        await query.message.delete()
        return

    pending_purchases[user_id] = query.data  # Save purchase type (buy_cc or buy_ticket)
    await query.message.edit_text(
        "🛍 <b>How many units would you like to buy?</b>\n\n"
        "💬 <i>Type the quantity in chat (e.g., 10 for 10 units).</i>",
        parse_mode="HTML"
    )

async def confirm_purchase(update: Update, context: CallbackContext) -> None:
    """Handles the confirmation & finalization of purchase."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if user_id not in pending_purchases:
        return  # Ignore messages unrelated to purchase

    purchase_type = pending_purchases.pop(user_id)  # Retrieve purchase type
    coins = user.get('coins', 0)

    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ <b>Invalid amount!</b> Enter a number greater than 0.", parse_mode="HTML")
            return
    except ValueError:
        await update.message.reply_text("❌ <b>Invalid input!</b> Please enter a valid number.", parse_mode="HTML")
        return

    if purchase_type == "buy_cc":
        total_cost = amount * CC_PRICE
        item_name = "Chrono Crystals"
        field = "chrono_crystals"
    elif purchase_type == "buy_ticket":
        total_cost = amount * TICKET_PRICE
        item_name = "Summon Tickets"
        field = "summon_tickets"

    if coins < total_cost:
        await update.message.reply_text(
            f"❌ <b>Not enough Zeni!</b>\nYou need <code>{total_cost}</code> Zeni for <code>{amount}</code> {item_name}.",
            parse_mode="HTML"
        )
        return

    # 📌 **Confirmation Step**
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{purchase_type}:{amount}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_purchase")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"⚠️ <b>Confirm Purchase</b>\n\n"
        f"🛒 You are about to buy:\n"
        f"🔹 <code>{amount}</code> {item_name}\n"
        f"💰 Cost: <code>{total_cost}</code> Zeni\n\n"
        f"✅ Click **Confirm** to proceed or **Cancel** to abort.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def finalize_purchase(update: Update, context: CallbackContext) -> None:
    """Finalizes purchase when user confirms."""
    query = update.callback_query
    user_id = query.from_user.id
    user = await user_collection.find_one({'id': user_id})

    _, purchase_type, amount = query.data.split(":")
    amount = int(amount)

    if purchase_type == "buy_cc":
        total_cost = amount * CC_PRICE
        item_name = "Chrono Crystals"
        field = "chrono_crystals"
    elif purchase_type == "buy_ticket":
        total_cost = amount * TICKET_PRICE
        item_name = "Summon Tickets"
        field = "summon_tickets"

    if user.get('coins', 0) < total_cost:
        await query.message.edit_text(
            f"❌ <b>Not enough Zeni!</b> You need <code>{total_cost}</code> Zeni for <code>{amount}</code> {item_name}.",
            parse_mode="HTML"
        )
        return

    # ✅ **Complete the purchase**
    await user_collection.update_one({'id': user_id}, {'$inc': {'coins': -total_cost, field: amount}})

    await query.message.edit_text(
        f"✅ <b>Purchase Successful!</b>\n\n"
        f"🎉 You received <code>{amount}</code> {item_name}.\n"
        f"💰 <b>Remaining Zeni:</b> <code>{user['coins'] - total_cost}</code>\n"
        f"🔹 Use /inventory to check your items.",
        parse_mode="HTML"
    )

async def cancel_purchase(update: Update, context: CallbackContext) -> None:
    """Cancels the purchase process."""
    query = update.callback_query
    await query.message.edit_text("❌ <b>Purchase Cancelled.</b>", parse_mode="HTML")

# ✅ **Add Handlers**
application.add_handler(CommandHandler("shop", shop, block=False))
application.add_handler(CallbackQueryHandler(request_amount, pattern="^buy_|close_shop$", block=False))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_purchase))
application.add_handler(CallbackQueryHandler(finalize_purchase, pattern="^confirm_", block=False))
application.add_handler(CallbackQueryHandler(cancel_purchase, pattern="^cancel_purchase$", block=False))
