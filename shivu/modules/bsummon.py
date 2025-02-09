import random
import asyncio
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from shivu import application, banners_collection, user_collection

SUMMON_COST_CC = 60  # Chrono Crystals per summon
SUMMON_COST_TICKET = 1  # Tickets per summon
MAX_SUMMONS = 10  # Max summons per pull

RARITY_ORDER = [
    "⚪ Common", "🟢 Uncommon", "🔵 Rare", "🟣 Extreme",
    "🟡 Sparking", "🔱 Ultra", "💠 Legends Limited",
    "🔮 Zenkai", "🏆 Event-Exclusive"
]  # Defines rarity order for sorting

ANIMATION_FRAMES = [
    "🌑 Loading Summon…",
    "🌒 Energy Gathering…",
    "🌓 Summon Circle Forming…",
    "🌔 Portal Opening…",
    "🌕 Summoning Character!"
]  # Fake summon animation frames

async def summon(update: Update, context: CallbackContext) -> None:
    """Handles user summon request from a banner with animations."""
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("❌ Usage: `/bsummon <banner_id> <1/10> <cc/ticket>`")
        return

    banner_id, summon_count, currency = args[0], int(args[1]), args[2].lower()
    if summon_count not in [1, 10] or currency not in ["cc", "ticket"]:
        await update.message.reply_text("❌ Invalid arguments! Use `/bsummon <banner_id> <1/10> <cc/ticket>`")
        return

    try:
        banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return
    except:
        await update.message.reply_text("❌ Invalid Banner ID!")
        return

    banner_characters = banner.get("characters", [])
    if not banner_characters:
        await update.message.reply_text("❌ No characters available in this banner!")
        return

    # ✅ Fetch user data
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text("❌ You don't have enough resources to summon!")
        return

    total_cost = (SUMMON_COST_CC if currency == "cc" else SUMMON_COST_TICKET) * summon_count
    balance_key = "chrono_crystals" if currency == "cc" else "summon_tickets"

    if user.get(balance_key, 0) < total_cost:
        await update.message.reply_text(f"❌ Not enough {balance_key.replace('_', ' ').title()}! You need {total_cost}.")
        return

    # ✅ Deduct CC/Tickets
    await user_collection.update_one({'id': user_id}, {'$inc': {balance_key: -total_cost}})

    # ✅ Start Summon Animation
    animation_message = await update.message.reply_text("🌑 Starting Summon…")
    for frame in ANIMATION_FRAMES:
        await asyncio.sleep(1.5)  # Delay between animation frames
        await animation_message.edit_text(frame)

    # ✅ Select random characters
    summoned_characters = random.sample(banner_characters, min(summon_count, len(banner_characters)))

    # ✅ Add to user's collection
    await user_collection.update_one({'id': user_id}, {'$push': {'characters': {'$each': summoned_characters}}})

    # ✅ Identify rarest character
    rarest_character = max(summoned_characters, key=lambda char: RARITY_ORDER.index(char['rarity']))

    # ✅ Create summon result message
    summon_results = f"🎟 **Summon Results ({banner['name']})** 🎟\n"
    for char in summoned_characters:
        summon_results += f"🔹 **{char['name']}** - {char['rarity']} - {char['category']}\n"

    keyboard = [[InlineKeyboardButton("📜 View Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Send rarest character’s image & results
    await animation_message.delete()
    await update.message.reply_photo(
        photo=rarest_character['image_file_id'],
        caption=summon_results,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ✅ Add Handlers
application.add_handler(CommandHandler("bsummon", summon, block=False))
