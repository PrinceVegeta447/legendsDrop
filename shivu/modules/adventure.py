import time, random, logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from shivu import user_collection, adventure_collection

# Enable logging
logging.basicConfig(level=logging.INFO)

# Adventure Type Configuration
ADVENTURE_TYPES = {
    "training": {"duration": 150, "zeni_range": (5000, 10000), "cc_range": (40, 50), "cc_chance": 60},
    "quest": {"duration": 300, "zeni_range": (10000, 20000), "cc_range": (80, 120), "cc_chance": 70},
    "expedition": {"duration": 600, "zeni_range": (20000, 40000), "cc_range": (160, 200), "cc_chance": 80},
}

# Start an adventure
async def start_adventure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    existing = await adventure_collection.find_one({"user_id": user_id, "status": "ongoing"})
    if existing:
        await update.message.reply_text("❌ **You already have an adventure in progress!**")
        return

    user = await user_collection.find_one({"id": user_id})
    if not user or "characters" not in user or not user["characters"]:
        await update.message.reply_text("❌ **You need at least one character!**")
        return

    character = random.choice(user["characters"])
    adventure_type = random.choice(list(ADVENTURE_TYPES.keys()))
    adventure_data = ADVENTURE_TYPES[adventure_type]
    end_time = time.time() + adventure_data["duration"]

    await adventure_collection.insert_one({
        "user_id": user_id, "character_name": character["name"],
        "rarity": character.get("rarity", "Unknown"), "adventure_type": adventure_type,
        "end_time": end_time, "status": "ongoing"
    })

    keyboard = [[InlineKeyboardButton("🔍 Check Status", callback_data=f"adventure_status:{user_id}")]]
    await update.message.reply_text(
        f"🌍 **Adventure Started!**\n"
        f"🎴 **Character:** {character['name']} ({character.get('rarity', 'Unknown')})\n"
        f"🏆 **Adventure Type:** {adventure_type.capitalize()}\n"
        f"⏳ **Duration:** {time.strftime('%M:%S', time.gmtime(adventure_data['duration']))} minutes\n"
        f"📌 **Use `/adventure_status` to check progress!**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.job_queue.run_once(auto_complete_adventure, when=adventure_data["duration"], data={"user_id": user_id, "chat_id": update.effective_chat.id})

# Check adventure status
async def adventure_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id if query else update.effective_user.id
    adventure = await adventure_collection.find_one({"user_id": user_id, "status": "ongoing"})
    
    if not adventure:
        await (query.answer("❌ No active adventure!", show_alert=True) if query else update.message.reply_text("❌ **No active adventure!**"))
        return

    remaining_time = max(0, int(adventure["end_time"] - time.time()))
    message = (
        f"🔍 **Adventure Status:**\n"
        f"🎴 **Character:** {adventure['character_name']} ({adventure['rarity']})\n"
        f"⏳ **Time Left:** {time.strftime('%M:%S', time.gmtime(remaining_time))} minutes\n"
        f"🏆 **Adventure Type:** {adventure['adventure_type'].capitalize()}"
    )

    await (query.edit_message_text(message) if query else update.message.reply_text(message))

# Automatically complete adventure
async def auto_complete_adventure(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]

    adventure = await adventure_collection.find_one({"user_id": user_id, "status": "ongoing"})
    if not adventure:
        return

    adventure_data = ADVENTURE_TYPES[adventure["adventure_type"]]
    zeni_reward = random.randint(*adventure_data["zeni_range"])
    cc_reward = random.randint(*adventure_data["cc_range"]) if random.randint(1, 100) <= adventure_data["cc_chance"] else 0

    await user_collection.update_one({"id": user_id}, {"$inc": {"zeni": zeni_reward, "cc": cc_reward}})
    await adventure_collection.delete_one({"user_id": user_id})

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🏆 **Adventure Completed!**\n"
            f"🎴 **Character:** {adventure['character_name']} ({adventure['rarity']})\n"
            f"💰 **Zeni Earned:** {zeni_reward}\n"
            f"✨ **Chrono Crystals Earned:** {cc_reward if cc_reward else 'None'}"
        )
    )

# Register Handlers
    application.add_handler(CommandHandler("adventure", start_adventure, block=False))
    application.add_handler(CommandHandler("adventure_status", adventure_status, block=False))
    application.add_handler(CallbackQueryHandler(adventure_status, pattern="^adventure_status:", block=False))
