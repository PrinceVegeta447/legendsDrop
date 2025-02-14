from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from shivu import user_collection, application
import math

# 🔹 Titles Based on Power Level
POWER_TITLES = [
    (5000, "🥋 Rookie Fighter"),
    (15000, "⚔️ Elite Warrior"),
    (30000, "🔥 Super Fighter"),
    (float("inf"), "🏆 Legendary Saiyan"),
]

# 🔹 Rarity Icons (Your Rarities)
RARITY_ICONS = {
    "⛔ Common": "⛔",
    "🍀 Rare": "🍀",
    "🟣 Extreme": "🟣",
    "🟡 Sparking": "🟡",
    "🔱 Ultimate": "🔱",
    "👑 Supreme": "👑",
    "🔮 Limited Edition": "🔮",
    "⛩️ Celestial": "⛩️"
}

async def powerlevel(update: Update, context: CallbackContext) -> None:
    """Shows user's power level, title, and character breakdown."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or not user.get("characters"):
        await update.message.reply_text("❌ You don’t own any characters yet!", parse_mode="HTML")
        return

    # 🔹 Calculate Power Level
    power_level = sum(c.get("power", 0) for c in user["characters"])
    
    # 🔹 Determine Power Level Title
    title = next(t[1] for t in POWER_TITLES if power_level < t[0])
    
    # 🔹 Character Breakdown by Rarity
    rarity_count = {r: 0 for r in RARITY_ICONS.keys()}
    for char in user["characters"]:
        if char["rarity"] in rarity_count:
            rarity_count[char["rarity"]] += 1
    
    rarity_display = "\n".join(f"{RARITY_ICONS[r]} {r} → {count} characters" for r, count in rarity_count.items() if count > 0)

    # 🔹 Power Progress Bar
    max_pl = 50000  # Adjust based on game balance
    progress = min(power_level / max_pl, 1.0)
    bar = "▓" * int(progress * 10) + "░" * (10 - int(progress * 10))

    # 🔹 Message Formatting
    message = (
        f"⚡ <b>{update.effective_user.first_name}'s Power Level</b>\n"
        f"💥 <b>Total PL:</b> {power_level:,}\n"
        f"🏷️ <b>Title:</b> {title}\n"
        f"📦 <b>Total Characters Owned:</b> {len(user['characters'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Power Progress:</b> [{bar}] ({int(progress * 100)}%)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{rarity_display}\n"
    )

    # 🔹 Inline Button to View Collection
    keyboard = [[InlineKeyboardButton("📜 View Collection", switch_inline_query_current_chat=f"collection.{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)

# ✅ Register Command
application.add_handler(CommandHandler("powerlevel", powerlevel, block=False))
