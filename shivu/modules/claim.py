from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection
import random
import time

# 📌 Claim Limits
MAX_CLAIMS = 2  # 2 claims per day
COOLDOWN_TIME = 6 * 60 * 60  # 6 hours in seconds
GIF_FILE_ID = "BQACAgUAAyEFAASS4tX2AAID1mepm3uPxHquFb9fbSrmnbKjhGqYAAK3FAAC1ftIVUrVTH-TVNlXNgQ"

async def claim(update: Update, context: CallbackContext) -> None:
    """Allows users to claim a random character from the database."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    # ✅ Initialize claim data if missing
    user.setdefault("claims", 0)
    user.setdefault("last_claim", 0)

    current_time = time.time()
    if user["claims"] >= MAX_CLAIMS:
        await update.message.reply_text("❌ You have reached your daily claim limit (2/2). Try again tomorrow!")
        return

    if current_time - user["last_claim"] < COOLDOWN_TIME:
        remaining_time = int((COOLDOWN_TIME - (current_time - user["last_claim"])) / 60)
        await update.message.reply_text(f"⏳ You must wait {remaining_time} minutes before claiming again!")
        return

    # ✅ Fetch a random character from the database
    total_characters = await collection.count_documents({})
    if total_characters == 0:
        await update.message.reply_text("❌ No characters available to claim!")
        return

    random_character = await collection.find_one({}, skip=random.randint(0, total_characters - 1))

    # ✅ Send GIF animation
    gif_message = await update.message.reply_animation(animation=GIF_FILE_ID, caption="✨ Claiming a character...")

    # ✅ Add character to user's collection
    await user_collection.update_one({"id": user_id}, {
        "$push": {"characters": random_character},
        "$set": {"last_claim": current_time},
        "$inc": {"claims": 1}
    })

    # ✅ Prepare Character Message
    char_name = random_character["name"]
    char_rarity = random_character.get("rarity", "Unknown")
    char_file_id = random_character.get("file_id")
    char_img_url = random_character.get("img_url")

    character_message = (
        f"🎉 <b>You have claimed:</b>\n"
        f"🎴 <b>{char_name}</b>\n"
        f"🎖 <b>Rarity:</b> {char_rarity}\n"
        "🔹 Use `/harem` to view your collection!"
    )

    # ✅ Delete GIF before sending character image
    await gif_message.delete()

    # ✅ Send Character Image After Animation
    if char_file_id:
        await update.message.reply_photo(photo=char_file_id, caption=character_message, parse_mode="HTML")
    elif char_img_url:
        await update.message.reply_photo(photo=char_img_url, caption=character_message, parse_mode="HTML")
    else:
        await update.message.reply_text(character_message, parse_mode="HTML")

# ✅ Register Handler
application.add_handler(CommandHandler("claim", claim, block=False))
