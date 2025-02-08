from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from shivu import collection, user_collection, application

# Rarity and Category Maps
RARITY_MAP = {
    "1": "⚪ Common",
    "2": "🟢 Uncommon",
    "3": "🔵 Rare",
    "4": "🟣 Extreme",
    "5": "🟡 Sparking",
    "6": "🔱 Ultra",
    "7": "💠 Legends Limited",
    "8": "🔮 Zenkai",
    "9": "🏆 Event-Exclusive"
}

CATEGORY_MAP = {
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
    "17": "☠️ Lineage Of Evil"       
}

# Function to display sort options
async def sort_collection(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("📌 Sort by Rarity", callback_data="sort:rarity")],
        [InlineKeyboardButton("📌 Sort by Category", callback_data="sort:category")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔄 Choose how you want to sort your collection:", reply_markup=reply_markup)

# Function to handle sort selection
async def sort_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data

    if data == "sort:rarity":
        keyboard = [[InlineKeyboardButton(r, callback_data=f"set_sort:rarity:{k}")] for k, r in RARITY_MAP.items()]
        await query.message.edit_text("🎖 Select Rarity to sort by:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "sort:category":
        keyboard = [[InlineKeyboardButton(c, callback_data=f"set_sort:category:{k}")] for k, c in CATEGORY_MAP.items()]
        await query.message.edit_text("🔹 Select Category to sort by:", reply_markup=InlineKeyboardMarkup(keyboard))

# Function to save user sorting preference
async def set_sort(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    _, sort_type, value = query.data.split(":")

    user_id = query.from_user.id
    sort_field = "rarity" if sort_type == "rarity" else "category"
    sort_value = RARITY_MAP.get(value) if sort_type == "rarity" else CATEGORY_MAP.get(value)

    await user_collection.update_one({'id': user_id}, {'$set': {'sort_preference': {sort_field: value}}}, upsert=True)

    await query.message.edit_text(f"✅ Your collection will now be sorted by **{sort_value}**!")

# Function to display collection (sorted)
async def harem(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or 'characters' not in user or not user['characters']:
        await update.message.reply_text('😔 You have not collected any characters yet!')
        return

    # Fetch user's sort preference
    sort_preference = user.get("sort_preference", {})
    sort_field = "rarity" if "rarity" in sort_preference else "category"
    sort_order = sort_preference.get(sort_field)

    # Sort characters based on user preference
    if sort_order:
        characters = sorted(user['characters'], key=lambda x: x.get(sort_field, ""))
    else:
        characters = user['characters']

    message_text = f"📜 **{update.effective_user.first_name}'s Collection (Sorted by {sort_field.title()})**\n"
    for char in characters:
        message_text += f"🏆 {char['name']} | {char.get('rarity', 'Unknown')} | {char.get('category', 'Unknown')}\n"

    await update.message.reply_text(message_text)

# Handlers
application.add_handler(CommandHandler("sort", sort_collection))
application.add_handler(CallbackQueryHandler(sort_callback, pattern="^sort:"))
application.add_handler(CallbackQueryHandler(set_sort, pattern="^set_sort:"))
application.add_handler(CommandHandler(["harem", "collection"], harem))
