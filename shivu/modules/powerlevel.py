from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from shivu import user_collection, application

# 🔹 Default Power Levels Based on Rarity
RARITY_POWER = {
    "⛔ Common": 100,
    "🍀 Rare": 300,
    "🟣 Extreme": 800,
    "🟡 Sparking": 1500,
    "🔱 Ultimate": 2500,
    "👑 Supreme": 4000,
    "🔮 Limited Edition": 6000,
    "⛩️ Celestial": 10000
}

# 🔹 Power Titles Based on Power Level
POWER_TITLES = [
    (5000, "🥋 Rookie Fighter"),
    (15000, "⚔️ Elite Warrior"),
    (30000, "🔥 Super Fighter"),
    (50000, "⚡ Ultimate Fighter"),
    (75000, "🌟 Legendary Saiyan"),
    (100000, "🛡️ Mythic Champion"),
    (150000, "🏆 Supreme God"),
    (float("inf"), "👑 Omni-King")
]

async def powerlevel(update: Update, context: CallbackContext) -> None:
    """Shows user's power level, title, and character breakdown."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})

    if not user or not user.get("characters"):
        await update.message.reply_text("❌ You don’t own any characters yet!", parse_mode="HTML")
        return

    # 🔹 Calculate Power Level Based on Rarity
    power_level = sum(RARITY_POWER.get(char["rarity"], 100) for char in user["characters"])

    # 🔹 Assign Power Level Title Dynamically
    title = next(t[1] for t in POWER_TITLES if power_level < t[0])
    
    # 🔹 Character Breakdown by Rarity
    rarity_count = {r: 0 for r in RARITY_POWER.keys()}
    for char in user["characters"]:
        if char["rarity"] in rarity_count:
            rarity_count[char["rarity"]] += 1
    
    rarity_display = "\n".join(f"{r} → {count} characters" for r, count in rarity_count.items() if count > 0)

    # 🔹 Power Progress Bar
    max_pl = 150000  # Adjust based on game balance
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
