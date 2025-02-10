from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, market_collection
from bson import ObjectId
import math

# ✅ Sell a Character (Fixed Listing Removal)
async def sell(update: Update, context: CallbackContext) -> None:
    """Allows users to sell a duplicate character."""
    user_id = update.effective_user.id

    if len(context.args) != 3:
        await update.message.reply_text(
            "❌ **Usage:** `/msell <character_id> <price> <currency>`\n"
            "💰 Example: `/msell 123 500 zeni`", parse_mode="Markdown"
        )
        return

    char_id, price, currency = context.args
    try:
        price = int(price)
    except ValueError:
        await update.message.reply_text("❌ **Invalid price!** Price must be a number.", parse_mode="Markdown")
        return

    if currency.lower() not in ["zeni", "cc"]:
        await update.message.reply_text("❌ **Invalid currency!** Choose `zeni` or `cc`.", parse_mode="Markdown")
        return

    # ✅ Fetch user data
    user = await user_collection.find_one({"id": user_id})
    if not user or "characters" not in user:
        await update.message.reply_text("❌ **You don't have any characters to sell!**", parse_mode="Markdown")
        return

    # ✅ Count occurrences of the character
    char_count = sum(1 for c in user["characters"] if c["id"] == char_id)
    if char_count < 2:
        await update.message.reply_text("❌ **You can only sell duplicates!**", parse_mode="Markdown")
        return

    # ✅ Fetch character details
    character = next((c for c in user["characters"] if c["id"] == char_id), None)
    if not character:
        await update.message.reply_text("❌ **Invalid character ID!**", parse_mode="Markdown")
        return

    # ✅ Remove character from user's collection
    await user_collection.update_one({"id": user_id}, {"$pull": {"characters": {"id": char_id}}})

    # ✅ Create a market listing
    listing = {
        "seller_id": user_id,
        "character": character,
        "price": price,
        "currency": currency.lower()
    }
    listing_doc = await market_collection.insert_one(listing)

    await update.message.reply_text(
        f"✅ **Character Listed for Sale!**\n"
        f"🎴 **Character:** {character['name']}\n"
        f"💰 **Price:** {price} {currency.capitalize()}\n"
        f"🆔 **Listing ID:** `{listing_doc.inserted_id}`\n\n"
        f"🔹 Use `/listings` to view your active sales.\n"
        f"🔹 Use `/mremove <listing_id>` to cancel a listing.",
        parse_mode="Markdown"
    )

# ✅ View Market Listings (Paginated)
async def market(update: Update, context: CallbackContext, page=0) -> None:
    """Displays all available characters for sale (Paginated)."""
    listings = await market_collection.find({}).to_list(length=None)
    if not listings:
        await update.message.reply_text("❌ *No characters are currently for sale!*", parse_mode="Markdown")
        return

    total_pages = math.ceil(len(listings) / 10)  # 10 Listings per page
    page = max(0, min(page, total_pages - 1))
    listings_page = listings[page * 10: (page + 1) * 10]

    message = f"🛒 *Market Listings - Page {page+1}/{total_pages}*\n━━━━━━━━━━━━━━━━━━\n"
    for listing in listings_page:
        char = listing["character"]
        rarity = char.get("rarity", "Unknown")

        message += (
            f"🎴 *{char['name']}* | 🆔 `{listing['_id']}`\n"
            f"🎖 *Rarity:* `{rarity}`\n"
            f"💰 *Price:* `{listing['price']} {listing['currency'].capitalize()}`\n"
            f"👤 *Seller:* `{listing['seller_id']}`\n"
            "━━━━━━━━━━━━━━━━━━\n"
        )

    message += "💰 *Use* `/mbuy <listing_id>` *to purchase a character.*"

    # ✅ Pagination Buttons
    keyboard = []
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"market:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"market:{page+1}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

# ✅ Market Pagination Callback
async def market_callback(update: Update, context: CallbackContext) -> None:
    """Handles market pagination."""
    query = update.callback_query
    _, page = query.data.split(":")
    page = int(page)

    await market(update, context, page)

# ✅ Buy Character (Fixed Currency Deduction)
async def buy_character(update: Update, context: CallbackContext) -> None:
    """Handles buying a character from the market and notifies the seller."""
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/mbuy <listing_id>`", parse_mode="Markdown")
        return

    listing_id = context.args[0]
    try:
        listing = await market_collection.find_one({"_id": ObjectId(listing_id)})
        if not listing:
            await update.message.reply_text("❌ **Listing not found or already sold!**", parse_mode="Markdown")
            return
    except:
        await update.message.reply_text("❌ **Invalid Listing ID format!**", parse_mode="Markdown")
        return

    char = listing["character"]
    price = listing["price"]
    currency = listing["currency"]
    seller_id = listing["seller_id"]

    if user_id == seller_id:
        await update.message.reply_text("❌ **You cannot buy your own listing!**", parse_mode="Markdown")
        return

    # Fetch buyer data
    buyer = await user_collection.find_one({"id": user_id})
    if not buyer:
        await update.message.reply_text("❌ **You need to guess characters first!**", parse_mode="Markdown")
        return

    buyer_balance = buyer.get(currency, 0)
    if buyer_balance < price:
        await update.message.reply_text(f"❌ **Not enough {currency.capitalize()}!**", parse_mode="Markdown")
        return

    # Deduct currency from buyer & add character
    await user_collection.update_one({"id": user_id}, {
        "$inc": {currency: -price},
        "$push": {"characters": char}
    })

    # Transfer currency to seller
    await user_collection.update_one({"id": seller_id}, {"$inc": {currency: price}})

    # Remove listing
    await market_collection.delete_one({"_id": ObjectId(listing_id)})

    # ✅ **Notify the Seller**
    try:
        seller_message = (
            f"📢 <b>Your Character Has Been Sold!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎴 <b>Character:</b> {char['name']}\n"
            f"🎖 <b>Rarity:</b> {char.get('rarity', 'Unknown')}\n"
            f"💰 <b>Sold for:</b> {price} {currency.capitalize()}\n"
            f"👤 <b>Buyer:</b> @{update.effective_user.username if update.effective_user.username else 'Unknown'}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔹 Use /market to list more characters!"
        )
        await context.bot.send_message(chat_id=seller_id, text=seller_message, parse_mode="HTML")
    except Exception as e:
        print(f"❌ Failed to notify seller {seller_id}: {str(e)}")

    await update.message.reply_text(
        f"✅ **Purchase Successful!**\n"
        f"🎴 **Character:** {char['name']}\n"
        f"💰 **Price:** {price} {currency.capitalize()}\n"
        f"🔹 The character has been added to your collection!",
        parse_mode="Markdown"
        )


async def market_help(update: Update, context: CallbackContext) -> None:
    """Provides help and instructions for the market system."""
    help_message = (
        "🛒 <b>Market Help</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 The Market allows you to sell and buy characters using Zeni or Chrono Crystals.\n\n"
        "💰 <b>Selling:</b>\n"
        "➜ <code>/msell char_id price</code> - Sell a character for Zeni.\n"
        "➜ <code>/msellcc char_id price</code> - Sell for Chrono Crystals.\n\n"
        "🔎 <b>Browsing:</b>\n"
        "➜ <code>/market</code> - View all available listings.\n"
        "➜ <code>/mylistings</code> - View your own listings.\n\n"
        "🛒 <b>Buying:</b>\n"
        "➜ <code>/mbuy listing_id</code> - Buy a character from the market.\n\n"
        "🚫 <b>Removing a Listing:</b>\n"
        "➜ <code>/mremove listing_id</code> - Remove your character from the market.\n\n"
        "Use <code>/market</code> to start browsing!"
    )
    await update.message.reply_text(help_message, parse_mode="HTML")


# ✅ View Active Listings
async def listings(update: Update, context: CallbackContext) -> None:
    """Displays a user's active market listings."""
    user_id = update.effective_user.id

    active_listings = await market_collection.find({"seller_id": user_id}).to_list(length=None)
    if not active_listings:
        await update.message.reply_text("❌ *You have no active listings!*", parse_mode="Markdown")
        return

    message = f"🛒 *Your Active Listings ({len(active_listings)})*\n━━━━━━━━━━━━━━━━━━\n"
    for listing in active_listings:
        char = listing["character"]
        rarity = char.get("rarity", "Unknown")

        message += (
            f"🎴 *{char['name']}* | 🆔 `{listing['_id']}`\n"
            f"🎖 *Rarity:* `{rarity}`\n"
            f"💰 *Price:* `{listing['price']} {listing['currency'].capitalize()}`\n"
            "━━━━━━━━━━━━━━━━━━\n"
        )

    message += "🚫 *Use* `/mremove <listing_id>` *to remove a listing.*"
    await update.message.reply_text(message, parse_mode="Markdown")

# ✅ Remove a Listing
async def remove_listing(update: Update, context: CallbackContext) -> None:
    """Removes a character from the market and returns it to the seller's collection."""
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("❌ *Usage:* `/mremove <listing_id>`", parse_mode="Markdown")
        return

    listing_id = context.args[0]
    try:
        listing = await market_collection.find_one({"_id": ObjectId(listing_id), "seller_id": user_id})
        if not listing:
            await update.message.reply_text("❌ *Invalid Listing ID!*", parse_mode="Markdown")
            return
    except:
        await update.message.reply_text("❌ *Invalid Listing ID format!*", parse_mode="Markdown")
        return

    # ✅ Remove listing and return character to seller
    await market_collection.delete_one({"_id": ObjectId(listing_id)})
    await user_collection.update_one({"id": user_id}, {"$push": {"characters": listing["character"]}})

    await update.message.reply_text(
        f"✅ *Listing Removed!*\n"
        f"🎴 *Character:* `{listing['character']['name']}`\n"
        f"🔹 The character has been returned to your collection.",
        parse_mode="Markdown"
    )

# ✅ Register Handlers
application.add_handler(CommandHandler("market", market, block=False))
application.add_handler(CallbackQueryHandler(market_callback, pattern="^market:", block=False))
application.add_handler(CommandHandler("mbuy", buy_character, block=False))
application.add_handler(CommandHandler("msell", sell, block=False))
application.add_handler(CommandHandler("mhelp", market_help, block=False))
application.add_handler(CommandHandler("listings", listings, block=False))
application.add_handler(CommandHandler("mremove", remove_listing, block=False))
