import random
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CallbackContext
from shivu import application, collection, user_collection, OWNER_ID

STORE_COLLECTION = "exclusive_store"  # Collection to store the exclusive shop items
MAX_STORE_ITEMS = 5  # Only 5 characters in store at a time

# 📌 Fixed Prices Based on Rarity
RARITY_PRICES = {
    "🟡 Sparking": 600,
    "🔱 Ultra": 900,
    "💠 Legends Limited": 1200,
    "🔮 Zenkai": 1500,
    "🏆 Event-Exclusive": 1800
}

# Conversation states
SELECT_ID, CONFIRM_PURCHASE = range(2)

# ✅ Function to refresh the store weekly
async def refresh_store():
    """Fetch 5 random high-rarity characters and set them in store with fixed prices."""
    await collection.update_many({}, {"$set": {"in_store": False}})  # Reset all store flags
    high_rarity = list(RARITY_PRICES.keys())
    
    characters = await collection.aggregate([
        {"$match": {"rarity": {"$in": high_rarity}}},
        {"$sample": {"size": MAX_STORE_ITEMS}}
    ]).to_list(None)

    for char in characters:
        char["stock"] = random.randint(2, 5)  # Random stock
        char["price"] = RARITY_PRICES.get(char["rarity"], 1000)  # Set fixed price based on rarity
        char["in_store"] = True
        await collection.update_one({"_id": char["_id"]}, {"$set": char})

# ✅ Function to display the store
async def exclusive_store(update: Update, context: CallbackContext):
    """Shows available characters in the exclusive store."""
    store_chars = await collection.find({"in_store": True}).to_list(None)

    if not store_chars:
        await update.message.reply_text("❌ The Exclusive Store is currently empty! Check back later.")
        return

    text = "🏪 **Exclusive Store** (Refreshes Weekly)\n\n"
    buttons = []
    
    for char in store_chars:
        text += f"🎴 **{char['name']}**\n"
        text += f"🆔 ID: `{char['id']}` | 🎖 Rarity: {char['rarity']}\n"
        text += f"💎 Price: {char['price']} CC | 📦 Stock: {char['stock']}\n\n"
        buttons.append([InlineKeyboardButton(f"🛒 Buy {char['name']}", callback_data=f"buy_{char['id']}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ✅ Function to handle buy button
async def buy_character(update: Update, context: CallbackContext):
    """Prompts user to enter the ID of the character they want to buy."""
    query = update.callback_query
    await query.answer()
    
    char_id = query.data.split("_")[1]
    context.user_data["buying_char"] = char_id

    await query.message.reply_text(f"🔢 **Enter the character ID ({char_id}) to confirm purchase:**")
    return SELECT_ID

# ✅ Function to verify character ID
async def verify_character(update: Update, context: CallbackContext):
    """Verifies the entered character ID and asks for confirmation."""
    user_id = update.message.from_user.id
    char_id = update.message.text.strip()

    # Check if the user is trying to buy a valid character
    if context.user_data.get("buying_char") != char_id:
        await update.message.reply_text("❌ Invalid ID! Please enter the correct character ID.")
        return SELECT_ID

    character = await collection.find_one({"id": char_id, "in_store": True})
    if not character or character["stock"] <= 0:
        await update.message.reply_text("❌ Character is no longer available!")
        return ConversationHandler.END

    user = await user_collection.find_one({"id": user_id})
    if not user or user.get("chrono_crystals", 0) < character["price"]:
        await update.message.reply_text("❌ You don’t have enough Chrono Crystals!")
        return ConversationHandler.END

    context.user_data["character"] = character  # Store character for final confirmation

    # Show confirmation message
    buttons = [
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_buy"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"⚠️ Are you sure you want to buy **{character['name']}** for {character['price']} CC?",
        reply_markup=keyboard
    )
    return CONFIRM_PURCHASE

# ✅ Function to confirm purchase
async def confirm_purchase(update: Update, context: CallbackContext):
    """Completes the purchase transaction."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    character = context.user_data.get("character")

    if not character:
        await query.message.edit_text("❌ Purchase failed. Try again!")
        return ConversationHandler.END

    user = await user_collection.find_one({"id": user_id})
    if user["chrono_crystals"] < character["price"]:
        await query.message.edit_text("❌ You don’t have enough Chrono Crystals!")
        return ConversationHandler.END

    # Deduct CC, decrease stock, and add character to user collection
    await user_collection.update_one({"id": user_id}, {
        "$inc": {"chrono_crystals": -character["price"]},
        "$push": {"characters": character}
    })

    await collection.update_one({"id": character["id"]}, {"$inc": {"stock": -1}})
    
    await query.message.edit_text(f"🎉 Successfully purchased **{character['name']}**!\n💎 Remaining CC: {user['chrono_crystals'] - character['price']}")
    return ConversationHandler.END

# ✅ Function to cancel purchase
async def cancel_purchase(update: Update, context: CallbackContext):
    """Cancels the purchase process."""
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("❌ Purchase canceled.")
    return ConversationHandler.END

# ✅ Function to manually add characters (Admin Only)
async def add_store_character(update: Update, context: CallbackContext):
    """Admins can manually add characters to the store."""
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the bot owner can add characters to the store!")
        return

    try:
        char_id, stock = context.args
        character = await collection.find_one({"id": char_id})
        if not character:
            await update.message.reply_text("❌ Character not found in the database!")
            return

        if character["rarity"] not in RARITY_PRICES:
            await update.message.reply_text("❌ This rarity is not allowed in the store!")
            return

        character["price"] = RARITY_PRICES[character["rarity"]]
        character["stock"] = int(stock)
        character["in_store"] = True
        await collection.update_one({"id": char_id}, {"$set": character})

        await update.message.reply_text(f"✅ **{character['name']}** added to the store!")
    except ValueError:
        await update.message.reply_text("❌ Usage: `/addstore <char_id> <stock>`")
    except IndexError:
        await update.message.reply_text("❌ Missing arguments! Usage: `/addstore <char_id> <stock>`")

# ✅ Conversation Handler
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(buy_character, pattern=r"buy_\d+")],
    states={
        SELECT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_character)],
        CONFIRM_PURCHASE: [CallbackQueryHandler(confirm_purchase, pattern="confirm_buy"),
                           CallbackQueryHandler(cancel_purchase, pattern="cancel_buy")]
    },
    fallbacks=[]
)

# ✅ Add Handlers
application.add_handler(CommandHandler("store", exclusive_store))
application.add_handler(CommandHandler("addstore", add_store_character))
application.add_handler(conv_handler)

# ✅ Schedule store refresh every week
asyncio.create_task(refresh_store())
