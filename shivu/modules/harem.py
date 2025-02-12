from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from itertools import groupby
from html import escape
import math
import random
from shivu import collection, user_collection, application, db

DEFAULT_SORT = "category"  # Default sorting option

CATEGORY_ICONS = {
    "🏆 Saiyan": "🏆", "🔥 Hybrid Saiyan": "🔥", "🤖 Android": "🤖",
    "❄️ Frieza Force": "❄️", "✨ God Ki": "✨", "💪 Super Warrior": "💪",
    "🩸 Regeneration": "🩸", "🔀 Fusion Warrior": "🔀", "🤝 Duo": "🤝",
    "🔱 Super Saiyan God SS": "🔱", "🗿 Ultra Instinct Sign": "🗿",
    "⚡ Super Saiyan": "⚡", "❤️‍🔥 Dragon Ball Saga": "❤️‍🔥",
    "💫 Majin Buu Saga": "💫", "👾 Cell Saga": "👾", "📽️ Sagas From the Movies": "📽️",
    "☠️ Lineage Of Evil": "☠️", "🌏 Universe Survival Saga": "🌏"
}

RARITY_ICONS = {
    "⚪ Common": "⚪", "🟢 Uncommon": "🟢", "🔵 Rare": "🔵",
    "🟣 Extreme": "🟣", "🟡 Sparking": "🟡", "🔱 Ultra": "🔱",
    "💠 Legends Limited": "💠", "🔮 Zenkai": "🔮", "🏆 Event-Exclusive": "🏆"
}

async def fetch_character_data(char_id):
    """Fetch character category from the main database."""
    character = await collection.find_one({"id": char_id})
    return character.get("category", "Unknown") if character else "Unknown"

async def harem(update: Update, context: CallbackContext, page=0, query=None) -> None:
    """Displays user's character collection with improved UI."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or not user.get("characters"):
        message = "❌ <b>You don't have any characters in your collection yet!</b>"
        if query:
            await query.answer(message, show_alert=True)
        else:
            await update.message.reply_text(message, parse_mode="HTML")
        return

    # ✅ Fetch sorting preference (Default: Category)
    user_pref = await db.user_sorting.find_one({'user_id': user_id}) or {"sort_by": DEFAULT_SORT}
    sort_by = user_pref["sort_by"]

    # ✅ Update character data with category if missing
    for character in user["characters"]:
        if "category" not in character:
            character["category"] = await fetch_character_data(character["id"])

    # ✅ Sorting logic (Category → Default, Rarity → Alternative)
    characters = sorted(user["characters"], key=lambda x: (x.get(sort_by, "Unknown"), x["id"]))

    # ✅ Grouping characters based on sort type
    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x["id"])}
    unique_characters = list({character['id']: character for character in characters}.values())
    total_pages = max(1, math.ceil(len(unique_characters) / 10))
    page = max(0, min(page, total_pages - 1))

    # ✅ Improved UI
    harem_message = (
        f"📜 <b>{escape(update.effective_user.first_name)}'s Collection</b>\n"
        f"📄 <b>Page {page+1}/{total_pages}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )

    current_characters = unique_characters[page * 10 : (page + 1) * 10]
    grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x.get(sort_by, "Unknown"))}

    for category, characters in grouped_characters.items():
        icon = CATEGORY_ICONS.get(category, "📦")  # Default if category icon is missing
        category_count = await collection.count_documents({"category": category})
        harem_message += f"\n{icon} <b>{category}</b> ({len(characters)}/{category_count})\n"

        for character in characters:
            count = character_counts[character["id"]]
            rarity_icon = RARITY_ICONS.get(character["rarity"], "🔹")
            harem_message += f"{rarity_icon} <b>{character['name']}</b> ×{count}\n"

    total_count = len(user['characters'])
    keyboard = [
        [InlineKeyboardButton(f"📜 See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")],
        [InlineKeyboardButton("📌 Sort by Rarity", callback_data="sort:rarity"),
         InlineKeyboardButton("📂 Sort by Category", callback_data="sort:category")]
    ]

    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Display Favorite Character if Available
    fav_character = next((c for c in user["characters"] if c["id"] == user.get("favorites", [None])[0]), None)
    
    if query:
        message = query.message
    else:
        message = update.message

    if fav_character and "file_id" in fav_character:
        await message.reply_photo(photo=fav_character["file_id"], caption=harem_message, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await message.reply_text(harem_message, parse_mode="HTML", reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext) -> None:
    """Handles pagination for the /harem command."""
    query = update.callback_query
    _, page, user_id = query.data.split(':')
    page = int(page)
    user_id = int(user_id)

    if query.from_user.id != user_id:
        await query.answer("❌ This is not your collection!", show_alert=True)
        return

    await harem(update, context, page, query)
    await query.answer()

async def sort_collection(update: Update, context: CallbackContext) -> None:
    """Allows users to choose sorting method."""
    keyboard = [
        [InlineKeyboardButton("📌 Sort by Rarity", callback_data="sort:rarity")],
        [InlineKeyboardButton("📂 Sort by Category", callback_data="sort:category")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔀 Choose how you want to sort your collection:", reply_markup=reply_markup)

async def sort_callback(update: Update, context: CallbackContext) -> None:
    """Handles sorting preference and saves it in the database."""
    query = update.callback_query
    _, sort_by = query.data.split(":")
    user_id = query.from_user.id

    await db.user_sorting.update_one({"user_id": user_id}, {"$set": {"sort_by": sort_by}}, upsert=True)

    await query.answer(f"✅ Collection will now be sorted by {sort_by.capitalize()}")
    await query.edit_message_text(f"✅ Collection is now sorted by **{sort_by.capitalize()}**. Use /collection to view.")

# ✅ Register Handlers
application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern="^harem", block=False))
application.add_handler(CommandHandler("sort", sort_collection, block=False))
application.add_handler(CallbackQueryHandler(sort_callback, pattern="^sort:", block=False))
