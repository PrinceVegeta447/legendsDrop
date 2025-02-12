from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, collection, user_collection

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
    rarity_text = character.get("rarity", "❓ Unknown Rarity")  # Now uses stored values directly
    category_text = character.get("category", "❓ Unknown Category")

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
        photo=character.get("file_id", None),
        caption=message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_top_collectors(update: Update, context: CallbackContext) -> None:
    """Displays top collectors for a specific character globally."""
    query = update.callback_query
    _, character_id = query.data.split(":")

    pipeline = [
        {"$match": {"characters.id": character_id}},  # Match users who own this character
        {"$unwind": "$characters"},  # Flatten characters array
        {"$match": {"characters.id": character_id}},  # Ensure only matching character is counted
        {"$group": {"_id": "$id", "count": {"$sum": 1}, "first_name": {"$first": "$first_name"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]

    collectors = await user_collection.aggregate(pipeline).to_list(length=5)

    if not collectors:
        await query.answer("❌ No collectors found for this character!", show_alert=True)
        return

    message = "🏆 **Top Collectors for this Character:**\n"
    for i, user in enumerate(collectors, 1):
        message += f"{i}. {user['first_name']} - {user['count']} times\n"

    await query.message.edit_text(message, parse_mode="Markdown")

async def show_local_collectors(update: Update, context: CallbackContext) -> None:
    """Displays collectors of a specific character in the current group."""
    query = update.callback_query
    _, character_id = query.data.split(":")
    group_id = query.message.chat.id

    pipeline = [
        {"$match": {"characters.id": character_id}},  # Match users who own this character
        {"$unwind": "$characters"},  # Flatten characters array
        {"$match": {"characters.id": character_id}},  # Ensure only matching character is counted
        {"$match": {"groups": group_id}},  # Filter only users in this group
        {"$group": {"_id": "$id", "count": {"$sum": 1}, "first_name": {"$first": "$first_name"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]

    collectors = await user_collection.aggregate(pipeline).to_list(length=5)

    if not collectors:
        await query.answer("❌ No collectors found in this group!", show_alert=True)
        return

    message = "📍 **Collectors in this Group:**\n"
    for i, user in enumerate(collectors, 1):
        message += f"{i}. {user['first_name']} - {user['count']} times\n"

    await query.message.edit_text(message, parse_mode="Markdown")

# ✅ Register Handlers
application.add_handler(CommandHandler("check", check_character, block=False))
application.add_handler(CallbackQueryHandler(show_top_collectors, pattern="^top_collectors:", block=False))
application.add_handler(CallbackQueryHandler(show_local_collectors, pattern="^local_collectors:", block=False))
