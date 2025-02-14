from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, collection

# ✅ Rarity Dictionary with Symbols
RARITIES = {
    "1": ("⛔", "Common"),
    "2": ("🍀", "Rare"),
    "3": ("🟣", "Extreme"),
    "4": ("🟡", "Sparking"),
    "5": ("🔮", "Limited Edition"),
    "6": ("🔱", "Ultimate"),
    "7": ("👑", "Supreme"),
    "8": ("⛩️", "Celestial"),
}

async def srarity(update: Update, context: CallbackContext) -> None:
    """Shows all rarities as inline buttons."""
    keyboard = [[InlineKeyboardButton(f"{symbol} {name}", callback_data=f"rarity:{key}:1")]
                for key, (symbol, name) in RARITIES.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🌟 **Select a Rarity:**", reply_markup=reply_markup, parse_mode="Markdown")

async def show_rarity(update: Update, context: CallbackContext) -> None:
    """Displays characters of a specific rarity with pagination."""
    query = update.callback_query
    _, rarity_key, page = query.data.split(":")
    page = int(page)

    # ✅ Get Rarity Symbol & Name
    if rarity_key not in RARITIES:
        await query.answer("❌ Invalid rarity selected!", show_alert=True)
        return
    rarity_symbol, rarity_name = RARITIES[rarity_key]

    # ✅ Fetch Characters of Selected Rarity
    characters = await collection.find({"rarity": f"{rarity_symbol} {rarity_name}"}).to_list(length=1000)
    total_chars = len(characters)
    per_page = 15
    start = (page - 1) * per_page
    end = min(start + per_page, total_chars)
    selected_chars = characters[start:end]

    if not selected_chars:
        await query.answer("❌ No characters found in this rarity!", show_alert=True)
        return

    # ✅ Format Message
    message = f"**{rarity_symbol} {rarity_name} Characters:**\n\n"
    for char in selected_chars:
        message += f"[{char['id']}] {rarity_symbol} {char['name']}\n"

    # ✅ Pagination Buttons
    keyboard = []
    if start > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"rarity:{rarity_key}:{page-1}"))
    if end < total_chars:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"rarity:{rarity_key}:{page+1}"))

    reply_markup = InlineKeyboardMarkup([keyboard] if keyboard else [])

    await query.message.edit_text(message, parse_mode="Markdown", reply_markup=reply_markup)

# ✅ Register Handlers
application.add_handler(CommandHandler("srarity", srarity, block=False))
application.add_handler(CallbackQueryHandler(show_rarity, pattern="^rarity:", block=False))
