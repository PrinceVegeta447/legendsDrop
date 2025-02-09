from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, banners_collection, OWNER_ID, sudo_users
from bson import ObjectId


# ✅ Create a new banner
async def create_banner(update: Update, context: CallbackContext) -> None:
    """Allows bot owners to create a new summon banner."""
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
            "characters": []  # Stores exclusive characters added to this banner
        }

        banner_doc = await banners_collection.insert_one(banner)
        banner_id = str(banner_doc.inserted_id)  # Convert ObjectId to string

        await update.message.reply_text(f"✅ Banner `{name}` created successfully!\n🆔 **Banner ID:** `{banner_id}`")
    except Exception as e:
        await update.message.reply_text(f"❌ Error creating banner: {str(e)}")


# ✅ List active banners
async def view_banners(update: Update, context: CallbackContext) -> None:
    """Displays all available summon banners."""
    banners = await banners_collection.find({}).to_list(length=None)

    if not banners:
        await update.message.reply_text("❌ No active banners at the moment!")
        return

    for banner in banners:
        keyboard = [
            [InlineKeyboardButton("🎟 Summon", callback_data=f"summon_banner:{banner['_id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_photo(
            photo=banner["image_url"],
            caption=f"🎟 **{banner['name']}**\n🆔 `{banner['_id']}`",
            parse_mode="Markdown", 
            reply_markup=reply_markup
        )


# ✅ Delete a banner
async def delete_banner(update: Update, context: CallbackContext) -> None:
    """Deletes a summon banner."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 You don't have permission to delete banners!")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ Usage: `/deletebanner <banner_id>`")
            return

        banner_id = args[0]

        banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})
        if not banner:
            await update.message.reply_text("❌ Invalid Banner ID!")
            return

        await banners_collection.delete_one({"_id": ObjectId(banner_id)})
        await update.message.reply_text(f"✅ Banner `{banner['name']}` deleted successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting banner: {str(e)}")


# ✅ Add Command Handlers
application.add_handler(CommandHandler("createbanner", create_banner, block=False))
application.add_handler(CommandHandler("banners", view_banners, block=False))
application.add_handler(CommandHandler("deletebanner", delete_banner, block=False))
