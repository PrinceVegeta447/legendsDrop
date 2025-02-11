from bson import ObjectId
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, banners_collection, collection, sudo_users, OWNER_ID, CHARA_CHANNEL_ID

async def badd(update: Update, context: CallbackContext) -> None:
    """Moves a single character to a banner."""
    user_id = update.effective_user.id
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to add characters to banners!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Usage: `/badd <banner_id> <character_id>`", parse_mode="Markdown")
            return

        banner_id, character_id = args
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        character = await collection.find_one({"id": character_id})
        if not character:
            await update.message.reply_text("❌ No character found with this ID in the main collection!")
            return

        if any(c["id"] == character_id for c in banner.get("characters", [])):
            await update.message.reply_text(f"⚠️ `{character['name']}` is already in `{banner['name']}`!")
            return

        await banners_collection.update_one({"_id": banner_id}, {"$push": {"characters": character}})

        await update.message.reply_text(f"✅ `{character['name']}` added to `{banner['name']}` banner!", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")

async def baddall(update: Update, context: CallbackContext) -> None:
    """Adds all available characters from the database to a banner."""
    user_id = update.effective_user.id
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to add characters to banners!")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Usage: `/baddall <banner_id>`", parse_mode="Markdown")
            return

        banner_id = args[0]
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        all_characters = await collection.find().to_list(length=None)
        if not all_characters:
            await update.message.reply_text("❌ No characters found in the database!")
            return

        await banners_collection.update_one({"_id": banner_id}, {"$set": {"characters": all_characters}})

        await update.message.reply_text(f"✅ **{len(all_characters)} characters added to `{banner['name']}` banner!**", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")

async def baddrarity(update: Update, context: CallbackContext) -> None:
    """Adds all characters of a specific rarity to a banner."""
    user_id = update.effective_user.id
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to add characters to banners!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Usage: `/baddrarity <banner_id> <rarity>`", parse_mode="Markdown")
            return

        banner_id, rarity = args
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        rarity = rarity.lower()
        valid_rarities = ["common", "uncommon", "rare", "extreme", "sparking", "ultra"]
        if rarity not in valid_rarities:
            await update.message.reply_text(f"❌ Invalid rarity! Choose from: `{', '.join(valid_rarities)}`", parse_mode="Markdown")
            return

        rarity_characters = await collection.find({"rarity": rarity}).to_list(length=None)
        if not rarity_characters:
            await update.message.reply_text(f"❌ No `{rarity}` characters found in the database!")
            return

        await banners_collection.update_one({"_id": banner_id}, {"$push": {"characters": {"$each": rarity_characters}}})

        await update.message.reply_text(f"✅ **{len(rarity_characters)} `{rarity}` characters added to `{banner['name']}` banner!**", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")

async def bdelete(update: Update, context: CallbackContext) -> None:
    """Removes a character from a banner."""
    user_id = update.effective_user.id
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to delete banner characters!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Usage: `/bdelete <banner_id> <character_id>`", parse_mode="Markdown")
            return

        banner_id, character_id = args
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        characters = banner.get("characters", [])
        character_to_delete = next((c for c in characters if c["id"] == character_id), None)
        if not character_to_delete:
            await update.message.reply_text("❌ No character found with this ID in the banner!")
            return

        await banners_collection.update_one({"_id": banner_id}, {"$pull": {"characters": {"id": character_id}}})

        await update.message.reply_text(f"✅ `{character_to_delete['name']}` removed from `{banner['name']}` banner!", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")

# ✅ **Command Handlers**
application.add_handler(CommandHandler("badd", badd, block=False))
application.add_handler(CommandHandler("baddall", baddall, block=False))
application.add_handler(CommandHandler("baddrarity", baddrarity, block=False))
application.add_handler(CommandHandler("bdelete", bdelete, block=False))
