from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, banners_collection, OWNER_ID, sudo_users
from bson import ObjectId


# ✅ Create a new banner with enhanced UI
async def create_banner(update: Update, context: CallbackContext) -> None:
    """Allows bot owners to create a new summon banner."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 **You don't have permission to create banners!**", parse_mode="Markdown")
        return

    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("❌ **Usage:**\n`/createbanner <name> <file_id>`", parse_mode="Markdown")
            return

        name, file_id = args

        banner = {
            "name": name,
            "file_id": file_id,
            "characters": []  # Stores exclusive characters added to this banner
        }

        banner_doc = await banners_collection.insert_one(banner)
        banner_id = str(banner_doc.inserted_id)  # Convert ObjectId to string

        await update.message.reply_text(
            f"✅ **New Summon Banner Created!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎟 **Banner Name:** `{name}`\n"
            f"🆔 **Banner ID:** `{banner_id}`\n\n"
            f"🔹 **Next Steps:**\n"
            f"➜ Use `/badd` to add characters.\n"
            f"➜ Use `/banners` to view banners.\n\n"
            f"✨ **Good Luck Summoning!** 🎉",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ **Error Creating Banner:** `{str(e)}`", parse_mode="Markdown")


# ✅ List active banners with enhanced UI
async def view_banners(update: Update, context: CallbackContext) -> None:
    """Displays all available summon banners with a professional look."""
    banners = await banners_collection.find({}).to_list(length=None)

    if not banners:
        await update.message.reply_text("❌ **No active banners at the moment!**", parse_mode="Markdown")
        return

    for banner in banners:
        await update.message.reply_photo(
            photo=banner["file_id"],
            caption=(
                f"🎟 **Summon Banner: {banner['name']}**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **Banner ID:** `{banner['_id']}`\n"
                f"📅 **Status:** 🟢 Active\n\n"
                f"🔹 **How to Summon?**\n"
                f"➜ Use `/bsummon {banner['_id']}` to summon characters.\n\n"
                f"✨ **Good Luck Summoning!** 🎉"
            ),
            parse_mode="Markdown"
        )


# ✅ Delete a banner with improved UI
async def delete_banner(update: Update, context: CallbackContext) -> None:
    """Deletes a summon banner."""
    if update.effective_user.id not in sudo_users and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 **You don't have permission to delete banners!**", parse_mode="Markdown")
        return

    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("❌ **Usage:**\n`/deletebanner <banner_id>`", parse_mode="Markdown")
            return

        banner_id = args[0]

        banner = await banners_collection.find_one({"_id": ObjectId(banner_id)})
        if not banner:
            await update.message.reply_text("❌ **Invalid Banner ID!**", parse_mode="Markdown")
            return

        await banners_collection.delete_one({"_id": ObjectId(banner_id)})
        await update.message.reply_text(
            f"✅ **Banner Deleted Successfully!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎟 **Banner Name:** `{banner['name']}`\n"
            f"🆔 **Banner ID:** `{banner_id}`\n\n"
            f"🔹 **Use `/createbanner` to add a new banner!**",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ **Error Deleting Banner:** `{str(e)}`", parse_mode="Markdown")


# ✅ Add Command Handlers
application.add_handler(CommandHandler("createbanner", create_banner, block=False))
application.add_handler(CommandHandler("banners", view_banners, block=False))
application.add_handler(CommandHandler("deletebanner", delete_banner, block=False))
