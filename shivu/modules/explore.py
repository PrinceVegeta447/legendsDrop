from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from datetime import datetime, timedelta
import random
from shivu import application, user_collection

# Explore settings
EXPLORE_COOLDOWN = 300  # 5 minutes in seconds
EXPLORE_LIMIT = 60  # Max explores per day
EXPLORE_LOCATIONS = [
    "🌳 Enchanted Forest",
    "🏙️ Bustling City",
    "🏝️ Hidden Island",
    "🏔️ Snowy Mountains",
    "🏜️ Desert Ruins",
    "🏰 Ancient Castle",
    "🚀 Space Colony",
    "⛩️ Mystic Temple",
    "🕵️ Secret Hideout",
    "🌋 Volcanic Crater"
]

async def explore(update: Update, context: CallbackContext) -> None:
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    now = datetime.utcnow()

    # Restrict to groups only
    if chat_type == "private":
        await update.message.reply_text("❌ You can only explore in groups!")
        return

    user_data = await user_collection.find_one({"user_id": user_id})
    
    if not user_data:
        user_data = {"user_id": user_id, "explore_count": 0, "last_explore": None}
        await user_collection.insert_one(user_data)

    explore_count = user_data.get("explore_count", 0)
    last_explore = user_data.get("last_explore")

    # Check daily limit
    if explore_count >= EXPLORE_LIMIT:
        await update.message.reply_text("❌ You have reached the daily explore limit (60). Try again tomorrow!")
        return

    # Check cooldown
    if last_explore:
        last_explore_time = datetime.strptime(last_explore, "%Y-%m-%d %H:%M:%S")
        time_diff = (now - last_explore_time).total_seconds()

        if time_diff < EXPLORE_COOLDOWN:
            remaining_time = int((EXPLORE_COOLDOWN - time_diff) / 60)
            await update.message.reply_text(f"⌛ You must wait {remaining_time} minutes before exploring again!")
            return

    # Select random location
    location = random.choice(EXPLORE_LOCATIONS)

    # Random rewards
    if random.random() < 0.7:  # 70% chance for Zeni, 50% for CC
        reward_type = "Zeni"
        reward_amount = random.randint(100, 12000)
        await user_collection.update_one({"user_id": user_id}, {"$inc": {"coins": reward_amount}})
    else:
        reward_type = "Chrono Crystals"
        reward_amount = random.randint(10, 100)
        await user_collection.update_one({"user_id": user_id}, {"$inc": {"chrono_crystals": reward_amount}})

    # Update explore count & timestamp
    await user_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_explore": now.strftime("%Y-%m-%d %H:%M:%S")},
         "$inc": {"explore_count": 1}}
    )

    # Create inline button for location
    keyboard = [[InlineKeyboardButton(text=location, callback_data="explore_location")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send explore result
    message = (
        f"🌍 **Exploration Successful!**\n"
        f"🎁 Reward: **{reward_amount} {reward_type}**\n"
        f"🚀 Keep exploring!"
    )

    await update.message.reply_text(message, reply_markup=reply_markup)

# Add command handler
application.add_handler(CommandHandler("explore", explore, block=False))
