import asyncio
import time
import random
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection

# 📌 Claim Limits
MAX_CLAIMS = 1  # Users can claim once per day
COOLDOWN_TIME = 24 * 60 * 60  # 24 hours cooldown
GIF_FILE_ID = "BQACAgUAAyEFAASS4tX2AAID1mepm3uPxHquFb9fbSrmnbKjhGqYAAK3FAAC1ftIVUrVTH-TVNlXNgQ"

async def claim(update: Update, context: CallbackContext) -> None:
    """Allows users to claim a random character from the database."""
    user_id = update.effective_user.id

    # ✅ Fetch or Register User in Database
    user = await user_collection.find_one({"id": user_id})
    if not user:
        user = {
            "id": user_id,
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
            "characters": [],
            "claims": 0,
            "last_claim": 0,
            "coins": 0,
            "chrono_crystals": 0
        }
        await user_collection.insert_one(user)

    # ✅ Fetch Claim Data
    claims = user.get("claims", 0)
    last_claim = user.get("last_claim", 0)
    current_time = time.time()

    # ✅ **Check Claim Limits**
    if claims >= MAX_CLAIMS:
        await update.message.reply_text("❌ You have already claimed today. Try again tomorrow!")
        return

    cooldown_remaining = COOLDOWN_TIME - (current_time - last_claim)
    if cooldown_remaining > 0:
        hours = int(cooldown_remaining // 3600)
        minutes = int((cooldown_remaining % 3600) // 60)
        await update.message.reply_text(f"⏳ You must wait {hours}h {minutes}m before claiming again!")
        return

    # ✅ Fetch a random character from the database
    total_characters = await collection.count_documents({})
    if total_characters == 0:
        await update.message.reply_text("❌ No characters available to claim!")
        return

    random_character = await collection.find_one({}, skip=random.randint(0, total_characters - 1))

    # ✅ Send GIF animation
    gif_message = await update.message.reply_animation(animation=GIF_FILE_ID, caption="✨ Claiming a character...")

    # ✅ **Wait for 7 seconds before proceeding**
    await asyncio.sleep(7)

    # ✅ **Ensure claimed character is saved correctly**
    await user_collection.update_one(
        {"id": user_id},
        {
            "$push": {"characters": random_character},
            "$set": {"last_claim": current_time},
            "$inc": {"claims": 1}
        }
    )

    # ✅ Prepare Character Message
    char_name = random_character["name"]
    char_rarity = random_character.get("rarity", "Unknown")
    char_file_id = random_character.get("file_id")
    char_img_url = random_character.get("img_url")

    character_message = (
        f"🎉 <b>You have claimed:</b>\n"
        f"🎴 <b>{char_name}</b>\n"
        f"🎖 <b>Rarity:</b> {char_rarity}\n"
        "🔹 Use `/collection` to view your collection!"
    )

    # ✅ Delete GIF after the delay
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
