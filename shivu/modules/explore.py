from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from datetime import datetime, timedelta
import random
from shivu import application, user_collection

# Explore settings
EXPLORE_COOLDOWN = 300  # 5 minutes (300 seconds)
EXPLORE_LIMIT = 60  # Max explores per day
EXPLORE_LOCATIONS = [
    ("🌳 Enchanted Forest", "forest"),
    ("🏙️ Bustling City", "city"),
    ("🏝️ Hidden Island", "island"),
    ("🏔️ Snowy Mountains", "mountains"),
    ("🏜️ Desert Ruins", "desert"),
    ("🏰 Ancient Castle", "castle"),
    ("🚀 Space Colony", "space"),
    ("⛩️ Mystic Temple", "temple"),
    ("🕵️ Secret Hideout", "hideout"),
    ("🌋 Volcanic Crater", "volcano")
]

async def explore(update: Update, context: CallbackContext) -> None:
    chat_type = update.effective_chat.type
    if chat_type == "private":
        await update.message.reply_text("❌ You can only explore in groups!")
        return

    # Show location options
    keyboard = [
        [InlineKeyboardButton(text=loc[0], callback_data=f"explore_{loc[1]}")]
        for loc in EXPLORE_LOCATIONS
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌍 **Choose a location to explore:**",
        reply_markup=reply_markup
    )

async def handle_explore(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    location_key = query.data.split("_")[1]
    location_name = next(loc[0] for loc in EXPLORE_LOCATIONS if loc[1] == location_key)
    now = datetime.utcnow()

    # Fetch user data
    user_data = await user_collection.find_one({"user_id": user_id})
    if not user_data:
        user_data = {"user_id": user_id, "explore_count": 0, "last_explore": None}
        await user_collection.insert_one(user_data)

    explore_count = user_data.get("explore_count", 0)
    last_explore = user_data.get("last_explore")

    # Check daily limit
    if explore_count >= EXPLORE_LIMIT:
        await query.answer("❌ You have reached the daily explore limit (60). Try again tomorrow!", show_alert=True)
        return

    # Check cooldown
    if last_explore:
        last_explore_time = datetime.strptime(last_explore, "%Y-%m-%d %H:%M:%S")
        time_diff = (now - last_explore_time).total_seconds()
        if time_diff < EXPLORE_COOLDOWN:
            remaining_time = int((EXPLORE_COOLDOWN - time_diff) / 60)
            await query.answer(f"⌛ You must wait {remaining_time} minutes before exploring again!", show_alert=True)
            return

    # Rewards
    zeni_reward = random.randint(100, 300)
    cc_reward = random.randint(1, 5)

    # Update user data
    await user_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_explore": now.strftime("%Y-%m-%d %H:%M:%S")},
         "$inc": {"explore_count": 1, "coins": zeni_reward, "chrono_crystals": cc_reward}}
    )

    # Send explore result
    message = (
        f"🌍 **You explored:** {location_name}\n"
        f"💰 **Zeni Earned:** {zeni_reward}\n"
        f"💎 **Chrono Crystals Earned:** {cc_reward}\n"
        f"🚀 Keep exploring!"
    )

    await query.message.edit_text(message)

# Handlers
application.add_handler(CommandHandler("explore", explore, block=False))
application.add_handler(CallbackQueryHandler(handle_explore, pattern="^explore_", block=False))
