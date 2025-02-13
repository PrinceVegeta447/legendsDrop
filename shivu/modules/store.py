import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CallbackContext
from shivu import application, collection, user_collection, OWNER_ID

STORE_COLLECTION = "exclusive_store"
MAX_STORE_ITEMS = 5

# Fixed Prices for Rarity
RARITY_PRICES = {
    "🟡 Sparking": 600,
    "🔱 Ultimate": 2500,
    "👑 Supreme": 10000, 
    "⛩️ Celestial": 5000,
    "🔮 Limited Edition": 1800
}

# Conversation states
SELECT_ID, CONFIRM_PURCHASE = range(2)

# ✅ Refresh store with 5 random high-rarity characters
async def refresh_store():
    await collection.update_many({}, {"$set": {"in_store": False}})
    high_rarity = list(RARITY_PRICES.keys())

    characters = await collection.aggregate([
        {"$match": {"rarity": {"$in": high_rarity}}},
        {"$sample": {"size": MAX_STORE_ITEMS}}
    ]).to_list(None)

    for char in characters:
        char["stock"] = random.randint(1, 4)
        char["price"] = RARITY_PRICES.get(char["rarity"], 1000)
        char["in_store"] = True
        await collection.update_one({"_id": char["_id"]}, {"$set": char})

# ✅ Display store with all characters on one page
async def exclusive_store(update: Update, context: CallbackContext):
    store_chars = await collection.find({"in_store": True}).to_list(None)
    
    if not store_chars:
        await update.message.reply_text("❌ The Exclusive Store is currently empty!")
        return

    text = "🏪 **Exclusive Store** (Refreshes Weekly)\n\n"
    
    for char in store_chars:
        text += f"🆔 `{char['id']}` {char['rarity']} **{char['name']}** (Stock: {char['stock']}X)\n"
        text += f"💎 **Price:** {char['price']} CC\n\n"

    keyboard = [
        [InlineKeyboardButton("🛒 Buy Now", callback_data="start_purchase")]
    ]
    
    await update.message.reply_text(
        text + "🔽 **Enter the Character ID you want to buy** and confirm below.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ✅ Start purchase - Ask user to enter character ID
async def start_purchase(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🔢 **Enter the Character ID you want to buy:**")
    return SELECT_ID

# ✅ Verify character ID
async def verify_character(update: Update, context: CallbackContext):
    char_id = update.message.text.strip()
    user_id = update.message.from_user.id
    print(f"🔍 Received Character ID: {char_id}")  

    character = await collection.find_one({"id": char_id, "in_store": True})
    print(f"🔍 Character Found: {character}")  

    if not character or character["stock"] <= 0:
        await update.message.reply_text("❌ Invalid ID or character out of stock!")
        return SELECT_ID

    user = await user_collection.find_one({"id": user_id})
    if not user or user.get("chrono_crystals", 0) < character["price"]:
        await update.message.reply_text("❌ You don’t have enough Chrono Crystals!")
        return ConversationHandler.END

    context.user_data["character"] = character
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

# ✅ Complete purchase
async def confirm_purchase(update: Update, context: CallbackContext):
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

    await user_collection.update_one({"id": user_id}, {
        "$inc": {"chrono_crystals": -character["price"]},
        "$push": {"characters": character}
    })
    await collection.update_one({"id": character["id"]}, {"$inc": {"stock": -1}})

    await query.message.edit_text(f"🎉 Successfully purchased **{character['name']}**!\n💎 Remaining CC: {user['chrono_crystals'] - character['price']}")
    return ConversationHandler.END

# ✅ Cancel purchase
async def cancel_purchase(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("❌ Purchase canceled.")
    return ConversationHandler.END

# ✅ Admin function to manually add characters
async def add_store_character(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the bot owner can add characters to the store!")
        return

    try:
        char_id, stock = context.args
        character = await collection.find_one({"id": char_id})
        if not character:
            await update.message.reply_text("❌ Character not found!")
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
    entry_points=[CallbackQueryHandler(start_purchase, pattern="start_purchase")],
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


loop = asyncio.get_event_loop()
loop.create_task(refresh_store())
