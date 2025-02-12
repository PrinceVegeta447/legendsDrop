from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, collection, user_collection

# ✅ Updated Rarity Icons
RARITY_ICONS = {
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

# ✅ Updated Category Icons
CATEGORY_ICONS = {
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

async def check_character(update: Update, context: CallbackContext) -> None:
    """Displays character details and collector buttons."""
    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/check <character_id>`", parse_mode="Markdown")
        return

    character_id = context.args[0]
    character = await collection.find_one({"id": character_id})

    if not character:
        await update.message.reply_text("❌ **Character not found!**", parse_mode="Markdown")
        return

    # ✅ Extract Character Details
    name = character["name"]
    rarity = str(character.get("rarity", "Unknown"))
    category = str(character.get("category", "Unknown"))

    rarity_text = RARITY_ICONS.get(rarity, "❓ Unknown Rarity")
    category_text = CATEGORY_ICONS.get(category, "❓ Unknown Category")

    message = (
        f"🎴 <b>Character:</b> {name}\n"
        f"🎖 <b>Rarity:</b> {rarity_text}\n"
        f"📜 <b>Category:</b> {category_text}"
    )

    # ✅ Buttons: Top Collectors | Show Collectors Here
    keyboard = [
        [InlineKeyboardButton("🏆 Top Collectors", callback_data=f"top_collectors:{character_id}")],
        [InlineKeyboardButton("📍 Show Collectors Here", callback_data=f"local_collectors:{character_id}")]
    ]

    await update.message.reply_photo(
        photo=character.get("file_id", None) or character.get("img_url", None),
        caption=message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_top_collectors(update: Update, context: CallbackContext) -> None:
    """Displays top collectors for a specific character globally."""
    query = update.callback_query
    _, character_id = query.data.split(":")

    collectors = await user_collection.find({"characters.id": character_id}).to_list(length=10)
    
    if not collectors:
        await query.answer("❌ No collectors found for this character!", show_alert=True)
        return

    leaderboard = sorted(collectors, key=lambda x: x["characters"].count(character_id), reverse=True)
    message = "🏆 **Top Collectors for this Character:**\n"

    for i, user in enumerate(leaderboard[:5], 1):
        message += f"{i}. {user['first_name']} - {user['characters'].count(character_id)} times\n"

    await query.message.reply_text(message, parse_mode="Markdown")

async def show_local_collectors(update: Update, context: CallbackContext) -> None:
    """Displays collectors of a specific character in the current group."""
    query = update.callback_query
    _, character_id = query.data.split(":")
    group_id = query.message.chat.id

    collectors = await user_collection.find({"characters.id": character_id, "groups": group_id}).to_list(length=10)

    if not collectors:
        await query.answer("❌ No collectors found in this group!", show_alert=True)
        return

    message = "📍 **Collectors in this Group:**\n"
    for i, user in enumerate(collectors[:5], 1):
        message += f"{i}. {user['first_name']} - {user['characters'].count(character_id)} times\n"

    await query.message.reply_text(message, parse_mode="Markdown")

# ✅ Register Handlers
application.add_handler(CommandHandler("check", check_character, block=False))
application.add_handler(CallbackQueryHandler(show_top_collectors, pattern="^top_collectors:", block=False))
application.add_handler(CallbackQueryHandler(show_local_collectors, pattern="^local_collectors:", block=False))
