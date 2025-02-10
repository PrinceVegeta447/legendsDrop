from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from shivu import application, user_collection

# 🏪 **Item Prices**
CC_PRICE = 500       # 500 Zeni per Chrono Crystal
TICKET_PRICE = 1000  # 1000 Zeni per Summon Ticket

# 📌 **Track Pending Purchases**
pending_purchases = {}

async def shop(update: Update, context: CallbackContext) -> None:
    """Displays the shop menu with better UI & inline buttons."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id}) or {}

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
        [InlineKeyboardButton("💎 Buy Chrono Crystals", callback_data="buy:cc")],
        [InlineKeyboardButton("🎟 Buy Summon Tickets", callback_data="buy:ticket")],
        [InlineKeyboardButton("❌ Close Shop", callback_data="close_shop")]
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

    _, item = query.data.split(":")  # Extract "cc" or "ticket"
    
    pending_purchases[user_id] = item  # Store purchase type

    await query.message.reply_text(
        "🛍 <b>Enter the amount you want to buy:</b>\n\n"
        "✏️ Type a number in chat (e.g., 10 for 10 units).",
        parse_mode="HTML"
    )

async def confirm_purchase(update: Update, context: CallbackContext) -> None:
    """Handles the confirmation & finalization of purchase."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id}) or {}

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

    price = CC_PRICE if purchase_type == "cc" else TICKET_PRICE
    total_cost = amount * price
    item_name = "Chrono Crystals" if purchase_type == "cc" else "Summon Tickets"

    if coins < total_cost:
        await update.message.reply_text(
            f"❌ <b>Not enough Zeni!</b>\nYou need <code>{total_cost}</code> Zeni for <code>{amount}</code> {item_name}.",
            parse_mode="HTML"
        )
        return

    # 📌 **Confirmation Step**
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{purchase_type}:{amount}")],
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
    """Process the purchase after user confirms."""
    query = update.callback_query
    user_id = query.from_user.id

    # ✅ Ensure callback data has the correct format
    data_parts = query.data.split(":")
    if len(data_parts) < 3:
        await query.answer("❌ Error: Invalid purchase data!", show_alert=True)
        return

    _, purchase_type, amount = data_parts  # Extract data safely

    try:
        amount = int(amount)
    except ValueError:
        await query.answer("❌ Invalid amount!", show_alert=True)
        return

    # ✅ Fetch user data
    user = await user_collection.find_one({'id': user_id}) or {}
    coins = user.get('coins', 0)
    price = CC_PRICE if purchase_type == "cc" else TICKET_PRICE
    total_cost = amount * price
    item_name = "Chrono Crystals" if purchase_type == "cc" else "Summon Tickets"

    if coins < total_cost:
        await query.answer(f"❌ Not enough Zeni! Need {total_cost} Zeni.", show_alert=True)
        return

    # ✅ Deduct Zeni & Add Purchased Items
    field = "chrono_crystals" if purchase_type == "cc" else "summon_tickets"
    await user_collection.update_one({'id': user_id}, {'$inc': {'coins': -total_cost, field: amount}})

    await query.message.edit_text(
        f"✅ <b>Purchase Successful!</b>\n\n"
        f"🎉 You received <code>{amount}</code> {item_name}.\n"
        f"💰 <b>Remaining Zeni:</b> <code>{coins - total_cost}</code>\n"
        f"🔹 Use /inventory to check your items.",
        parse_mode="HTML"
    )

async def cancel_purchase(update: Update, context: CallbackContext) -> None:
    """Cancels the purchase process."""
    query = update.callback_query
    await query.message.edit_text("❌ <b>Purchase Cancelled.</b>", parse_mode="HTML")

# ✅ **Add Handlers**
application.add_handler(CommandHandler("shop", shop, block=False))
application.add_handler(CallbackQueryHandler(request_amount, pattern="^buy:", block=False))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_purchase))
application.add_handler(CallbackQueryHandler(finalize_purchase, pattern="^confirm:", block=False))
application.add_handler(CallbackQueryHandler(cancel_purchase, pattern="^cancel_purchase$", block=False))
