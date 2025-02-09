from bson import ObjectId
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, banners_collection, db, sudo_users, OWNER_ID

async def get_next_banner_character_id():
    """Generates a unique ID for banner-exclusive characters."""
    sequence_doc = await db.banner_character_sequence.find_one_and_update(
        {"_id": "banner_character_id"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return str(sequence_doc["sequence_value"]).zfill(4)  # ID padded to 4 digits

async def bupload(update: Update, context: CallbackContext) -> None:
    """Uploads an exclusive character to a banner with a unique ID."""
    user_id = update.effective_user.id

    # ✅ Check if user has permission
    if user_id not in sudo_users and user_id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to upload banner characters!")
        return

    try:
        args = context.args
        if len(args) != 5:
            await update.message.reply_text("❌ Usage: `/bupload <banner_id> <image_url> <character_name> <rarity> <category>`")
            return

        banner_id, image_url, character_name, rarity, category = args

        # ✅ Convert banner_id to ObjectId
        try:
            banner_id = ObjectId(banner_id)
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        # ✅ Fetch the banner from the database
        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        # ✅ Define rarity map
        rarity_map = {
            "1": "⚪ Common",
            "2": "🟢 Uncommon",
            "3": "🔵 Rare",
            "4": "🟣 Extreme",
            "5": "🟡 Sparking",
            "6": "🔱 Ultra",
            "7": "💠 Legends Limited",
            "8": "🔮 Zenkai",
            "9": "🏆 Event-Exclusive"
        }

        # ✅ Validate rarity
        if rarity not in rarity_map:
            await update.message.reply_text("❌ Invalid rarity! Use numbers 1-9.")
            return
        rarity = rarity_map[rarity]

        # ✅ Define category map
        category_map = {
            "1": "🏆 Saiyan",
            "2": "🔥 Hybrid Saiyan",
            "3": "🤖 Android",
            "4": "❄️ Frieza Force",
            "5": "✨ God Ki",
            "6": "💪 Super Warrior",
            "7": "🩸 Regeneration",
            "8": "🔀 Fusion Warrior",
            "9": "🤝 Duo",
           "10": "🔱 Super Saiyan God SS",
           "11": "🗿 Ultra Instinct Sign",
           "12": "⚡ Super Saiyan",
           "13": "❤️‍🔥 Dragon Ball Saga",
           "14": "💫 Majin Buu Saga",
           "15": "👾 Cell Saga",
           "16": "📽️ Sagas From the Movies",
           "17": "☠️ Lineage Of Evil"
        }

        # ✅ Validate category
        if category not in category_map:
            await update.message.reply_text("❌ Invalid category! Use numbers 1-9.")
            return
        category = category_map[category]

        # ✅ Generate Unique Character ID
        character_id = await get_next_banner_character_id()

        # ✅ Create character object
        character = {
            "id": character_id,  # Unique ID
            "image_url": image_url,
            "name": character_name.title(),
            "rarity": rarity,
            "category": category,
            "exclusive": True  # Mark as exclusive
        }

        # ✅ Add character to the banner
        await banners_collection.update_one({"_id": banner_id}, {"$push": {"characters": character}})
        await update.message.reply_text(f"✅ `{character_name}` (ID: `{character_id}`) added to `{banner['name']}` banner!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading character: {str(e)}")

async def bdelete(update: Update, context: CallbackContext) -> None:
    """Deletes a character from a banner using its ID and removes it from the character channel."""
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

        # ✅ Find the character within the banner
        characters = banner.get("characters", [])
        character_to_delete = next((c for c in characters if c["id"] == character_id), None)

        if not character_to_delete:
            await update.message.reply_text("❌ No character found with this ID in the banner!")
            return

        # ✅ Remove the character from the banner
        await banners_collection.update_one({"_id": banner_id}, {"$pull": {"characters": {"id": character_id}}})

        # ✅ Try deleting the message from the character channel (if stored)
        if "message_id" in character_to_delete:
            try:
                await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character_to_delete["message_id"])
            except:
                pass  # Ignore if the message was already deleted

        await update.message.reply_text(f"✅ `{character_to_delete['name']}` (ID: `{character_id}`) removed from `{banner['name']}` banner!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting character: {str(e)}")

# ✅ Add Command Handler
application.add_handler(CommandHandler("bdelete", bdelete, block=False))
application.add_handler(CommandHandler("bupload", bupload, block=False))
