from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from itertools import groupby
import math
import random
from html import escape
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import collection, user_collection, application, db

# ✅ Default Sorting Option
DEFAULT_SORT = "category"

async def harem(update: Update, context: CallbackContext, page=0) -> None:
    """Displays the user's character collection with sorting and pagination."""
    user_id = update.effective_user.id

    user = await user_collection.find_one({'id': user_id})
    if not user or "characters" not in user or not user["characters"]:
        text = '😔 You have not collected any characters yet!'
        if update.message:
            await update.message.reply_text(text)
        else:
            await update.callback_query.edit_message_text(text)
        return

    # ✅ Retrieve Sorting Preference (Default: Category)
    user_pref = await db.user_sorting.find_one({'user_id': user_id}) or {"sort_by": DEFAULT_SORT}
    sort_by = user_pref["sort_by"]

    # ✅ Sorting
    if sort_by == "rarity":
        characters = sorted(user["characters"], key=lambda x: x.get("rarity", "Common"), reverse=True)
    else:
        characters = sorted(user["characters"], key=lambda x: x.get("category", "Unknown"))

    # ✅ Group by ID to count duplicates
    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x["id"])}
    unique_characters = list({char["id"]: char for char in characters}.values())

    # ✅ Pagination
    total_pages = max(1, math.ceil(len(unique_characters) / 15))  # Ensure at least 1 page
    page = max(0, min(page, total_pages - 1))

    # ✅ Harem Header
    harem_message = (
        f"🎴 <b>{escape(update.effective_user.first_name)}'s Collection</b>\n"
        f"📖 **Page {page+1}/{total_pages}** (Sorted by `{sort_by.capitalize()}`)\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )

    # ✅ Current Page Characters
    current_characters = unique_characters[page * 15 : (page + 1) * 15]
    grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x.get(sort_by, "Unknown"))}

    # ✅ Display Character Info
    for key, characters in grouped_characters.items():
        total_in_category = await collection.count_documents({sort_by: key})
        harem_message += f"\n<b>{key} {len(characters)}/{total_in_category}</b>\n"
        for character in characters:
            count = character_counts[character["id"]]
            harem_message += f'{character["id"]} {character["name"]} ×{count}\n'

    # ✅ Buttons (Sorting + Pagination)
    keyboard = [
        [InlineKeyboardButton(f"📜 See Collection ({len(user['characters'])})", switch_inline_query_current_chat=f"collection.{user_id}")],
        [InlineKeyboardButton("📌 Sort by Rarity", callback_data="sort:rarity"), InlineKeyboardButton("📂 Sort by Category", callback_data="sort:category")],
    ]

    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Display Favorite Character (or Random if None)
    fav_character = None
    if "favorites" in user and user["favorites"]:
        fav_character_id = user["favorites"][0]
        fav_character = next((c for c in user["characters"] if c["id"] == fav_character_id), None)

    message = update.message if update.message else update.callback_query.message

    if fav_character and "file_id" in fav_character:
        await message.reply_photo(photo=fav_character["file_id"], parse_mode="HTML", caption=harem_message, reply_markup=reply_markup)
    else:
        random_character = random.choice(user["characters"]) if user["characters"] else None
        if random_character and "file_id" in random_character:
            await message.reply_photo(photo=random_character["file_id"], parse_mode="HTML", caption=harem_message, reply_markup=reply_markup)
        else:
            await message.edit_text(harem_message, parse_mode="HTML", reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext) -> None:
    """Handles pagination when navigating through harem pages."""
    query = update.callback_query
    _, page, user_id = query.data.split(":")
    page = int(page)
    user_id = int(user_id)

    if query.from_user.id != user_id:
        await query.answer("❌ This is not your Collection!", show_alert=True)
        return

    await harem(update, context, page)

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

# ✅ Add Handlers
application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern="^harem", block=False))
application.add_handler(CommandHandler("sort", sort_collection, block=False))
application.add_handler(CallbackQueryHandler(sort_callback, pattern="^sort:", block=False))
