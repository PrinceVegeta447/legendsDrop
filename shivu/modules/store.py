import asyncio
import time
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, collection, store_collection

# 🏷 **Define Rarity-Based Prices**
RARITY_PRICES = {
            "1": "⚪ Common" : 25000,
            "2": "🟢 Uncommon" : 45000,
            "3": "🔵 Rare" : 80000,
            "4": "🟣 Extreme" : 125000,
            "5": "🟡 Sparking" : 250000,
            "6": "🔱 Ultra" : 400000
}

# 🚫 **Excluded Rarities**
EXCLUDED_RARITIES = ["💠 Legends Limited", "🔮 Zenkai", "🏆 Event-Exclusive"]

# 🛒 **Fetch & Refresh Store**
async def refresh_store(user_id: int, force=False):
    """Fetches a new set of store characters, ensuring unique items daily."""
    user = await user_collection.find_one({"id": user_id}) or {}

    # ✅ **Check Free Refresh Limit**
    last_refresh = user.get("last_store_refresh", 0)
    refresh_count = user.get("store_refreshes", 0)
    current_day = datetime.utcnow().date().isoformat()

    # ✅ **Ensure Store Resets Daily**
    if last_refresh != current_day or force:
        # 🎴 **Fetch 10 Unique Characters (Excluding Some Rarities)**
        available_characters = await collection.find(
            {"rarity": {"$nin": EXCLUDED_RARITIES}}
        ).to_list(length=None)

        if len(available_characters) < 10:
            return None  # Not enough characters for the store.

        store_characters = random.sample(available_characters, 10)

        # ✅ **Store the New Characters**
        await store_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "characters": store_characters,
                "last_store_refresh": current_day,
                "store_refreshes": 0  # Reset refreshes daily
            }},
            upsert=True
        )

    return await store_collection.find_one({"user_id": user_id})

# 🛍 **Display the Store**
async def view_store(update: Update, context: CallbackContext):
    """Displays the user's store with today's available characters."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    store_data = await refresh_store(user_id)
    if not store_data:
        await update.message.reply_text("❌ No characters available in the store!")
        return

    characters = store_data["characters"]
    refresh_count = user.get("store_refreshes", 0)
    free_refresh = refresh_count == 0
    refresh_cost = "Free" if free_refresh else "25,000 Zeni"

    # 📝 **Format Store Message**
    store_message = "<b>🛒 Today's Store:</b>\n\n"
    for char in characters:
        rarity = char["rarity"]
        price = RARITY_PRICES.get(rarity, 50000)  # Default price if not listed
        store_message += f"{rarity} {char['id']} {char['name']}\n"
        store_message += f"💰 Price: {price} Zeni\n\n"

    store_message += f"🔄 <b>Refresh Cost:</b> {refresh_cost}\n"
    
    # 🔘 **Inline Buttons**
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Store", callback_data=f"refresh_store:{user_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(store_message, parse_mode="HTML", reply_markup=reply_markup)

# 🔄 **Handle Store Refresh**
async def refresh_store_callback(update: Update, context: CallbackContext):
    """Handles store refresh when the button is clicked."""
    query = update.callback_query
    user_id = query.from_user.id

    user = await user_collection.find_one({"id": user_id}) or {}
    refresh_count = user.get("store_refreshes", 0)

    if refresh_count == 0:
        await user_collection.update_one({"id": user_id}, {"$inc": {"store_refreshes": 1}})
    else:
        # Deduct Zeni for extra refresh
        if user.get("coins", 0) < 25000:
            await query.answer("❌ Not enough Zeni to refresh!", show_alert=True)
            return

        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -25000, "store_refreshes": 1}})

    # Refresh Store
    await refresh_store(user_id, force=True)
    await query.answer("🔄 Store Refreshed!")
    await view_store(update, context)

# 🛍 **Buy a Character**
async def buy_character(update: Update, context: CallbackContext):
    """Allows users to buy a character from the store."""
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/buy <character_id>`", parse_mode="Markdown")
        return

    char_id = context.args[0]

    # ✅ **Fetch Store Data**
    store_data = await store_collection.find_one({"user_id": user_id})
    if not store_data:
        await update.message.reply_text("❌ Your store is empty! Use /store to view available characters.")
        return

    # ✅ **Find the Character**
    character = next((c for c in store_data["characters"] if str(c["id"]) == char_id), None)
    if not character:
        await update.message.reply_text("❌ Character not found in your store!")
        return

    price = RARITY_PRICES.get(character["rarity"], 50000)  # Default price

    # ✅ **Check Zeni Balance**
    user = await user_collection.find_one({"id": user_id}) or {}
    user_balance = user.get("coins", 0)

    if user_balance < price:
        await update.message.reply_text(f"❌ Not enough Zeni! You need {price}, but you have {user_balance}.")
        return

    # ✅ **Deduct Zeni & Add Character**
    await user_collection.update_one({"id": user_id}, {
        "$inc": {"coins": -price},
        "$push": {"characters": character}
    })

    # ✅ **Remove Character from Store**
    await store_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"characters": {"id": char_id}}}
    )

    await update.message.reply_text(
        f"✅ **Purchase Successful!**\n"
        f"🎴 **Character:** {character['name']}\n"
        f"🎖 **Rarity:** {character['rarity']}\n"
        f"💰 **Price:** {price} Zeni\n"
        f"🔹 The character has been added to your collection!",
        parse_mode="Markdown"
    )

# ✅ **Register Handlers**
application.add_handler(CommandHandler("store", view_store, block=False))
application.add_handler(CommandHandler("buy", buy_character, block=False))
application.add_handler(CallbackQueryHandler(refresh_store_callback, pattern="^refresh_store:", block=False))
