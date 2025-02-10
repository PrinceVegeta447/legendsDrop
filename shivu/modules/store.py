import random
import time
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
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
CATEGORIES = {
    "1": "🏆 Saiyan",
    "2": "🔥 Hybrid Saiyan",
    "3": "🤖 Android",
    "4": "❄️ Frieza Force",
    "5": "✨ God Ki",
    "6": "💪 Super Warrior",
    "7": "🩸 Regeneration",
    "8": "🔀 Fusion Warrior",
    "9": "🤝 Duo",
   "10": "🔱 Super Saiyan God SS", 
   "11": "🗿 Ultra Instinct Sign",
   "12": "⚡ Super Saiyan",
   "13": "❤️‍🔥 Dragon Ball Saga",
   "14": "💫 Majin Buu Saga",
   "15": "👾 Cell Saga",
   "16": "📽️ Sagas From the Movies",
   "17": "☠️ Lineage Of Evil",
   "18": "🌏 Universe Survival Saga"
}
FREE_REFRESH_LIMIT = 1
REFRESH_COST = 25000  # Cost after free refresh is used

async def generate_store():
    """Generates a new daily store with 10 random characters, avoiding excluded rarities."""
    available_characters = await collection.find({"rarity": {"$nin": EXCLUDED_RARITIES}}).to_list(None)
    if len(available_characters) < 10:
        return []  # Not enough characters

    store = []
    selected_characters = random.sample(available_characters, 10)  # Select 10 random characters

    for char in selected_characters:
        price = RARITY_PRICES.get(char["rarity"], 999999)  # Assign price
        category = CATEGORIES.get(char.get("category", "Unknown"), "Unknown")  # Assign category
        char["price"] = price
        char["category"] = category
        store.append(char)

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
    for char in characters:
        store_message += (
            f"{char['rarity']} {char['id']} <b>{char['name']}</b>\n"
            f"🏷 <b>Category:</b> {char['category']}\n"
            f"💰 <b>Price:</b> <code>{char['price']} Zeni</code>\n━━━━━━━━━━━━━━━━━━━━\n"
        )

    store_message += "🔹 Use `/refreshstore` to refresh the store.\n"
    store_message += "💰 Use `/storebuy <character_id>` to purchase a character."

    await update.message.reply_text(store_message, parse_mode="HTML")

async def refresh_store(update: Update, context: CallbackContext) -> None:
    """Allows users to refresh the store, with one free refresh per day."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id}) or {}
    user.setdefault("store_refreshes", 0)
    user.setdefault("coins", 0)

    if user["store_refreshes"] < FREE_REFRESH_LIMIT:
        await generate_store()
        await user_collection.update_one({"id": user_id}, {"$inc": {"store_refreshes": 1}})
        await update.message.reply_text("✅ Store refreshed for free!")
    elif user["coins"] >= REFRESH_COST:
        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -REFRESH_COST, "store_refreshes": 1}})
        await generate_store()
        await update.message.reply_text(f"✅ Store refreshed! You spent {REFRESH_COST} Zeni.")
    else:
        await update.message.reply_text("❌ Not enough Zeni to refresh!")
        return

    await store(update, context)  # Re-send the updated store

async def buy_store_character(update: Update, context: CallbackContext) -> None:
    """Handles buying a character from the store."""
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/storebuy <character_id>`", parse_mode="Markdown")
        return

    char_id = context.args[0]

    # ✅ Fetch User Data
    user = await user_collection.find_one({"id": user_id}) or {}
    user.setdefault("characters", [])
    user_coins = int(user.get("coins", 0))  # ✅ Fetches from "coins"

    # ✅ Fetch Store Data
    store_data = await store_collection.find_one({})
    if not store_data:
        await update.message.reply_text("❌ **Store is currently empty!**", parse_mode="Markdown")
        return

    # ✅ Find the Character in Store
    character = next((c for c in store_data["characters"] if c["id"] == char_id), None)
    if not character:
        await update.message.reply_text("❌ **Invalid character ID!**", parse_mode="Markdown")
        return

    price = character.get("price", 999999)  # Ensure price exists

    # ✅ Check Zeni Balance
    if user_coins < price:
        await update.message.reply_text(
            f"❌ **Not enough Zeni!** You need `{price}`, but you have `{user_coins}`.",
            parse_mode="Markdown"
        )
        return

    # ✅ Deduct Zeni & Add Character to Inventory
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"coins": -price}, "$push": {"characters": character}}
    )

    # ✅ Confirm Purchase
    await update.message.reply_text(
        f"✅ **Purchase Successful!**\n"
        f"🎴 **Character:** {character['name']}\n"
        f"🎖 **Rarity:** {character['rarity']}\n"
        f"🏷 **Category:** {character['category']}\n"
        f"💰 **Price:** {price} Zeni\n"
        f"🔹 The character has been added to your collection!",
        parse_mode="Markdown"
    )


# ✅ **Register Handlers**
application.add_handler(CommandHandler("storebuy", buy_store_character, block=False))
application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CommandHandler("refreshstore", refresh_store, block=False))
