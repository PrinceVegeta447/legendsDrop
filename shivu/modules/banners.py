import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, banners_collection, user_collection, OWNER_ID, sudo_users
from bson import ObjectId

# ✅ Function to create a new banner
async def create_banner(update: Update, context: CallbackContext) -> None:
    """Allows bot owners to create new banners."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to create banners!")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ Usage: `/createbanner <name> <image_url>`")
            return

        name, image_url = args

        banner = {
            "name": name,
            "image_url": image_url,
            "characters": []
        }

        banner_doc = await banners_collection.insert_one(banner)
        banner_id = banner_doc.inserted_id

        await update.message.reply_text(f"✅ Banner `{name}` created successfully!\n🆔 Banner ID: `{banner_id}`")
    except Exception as e:
        await update.message.reply_text(f"❌ Error creating banner: {str(e)}")

# ✅ Function to upload a character to a banner
  # Import this at the top

async def banner_upload(update: Update, context: CallbackContext) -> None:
    """Uploads a character to a banner (Exclusive Characters)."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
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
            banner_id = ObjectId(banner_id)  # Convert string ID to ObjectId
        except:
            await update.message.reply_text("❌ Invalid Banner ID format!")
            return

        # ✅ Fetch the banner from the database
        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ No banner found with this ID!")
            return

        # ✅ Create character object
        character = {
            "image_url": image_url,
            "name": character_name,
            "rarity": rarity,
            "category": category
        }

        # ✅ Add character to the banner
        await banners_collection.update_one({"_id": banner_id}, {"$push": {"characters": character}})
        await update.message.reply_text(f"✅ Character `{character_name}` added to `{banner['name']}` banner!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error uploading character: {str(e)}")

# ✅ Function to display banners
async def view_banners(update: Update, context: CallbackContext) -> None:
    """Shows all available banners."""
    banners = await banners_collection.find({}).to_list(length=None)

    if not banners:
        await update.message.reply_text("❌ No active banners!")
        return

    for banner in banners:
        keyboard = [
            [InlineKeyboardButton("🎟 Summon", callback_data=f"summon:{banner['_id']}")],
            [InlineKeyboardButton("🔍 View Characters", callback_data=f"view:{banner['_id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_photo(photo=banner["image_url"],
                                         caption=f"🎟 **{banner['name']}**",
                                         parse_mode="Markdown", reply_markup=reply_markup)

# ✅ Function to delete a banner
async def delete_banner(update: Update, context: CallbackContext) -> None:
    """Deletes a banner and removes all its characters."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to delete banners!")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Usage: `/deletebanner <banner_id>`")
            return

        banner_id = args[0]

        banner = await banners_collection.find_one({"_id": banner_id})
        if not banner:
            await update.message.reply_text("❌ Invalid Banner ID!")
            return

        await banners_collection.delete_one({"_id": banner_id})
        await update.message.reply_text(f"✅ Banner `{banner['name']}` deleted successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting banner: {str(e)}")

# ✅ Add Handlers
application.add_handler(CommandHandler("createbanner", create_banner))
application.add_handler(CommandHandler("bupload", banner_upload))
application.add_handler(CommandHandler("banners", view_banners))
application.add_handler(CommandHandler("deletebanner", delete_banner))
