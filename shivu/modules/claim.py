from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection, collection
import random
import time

# ✅ Claim Settings
CLAIM_LIMIT = 2  # Max claims per day
CLAIM_COOLDOWN = 6 * 60 * 60  # 6 hours in seconds
CLAIM_GIF = "BQACAgUAAyEFAASS4tX2AAID1mepm3uPxHquFb9fbSrmnbKjhGqYAAK3FAAC1ftIVUrVTH-TVNlXNgQ"  # Claim animation

async def claim(update: Update, context: CallbackContext) -> None:
    """Allows users to claim a random character with cooldown & daily limit."""
    user_id = update.effective_user.id
    current_time = int(time.time())

    user = await user_collection.find_one({'id': user_id}) or {}

    # ✅ Initialize missing fields
    user.setdefault("last_claim", 0)
    user.setdefault("claim_count", 0)
    user.setdefault("claim_date", current_time)

    # ✅ Reset claim count daily
    last_claim_date = time.gmtime(user["claim_date"]).tm_yday
    current_day = time.gmtime(current_time).tm_yday
    if last_claim_date != current_day:
        user["claim_count"] = 0
        user["claim_date"] = current_time

    # ✅ Check if user reached daily limit
    if user["claim_count"] >= CLAIM_LIMIT:
        await update.message.reply_text("❌ You have reached your daily claim limit! Try again tomorrow.")
        return

    # ✅ Check cooldown
    time_since_last_claim = current_time - user["last_claim"]
    if time_since_last_claim < CLAIM_COOLDOWN:
        remaining_time = CLAIM_COOLDOWN - time_since_last_claim
        hours = remaining_time // 3600
        minutes = (remaining_time % 3600) // 60
        await update.message.reply_text(f"⏳ You must wait {hours}h {minutes}m before claiming again!")
        return

    # ✅ Get a random character from database
    total_characters = await collection.count_documents({})
    if total_characters == 0:
        await update.message.reply_text("❌ No characters available to claim.")
        return

    random_character = await collection.find_one({}, skip=random.randint(0, total_characters - 1))
    if not random_character:
        await update.message.reply_text("❌ Failed to claim a character. Try again!")
        return

    # ✅ Play Claim Animation (GIF)
    gif_message = await update.message.reply_animation(animation=CLAIM_GIF, caption="✨ Claiming Character...")

    # ✅ Wait 2 seconds before revealing character
    await gif_message.edit_caption("🔍 Searching for a character...")
    await context.bot.sleep(2)

    # ✅ Update User Data (Add character & update claim info)
    await user_collection.update_one(
        {"id": user_id},
        {"$push": {"characters": random_character}, "$set": {"last_claim": current_time, "claim_count": user["claim_count"] + 1, "claim_date": current_time}},
        upsert=True
    )

    # ✅ Show Claimed Character
    await gif_message.edit_caption(
        f"🎉 **You Claimed:** {random_character['name']}!\n"
        f"🔖 **Rarity:** {random_character.get('rarity', 'Unknown')}\n"
        f"🎴 **Category:** {random_character.get('category', 'General')}\n\n"
        f"🔹 Use `/collection` to view your collection!",
        parse_mode="Markdown"
    )

# ✅ Register Handler
application.add_handler(CommandHandler("claim", claim, block=False))
