from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
import random
import datetime
from shivu import application, user_collection, collection

CLAIM_COOLDOWN = 6 * 60 * 60  # 6 Hours in Seconds
MAX_CLAIMS = 2
ANIMATION_FILE_ID = "BQACAgUAAyEFAASS4tX2AAID1mepm3uPxHquFb9fbSrmnbKjhGqYAAK3FAAC1ftIVUrVTH-TVNlXNgQ"  # 🔥 Your GIF File ID

async def claim(update: Update, context: CallbackContext) -> None:
    """Allows users to claim a random character with cooldown and animation."""
    user_id = update.effective_user.id
    user = await user_collection.find_one({"id": user_id}) or {}

    # ✅ Initialize user claims
    user.setdefault("claims", 0)
    user.setdefault("last_claim", None)

    now = datetime.datetime.utcnow()

    # ✅ Check if user has claims left
    if user["claims"] >= MAX_CLAIMS:
        await update.message.reply_text("❌ You've reached the daily claim limit! Try again tomorrow.")
        return

    # ✅ Check cooldown
    if user["last_claim"]:
        last_claim_time = datetime.datetime.fromtimestamp(user["last_claim"])
        if (now - last_claim_time).total_seconds() < CLAIM_COOLDOWN:
            remaining = CLAIM_COOLDOWN - (now - last_claim_time).total_seconds()
            hours, minutes = divmod(int(remaining / 60), 60)
            await update.message.reply_text(f"⏳ You can claim again in {hours}h {minutes}m.")
            return

    # ✅ Play animation before revealing character
    await update.message.reply_animation(animation=ANIMATION_FILE_ID, caption="✨ Claiming a character...")

    # ✅ Fetch a random character from the database
    total_characters = await collection.count_documents({})
    if total_characters == 0:
        await update.message.reply_text("❌ No characters available in the database!")
        return

    random_index = random.randint(0, total_characters - 1)
    random_character = await collection.find().skip(random_index).limit(1).to_list(None)

    if not random_character:
        await update.message.reply_text("❌ Failed to retrieve a character. Try again.")
        return

    character = random_character[0]

    # ✅ Add character to user's collection
    await user_collection.update_one(
        {"id": user_id},
        {
            "$push": {"characters": character},
            "$set": {"last_claim": now.timestamp()},
            "$inc": {"claims": 1}
        },
        upsert=True
    )

    # ✅ Send the character details after the animation
    await update.message.reply_photo(
        photo=character["file_id"],
        caption=f"🎉 **You Claimed:** {character['name']}!\n"
                f"🎖 **Rarity:** {character['rarity']}\n"
                f"🔹 **Category:** {character['category']}\n"
        parse_mode="Markdown"
    )

# ✅ Register Command
application.add_handler(CommandHandler("claim", claim, block=False))
