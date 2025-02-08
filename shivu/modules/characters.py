from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, collection

# ✅ Number of characters per page
CHARACTERS_PER_PAGE = 10

async def list_characters(update: Update, context: CallbackContext) -> None:
    """Command to list characters from the database (Paginated)"""
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1

    # ✅ Count total characters
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
        message += f"🆔 `{char['id']}` | **{char['name']}**\n🎖️ {char['rarity']} | 🔹 {char['category']}\n\n"

    # ✅ Pagination buttons
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️", callback_data=f"characters:{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("➡️", callback_data=f"characters:{page+1}"))

    reply_markup = InlineKeyboardMarkup([buttons] if buttons else [])

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def paginate_characters(update: Update, context: CallbackContext) -> None:
    """Handles pagination for character list"""
    query = update.callback_query
    _, page = query.data.split(":")
    page = int(page)

    await list_characters(update, context)

# ✅ Add command handlers
application.add_handler(CommandHandler("characters", list_characters, block=False))
application.add_handler(CallbackQueryHandler(paginate_characters, pattern="^characters:", block=False))
