import random
import asyncio
from bson import ObjectId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler
from shivu import application, banners_collection, user_collection

SUMMON_COST_CC = 60  # Chrono Crystals per summon
SUMMON_COST_TICKET = 1  # Summon Tickets per summon
MAX_SUMMONS = 10  # Max summons per pull

RARITY_ORDER = [
    "⚪ Common", "🟢 Uncommon", "🔵 Rare", "🟣 Extreme",
    "🟡 Sparking", "🔱 Ultra", "💠 Legends Limited",
    "🔮 Zenkai", "🏆 Event-Exclusive"
]

DROP_RATES = {
    "⚪ Common": 40, "🟢 Uncommon": 25, "🔵 Rare": 15, "🟣 Extreme": 10,
    "🟡 Sparking": 6, "🔱 Ultra": 2, "💠 Legends Limited": 1,
    "🔮 Zenkai": 0.5, "🏆 Event-Exclusive": 0.5
}

ANIMATION_FRAMES = [
    "🔮 **Summoning…** 🔮",
    "⚡ **Energy Gathering…** ⚡",
    "🌪 **Summon Portal Opening…** 🌪",
    "💥 **Characters Emerging…** 💥",
    "✨ **Summon Complete!** ✨"
]

async def summon(update: Update, context: CallbackContext) -> None:
    """Handles user summon request with enhanced UI and animations."""
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("❌ **Usage:** `/bsummon <banner_id> <1/10> <cc/ticket>`", parse_mode="Markdown")
        return

    try:
        banner_id, summon_count, currency = args[0], int(args[1]), args[2].lower()
    except ValueError:
        await update.message.reply_text("❌ **Invalid arguments!**\nUse: `/bsummon <banner_id> <1/10> <cc/ticket>`", parse_mode="Markdown")
        return

    if summon_count not in [1, 10] or currency not in ["cc", "ticket"]:
        await update.message.reply_text("❌ **Invalid summon count or currency!**\nUse: `/bsummon <banner_id> <1/10> <cc/ticket>`", parse_mode="Markdown")
        return

    # ✅ Fetch banner details
    banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})
    if not banner:
        await update.message.reply_text("❌ **No banner found with this ID!**", parse_mode="Markdown")
        return

    banner_characters = banner.get("characters", [])
    if not banner_characters:
        await update.message.reply_text("❌ **No characters available in this banner!**", parse_mode="Markdown")
        return

    # ✅ Fetch or create user profile
    user = await user_collection.find_one({'id': user_id})
    if not user:
        user = {"id": user_id, "chrono_crystals": 0, "summon_tickets": 0, "characters": []}
        await user_collection.insert_one(user)

    # ✅ Check user balance
    total_cost = (SUMMON_COST_CC if currency == "cc" else SUMMON_COST_TICKET) * summon_count
    balance_key = "chrono_crystals" if currency == "cc" else "summon_tickets"

    if user.get(balance_key, 0) < total_cost:
        await update.message.reply_text(f"❌ **Not enough {balance_key.replace('_', ' ').title()}!**\nYou need `{total_cost}`.", parse_mode="Markdown")
        return

    # ✅ Deduct CC/Tickets
    await user_collection.update_one({'id': user_id}, {'$inc': {balance_key: -total_cost}})

    # ✅ Start Summon Animation
    animation_message = await update.message.reply_text("🔮 **Summoning…**")
    for frame in ANIMATION_FRAMES:
        await asyncio.sleep(1.2)
        await animation_message.edit_text(frame, parse_mode="Markdown")

    # ✅ Weighted Character Selection
    def get_weighted_character():
        available_characters = sorted(banner_characters, key=lambda c: DROP_RATES.get(c.get("rarity", "⚪ Common"), 0), reverse=True)
        weights = [DROP_RATES.get(c.get("rarity", "⚪ Common"), 0) for c in available_characters]
        return random.choices(available_characters, weights=weights, k=1)[0]

    summoned_characters = [get_weighted_character() for _ in range(summon_count)]

    # ✅ Add to user's collection
    await user_collection.update_one({'id': user_id}, {'$push': {'characters': {'$each': summoned_characters}}})

    # ✅ Identify rarest character
    rarest_character = max(summoned_characters, key=lambda char: RARITY_ORDER.index(char.get('rarity', "⚪ Common")))
    rarest_image = rarest_character.get('file_id', "https://i.imgur.com/5h9N2JF.png")  # High-quality default image

    # ✅ Summon Result Message with Improved Formatting
    summon_results = (
        f"🎟 **Summon Results - {banner['name']}** 🎟\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    for char in summoned_characters:
        new_tag = "🔥 **NEW!**" if char not in user.get("characters", []) else ""
        summon_results += f"🔹 **{char.get('name', 'Unknown')}** {new_tag}\n" \
                          f"🎖 **Rarity:** {char.get('rarity', '⚪ Common')}\n" \
                          f"📌 **Category:** {char.get('category', 'N/A')}\n" \
                          f"━━━━━━━━━━━━━━━━━━━━━━\n"

    keyboard = [[InlineKeyboardButton("💠 View Full Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Send summon result with rarest character’s image
    await animation_message.delete()
    await update.message.reply_photo(
        photo=rarest_image,
        caption=f"✨ **Your Rarest Pull!** ✨\n\n{summon_results}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ✅ Add Command Handler
application.add_handler(CommandHandler("bsummon", summon, block=False))
