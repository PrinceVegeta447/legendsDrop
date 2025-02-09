from bson import ObjectId
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, banners_collection, collection, sudo_users, OWNER_ID, CHARA_CHANNEL_ID


async def badd(update: Update, context: CallbackContext) -> None:
    """Moves a normal character (from /upload) to a banner & logs it."""
    user_id = update.effective_user.id

    # ✅ Permission check
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to add characters to banners!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Usage: `/badd <banner_id> <character_id>`")
            return

        banner_id, character_id = args

        # ✅ Convert banner_id to ObjectId
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        # ✅ Fetch the banner
        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        banner_name = banner.get("name", "Unknown Banner")  # ✅ Ensure correct banner name

        # ✅ Fetch the character from normal collection
        character = await collection.find_one({"id": character_id})
        if not character:
            await update.message.reply_text("❌ No character found with this ID in the main collection!")
            return

        # ✅ Prevent duplicate characters in the banner
        if any(c["id"] == character_id for c in banner.get("characters", [])):
            await update.message.reply_text(f"⚠️ `{character['name']}` is already in `{banner_name}`!")
            return

        # ✅ Add the character to the banner
        await banners_collection.update_one(
            {"_id": banner_id}, 
            {"$push": {"characters": character}}
        )

        await update.message.reply_text(f"✅ `{character['name']}` added to `{banner_name}` banner!")

        # ✅ Log upload in log channel
        log_message = (
            f"📢 **Character Added to Banner** 📢\n\n"
            f"🔹 **Banner:** `{banner_name}`\n"
            f"🔸 **Character:** `{character['name']}`\n"
            f"🎖 **Rarity:** `{character['rarity']}`\n"
            f"🔹 **Category:** `{character['category']}`\n"
            f"📸 **Uploaded By:** [{update.effective_user.first_name}](tg://user?id={user_id})"
        )

        await context.bot.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=character["file_id"],
            caption=log_message,
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error adding character to banner: {str(e)}")

async def bdelete(update: Update, context: CallbackContext) -> None:
    """Removes a character from a banner using its ID."""
    user_id = update.effective_user.id

    # ✅ Check if the user has permission
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to delete banner characters!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Usage: `/bdelete <banner_id> <character_id>`")
            return

        banner_id, character_id = args

        # ✅ Convert banner_id to ObjectId
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        # ✅ Fetch the banner
        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        banner_name = banner.get("name", "Unknown Banner")  # ✅ Ensure correct banner name

        # ✅ Check if the character exists in the banner
        characters = banner.get("characters", [])
        character_to_delete = next((c for c in characters if c["id"] == character_id), None)

        if not character_to_delete:
            await update.message.reply_text("❌ No character found with this ID in the banner!")
            return

        # ✅ Remove the character from the banner
        await banners_collection.update_one(
            {"_id": banner_id}, 
            {"$pull": {"characters": {"id": character_id}}}
        )

        await update.message.reply_text(f"✅ `{character_to_delete['name']}` removed from `{banner_name}` banner!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting character: {str(e)}")

# ✅ Add Command Handlers
application.add_handler(CommandHandler("badd", badd, block=False))
application.add_handler(CommandHandler("bdelete", bdelete, block=False))
