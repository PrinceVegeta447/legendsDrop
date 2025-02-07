from telegram import Update
from itertools import groupby
import math
from html import escape
import random

from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from shivu import collection, user_collection, application


async def harem(update: Update, context: CallbackContext, page=0) -> None:
    """Shows the user's collected characters (Harem) with pagination, grouped by category."""

    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or 'characters' not in user or not user['characters']:
        if update.message:
            await update.message.reply_text('😔 You have not collected any characters yet!')
        else:
            await update.callback_query.edit_message_text('😔 You have not collected any characters yet!')
        return

    # Sort characters by category and ID
    characters = sorted(user['characters'], key=lambda x: (x.get('category', "Uncategorized"), x['id']))

    # Group characters by ID to count duplicates
    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x['id'])}

    # Remove duplicates, keeping one instance per character
    unique_characters = list({char['id']: char for char in characters}.values())

    # Pagination logic
    total_pages = math.ceil(len(unique_characters) / 15)  
    page = max(0, min(page, total_pages - 1))  # Ensuring valid page number

    # Prepare message header
    harem_message = f"<b>{escape(update.effective_user.first_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"

    # Get characters for the current page
    current_characters = unique_characters[page*15:(page+1)*15]

    # Group characters by category
    grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x.get('category', "Uncategorized"))}

    # Add character details to message
    for category, characters in grouped_characters.items():
        total_in_category = await collection.count_documents({"category": category})
        harem_message += f'\n<b>{category} {len(characters)}/{total_in_category}</b>\n'
        for character in characters:
            count = character_counts[character['id']]
            harem_message += f'{character["id"]} {character["name"]} ×{count}\n'

    # Total collection count
    total_count = len(user['characters'])

    # Buttons
    keyboard = [[InlineKeyboardButton(f"📜 See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")]]
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Fetch user's favorite character
    fav_character = None
    if 'favorites' in user and user['favorites']:
        fav_character_id = user['favorites'][0]
        fav_character = next((c for c in user['characters'] if c['id'] == fav_character_id), None)

    # If favorite exists, send that
    if fav_character and 'img_url' in fav_character:
        if update.message:
            await update.message.reply_photo(photo=fav_character['img_url'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
        else:
            if update.callback_query.message.caption != harem_message:
                await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
        return

    # If no favorite, send a random character
    if user['characters']:
        random_character = random.choice(user['characters'])
        if 'img_url' in random_character:
            if update.message:
                await update.message.reply_photo(photo=random_character['img_url'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
            else:
                if update.callback_query.message.caption != harem_message:
                    await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
            return

    # If no image available, send text message
    if update.message:
        await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
    else:
        if update.callback_query.message.text != harem_message:
            await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)


async def harem_callback(update: Update, context: CallbackContext) -> None:
    """Handles pagination when navigating through harem pages."""
    query = update.callback_query
    _, page, user_id = query.data.split(':')
    page = int(page)
    user_id = int(user_id)

    # Restrict viewing to the owner of the harem
    if query.from_user.id != user_id:
        await query.answer("❌ This is not your Harem!", show_alert=True)
        return

    await harem(update, context, page)


# Add handlers to the bot
application.add_handler(CommandHandler(["harem", "collection"], harem, block=False))
application.add_handler(CallbackQueryHandler(harem_callback, pattern='^harem', block=False))
