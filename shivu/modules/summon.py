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
]  # Defines rarity order for sorting

ANIMATION_FRAMES = [
    "🔮 **Summoning…** 🔮",
    "⚡ **Energy Gathering…** ⚡",
    "🌪 **Summon Portal Opening…** 🌪",
    "💥 **Characters Emerging…** 💥",
    "✨ **Summon Complete!** ✨"
]  # Summon animation frames

RARITY_COLORS = {
    "⚪ Common": "⚪",
    "🟢 Uncommon": "🟢",
    "🔵 Rare": "🔵",
    "🟣 Extreme": "🟣",
    "🟡 Sparking": "🟡✨",
    "🔱 Ultra": "🔱🔥",
    "💠 Legends Limited": "💠🌟",
    "🔮 Zenkai": "🔮⚡",
    "🏆 Event-Exclusive": "🏆🎖️"
}  # Assigning icons to each rarity

async def summon(update: Update, context: CallbackContext) -> None:
    """Handles user summon request from a banner with enhanced UI and animations."""
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("❌ **Usage:** `/bsummon <banner_id> <1/10> <cc/ticket>`", parse_mode="Markdown")
        return

    banner_id, summon_count, currency = args[0], int(args[1]), args[2].lower()
    if summon_count not in [1, 10] or currency not in ["cc", "ticket"]:
        await update.message.reply_text("❌ **Invalid arguments!**\nUse: `/bsummon <banner_id> <1/10> <cc/ticket>`", parse_mode="Markdown")
        return

    try:
        banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})
        if not banner:
            await update.message.reply_text("❌ **No banner found with this ID!**", parse_mode="Markdown")
            return
    except:
        await update.message.reply_text("❌ **Invalid Banner ID!**", parse_mode="Markdown")
        return

    banner_characters = banner.get("characters", [])
    if not banner_characters:
        await update.message.reply_text("❌ **No characters available in this banner!**", parse_mode="Markdown")
        return

    # ✅ Fetch user data
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await update.message.reply_text("❌ **You don't have enough resources to summon!**", parse_mode="Markdown")
        return

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
        await asyncio.sleep(1.2)  # Delay between animation frames
        await animation_message.edit_text(frame, parse_mode="Markdown")

    # ✅ Select random characters
    summoned_characters = random.sample(banner_characters, min(summon_count, len(banner_characters)))

    # ✅ Add to user's collection
    await user_collection.update_one({'id': user_id}, {'$push': {'characters': {'$each': summoned_characters}}})

    # ✅ Identify rarest character
    rarest_character = max(summoned_characters, key=lambda char: RARITY_ORDER.index(char.get('rarity', "⚪ Common")))

    # ✅ Ensure rarest character has a valid image
    rarest_image = rarest_character.get('image_url')
    if not rarest_image or not rarest_image.startswith("http"):
        rarest_image = "https://example.com/default_image.jpg"  # Default fallback image

    # ✅ Create summon result message with a structured format
    summon_results = f"🎟 **Summon Results - {banner['name']}** 🎟\n━━━━━━━━━━━━━━━━━━━━━━\n"

    for char in summoned_characters:
        rarity_icon = RARITY_COLORS.get(char["rarity"], "🔹")  # Assign rarity icon
        summon_results += (
            f"{rarity_icon} **{char['name']}**\n"
            f"🎖 **Rarity:** {char['rarity']}\n"
            f"🔹 **Category:** {char['category']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
        )

    keyboard = [[InlineKeyboardButton("📜 View Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Send rarest character’s image & results
    await animation_message.delete()
    await update.message.reply_photo(
        photo=rarest_image,
        caption=summon_results,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ✅ Add Handlers
application.add_handler(CommandHandler("bsummon", summon, block=False))
