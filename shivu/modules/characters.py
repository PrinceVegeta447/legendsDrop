from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, collection

# ✅ Number of characters per page
CHARACTERS_PER_PAGE = 10

async def list_characters(update: Update, context: CallbackContext, page=1) -> None:
    """Command to list characters from the database (Paginated)"""
    
    total_characters = await collection.count_documents({})
    total_pages = (total_characters // CHARACTERS_PER_PAGE) + (1 if total_characters % CHARACTERS_PER_PAGE else 0)

    if total_characters == 0:
        await update.message.reply_text("⚠️ No characters have been uploaded yet.")
        return

    if page < 1 or page > total_pages:
        await update.message.reply_text(f"⚠️ Invalid page number! Choose between `1-{total_pages}`.")
        return

    # ✅ Fetch characters for the current page
    characters = collection.find().skip((page - 1) * CHARACTERS_PER_PAGE).limit(CHARACTERS_PER_PAGE)
    characters = await characters.to_list(length=CHARACTERS_PER_PAGE)

    # ✅ Format message
    message = f"📜 **Character List (Page {page}/{total_pages})**\n\n"
    for char in characters:
        message += f"🆔 `{char['id']}` | **{char['name']}**\n🎖️ {char['rarity']} | 🔹 **{char['category']}**\n\n"

    # ✅ Pagination buttons
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"characters:{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"characters:{page+1}"))

    reply_markup = InlineKeyboardMarkup([buttons] if buttons else [])

    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def paginate_characters(update: Update, context: CallbackContext) -> None:
    """Handles inline button pagination"""
    query = update.callback_query
    _, page = query.data.split(":")
    page = int(page)

    await list_characters(update, context, page)
    await query.answer()

# ✅ Add command handlers
application.add_handler(CommandHandler("characters", list_characters, block=False))
application.add_handler(CallbackQueryHandler(paginate_characters, pattern="^characters:", block=False))
