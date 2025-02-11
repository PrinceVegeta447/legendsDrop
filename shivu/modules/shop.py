from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from shivu import application, user_collection

# 🏪 **Item Prices**
CC_PRICE = 500       # 500 Zeni per Chrono Crystal
TICKET_PRICE = 1000  # 1000 Zeni per Summon Ticket

# 📌 **Track Sessions & Purchases**
pending_purchases = {}  # Tracks purchase type (cc/ticket)
shop_sessions = {}       # Tracks user who opened the shop

async def shop(update: Update, context: CallbackContext) -> None:
    """Displays the shop menu with enhanced UI & inline buttons."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id}) or {}

    coins = user.get('coins', 0)
    chrono_crystals = user.get('chrono_crystals', 0)
    summon_tickets = user.get('summon_tickets', 0)

    # 🎨 **Shop UI Message**
    shop_message = (
        f"<b>🛒 Welcome to the Shop, Warrior!</b>\n\n"
        f"💰 <b>Your Zeni:</b> <code>{coins}</code>\n"
        f"💎 <b>Chrono Crystals:</b> <code>{chrono_crystals}</code>\n"
        f"🎟 <b>Summon Tickets:</b> <code>{summon_tickets}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 <b>Available Items:</b>\n"
        f"   ├ 💎 <b>Chrono Crystals</b> → <code>{CC_PRICE}</code> Zeni each\n"
        f"   └ 🎟 <b>Summon Tickets</b> → <code>{TICKET_PRICE}</code> Zeni each\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <i>Select an item below to purchase:</i>"
    )

    # 🛍 **Shop Buttons**
    keyboard = [
        [InlineKeyboardButton("💎 Buy Chrono Crystals", callback_data=f"buy:cc:{user_id}")],
        [InlineKeyboardButton("🎟 Buy Summon Tickets", callback_data=f"buy:ticket:{user_id}")],
        [InlineKeyboardButton("❌ Close Shop", callback_data=f"close_shop:{user_id}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Store user's message ID to reply later
    shop_sessions[user_id] = update.message.message_id

    await update.message.reply_text(shop_message, parse_mode="HTML", reply_markup=reply_markup)

async def request_amount(update: Update, context: CallbackContext) -> None:
    """Prompt the user to enter an amount after clicking a button."""
    query = update.callback_query
    user_id = query.from_user.id
    data_parts = query.data.split(":")

    if len(data_parts) < 3:
        await query.answer("❌ Invalid request!", show_alert=True)
        return

    _, item, shop_owner_id = data_parts
    shop_owner_id = int(shop_owner_id)

    # ✅ **Restrict other users from using the shop buttons**
    if user_id != shop_owner_id:
        await query.answer("❌ You can't use someone else's shop!", show_alert=True)
        return

    pending_purchases[user_id] = item  # Store purchase type

    # ✅ **Reply to the user's original `/shop` command**
    if shop_owner_id in shop_sessions:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🛍 <b>Enter the amount you want to buy:</b>\n\n"
                 "✏️ Type a number in chat (e.g., 10 for 10 units).",
            parse_mode="HTML",
            reply_to_message_id=shop_sessions[shop_owner_id]
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
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{purchase_type}:{amount}:{user_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{user_id}")]
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
    data_parts = query.data.split(":")

    if len(data_parts) < 4:
        await query.answer("❌ Error: Invalid purchase data!", show_alert=True)
        return

    _, purchase_type, amount, purchase_owner = data_parts
    purchase_owner = int(purchase_owner)

    # ✅ Restrict confirmation to the correct user
    if user_id != purchase_owner:
        await query.answer("❌ You can't confirm someone else's purchase!", show_alert=True)
        return

    try:
        amount = int(amount)
    except ValueError:
        await query.answer("❌ Invalid amount!", show_alert=True)
        return

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

# ✅ **Handlers**
application.add_handler(CommandHandler("shop", shop, block=False))
application.add_handler(CallbackQueryHandler(request_amount, pattern="^buy:", block=False))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_purchase))
application.add_handler(CallbackQueryHandler(finalize_purchase, pattern="^confirm:", block=False))
