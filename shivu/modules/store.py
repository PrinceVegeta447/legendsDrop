import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, user_collection, collection, store_collection

# ⚡ **Store Settings**
EXCLUDED_RARITIES = ["💠 Legends Limited", "🔮 Zenkai", "🏆 Event-Exclusive"]
RARITY_PRICES = {
    "⚪ Common": 20000,
    "🟢 Uncommon": 30000,
    "🔵 Rare": 50000,
    "🟣 Extreme": 70000,
    "🟡 Sparking": 100000,
    "🔱 Ultra": 250000
}
FREE_REFRESH_LIMIT = 1
REFRESH_COST = 25000  # Cost after free refresh is used

async def generate_store():
    """Generates a new daily store with 10 random characters, ensuring prices are correctly stored."""
    available_characters = await collection.find({"rarity": {"$nin": EXCLUDED_RARITIES}}).to_list(None)
    if len(available_characters) < 10:
        return []  # Not enough characters

    store = []
    selected_characters = random.sample(available_characters, 10)  # Select 10 random characters

    for char in selected_characters:
        price = RARITY_PRICES.get(char.get("rarity", "Unknown"), 999999)  # Assign price properly
        store.append({
            "id": char.get("id"),
            "name": char.get("name"),
            "rarity": char.get("rarity"),
            "price": price  # ✅ Always include the price field
        })

    # ✅ Save Store to Database
    await store_collection.delete_many({})
    await store_collection.insert_one({"date": time.strftime("%Y-%m-%d"), "characters": store})
    return store

async def get_store():
    """Fetches the current store, generates a new one if expired."""
    store_data = await store_collection.find_one({})
    if not store_data or store_data["date"] != time.strftime("%Y-%m-%d"):
        return await generate_store()
    return store_data["characters"]

async def store(update: Update, context: CallbackContext) -> None:
    """Displays the current character store with pricing."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id}) or {}
    user.setdefault("store_refreshes", 0)

    characters = await get_store()
    if not characters:
        await update.message.reply_text("❌ No characters available in the store right now!")
        return

    store_message = "<b>🛒 Today's Character Store</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    keyboard = []

    for char in characters:
        store_message += (
            f"{char['rarity']} <b>{char['name']}</b>\n"
            f"💰 <b>Price:</b> <code>{char.get('price', 'Unknown')} Zeni</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
        )
        keyboard.append([InlineKeyboardButton(f"🛍 Buy {char['name']}", callback_data=f"storebuy_{char['id']}")])

    # ✅ Add Refresh Button
    keyboard.append([InlineKeyboardButton("🔄 Refresh Store", callback_data="refresh_store")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(store_message, parse_mode="HTML", reply_markup=reply_markup)

async def refresh_store(update: Update, context: CallbackContext) -> None:
    """Allows users to refresh the store, with one free refresh per day."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id}) or {}
    user.setdefault("store_refreshes", 0)
    user.setdefault("coins", 0)

    if user["store_refreshes"] < FREE_REFRESH_LIMIT:
        await generate_store()
        await user_collection.update_one({"id": user_id}, {"$inc": {"store_refreshes": 1}})
        await update.callback_query.answer("✅ Store refreshed for free!", show_alert=True)
    elif user["coins"] >= REFRESH_COST:
        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -REFRESH_COST, "store_refreshes": 1}})
        await generate_store()
        await update.callback_query.answer(f"✅ Store refreshed! You spent {REFRESH_COST} Zeni.", show_alert=True)
    else:
        await update.callback_query.answer("❌ Not enough Zeni to refresh!", show_alert=True)
        return

    await store(update, context)  # Re-send the updated store

async def buy_store_character(update: Update, context: CallbackContext) -> None:
    """Handles buying a character from the store."""
    query = update.callback_query
    user_id = update.effective_user.id
    char_id = query.data.split("_")[1]

    # ✅ Fetch User Data
    user = await user_collection.find_one({"id": user_id}) or {}
    user_coins = int(user.get("coins", 0))  # ✅ Fetches from "coins"

    # ✅ Fetch Store Data
    store_data = await store_collection.find_one({})
    if not store_data:
        await query.answer("❌ Store is empty!", show_alert=True)
        return

    # ✅ Find the Character in Store
    character = next((c for c in store_data["characters"] if c["id"] == char_id), None)
    if not character:
        await query.answer("❌ Character not found in store!", show_alert=True)
        return

    price = int(character.get("price", 999999))  # ✅ Ensure price is correctly assigned

    # ✅ Check Zeni Balance
    if user_coins < price:
        await query.answer(f"❌ Not enough Zeni! You need {price}, but have {user_coins}.", show_alert=True)
        return

    # ✅ Deduct Zeni & Add Character to Inventory
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"coins": -price}, "$push": {"characters": character}}
    )

    # ✅ Confirm Purchase
    await query.answer(f"✅ Purchased {character['name']} for {price} Zeni!", show_alert=True)
    await update.callback_query.message.reply_text(
        f"✅ <b>Purchase Successful!</b>\n"
        f"🎴 <b>Character:</b> {character['name']}\n"
        f"🎖 <b>Rarity:</b> {character['rarity']}\n"
        f"💰 <b>Price:</b> {price} Zeni\n"
        f"🔹 The character has been added to your collection!",
        parse_mode="HTML"
    )

# ✅ **Register Handler**
application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CallbackQueryHandler(refresh_store, pattern="^refresh_store$", block=False))
application.add_handler(CallbackQueryHandler(buy_store_character, pattern="^storebuy_", block=False))
