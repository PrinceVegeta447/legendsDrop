from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, user_collection

# 💰 **Balanced Sell Prices**
SELL_PRICES = {
    "⚪ Common": 5000,
    "🟢 Uncommon": 10000,
    "🔵 Rare": 20000,
    "🟣 Extreme": 40000,
    "🟡 Sparking": 80000,
    "🔱 Ultra": 200000
}

async def sell_character(update: Update, context: CallbackContext) -> None:
    """Allows users to sell a character to the bot for Zeni."""
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("❌ **Usage:** `/sell <character_id>`\n📌 Example: `/sell 007`", parse_mode="Markdown")
        return

    char_id = context.args[0]

    # ✅ Fetch User Data
    user = await user_collection.find_one({"id": user_id}) or {}
    user_characters = user.get("characters", [])

    # ✅ Find Character in User's Collection
    character = next((c for c in user_characters if c["id"] == char_id), None)
    if not character:
        await update.message.reply_text("❌ **You don't own this character!**", parse_mode="Markdown")
        return

    rarity = character["rarity"]
    price = SELL_PRICES.get(rarity, 0)

    # ✅ Check if Price is Defined
    if price == 0:
        await update.message.reply_text("❌ **This character cannot be sold!**", parse_mode="Markdown")
        return

    # ✅ Remove Character from Collection & Add Zeni
    await user_collection.update_one(
        {"id": user_id},
        {"$pull": {"characters": {"id": char_id}}, "$inc": {"coins": price}}
    )

    # ✅ Confirm Sale
    await update.message.reply_text(
        f"✅ **Character Sold!**\n"
        f"🎴 **{character['name']}** ({rarity})\n"
        f"💰 **Received:** {price} Zeni\n"
        f"🔹 Your Zeni balance has been updated.",
        parse_mode="Markdown"
    )

# ✅ **Register Handler**
application.add_handler(CommandHandler("csell", sell_character, block=False))
