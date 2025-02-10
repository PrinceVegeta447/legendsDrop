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
    """Generates a new daily store with 10 random characters, avoiding excluded rarities."""
    available_characters = await collection.find({"rarity": {"$nin": EXCLUDED_RARITIES}}).to_list(None)
    if len(available_characters) < 10:
        return []  # Not enough characters

    store = random.sample(available_characters, 10)  # Select 10 random characters
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
        rarity = char["rarity"]
        price = RARITY_PRICES.get(rarity, 999999)
        store_message += f"{rarity} {char['id']} <b>{char['name']}</b>\n💰 Price: <code>{price} Zeni</code>\n━━━━━━━━━━━━━━━━━━━━\n"

    keyboard = [[InlineKeyboardButton("🔄 Refresh Store", callback_data="refresh_store")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(store_message, parse_mode="HTML", reply_markup=reply_markup)

async def refresh_store(update: Update, context: CallbackContext) -> None:
    """Allows users to refresh the store, with one free refresh per day."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id}) or {}
    user.setdefault("store_refreshes", 0)
    user.setdefault("coins", 0)

    if user["store_refreshes"] < FREE_REFRESH_LIMIT:
        new_store = await generate_store()
        await user_collection.update_one({"id": user_id}, {"$inc": {"store_refreshes": 1}})
        await update.callback_query.answer("✅ Store refreshed for free!", show_alert=True)
    elif user["coins"] >= REFRESH_COST:
        await user_collection.update_one({"id": user_id}, {"$inc": {"coins": -REFRESH_COST, "store_refreshes": 1}})
        new_store = await generate_store()
        await update.callback_query.answer(f"✅ Store refreshed! You spent {REFRESH_COST} Zeni.", show_alert=True)
    else:
        await update.callback_query.answer("❌ Not enough Zeni to refresh!", show_alert=True)
        return

    await store(update, context)  # Re-send the updated store

async def buy_store_character(update: Update, context: CallbackContext) -> None:
    """Handles buying a character from the store."""
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/buy <character_id>`", parse_mode="Markdown")
        return

    char_id = context.args[0]

    # ✅ Fetch User Data
    user = await user_collection.find_one({"id": user_id}) or {}
    user_coins = int(user.get("coins", 0))  # ✅ Fetches from "coins" instead of "zeni"

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

    price = int(character["price"])

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
        f"💰 **Price:** {price} Zeni\n"
        f"🔹 The character has been added to your collection!",
        parse_mode="Markdown"
    )


# ✅ **Register Handler**
application.add_handler(CommandHandler("storebuy", buy_store_character, block=False))
application.add_handler(CommandHandler("store", store, block=False))
application.add_handler(CallbackQueryHandler(refresh_store, pattern="^refresh_store$", block=False))
