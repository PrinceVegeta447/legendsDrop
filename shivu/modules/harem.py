from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from itertools import groupby
import math
from html import escape
import random
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import collection, banners_collection, user_collection, application, db

async def harem(update: Update, context: CallbackContext, page=0) -> None:
    """Shows the user's collected characters (including banner characters) with sorting and pagination."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or 'characters' not in user or not user['characters']:  
        text = '😔 You have not collected any characters yet!'  
        if update.message:
            await update.message.reply_text(text)
        else:
            await update.callback_query.message.edit_text(text)
        return  

    # Retrieve sorting preference (Default: Category)  
    user_pref = await db.user_sorting.find_one({'user_id': user_id}) or {"sort_by": "category"}  
    sort_by = user_pref["sort_by"]  

    # Fetch banner-exclusive characters collected by the user  
    banner_characters = []
    for banner in await banners_collection.find({}).to_list(length=None):  
        if 'characters' in banner:  
            for char in banner['characters']:  
                if char['id'] in [c['id'] for c in user['characters']]:  # If user owns this banner character  
                
                    banner_characters.append(char)  

    # Merge all collected characters  
    all_characters = user['characters'] + banner_characters  

    # Sorting  
    if sort_by == "rarity":  
        all_characters = sorted(all_characters, key=lambda x: x.get('rarity', "Common"), reverse=True)  
    else:  
        all_characters = sorted(all_characters, key=lambda x: x.get('category', "Uncategorized"))  

    # Group by ID to count duplicates  
    character_counts = {k: len(list(v)) for k, v in groupby(all_characters, key=lambda x: x['id'])}  
    unique_characters = list({char['id']: char for char in all_characters}.values())  

    # Pagination  
    total_pages = math.ceil(len(unique_characters) / 15)  
    page = max(0, min(page, total_pages - 1))  

    # Message header  
    harem_message = (
        f"🎴 **{escape(update.effective_user.first_name)}'s Collection**\n"
        f"📖 **Page {page + 1}/{total_pages}** (Sorted by `{sort_by.capitalize()}`)\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )

    # Current page characters  
    current_characters = unique_characters[page * 15:(page + 1) * 15]  
    grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x.get(sort_by, "Uncategorized"))}  

    # Display character info  
    for key, characters in grouped_characters.items():  
        total_in_category = await collection.count_documents({sort_by: key})  
        harem_message += f'\n<b>{key} {len(characters)}/{total_in_category}</b>\n'  
        for character in characters:  
            count = character_counts[character['id']]  
            harem_message += f'{character["id"]} {character["name"]} ×{count}\n'  

    # Buttons  
    keyboard = [[InlineKeyboardButton(f"📜 See Collection ({len(all_characters)})", switch_inline_query_current_chat=f"collection.{user_id}")]]  
    if total_pages > 1:  
        nav_buttons = []  
        if page > 0:  
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}"))  
        if page < total_pages - 1:  
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}"))  
        keyboard.append(nav_buttons)  

    reply_markup = InlineKeyboardMarkup(keyboard)  

    # Display favorite character (or random if none)  
    fav_character = None  
    if 'favorites' in user and user['favorites']:  
        fav_character_id = user['favorites'][0]  
        fav_character = next((c for c in all_characters if c['id'] == fav_character_id), None)  

    # ✅ Fix: Use `callback_query.message` if inside a callback
    message = update.message if update.message else update.callback_query.message

    # Send image if available  
    if fav_character and 'file_id' in fav_character:  
        await message.reply_photo(photo=fav_character['file_id'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
        return  

    # If no favorite, send a random character  
    if all_characters:  
        random_character = random.choice(all_characters)
        if 'file_id' in random_character:  
            await message.reply_photo(photo=random_character['file_id'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
            return  

    # Send text message if no image available  
    await message.edit_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)

async def harem_callback(update: Update, context: CallbackContext) -> None:
    """Handles pagination when navigating through harem pages."""
    query = update.callback_query
    _, page, user_id = query.data.split(':')
    page = int(page)
    user_id = int(user_id)

    if query.from_user.id != user_id:  
        await query.answer("❌ This is not your Collection!", show_alert=True)  
        return  

    # Edit the existing message instead of sending a new one
    message = query.message
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

    await db.user_sorting.update_one(  
        {"user_id": user_id},   
        {"$set": {"sort_by": sort_by}},   
        upsert=True  
    )  

    await query.answer(f"✅ Collection will now be sorted by {sort_by.capitalize()}")  
    await query.edit_message_text(f"✅ Collection is now sorted by **{sort_by.capitalize()}**. Use /collection to view.")

# ✅ Add Handlers
application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern='^harem', block=False))
application.add_handler(CommandHandler("sort", sort_collection, block=False))
application.add_handler(CallbackQueryHandler(sort_callback, pattern="^sort:", block=False))
