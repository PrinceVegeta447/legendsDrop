import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, collection, user_collection

SUMMON_COST = 60  # Cost per summon in Chrono Crystals
MAX_SUMMONS = 10  # Maximum characters a user can summon at once

async def summon(update: Update, context: CallbackContext) -> None:
    """Allows users to summon characters using Chrono Crystals."""
    user_id = update.effective_user.id

    # ✅ Fetch user data
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text("❌ You don't have any Chrono Crystals! Start collecting characters first.")
        return

    # ✅ Check user input (number of summons)
    args = context.args
    num_summons = int(args[0]) if args and args[0].isdigit() else 1
    num_summons = min(max(1, num_summons), MAX_SUMMONS)  # Ensure valid range

    total_cost = num_summons * SUMMON_COST

    # ✅ Check if user has enough Chrono Crystals
    if user.get("chrono_crystals", 0) < total_cost:
        await update.message.reply_text(f"❌ Not enough Chrono Crystals! You need {total_cost} CC for {num_summons} summons.")
        return

    # ✅ Fetch characters from the database
    all_characters = list(await collection.find({}).to_list(length=None))
    if not all_characters:
        await update.message.reply_text("❌ No characters available for summoning!")
        return

    summoned_characters = random.sample(all_characters, min(num_summons, len(all_characters)))

    # ✅ Deduct Chrono Crystals
    await user_collection.update_one({'id': user_id}, {'$inc': {'chrono_crystals': -total_cost}})

    # ✅ Add summoned characters to user's collection
    await user_collection.update_one({'id': user_id}, {'$push': {'characters': {'$each': summoned_characters}}})

    # ✅ Display the summoned characters
    summon_results = "🎉 **Summon Results** 🎉\n"
    summon_images = []

    for character in summoned_characters:
        summon_results += f"🔹 **{character['name']}** - {character['rarity']} - {character['category']}\n"
        summon_images.append(character['img_url'])

    keyboard = [[InlineKeyboardButton("📜 View Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Send results (single or multiple images)
    if len(summon_images) == 1:
        await update.message.reply_photo(photo=summon_images[0], caption=summon_results, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        media_group = [telegram.InputMediaPhoto(photo, caption=summon_results if i == 0 else "") for i, photo in enumerate(summon_images)]
        await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
        await update.message.reply_text(summon_results, parse_mode="Markdown", reply_markup=reply_markup)

# ✅ Add the command handler
application.add_handler(CommandHandler("summon", summon, block=False))
